"""Unit tests for edit/delete source chat id resolution."""

from types import SimpleNamespace

from app.telegram.handlers import _event_source_chat_id_for_sync


def test_prefers_chat_id_when_present():
    ev = SimpleNamespace(chat_id=-100123, peer=None)
    assert _event_source_chat_id_for_sync(ev) == -100123


def test_falls_back_to_peer_when_no_chat_id():
    peer = object()
    ev = SimpleNamespace(chat_id=None, peer=peer)

    class FakeUtils:
        @staticmethod
        def get_peer_id(p):
            assert p is peer
            return -100999

    import app.telegram.handlers as h

    real_utils = h.utils
    h.utils = FakeUtils  # type: ignore[misc]
    try:
        assert _event_source_chat_id_for_sync(ev) == -100999
    finally:
        h.utils = real_utils


def test_invalid_chat_id_falls_back_to_peer():
    peer = SimpleNamespace()
    ev = SimpleNamespace(chat_id="not-an-int", peer=peer)

    import app.telegram.handlers as h

    real_utils = h.utils

    class FakeUtils:
        @staticmethod
        def get_peer_id(p):
            return 42

    h.utils = FakeUtils  # type: ignore[misc]
    try:
        assert _event_source_chat_id_for_sync(ev) == 42
    finally:
        h.utils = real_utils


def test_returns_none_when_unresolvable():
    ev = SimpleNamespace(chat_id=None, peer=None)
    assert _event_source_chat_id_for_sync(ev) is None


def test_peer_get_peer_id_raises_returns_none():
    ev = SimpleNamespace(chat_id=None, peer=object())

    import app.telegram.handlers as h

    real_utils = h.utils

    class FakeUtils:
        @staticmethod
        def get_peer_id(_p):
            raise RuntimeError("boom")

    h.utils = FakeUtils  # type: ignore[misc]
    try:
        assert _event_source_chat_id_for_sync(ev) is None
    finally:
        h.utils = real_utils
