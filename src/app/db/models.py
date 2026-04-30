from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, PrimaryKeyConstraint, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    role: Mapped[str] = mapped_column(Text, nullable=False, default="user")
    status: Mapped[str] = mapped_column(Text, nullable=False, default="active")
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default="CURRENT_TIMESTAMP")
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    timezone: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_users_id_status", "id", "status"),)


class TelegramAccount(Base):
    __tablename__ = "telegram_accounts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    session_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(Text, nullable=True)
    bot_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="active")
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_telegram_accounts_user_id", "user_id"),
        Index("ix_telegram_accounts_user_status", "user_id", "status"),
    )


class ChannelMapping(Base):
    __tablename__ = "channel_mappings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    source_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    dest_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    enabled: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_chat_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    dest_chat_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    telegram_account_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("telegram_accounts.id"), nullable=True
    )
    send_delay_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sync_edits: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    edit_strategy: Mapped[str] = mapped_column(Text, nullable=False, default="replace_text")
    sync_deletes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    copy_webhook_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    copy_webhook_secret: Mapped[str | None] = mapped_column(Text, nullable=True)
    copy_webhook_payload_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    copy_webhook_secret_header_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    copy_webhook_secret_header_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    copy_webhook_secret_mode: Mapped[str] = mapped_column(
        Text, nullable=False, default="hmac_sha256"
    )

    __table_args__ = (
        Index("ix_channel_mappings_user_id", "user_id"),
        Index("ix_channel_mappings_user_src_dest", "user_id", "source_chat_id", "dest_chat_id"),
    )


class MappingFilter(Base):
    __tablename__ = "mapping_filters"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    mapping_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("channel_mappings.id"), nullable=False
    )
    include_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    exclude_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_types: Mapped[str | None] = mapped_column(Text, nullable=True)
    regex_pattern: Mapped[str | None] = mapped_column(Text, nullable=True)
    or_group_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    allowed_sender_ids: Mapped[str | None] = mapped_column(Text, nullable=True)
    denied_usernames: Mapped[str | None] = mapped_column(Text, nullable=True)
    min_url_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_url_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    required_hashtags: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_mapping_filters_mapping_id", "mapping_id"),)


class DestMessageIndex(Base):
    __tablename__ = "dest_message_index"

    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source_msg_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    dest_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    dest_msg_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        PrimaryKeyConstraint("user_id", "source_chat_id", "source_msg_id", "dest_chat_id"),
        Index("ix_dest_message_index_user_id", "user_id"),
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default="CURRENT_TIMESTAMP")

    __table_args__ = (Index("ix_refresh_tokens_token_hash", "token_hash"),)


class AdminInvite(Base):
    __tablename__ = "admin_invites"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(Text, nullable=False)
    token: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    expires_at: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default="CURRENT_TIMESTAMP")


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False, default="CURRENT_TIMESTAMP")


class LoginSession(Base):
    __tablename__ = "login_sessions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    phone: Mapped[str] = mapped_column(Text, nullable=False)
    tmp_session_name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default="CURRENT_TIMESTAMP")
    phone_code_hash: Mapped[str | None] = mapped_column(Text, nullable=True)


class WorkerRegistry(Base):
    __tablename__ = "worker_registry"

    worker_id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    account_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    session_path: Mapped[str] = mapped_column(Text, nullable=False)
    pid: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default="CURRENT_TIMESTAMP")
    last_heartbeat_at: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_worker_registry_account_id", "account_id", unique=True),)


