"""Unit tests for filter validation helpers."""

import pytest
from fastapi import HTTPException

from app.web.validation.filter_validation import (
    compile_filter_regex,
    filter_has_criteria,
    hashtag_present,
    validate_filter_payload,
    validate_filter_regex,
)


def test_filter_has_criteria_requires_nonempty_field():
    assert not filter_has_criteria()
    assert filter_has_criteria(include_text="x")
    assert not filter_has_criteria(exclude_text="  ")


def test_validate_filter_payload_rejects_empty():
    with pytest.raises(HTTPException) as exc:
        validate_filter_payload()
    assert exc.value.status_code == 400


def test_validate_filter_regex_rejects_invalid():
    with pytest.raises(HTTPException) as exc:
        validate_filter_regex("[bad")
    assert exc.value.status_code == 400


def test_compile_filter_regex_caches():
    p1 = compile_filter_regex(r"\d+")
    p2 = compile_filter_regex(r"\d+")
    assert p1 is p2
    assert compile_filter_regex("[bad") is None


def test_hashtag_not_prefix_of_longer_tag():
    assert hashtag_present("see #news here", "news")
    assert not hashtag_present("see #newsletter here", "news")
