from app.services.mapping_service import MappingTransform
from app.telegram.handlers import _apply_transforms, _pick_media_replacement


def test_apply_text_transform():
    rules = [
        MappingTransform(
            id=1,
            rule_type="text",
            find_text="Sam channel",
            replace_text="Tom channel",
            regex_pattern=None,
            regex_flags=None,
            enabled=True,
            priority=10,
        )
    ]
    out = _apply_transforms("Welcome to Sam channel", rules)
    assert out == "Welcome to Tom channel"


def test_apply_regex_transform_case_insensitive():
    rules = [
        MappingTransform(
            id=1,
            rule_type="regex",
            find_text=None,
            replace_text="Tom channel",
            regex_pattern=r"sam channel",
            regex_flags="i",
            enabled=True,
            priority=10,
        )
    ]
    out = _apply_transforms("Welcome to SAM CHANNEL", rules)
    assert out == "Welcome to Tom channel"


def test_apply_emoji_transform():
    rules = [
        MappingTransform(
            id=1,
            rule_type="emoji",
            find_text="🔥",
            replace_text="⭐",
            regex_pattern=None,
            regex_flags=None,
            enabled=True,
            priority=10,
        )
    ]
    out = _apply_transforms("Hot deal 🔥🔥", rules)
    assert out == "Hot deal ⭐⭐"


def test_disabled_transform_is_ignored():
    rules = [
        MappingTransform(
            id=1,
            rule_type="text",
            find_text="Sam",
            replace_text="Tom",
            regex_pattern=None,
            regex_flags=None,
            enabled=False,
            priority=10,
        )
    ]
    out = _apply_transforms("Sam channel", rules)
    assert out == "Sam channel"


def test_invalid_regex_transform_is_skipped():
    rules = [
        MappingTransform(
            id=1,
            rule_type="regex",
            find_text=None,
            replace_text="x",
            regex_pattern="(",
            regex_flags=None,
            enabled=True,
            priority=10,
        )
    ]
    out = _apply_transforms("sample text", rules)
    assert out == "sample text"


def test_apply_template_transform_with_context():
    rules = [
        MappingTransform(
            id=1,
            rule_type="template",
            replace_text="[{{source_chat_id}}] {{text}}",
            enabled=True,
            priority=10,
        )
    ]
    out = _apply_transforms(
        "hello world",
        rules,
        context={"source_chat_id": 12345},
        media_type="text",
    )
    assert out == "[12345] hello world"


def test_apply_template_transform_after_text_replace():
    rules = [
        MappingTransform(
            id=1,
            rule_type="text",
            find_text="Sam channel",
            replace_text="Tom channel",
            enabled=True,
            priority=10,
        ),
        MappingTransform(
            id=2,
            rule_type="template",
            replace_text="{{text}} :: {{media_type}}",
            enabled=True,
            priority=20,
        ),
    ]
    out = _apply_transforms(
        "Welcome to Sam channel",
        rules,
        context={"media_type": "text"},
        media_type="text",
    )
    assert out == "Welcome to Tom channel :: text"


def test_template_transform_media_type_scope():
    rules = [
        MappingTransform(
            id=1,
            rule_type="template",
            replace_text="caption={{text}}",
            apply_to_media_types="photo",
            enabled=True,
            priority=10,
        )
    ]
    out_text = _apply_transforms("plain", rules, media_type="text")
    out_photo = _apply_transforms("plain", rules, media_type="photo")
    assert out_text == "plain"
    assert out_photo == "caption=plain"


class _DummyMessage:
    def __init__(self, *, media=None, photo=False, video=False, voice=False):
        self.media = media
        self.photo = photo
        self.video = video
        self.voice = voice
        self.text = ""
        self.message = ""


def test_pick_media_replacement_for_photo():
    msg = _DummyMessage(media="source-bytes", photo=True)
    rules = [
        MappingTransform(
            id=1,
            rule_type="media",
            replacement_media_asset_id=100,
            replacement_media_asset_path="/tmp/replacement.jpg",
            apply_to_media_types="photo",
            enabled=True,
            priority=1,
        )
    ]
    picked = _pick_media_replacement(msg, rules)
    assert picked == "/tmp/replacement.jpg"


def test_pick_media_replacement_ignores_non_matching_media_type():
    msg = _DummyMessage(media="source-bytes", video=True)
    rules = [
        MappingTransform(
            id=1,
            rule_type="media",
            replacement_media_asset_id=100,
            replacement_media_asset_path="/tmp/replacement.jpg",
            apply_to_media_types="photo",
            enabled=True,
            priority=1,
        )
    ]
    picked = _pick_media_replacement(msg, rules)
    assert picked is None