class UserSchedule(Base):
    __tablename__ = "user_schedules"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), primary_key=True)
    mon_start_utc: Mapped[str | None] = mapped_column(Text, nullable=True)
    mon_end_utc: Mapped[str | None] = mapped_column(Text, nullable=True)
    tue_start_utc: Mapped[str | None] = mapped_column(Text, nullable=True)
    tue_end_utc: Mapped[str | None] = mapped_column(Text, nullable=True)
    wed_start_utc: Mapped[str | None] = mapped_column(Text, nullable=True)
    wed_end_utc: Mapped[str | None] = mapped_column(Text, nullable=True)
    thu_start_utc: Mapped[str | None] = mapped_column(Text, nullable=True)
    thu_end_utc: Mapped[str | None] = mapped_column(Text, nullable=True)
    fri_start_utc: Mapped[str | None] = mapped_column(Text, nullable=True)
    fri_end_utc: Mapped[str | None] = mapped_column(Text, nullable=True)
    sat_start_utc: Mapped[str | None] = mapped_column(Text, nullable=True)
    sat_end_utc: Mapped[str | None] = mapped_column(Text, nullable=True)
    sun_start_utc: Mapped[str | None] = mapped_column(Text, nullable=True)
    sun_end_utc: Mapped[str | None] = mapped_column(Text, nullable=True)


class MappingSchedule(Base):
    __tablename__ = "mapping_schedules"

    mapping_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("channel_mappings.id"), primary_key=True
    )
    mon_start_utc: Mapped[str | None] = mapped_column(Text, nullable=True)
    mon_end_utc: Mapped[str | None] = mapped_column(Text, nullable=True)
    tue_start_utc: Mapped[str | None] = mapped_column(Text, nullable=True)
    tue_end_utc: Mapped[str | None] = mapped_column(Text, nullable=True)
    wed_start_utc: Mapped[str | None] = mapped_column(Text, nullable=True)
    wed_end_utc: Mapped[str | None] = mapped_column(Text, nullable=True)
    thu_start_utc: Mapped[str | None] = mapped_column(Text, nullable=True)
    thu_end_utc: Mapped[str | None] = mapped_column(Text, nullable=True)
    fri_start_utc: Mapped[str | None] = mapped_column(Text, nullable=True)
    fri_end_utc: Mapped[str | None] = mapped_column(Text, nullable=True)
    sat_start_utc: Mapped[str | None] = mapped_column(Text, nullable=True)
    sat_end_utc: Mapped[str | None] = mapped_column(Text, nullable=True)
    sun_start_utc: Mapped[str | None] = mapped_column(Text, nullable=True)
    sun_end_utc: Mapped[str | None] = mapped_column(Text, nullable=True)


class MappingTransformRule(Base):
    __tablename__ = "mapping_transform_rules"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    mapping_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("channel_mappings.id"), nullable=False
    )
    rule_type: Mapped[str] = mapped_column(Text, nullable=False)
    find_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    replace_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    regex_pattern: Mapped[str | None] = mapped_column(Text, nullable=True)
    regex_flags: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default="CURRENT_TIMESTAMP")
    replacement_media_asset_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    apply_to_media_types: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_mapping_transform_rules_mapping_id", "mapping_id"),)


class MediaAsset(Base):
    __tablename__ = "media_assets"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    media_kind: Mapped[str] = mapped_column(Text, nullable=False, default="other")
    mime_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default="CURRENT_TIMESTAMP")

    __table_args__ = (Index("ix_media_assets_user_id", "user_id"),)


class UserAlertWebhook(Base):
    __tablename__ = "user_alert_webhooks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    secret: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default="CURRENT_TIMESTAMP")

    __table_args__ = (Index("ix_user_alert_webhooks_user_id", "user_id"),)


class UserApiKey(Base):
    __tablename__ = "user_api_keys"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    key_hash: Mapped[str] = mapped_column(Text, nullable=False)
    scopes: Mapped[str] = mapped_column(Text, nullable=False, default="mappings:read")
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default="CURRENT_TIMESTAMP")
    last_used_at: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_user_api_keys_user_id", "user_id"),
        Index("ix_user_api_keys_key_hash", "key_hash", unique=True),
    )


class MigrationVersion(Base):
    __tablename__ = "_migrations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    applied_at: Mapped[str] = mapped_column(Text, nullable=False, default="CURRENT_TIMESTAMP")
