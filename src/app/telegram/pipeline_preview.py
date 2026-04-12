"""Pure filter/schedule/transform evaluation for workers and preview API."""

from __future__ import annotations

import datetime
import logging
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Iterable

from app.services.mapping_service import MappingFilter, MappingTransform, Schedule

if TYPE_CHECKING:
    from telethon.tl.custom.message import Message as TLMessage
from app.utils.regex import regex_flags_from_string

logger = logging.getLogger(__name__)
_TEMPLATE_TOKEN_RE = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")
_URL_RE = re.compile(r"https?://[^\s]+", re.IGNORECASE)


def media_type_for_telethon_message(message: Any) -> str:
    """Classify Telethon Message media (same rules as legacy worker handler)."""
    if getattr(message, "voice", None):
        return "voice"
    if getattr(message, "video", None):
        return "video"
    if getattr(message, "photo", None):
        return "photo"
    if getattr(message, "message", None) or getattr(message, "text", None):
        return "text"
    return "other"


@dataclass(frozen=True, slots=True)
class MessagePreview:
    """Minimal message shape for filter/transform preview (no Telethon)."""

    text: str
    media_type: str
    sender_id: int | None = None
    sender_username: str | None = None


def passes_schedule(now_utc: datetime.datetime, schedule: Schedule | None) -> bool:
    if schedule is None or schedule.is_empty():
        return True
    weekday = now_utc.weekday()
    start_utc, end_utc = schedule.get_for_weekday(weekday)
    if start_utc is None and end_utc is None:
        return True
    try:
        now_t = now_utc.time()
        start_t = datetime.datetime.strptime(start_utc or "00:00", "%H:%M").time()
        end_t = datetime.datetime.strptime(end_utc or "23:59", "%H:%M").time()
    except (ValueError, TypeError):
        return True
    if start_utc is None:
        return now_t <= end_t
    if end_utc is None:
        return now_t >= start_t
    if start_t <= end_t:
        return start_t <= now_t <= end_t
    return now_t >= start_t or now_t <= end_t


def _url_count(text: str) -> int:
    return len(_URL_RE.findall(text or ""))


def single_filter_matches(
    preview: MessagePreview,
    filter_rule: MappingFilter,
    *,
    text: str,
    media_type: str,
) -> bool:
    if filter_rule.media_types:
        allowed = {
            part.strip().lower()
            for part in filter_rule.media_types.split(",")
            if part.strip()
        }
        if allowed and media_type not in allowed:
            return False
    if filter_rule.include_text and filter_rule.include_text not in text:
        return False
    if filter_rule.exclude_text and filter_rule.exclude_text in text:
        return False
    if filter_rule.regex_pattern and not re.search(filter_rule.regex_pattern, text):
        return False
    if filter_rule.allowed_sender_ids and filter_rule.allowed_sender_ids.strip():
        allowed: set[int] = set()
        for x in filter_rule.allowed_sender_ids.split(","):
            x = x.strip()
            if not x:
                continue
            try:
                allowed.add(int(x))
            except ValueError:
                continue
        if allowed and (preview.sender_id is None or preview.sender_id not in allowed):
            return False
    if filter_rule.denied_usernames and filter_rule.denied_usernames.strip():
        denied = {u.strip().lower().lstrip("@") for u in filter_rule.denied_usernames.split(",") if u.strip()}
        su = (preview.sender_username or "").lower().lstrip("@")
        if su and su in denied:
            return False
    n_urls = _url_count(text)
    if filter_rule.min_url_count is not None and n_urls < filter_rule.min_url_count:
        return False
    if filter_rule.max_url_count is not None and n_urls > filter_rule.max_url_count:
        return False
    if filter_rule.required_hashtags and filter_rule.required_hashtags.strip():
        lower = text.lower()
        for tag in filter_rule.required_hashtags.split(","):
            t = tag.strip().lower()
            if not t:
                continue
            if not t.startswith("#"):
                t = "#" + t
            if t not in lower:
                return False
    return True


def passes_filters(preview: MessagePreview, filters: Iterable[MappingFilter]) -> bool:
    filter_list = list(filters)
    if not filter_list:
        return True
    text = preview.text or ""
    media_type = preview.media_type
    by_group: dict[int, list[MappingFilter]] = defaultdict(list)
    for f in filter_list:
        by_group[f.or_group_id].append(f)
    for gid in sorted(by_group.keys()):
        group_filters = by_group[gid]
        if not any(
            single_filter_matches(preview, fr, text=text, media_type=media_type)
            for fr in group_filters
        ):
            return False
    return True


def rule_applies_to_media_type(rule: MappingTransform, media_type: str) -> bool:
    if not rule.apply_to_media_types:
        return True
    allowed = {
        p.strip().lower()
        for p in rule.apply_to_media_types.split(",")
        if p.strip()
    }
    if not allowed:
        return True
    return media_type in allowed or "any" in allowed or "*" in allowed or "all" in allowed


def render_template(template: str, context: dict[str, object]) -> str:
    def _sub(match: re.Match[str]) -> str:
        key = match.group(1)
        value = context.get(key, "")
        if value is None:
            return ""
        return str(value)

    return _TEMPLATE_TOKEN_RE.sub(_sub, template)


def apply_transforms(
    text: str,
    transforms: Iterable[MappingTransform],
    *,
    context: dict[str, object] | None = None,
    media_type: str = "text",
) -> str:
    if not transforms:
        return text
    output = text
    for rule in transforms:
        if not rule.enabled:
            continue
        if rule.rule_type == "media":
            continue
        if not rule_applies_to_media_type(rule, media_type):
            continue
        if rule.rule_type in {"text", "emoji"}:
            if rule.find_text:
                output = output.replace(rule.find_text, rule.replace_text or "")
            continue
        if rule.rule_type == "regex" and rule.regex_pattern:
            try:
                output = re.sub(
                    rule.regex_pattern,
                    rule.replace_text or "",
                    output,
                    flags=regex_flags_from_string(rule.regex_flags),
                )
            except re.error:
                logger.warning(
                    "Invalid regex transform skipped: rule_id=%s pattern=%r",
                    rule.id,
                    rule.regex_pattern,
                )
            continue
        if rule.rule_type == "template":
            template_context = dict(context or {})
            template_context["text"] = output
            output = render_template(rule.replace_text or "", template_context)
    return output
