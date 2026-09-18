import { api, type TelegramDialog } from './api';
import { parseChatId } from './mappingValidation';

export async function resolveChatQuery(
  accountId: number,
  query: string,
  existingTitle = ''
): Promise<{ chat_id: number; title: string }> {
  const trimmed = query.trim();
  const asId = parseChatId(trimmed);
  if (asId != null) {
    return { chat_id: asId, title: existingTitle };
  }
  const { data } = await api.post<TelegramDialog>(`/accounts/${accountId}/resolve-peer`, {
    query: trimmed,
  });
  return { chat_id: data.chat_id, title: data.title };
}

export async function resolveMappingRouteChats(
  accountId: number,
  sourceQuery: string,
  destQuery: string,
  sourceTitle = '',
  destTitle = ''
): Promise<{
  source_chat_id: number;
  dest_chat_id: number;
  source_chat_title: string;
  dest_chat_title: string;
}> {
  // Sequential: a user session cannot open two Telethon clients at once.
  const source = await resolveChatQuery(accountId, sourceQuery, sourceTitle);
  const dest = await resolveChatQuery(accountId, destQuery, destTitle);
  if (source.chat_id === dest.chat_id) {
    throw new Error('Destination must differ from source');
  }
  return {
    source_chat_id: source.chat_id,
    dest_chat_id: dest.chat_id,
    source_chat_title: source.title,
    dest_chat_title: dest.title,
  };
}
