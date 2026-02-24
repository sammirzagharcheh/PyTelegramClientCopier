"""Regex utilities shared across web and telegram layers."""

from __future__ import annotations

import re


def regex_flags_from_string(flag_string: str | None) -> int:
    """Convert a regex flag string (e.g. 'ims') into a Python re flags bitmask."""
    flags = 0
    if not flag_string:
        return flags
    s = flag_string.lower()
    if "i" in s:
        flags |= re.IGNORECASE
    if "m" in s:
        flags |= re.MULTILINE
    if "s" in s:
        flags |= re.DOTALL
    return flags
