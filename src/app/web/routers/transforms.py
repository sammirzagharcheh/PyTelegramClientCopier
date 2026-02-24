"""Mapping transforms API routes (text/regex/emoji replacements)."""

from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException, status

from app.web.deps import CurrentUser, Db
from app.web.routers.workers import restart_workers_for_mapping
from app.web.schemas.mappings import (
    MappingTransformCreate,
    MappingTransformResponse,
    MappingTransformUpdate,
)

router = APIRouter(prefix="/mappings", tags=["transforms"])

_ALLOWED_RULE_TYPES = {"text", "regex", "emoji"}
_ALLOWED_REGEX_FLAGS = {"i", "m", "s"}


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


def _regex_flags_value(flag_string: str | None) -> int:
    flags = 0
    if not flag_string:
        return flags
    if "i" in flag_string:
        flags |= re.IGNORECASE
    if "m" in flag_string:
        flags |= re.MULTILINE
    if "s" in flag_string:
        flags |= re.DOTALL
    return flags


def _validate_transform_payload(
    *,
    rule_type: str,
    find_text: str | None,
    regex_pattern: str | None,
    regex_flags: str | None,
) -> tuple[str | None, str | None, str | None]:
    if rule_type not in _ALLOWED_RULE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="rule_type must be one of: text, regex, emoji",
        )
    if rule_type in {"text", "emoji"}:
        if find_text is None or find_text == "":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="find_text is required for text/emoji rules",
            )
        return find_text, None, None

    if not regex_pattern:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="regex_pattern is required for regex rules",
        )
    try:
        re.compile(regex_pattern, flags=_regex_flags_value(regex_flags))
    except re.error as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid regex pattern: {e}",
        ) from e
    return None, regex_pattern, regex_flags


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


def _row_to_response(row: tuple) -> dict:
    return {
        "id": row[0],
        "mapping_id": row[1],
        "rule_type": row[2],
        "find_text": row[3],
        "replace_text": row[4],
        "regex_pattern": row[5],
        "regex_flags": row[6],
        "enabled": bool(row[7]),
        "priority": row[8],
        "created_at": row[9],
    }


@router.get("/{mapping_id}/transforms", response_model=list[MappingTransformResponse])
async def list_transforms(mapping_id: int, db: Db, user: CurrentUser) -> list[dict]:
    """List text/regex/emoji transformation rules for a mapping."""
    await _get_mapping_scope(db, user, mapping_id)
    async with db.execute(
        "SELECT id, mapping_id, rule_type, find_text, replace_text, regex_pattern, regex_flags, "
        "enabled, priority, created_at "
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
    find_text, regex_pattern, regex_flags = _validate_transform_payload(
        rule_type=rule_type,
        find_text=data.find_text,
        regex_pattern=data.regex_pattern,
        regex_flags=regex_flags,
    )

    cursor = await db.execute(
        "INSERT INTO mapping_transform_rules "
        "(mapping_id, rule_type, find_text, replace_text, regex_pattern, regex_flags, enabled, priority) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            mapping_id,
            rule_type,
            find_text,
            data.replace_text,
            regex_pattern,
            regex_flags,
            1 if data.enabled else 0,
            data.priority,
        ),
    )
    await db.commit()
    transform_id = cursor.lastrowid

    async with db.execute(
        "SELECT id, mapping_id, rule_type, find_text, replace_text, regex_pattern, regex_flags, "
        "enabled, priority, created_at FROM mapping_transform_rules WHERE id = ?",
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
        "enabled, priority, created_at "
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
            "enabled": patch.get("enabled", bool(row[7])),
            "priority": patch.get("priority", row[8]),
        }
        merged["rule_type"] = _normalize_rule_type(merged["rule_type"])
        normalized_flags = _normalize_regex_flags(merged["regex_flags"])
        find_text, regex_pattern, regex_flags = _validate_transform_payload(
            rule_type=merged["rule_type"],
            find_text=merged["find_text"],
            regex_pattern=merged["regex_pattern"],
            regex_flags=normalized_flags,
        )

        await db.execute(
            "UPDATE mapping_transform_rules SET "
            "rule_type = ?, find_text = ?, replace_text = ?, regex_pattern = ?, regex_flags = ?, "
            "enabled = ?, priority = ? "
            "WHERE id = ?",
            (
                merged["rule_type"],
                find_text,
                merged["replace_text"],
                regex_pattern,
                regex_flags,
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
        "enabled, priority, created_at FROM mapping_transform_rules WHERE id = ?",
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
