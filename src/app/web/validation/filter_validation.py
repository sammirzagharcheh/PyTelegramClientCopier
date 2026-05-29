"""Shared mapping filter validation and helpers."""

from __future__ import annotations

import re

from fastapi import HTTPException, status

from app.services.mapping_service import MappingFilter

_FILTER_REGEX_CACHE: dict[str, re.Pattern[str] | None] = {}
_FILTER_REGEX_CACHE_MAX = 256


def filter_has_criteria(
    *,
    include_text: str | None = None,
    exclude_text: str | None = None,
    media_types: str | None = None,
    regex_pattern: str | None = None,
    allowed_sender_ids: str | None = None,
    denied_usernames: str | None = None,
    min_url_count: int | None = None,
    max_url_count: int | None = None,
    required_hashtags: str | None = None,
) -> bool:
    if include_text and include_text.strip():
        return True
    if exclude_text and exclude_text.strip():
        return True
    if media_types and media_types.strip():
        return True
    if regex_pattern and regex_pattern.strip():
        return True
    if allowed_sender_ids and allowed_sender_ids.strip():
        return True
    if denied_usernames and denied_usernames.strip():
        return True
    if min_url_count is not None:
        return True
    if max_url_count is not None:
        return True
    if required_hashtags and required_hashtags.strip():
        return True
    return False


def mapping_filter_has_criteria(filter_rule: MappingFilter) -> bool:
    return filter_has_criteria(
        include_text=filter_rule.include_text,
        exclude_text=filter_rule.exclude_text,
        media_types=filter_rule.media_types,
        regex_pattern=filter_rule.regex_pattern,
        allowed_sender_ids=filter_rule.allowed_sender_ids,
        denied_usernames=filter_rule.denied_usernames,
        min_url_count=filter_rule.min_url_count,
        max_url_count=filter_rule.max_url_count,
        required_hashtags=filter_rule.required_hashtags,
    )


def validate_filter_regex(pattern: str | None) -> None:
    if not pattern or not pattern.strip():
        return
    try:
        re.compile(pattern)
    except re.error as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid regex pattern: {exc}",
        ) from exc


def validate_filter_url_bounds(
    min_url_count: int | None,
    max_url_count: int | None,
) -> None:
    for label, value in (("min_url_count", min_url_count), ("max_url_count", max_url_count)):
        if value is not None and value < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{label} must be non-negative",
            )
    if (
        min_url_count is not None
        and max_url_count is not None
        and min_url_count > max_url_count
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="min_url_count cannot be greater than max_url_count",
        )


def validate_filter_payload(
    *,
    include_text: str | None = None,
    exclude_text: str | None = None,
    media_types: str | None = None,
    regex_pattern: str | None = None,
    allowed_sender_ids: str | None = None,
    denied_usernames: str | None = None,
    min_url_count: int | None = None,
    max_url_count: int | None = None,
    required_hashtags: str | None = None,
) -> None:
    validate_filter_regex(regex_pattern)
    validate_filter_url_bounds(min_url_count, max_url_count)
    if not filter_has_criteria(
        include_text=include_text,
        exclude_text=exclude_text,
        media_types=media_types,
        regex_pattern=regex_pattern,
        allowed_sender_ids=allowed_sender_ids,
        denied_usernames=denied_usernames,
        min_url_count=min_url_count,
        max_url_count=max_url_count,
        required_hashtags=required_hashtags,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one filter rule is required",
        )


def compile_filter_regex(pattern: str) -> re.Pattern[str] | None:
    """Compile and cache filter regex patterns; None if invalid."""
    cached = _FILTER_REGEX_CACHE.get(pattern)
    if cached is not None or pattern in _FILTER_REGEX_CACHE:
        return cached
    try:
        compiled = re.compile(pattern)
    except re.error:
        compiled = None
    if len(_FILTER_REGEX_CACHE) >= _FILTER_REGEX_CACHE_MAX:
        _FILTER_REGEX_CACHE.clear()
    _FILTER_REGEX_CACHE[pattern] = compiled
    return compiled


def clear_filter_regex_cache() -> None:
    _FILTER_REGEX_CACHE.clear()


def hashtag_present(text: str, raw_tag: str) -> bool:
    """True when `raw_tag` appears as a whole hashtag (not a prefix of another tag)."""
    tag = raw_tag.strip().lower()
    if not tag:
        return True
    if not tag.startswith("#"):
        tag = "#" + tag
    body = tag[1:]
    if not body:
        return False
    pattern = re.compile(rf"(?<![\w#]){re.escape(tag)}(?![\w])", re.IGNORECASE)
    return bool(pattern.search(text))
