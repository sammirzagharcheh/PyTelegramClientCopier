"""Mapping transforms API routes (text/regex/emoji/media/template replacements)."""

from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException, status

from app.utils.regex import regex_flags_from_string
from app.web.deps import CurrentUser, Db
from app.web.routers.workers import restart_workers_for_mapping
from app.web.schemas.mappings import (
    MappingTransformCreate,
    MappingTransformResponse,
    MappingTransformUpdate,
)

router = APIRouter(prefix="/mappings", tags=["transforms"])

_ALLOWED_RULE_TYPES = {"text", "regex", "emoji", "media", "template"}
_ALLOWED_REGEX_FLAGS = {"i", "m", "s"}
_ALLOWED_MEDIA_TYPES = {"text", "photo", "video", "voice", "other", "any", "all", "*"}


def _normalize_rule_type(value: str) -> str:
    return value.strip().lower()


def _normalize_regex_flags(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = "".join(ch for ch in value.lower() if not ch.isspace())
    if any(ch not in _ALLOWED_REGEX_FLAGS for ch in cleaned):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="regex_flags may only contain i, m, s",
        )
    # Keep flags deterministic and unique for storage.
    ordered = "".join(ch for ch in "ims" if ch in cleaned)
    return ordered or None


def _normalize_apply_to_media_types(value: str | None) -> str | None:
    if value is None:
        return None
    parts = [p.strip().lower() for p in value.split(",") if p.strip()]
    if not parts:
        return None
    if any(p not in _ALLOWED_MEDIA_TYPES for p in parts):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="apply_to_media_types may only contain text, photo, video, voice, other, any",
        )
    # deterministic order and uniqueness
    deduped: list[str] = []
    for p in ["text", "photo", "video", "voice", "other", "any", "all", "*"]:
        if p in parts and p not in deduped:
            deduped.append(p)
    return ",".join(deduped)


def _validate_transform_payload(
    *,
    rule_type: str,
    find_text: str | None,
    replace_text: str | None,
    regex_pattern: str | None,
    regex_flags: str | None,
    replacement_media_asset_id: int | None,
    apply_to_media_types: str | None,
) -> tuple[str | None, str | None, str | None, int | None, str | None]:
    if rule_type not in _ALLOWED_RULE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="rule_type must be one of: text, regex, emoji, media, template",
        )
    if rule_type in {"text", "emoji"}:
        if find_text is None or find_text == "":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="find_text is required for text/emoji rules",
            )
        if replacement_media_asset_id is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="replacement_media_asset_id is only valid for media rules",
            )
        return find_text, None, None, None, apply_to_media_types

    if rule_type == "regex":
        if not regex_pattern:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="regex_pattern is required for regex rules",
            )
        try:
            re.compile(regex_pattern, flags=regex_flags_from_string(regex_flags))
        except re.error as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid regex pattern: {e}",
            ) from e
        if replacement_media_asset_id is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="replacement_media_asset_id is only valid for media rules",
            )
        return None, regex_pattern, regex_flags, None, apply_to_media_types

    if rule_type == "template":
        if replace_text is None or replace_text == "":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="replace_text is required for template rules",
            )
        if replacement_media_asset_id is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="replacement_media_asset_id is only valid for media rules",
            )
        return None, None, None, None, apply_to_media_types

    # media replacement rule
    if replacement_media_asset_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="replacement_media_asset_id is required for media rules",
        )
    return None, None, None, replacement_media_asset_id, apply_to_media_types


async def _get_mapping_scope(db: Db, user: dict, mapping_id: int) -> tuple[int, int | None]:
    async with db.execute(
        "SELECT user_id, telegram_account_id FROM channel_mappings WHERE id = ?",
        (mapping_id,),
    ) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapping not found")
    if user["role"] != "admin" and row[0] != user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return int(row[0]), row[1]


async def _validate_media_asset_for_mapping(
    db: Db,
    *,
    mapping_user_id: int,
    replacement_media_asset_id: int,
) -> None:
    async with db.execute(
        "SELECT user_id FROM media_assets WHERE id = ?",
        (replacement_media_asset_id,),
    ) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="replacement_media_asset_id does not exist",
        )
    if int(row[0]) != int(mapping_user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="replacement media asset must belong to mapping owner",
        )


