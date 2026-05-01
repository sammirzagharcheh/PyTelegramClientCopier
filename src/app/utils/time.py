from __future__ import annotations

from datetime import datetime, timezone


def normalize_utc_iso_for_json(value: str | datetime | None) -> str | None:
    """Normalize legacy SQLite UTC strings for consistent JSON output.

    SQLite often stores UTC timestamps like `YYYY-MM-DD HH:MM:SS`.
    JS parsers can treat these as local time; convert to ISO UTC with `Z`.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.isoformat()
    s = str(value).strip()
    if not s:
        return s
    if " " in s and ("+00:00" in s or "-00:00" in s):
        s = s.replace(" ", "T", 1)
    if s.endswith("+00:00") or s.endswith("-00:00"):
        return s
    if " " in s and "T" not in s and "Z" not in s and "+" not in s:
        return s.replace(" ", "T", 1) + "Z"
    return s


def sql_ts_expr(column: str) -> str:
    """Return SQL expression for timestamp comparison in PostgreSQL."""
    return f"({column})::timestamptz"
