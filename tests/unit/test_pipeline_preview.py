"""Unit tests for pipeline_preview filter/transform helpers."""

from app.services.mapping_service import MappingFilter
from app.telegram.pipeline_preview import MessagePreview, passes_filters, single_filter_matches


def test_url_count_filter_min_max():
    f = MappingFilter(
        include_text=None,
        exclude_text=None,
        media_types=None,
        regex_pattern=None,
        or_group_id=0,
        min_url_count=1,
        max_url_count=3,
    )
    p = MessagePreview(text="see https://a.com and http://b.org", media_type="text")
    assert single_filter_matches(p, f, text=p.text, media_type="text")
    p2 = MessagePreview(text="no links here", media_type="text")
    assert not single_filter_matches(p2, f, text=p2.text, media_type="text")


def test_required_hashtags():
    f = MappingFilter(
        include_text=None,
        exclude_text=None,
        media_types=None,
        regex_pattern=None,
        or_group_id=0,
        required_hashtags="news, #urgent",
    )
    p = MessagePreview(text="Hello #news and #urgent", media_type="text")
    assert single_filter_matches(p, f, text=p.text, media_type="text")
    p2 = MessagePreview(text="Hello #news only", media_type="text")
    assert not single_filter_matches(p2, f, text=p2.text, media_type="text")


def test_allowed_sender_ids():
    f = MappingFilter(
        include_text=None,
        exclude_text=None,
        media_types=None,
        regex_pattern=None,
        or_group_id=0,
        allowed_sender_ids="100, 200",
    )
    p = MessagePreview(text="x", media_type="text", sender_id=100)
    assert single_filter_matches(p, f, text=p.text, media_type="text")
    p2 = MessagePreview(text="x", media_type="text", sender_id=999)
    assert not single_filter_matches(p2, f, text=p2.text, media_type="text")


def test_denied_username():
    f = MappingFilter(
        include_text=None,
        exclude_text=None,
        media_types=None,
        regex_pattern=None,
        or_group_id=0,
        denied_usernames="spammer",
    )
    p = MessagePreview(text="hi", media_type="text", sender_username="good")
    assert single_filter_matches(p, f, text=p.text, media_type="text")
    p2 = MessagePreview(text="hi", media_type="text", sender_username="Spammer")
    assert not single_filter_matches(p2, f, text=p2.text, media_type="text")


def test_passes_filters_or_groups():
    g1 = MappingFilter(None, None, None, None, 1)
    g2 = MappingFilter("must", None, None, None, 1)
    p = MessagePreview(text="hello", media_type="text")
    assert passes_filters(p, [g1, g2])