def _row_to_response(row: tuple) -> dict:
    return {
        "id": row[0],
        "mapping_id": row[1],
        "rule_type": row[2],
        "find_text": row[3],
        "replace_text": row[4],
        "regex_pattern": row[5],
        "regex_flags": row[6],
        "replacement_media_asset_id": row[7],
        "apply_to_media_types": row[8],
        "enabled": bool(row[9]),
        "priority": row[10],
        "created_at": row[11],
    }


@router.get("/{mapping_id}/transforms", response_model=list[MappingTransformResponse])
async def list_transforms(mapping_id: int, db: Db, user: CurrentUser) -> list[dict]:
    """List text/regex/emoji/media/template transformation rules for a mapping."""
    await _get_mapping_scope(db, user, mapping_id)
    async with db.execute(
        "SELECT id, mapping_id, rule_type, find_text, replace_text, regex_pattern, regex_flags, "
        "replacement_media_asset_id, apply_to_media_types, enabled, priority, created_at "
        "FROM mapping_transform_rules WHERE mapping_id = ? "
        "ORDER BY priority ASC, id ASC",
        (mapping_id,),
    ) as cur:
        rows = await cur.fetchall()
    return [_row_to_response(r) for r in rows]


@router.post(
    "/{mapping_id}/transforms",
    response_model=MappingTransformResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_transform(
    mapping_id: int,
    data: MappingTransformCreate,
    db: Db,
    user: CurrentUser,
) -> dict:
    """Create a transformation rule for a mapping."""
    mapping_user_id, mapping_account_id = await _get_mapping_scope(db, user, mapping_id)
    rule_type = _normalize_rule_type(data.rule_type)
    regex_flags = _normalize_regex_flags(data.regex_flags)
    apply_to_media_types = _normalize_apply_to_media_types(data.apply_to_media_types)
    (
        find_text,
        regex_pattern,
        regex_flags,
        replacement_media_asset_id,
        apply_to_media_types,
    ) = _validate_transform_payload(
        rule_type=rule_type,
        find_text=data.find_text,
        replace_text=data.replace_text,
        regex_pattern=data.regex_pattern,
        regex_flags=regex_flags,
        replacement_media_asset_id=data.replacement_media_asset_id,
        apply_to_media_types=apply_to_media_types,
    )
    if replacement_media_asset_id is not None:
        await _validate_media_asset_for_mapping(
            db,
            mapping_user_id=mapping_user_id,
            replacement_media_asset_id=replacement_media_asset_id,
        )

    cursor = await db.execute(
        "INSERT INTO mapping_transform_rules "
        "(mapping_id, rule_type, find_text, replace_text, regex_pattern, regex_flags, "
        "replacement_media_asset_id, apply_to_media_types, enabled, priority) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            mapping_id,
            rule_type,
            find_text,
            data.replace_text,
            regex_pattern,
            regex_flags,
            replacement_media_asset_id,
            apply_to_media_types,
            1 if data.enabled else 0,
            data.priority,
        ),
    )
    await db.commit()
    transform_id = cursor.lastrowid

    async with db.execute(
        "SELECT id, mapping_id, rule_type, find_text, replace_text, regex_pattern, regex_flags, "
        "replacement_media_asset_id, apply_to_media_types, enabled, priority, created_at "
        "FROM mapping_transform_rules WHERE id = ?",
        (transform_id,),
    ) as cur:
        row = await cur.fetchone()

    try:
        await restart_workers_for_mapping(db, mapping_user_id, mapping_account_id)
    except Exception:
        pass
    return _row_to_response(row)


