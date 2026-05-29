"""Unit tests for mapping validation helpers."""

import pytest

from app.telegram.chat_ids import alternate_chat_id
from app.web.validation.mapping_validation import (
    normalize_chat_id,
    validate_chat_id_field,
    validate_route_pair,
)
from fastapi import HTTPException


def test_normalize_chat_id_prefers_full_channel_form():
    legacy = -1234567890
    full = alternate_chat_id(legacy)
    assert full is not None
    assert normalize_chat_id(legacy) == full
    assert normalize_chat_id(full) == full


def test_validate_route_pair_rejects_same_chat():
    with pytest.raises(HTTPException) as exc:
        validate_route_pair(-100111, -100111)
    assert exc.value.status_code == 400
    assert "different" in exc.value.detail.lower()


def test_validate_chat_id_field_rejects_zero():
    with pytest.raises(HTTPException) as exc:
        validate_chat_id_field(0, "source_chat_id")
    assert exc.value.status_code == 400
