from app.services.mapping_service import MappingFilter
from app.telegram.handlers import _message_media_type, _passes_filters


class DummyMessage:
    def __init__(self, message: str = "", *, voice=False, video=False, photo=False):
        self.message = message
        self.text = message
        self.voice = voice
        self.video = video
        self.photo = photo


def test_message_media_type_text():
    msg = DummyMessage("hello")
    assert _message_media_type(msg) == "text"


def test_message_media_type_voice():
    msg = DummyMessage("", voice=True)
    assert _message_media_type(msg) == "voice"


def test_passes_filters_include_exclude():
    msg = DummyMessage("hello world")
    filters = [
        MappingFilter(include_text="hello", exclude_text=None, media_types=None, regex_pattern=None),
        MappingFilter(include_text=None, exclude_text="spam", media_types=None, regex_pattern=None),
    ]
    assert _passes_filters(msg, filters) is True


def test_passes_filters_rejects_media_type():
    msg = DummyMessage("hi", photo=True)
    filters = [MappingFilter(include_text=None, exclude_text=None, media_types="video,voice", regex_pattern=None)]
    assert _passes_filters(msg, filters) is False


def test_passes_filters_regex():
    msg = DummyMessage("order #123")
    filters = [MappingFilter(include_text=None, exclude_text=None, media_types=None, regex_pattern=r"#\d+")]
    assert _passes_filters(msg, filters) is True


def test_passes_filters_multiple_rules_all_must_match():
    msg = DummyMessage("hello world")
    filters = [
        MappingFilter(include_text="hello", exclude_text=None, media_types=None, regex_pattern=None),
        MappingFilter(include_text="missing", exclude_text=None, media_types=None, regex_pattern=None),
    ]
    assert _passes_filters(msg, filters) is False
