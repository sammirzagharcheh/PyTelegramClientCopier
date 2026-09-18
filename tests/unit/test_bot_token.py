"""Bot token format validation."""

import pytest

from app.telegram.bot_token import is_valid_bot_token, normalize_bot_token


@pytest.mark.parametrize(
    "token",
    [
        "123456:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw",
        "7123456789:AAFxdGVzdF90b2tlbl9mb3JfdW5pdF90ZXN0cw",
    ],
)
def test_valid_bot_tokens(token):
    assert is_valid_bot_token(token) is True


@pytest.mark.parametrize(
    "token",
    [
        "",
        "not-a-token",
        "🌓 New Planet 🪐 @newplanetitbot",
        "123456",
        ":AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw",
        "abc:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw",
    ],
)
def test_invalid_bot_tokens(token):
    assert is_valid_bot_token(token) is False


def test_normalize_strips_whitespace():
    raw = "  123456:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw  "
    assert normalize_bot_token(raw) == "123456:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw"
