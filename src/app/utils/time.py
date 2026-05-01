from __future__ import annotations

def normalize_utc_iso_for_json(value: str | None) -> str | None:
    """Normalize legacy SQLite UTC strings for consistent JSON output.

    SQLite often stores UTC timestamps like `YYYY-MM-DD HH:MM:SS`.
    JS parsers can treat these as local time; convert to ISO UTC with `Z`.
    """
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return s
    if " " in s and "T" not in s and "Z" not in s and "+" not in s:
        return s.replace(" ", "T", 1) + "Z"
    return s


def sql_ts_expr(column: str) -> str:
    """Return SQL expression for timestamp comparison in PostgreSQL."""
    return f"({column})::timestamptz"
