import type { ChannelMapping } from './api';

/** Fill defaults for edit dialog when opening from list rows that may omit advanced columns. */
export function coerceChannelMappingForEdit(
  m: Partial<ChannelMapping> & Pick<ChannelMapping, 'id' | 'user_id' | 'source_chat_id' | 'dest_chat_id' | 'enabled'>
): ChannelMapping {
  return {
    id: m.id,
    user_id: m.user_id,
    source_chat_id: m.source_chat_id,
    dest_chat_id: m.dest_chat_id,
    name: m.name ?? null,
    source_chat_title: m.source_chat_title ?? null,
    dest_chat_title: m.dest_chat_title ?? null,
    enabled: m.enabled,
    telegram_account_id: m.telegram_account_id ?? null,
    created_at: m.created_at ?? null,
    send_delay_ms: m.send_delay_ms ?? 0,
    sync_edits: m.sync_edits ?? false,
    edit_strategy: m.edit_strategy ?? 'replace_text',
    sync_deletes: m.sync_deletes ?? false,
    copy_webhook_url: m.copy_webhook_url ?? null,
    copy_webhook_secret: m.copy_webhook_secret ?? null,
    webhook_secret_configured: m.webhook_secret_configured,
  };
}
