"""Channel mapping Pydantic schemas."""

from __future__ import annotations

from pydantic import BaseModel


class MappingFilterCreate(BaseModel):
    include_text: str | None = None
    exclude_text: str | None = None
    media_types: str | None = None
    regex_pattern: str | None = None
    # Omitted => server sets to new row id (own OR group; AND with other filters by default).
    or_group_id: int | None = None
    allowed_sender_ids: str | None = None
    denied_usernames: str | None = None
    min_url_count: int | None = None
    max_url_count: int | None = None
    required_hashtags: str | None = None


class MappingFilterUpdate(BaseModel):
    include_text: str | None = None
    exclude_text: str | None = None
    media_types: str | None = None
    regex_pattern: str | None = None
    or_group_id: int | None = None
    allowed_sender_ids: str | None = None
    denied_usernames: str | None = None
    min_url_count: int | None = None
    max_url_count: int | None = None
    required_hashtags: str | None = None


class MappingFilterResponse(BaseModel):
    id: int
    mapping_id: int
    include_text: str | None
    exclude_text: str | None
    media_types: str | None
    regex_pattern: str | None
    or_group_id: int
    allowed_sender_ids: str | None = None
    denied_usernames: str | None = None
    min_url_count: int | None = None
    max_url_count: int | None = None
    required_hashtags: str | None = None


class MappingTransformCreate(BaseModel):
    rule_type: str
    find_text: str | None = None
    replace_text: str | None = None
    regex_pattern: str | None = None
    regex_flags: str | None = None
    replacement_media_asset_id: int | None = None
    apply_to_media_types: str | None = None
    enabled: bool = True
    priority: int = 100


class MappingTransformUpdate(BaseModel):
    rule_type: str | None = None
    find_text: str | None = None
    replace_text: str | None = None
    regex_pattern: str | None = None
    regex_flags: str | None = None
    replacement_media_asset_id: int | None = None
    apply_to_media_types: str | None = None
    enabled: bool | None = None
    priority: int | None = None


class MappingTransformResponse(BaseModel):
    id: int
    mapping_id: int
    rule_type: str
    find_text: str | None
    replace_text: str | None
    regex_pattern: str | None
    regex_flags: str | None
    replacement_media_asset_id: int | None
    apply_to_media_types: str | None
    enabled: bool
    priority: int
    created_at: str | None


class ChannelMappingCreate(BaseModel):
    source_chat_id: int
    dest_chat_id: int
    name: str | None = None
    telegram_account_id: int | None = None
    source_chat_title: str | None = None
    dest_chat_title: str | None = None


class ChannelMappingUpdate(BaseModel):
    name: str | None = None
    source_chat_id: int | None = None
    dest_chat_id: int | None = None
    enabled: bool | None = None
    source_chat_title: str | None = None
    dest_chat_title: str | None = None
    send_delay_ms: int | None = None
    sync_edits: bool | None = None
    edit_strategy: str | None = None
    sync_deletes: bool | None = None
    copy_webhook_url: str | None = None
    copy_webhook_secret: str | None = None
    copy_webhook_payload_template: str | None = None
    copy_webhook_secret_header_name: str | None = None
    copy_webhook_secret_header_value: str | None = None
    copy_webhook_secret_mode: str | None = None


class ChannelMappingResponse(BaseModel):
    id: int
    user_id: int
    source_chat_id: int
    dest_chat_id: int
    name: str | None
    source_chat_title: str | None
    dest_chat_title: str | None
    enabled: bool
    telegram_account_id: int | None
    created_at: str | None
    send_delay_ms: int = 0
    sync_edits: bool = False
    edit_strategy: str = "replace_text"
    sync_deletes: bool = False
    copy_webhook_url: str | None = None
    copy_webhook_secret: str | None = None
    copy_webhook_payload_template: str | None = None
    copy_webhook_secret_header_name: str | None = None
    copy_webhook_secret_mode: str | None = None
    webhook_secret_header_configured: bool = False


class MappingPreviewRequest(BaseModel):
    sample_text: str = ""
    media_type: str = "text"
    sender_id: int | None = None
    sender_username: str | None = None


class MappingPreviewResponse(BaseModel):
    passes_filters: bool
    passes_schedule: bool
    transformed_text: str
