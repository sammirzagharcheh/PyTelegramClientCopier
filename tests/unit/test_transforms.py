from app.services.mapping_service import MappingTransform
from app.telegram.handlers import _apply_transforms


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
