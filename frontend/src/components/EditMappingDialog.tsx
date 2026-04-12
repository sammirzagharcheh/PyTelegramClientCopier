import { Pencil } from 'lucide-react';
import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';
import type { ChannelMapping } from '../lib/api';
import { MappingFormFields } from './MappingFormFields';
import { useToast } from './Toast';

export type { ChannelMapping as Mapping } from '../lib/api';

type Props = {
  mapping: ChannelMapping;
  onClose: () => void;
};

const MAX_SEND_DELAY_MS = 60_000;

export function EditMappingDialog({ mapping, onClose }: Props) {
  const [name, setName] = useState(mapping.name ?? '');
  const [sourceChatId, setSourceChatId] = useState(String(mapping.source_chat_id));
  const [destChatId, setDestChatId] = useState(String(mapping.dest_chat_id));
  const [sendDelayMs, setSendDelayMs] = useState(String(mapping.send_delay_ms ?? 0));
  const [syncEdits, setSyncEdits] = useState(Boolean(mapping.sync_edits));
  const [syncDeletes, setSyncDeletes] = useState(Boolean(mapping.sync_deletes));
  const [editStrategy, setEditStrategy] = useState<'replace_text' | 'append_notice'>(
    mapping.edit_strategy === 'append_notice' ? 'append_notice' : 'replace_text'
  );
  const [copyWebhookUrl, setCopyWebhookUrl] = useState(mapping.copy_webhook_url ?? '');
  const [copyWebhookSecret, setCopyWebhookSecret] = useState('');
  const [clearWebhookSecret, setClearWebhookSecret] = useState(false);
  const webhookSecretPresent =
    Boolean(mapping.copy_webhook_secret?.trim()) || Boolean(mapping.webhook_secret_configured);
  const [error, setError] = useState('');
  const queryClient = useQueryClient();
  const { show: showToast } = useToast();

  const mutation = useMutation({
    mutationFn: async () => {
      const body: Record<string, unknown> = {};
      const nextName = name.trim() || null;
      if (nextName !== (mapping.name ?? null)) body.name = nextName;
      const src = parseInt(sourceChatId, 10);
      const dst = parseInt(destChatId, 10);
      if (src !== mapping.source_chat_id) body.source_chat_id = src;
      if (dst !== mapping.dest_chat_id) body.dest_chat_id = dst;

      const delay = parseInt(sendDelayMs, 10);
      if (Number.isNaN(delay) || delay < 0 || delay > MAX_SEND_DELAY_MS) {
        throw new Error(`Send delay must be between 0 and ${MAX_SEND_DELAY_MS} ms`);
      }
      if (delay !== (mapping.send_delay_ms ?? 0)) body.send_delay_ms = delay;
      if (syncEdits !== Boolean(mapping.sync_edits)) body.sync_edits = syncEdits;
      if (syncDeletes !== Boolean(mapping.sync_deletes)) body.sync_deletes = syncDeletes;
      const strat = editStrategy;
      if (strat !== (mapping.edit_strategy || 'replace_text')) body.edit_strategy = strat;

      const urlTrim = copyWebhookUrl.trim();
      const origUrl = (mapping.copy_webhook_url ?? '').trim();
      if (urlTrim !== origUrl) body.copy_webhook_url = urlTrim || null;

      if (clearWebhookSecret) {
        body.copy_webhook_secret = '';
      } else if (copyWebhookSecret.trim()) {
        body.copy_webhook_secret = copyWebhookSecret.trim();
      }

      if (Object.keys(body).length === 0) {
        onClose();
        return null;
      }
      return (await api.patch(`/mappings/${mapping.id}`, body)).data;
    },
    onSuccess: (data) => {
      if (data === null) return;
      // Apply server response immediately so MappingDetail (sync flags, strategy, etc.)
      // updates without waiting on refetch; staleTime + refetchOnWindowFocus: false otherwise
      // leaves old values visible until a background refetch completes.
      queryClient.setQueryData<ChannelMapping>(['mapping', String(mapping.id)], data);
      // List page (`/mappings`) never had sync_* in row payloads; merge PATCH result into any
      // paginated `['mappings', …]` cache so reopening Edit from the table shows saved toggles.
      const secretTrim =
        typeof data.copy_webhook_secret === 'string' ? data.copy_webhook_secret.trim() : '';
      queryClient.setQueriesData({ queryKey: ['mappings'], exact: false }, (old) => {
        if (!old || typeof old !== 'object' || !Array.isArray((old as { items?: unknown }).items)) {
          return old;
        }
        const rec = old as {
          items: Array<Record<string, unknown> & { id: number }>;
          total: number;
          page: number;
          page_size: number;
          total_pages: number;
        };
        return {
          ...rec,
          items: rec.items.map((it) =>
            it.id === data.id
              ? {
                  ...it,
                  name: data.name,
                  source_chat_id: data.source_chat_id,
                  dest_chat_id: data.dest_chat_id,
                  source_chat_title: data.source_chat_title,
                  dest_chat_title: data.dest_chat_title,
                  enabled: data.enabled,
                  telegram_account_id: data.telegram_account_id,
                  created_at: data.created_at,
                  send_delay_ms: data.send_delay_ms,
                  sync_edits: data.sync_edits,
                  sync_deletes: data.sync_deletes,
                  edit_strategy: data.edit_strategy,
                  copy_webhook_url: data.copy_webhook_url,
                  copy_webhook_secret: null,
                  webhook_secret_configured: Boolean(secretTrim),
                }
              : it
          ),
        };
      });
      queryClient.invalidateQueries({ queryKey: ['mappings'] });
      queryClient.invalidateQueries({ queryKey: ['mapping', String(mapping.id)] });
      showToast('Mapping updated. Workers restarting to apply changes.');
      onClose();
    },
    onError: (err: unknown) => {
      const msg =
        err instanceof Error && err.message.startsWith('Send delay')
          ? err.message
          : err &&
              typeof err === 'object' &&
              'response' in err &&
              err.response &&
              typeof err.response === 'object' &&
              'data' in err.response &&
              err.response.data &&
              typeof err.response.data === 'object' &&
              'detail' in err.response.data
            ? String((err.response.data as { detail: unknown }).detail)
            : 'Failed to update mapping';
      setError(msg);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    const src = parseInt(sourceChatId, 10);
    const dst = parseInt(destChatId, 10);
    if (isNaN(src) || isNaN(dst)) {
      setError('Invalid chat IDs');
      return;
    }
    const delay = parseInt(sendDelayMs, 10);
    if (isNaN(delay) || delay < 0 || delay > MAX_SEND_DELAY_MS) {
      setError(`Send delay must be between 0 and ${MAX_SEND_DELAY_MS} ms`);
      return;
    }
    mutation.mutate();
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <div
        className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-2 mb-4">
          <Pencil className="h-5 w-5 text-blue-600 dark:text-blue-400" />
          <h2 className="text-xl font-bold">Edit Channel Mapping</h2>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="p-3 rounded bg-red-50 dark:bg-red-900/20 text-red-600 text-sm">{error}</div>
          )}
          <MappingFormFields
            name={name}
            sourceChatId={sourceChatId}
            destChatId={destChatId}
            onNameChange={setName}
            onSourceChatIdChange={setSourceChatId}
            onDestChatIdChange={setDestChatId}
          />

          <fieldset className="border border-gray-200 dark:border-gray-600 rounded-lg p-4 space-y-3">
            <legend className="text-sm font-medium px-1">Advanced</legend>
            <div>
              <label htmlFor="edit-mapping-send-delay" className="block text-sm font-medium mb-1">
                Send delay (ms)
              </label>
              <input
                id="edit-mapping-send-delay"
                type="number"
                min={0}
                max={MAX_SEND_DELAY_MS}
                value={sendDelayMs}
                onChange={(e) => setSendDelayMs(e.target.value)}
                className="w-full max-w-xs px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700"
              />
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Extra delay before each forwarded message (0–{MAX_SEND_DELAY_MS} ms).
              </p>
            </div>
            <div className="flex flex-wrap gap-4">
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input
                  type="checkbox"
                  checked={syncEdits}
                  onChange={(e) => setSyncEdits(e.target.checked)}
                  className="rounded border-gray-300"
                />
                Sync edits to destination
              </label>
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input
                  type="checkbox"
                  checked={syncDeletes}
                  onChange={(e) => setSyncDeletes(e.target.checked)}
                  className="rounded border-gray-300"
                />
                Sync deletes to destination
              </label>
            </div>
            <div>
              <span className="block text-sm font-medium mb-1">Edit strategy</span>
              <div className="flex flex-wrap gap-3 text-sm">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="edit_strategy"
                    checked={editStrategy === 'replace_text'}
                    onChange={() => setEditStrategy('replace_text')}
                  />
                  Replace destination text
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="edit_strategy"
                    checked={editStrategy === 'append_notice'}
                    onChange={() => setEditStrategy('append_notice')}
                  />
                  Append notice (new message)
                </label>
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Use “Append notice” when destination messages cannot be edited (e.g. some media-only posts).
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Copy webhook URL (optional)</label>
              <input
                type="url"
                value={copyWebhookUrl}
                onChange={(e) => setCopyWebhookUrl(e.target.value)}
                className="w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 font-mono text-sm"
                placeholder="https://…"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Webhook secret (optional)</label>
              <input
                type="password"
                value={copyWebhookSecret}
                onChange={(e) => setCopyWebhookSecret(e.target.value)}
                className="w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 font-mono text-sm"
                placeholder={
                  webhookSecretPresent ? 'Leave blank to keep; enter new to rotate' : 'Optional'
                }
                autoComplete="off"
              />
              {webhookSecretPresent ? (
                <label className="flex items-center gap-2 mt-2 text-sm cursor-pointer">
                  <input
                    type="checkbox"
                    checked={clearWebhookSecret}
                    onChange={(e) => {
                      setClearWebhookSecret(e.target.checked);
                      if (e.target.checked) setCopyWebhookSecret('');
                    }}
                  />
                  Clear stored webhook secret
                </label>
              ) : null}
            </div>
          </fieldset>

          <div className="flex gap-2 justify-end">
            <button type="button" onClick={onClose} className="px-4 py-2 rounded border border-gray-300">
              Cancel
            </button>
            <button
              type="submit"
              disabled={mutation.isPending}
              className="px-4 py-2 rounded bg-blue-600 text-white disabled:opacity-50"
            >
              {mutation.isPending ? 'Saving…' : 'Save'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