@router.patch("/{mapping_id}/transforms/{transform_id}", response_model=MappingTransformResponse)
async def update_transform(
    mapping_id: int,
    transform_id: int,
    data: MappingTransformUpdate,
    db: Db,
    user: CurrentUser,
) -> dict:
    """Update a transformation rule."""
    mapping_user_id, mapping_account_id = await _get_mapping_scope(db, user, mapping_id)
    async with db.execute(
        "SELECT id, mapping_id, rule_type, find_text, replace_text, regex_pattern, regex_flags, "
        "replacement_media_asset_id, apply_to_media_types, enabled, priority, created_at "
        "FROM mapping_transform_rules WHERE id = ? AND mapping_id = ?",
        (transform_id, mapping_id),
    ) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transform not found")

    patch = data.model_dump(exclude_unset=True)
    if patch:
        merged = {
            "rule_type": patch.get("rule_type", row[2]),
            "find_text": patch.get("find_text", row[3]),
            "replace_text": patch.get("replace_text", row[4]),
            "regex_pattern": patch.get("regex_pattern", row[5]),
            "regex_flags": patch.get("regex_flags", row[6]),
            "replacement_media_asset_id": patch.get("replacement_media_asset_id", row[7]),
            "apply_to_media_types": patch.get("apply_to_media_types", row[8]),
            "enabled": patch.get("enabled", bool(row[9])),
            "priority": patch.get("priority", row[10]),
        }
        merged["rule_type"] = _normalize_rule_type(merged["rule_type"])
        # When switching from media to any other rule type, the frontend omits
        # replacement_media_asset_id. Clear it so validation doesn't reject with 400.
        if merged["rule_type"] != "media":
            merged["replacement_media_asset_id"] = None
        # When switching from media/template to text/emoji/regex, the frontend omits
        # apply_to_media_types. Clear it so the rule applies to all media types.
        # Otherwise _rule_applies_to_media_type would restrict application to the
        # old value (e.g. only photo captions) with no UI indication.
        if merged["rule_type"] in {"text", "emoji", "regex"}:
            merged["apply_to_media_types"] = None
        normalized_flags = _normalize_regex_flags(merged["regex_flags"])
        normalized_media_types = _normalize_apply_to_media_types(
            merged["apply_to_media_types"]
        )
        (
            find_text,
            regex_pattern,
            regex_flags,
            replacement_media_asset_id,
            apply_to_media_types,
        ) = _validate_transform_payload(
            rule_type=merged["rule_type"],
            find_text=merged["find_text"],
            replace_text=merged["replace_text"],
            regex_pattern=merged["regex_pattern"],
            regex_flags=normalized_flags,
            replacement_media_asset_id=merged["replacement_media_asset_id"],
            apply_to_media_types=normalized_media_types,
        )
        if replacement_media_asset_id is not None:
            await _validate_media_asset_for_mapping(
                db,
                mapping_user_id=mapping_user_id,
                replacement_media_asset_id=replacement_media_asset_id,
            )

        await db.execute(
            "UPDATE mapping_transform_rules SET "
            "rule_type = ?, find_text = ?, replace_text = ?, regex_pattern = ?, regex_flags = ?, "
            "replacement_media_asset_id = ?, apply_to_media_types = ?, enabled = ?, priority = ? "
            "WHERE id = ?",
            (
                merged["rule_type"],
                find_text,
                merged["replace_text"],
                regex_pattern,
                regex_flags,
                replacement_media_asset_id,
                apply_to_media_types,
                1 if merged["enabled"] else 0,
                merged["priority"],
                transform_id,
            ),
        )
        await db.commit()
        try:
            await restart_workers_for_mapping(db, mapping_user_id, mapping_account_id)
        except Exception:
            pass

    async with db.execute(
        "SELECT id, mapping_id, rule_type, find_text, replace_text, regex_pattern, regex_flags, "
        "replacement_media_asset_id, apply_to_media_types, enabled, priority, created_at "
        "FROM mapping_transform_rules WHERE id = ?",
        (transform_id,),
    ) as cur:
        updated = await cur.fetchone()
    return _row_to_response(updated)


@router.delete("/{mapping_id}/transforms/{transform_id}")
async def delete_transform(mapping_id: int, transform_id: int, db: Db, user: CurrentUser) -> dict:
    """Delete a transformation rule."""
    mapping_user_id, mapping_account_id = await _get_mapping_scope(db, user, mapping_id)
    result = await db.execute(
        "DELETE FROM mapping_transform_rules WHERE id = ? AND mapping_id = ?",
        (transform_id, mapping_id),
    )
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transform not found")
    try:
        await restart_workers_for_mapping(db, mapping_user_id, mapping_account_id)
    except Exception:
        pass
    return {"status": "ok"}
