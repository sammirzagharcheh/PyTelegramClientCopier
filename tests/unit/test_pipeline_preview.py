"""Unit tests for pipeline_preview filter/transform helpers."""

import datetime

from app.services.mapping_service import MappingFilter, Schedule
from app.telegram.pipeline_preview import (
    MessagePreview,
    admission_skip,
    first_filter_fail_detail,
    passes_filters,
    single_filter_matches,
)


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
    g1 = MappingFilter("hello", None, None, None, 1)
    g2 = MappingFilter("must", None, None, None, 1)
    p = MessagePreview(text="hello", media_type="text")
    assert passes_filters(p, [g1, g2])
    p2 = MessagePreview(text="other", media_type="text")
    assert not passes_filters(p2, [g1, g2])


def test_hashtag_whole_word_only():
    f = MappingFilter(
        include_text=None,
        exclude_text=None,
        media_types=None,
        regex_pattern=None,
        or_group_id=0,
        required_hashtags="news",
    )
    p = MessagePreview(text="Hello #news today", media_type="text")
    assert single_filter_matches(p, f, text=p.text, media_type="text")
    p2 = MessagePreview(text="Hello #newsletter today", media_type="text")
    assert not single_filter_matches(p2, f, text=p2.text, media_type="text")


def test_first_filter_fail_detail_exclude_text():
    f = MappingFilter(None, "spam", None, None, 0)
    p = MessagePreview(text="this is spam", media_type="text")
    assert first_filter_fail_detail(p, [f]) == "exclude_text"
    assert admission_skip(p, [f], datetime.datetime.now(datetime.UTC), None).reason == "filter"


def test_first_filter_fail_detail_empty_filters():
    p = MessagePreview(text="anything", media_type="text")
    assert first_filter_fail_detail(p, []) is None
    assert admission_skip(p, [], datetime.datetime.now(datetime.UTC), None) is None


def test_admission_skip_schedule():
    # Monday 10:00 UTC; schedule only allows Mon 09:00–09:30
    sched = Schedule(
        mon_start_utc="09:00",
        mon_end_utc="09:30",
        tue_start_utc=None,
        tue_end_utc=None,
        wed_start_utc=None,
        wed_end_utc=None,
        thu_start_utc=None,
        thu_end_utc=None,
        fri_start_utc=None,
        fri_end_utc=None,
        sat_start_utc=None,
        sat_end_utc=None,
        sun_start_utc=None,
        sun_end_utc=None,
    )
    p = MessagePreview(text="hi", media_type="text")
    now = datetime.datetime(2026, 9, 14, 10, 0, tzinfo=datetime.UTC)  # Monday
    skip = admission_skip(p, [], now, sched)
    assert skip is not None
    assert skip.reason == "schedule"
