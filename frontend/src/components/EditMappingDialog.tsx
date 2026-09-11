import { Pencil } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';
import type { ChannelMapping } from '../lib/api';
import { errorMessage } from '../lib/apiError';
import { MappingRouteFields } from './MappingRouteFields';
import { useToast } from './Toast';
import { Button } from './ui/Button';
import { Field, Input, Select, Textarea } from './ui/Field';
import { FormError } from './ui/FormError';
import { Modal } from './ui/Modal';
import {
  hasRouteErrors,
  parseChatId,
  validateMappingRoute,
  type MappingRouteFieldErrors,
  type MappingRouteValues,
} from '../lib/mappingValidation';

export type { ChannelMapping as Mapping } from '../lib/api';

type Props = {
  mapping: ChannelMapping;
  onClose: () => void;
};

const MAX_SEND_DELAY_MS = 60_000;
const WEBHOOK_TEMPLATE_TOKENS = [
  { label: 'event', value: '{{event}}' },
  { label: 'user_id', value: '{{user_id}}' },
  { label: 'mapping_id', value: '{{mapping_id}}' },
  { label: 'source_chat_id', value: '{{source_chat_id}}' },
  { label: 'source_msg_id', value: '{{source_msg_id}}' },
  { label: 'source_msg_ids', value: '{{source_msg_ids}}' },
  { label: 'source_chat_title', value: '{{source_chat_title}}' },
  { label: 'dest_chat_id', value: '{{dest_chat_id}}' },
  { label: 'dest_msg_id', value: '{{dest_msg_id}}' },
  {
    label: 'source_reply_msg_id (parent in source, if reply)',
    value: '{{source_reply_msg_id}}',
  },
  {
    label: 'dest_reply_msg_id (mapped parent in dest, if known)',
    value: '{{dest_reply_msg_id}}',
  },
  { label: 'dest_chat_title', value: '{{dest_chat_title}}' },
  { label: 'media_type', value: '{{media_type}}' },
  { label: 'date_utc', value: '{{date_utc}}' },
  { label: 'text', value: '{{text}}' },
  { label: 'guid', value: '{{guid}}' },
];

const checkboxClass = 'h-4 w-4 rounded border-line-strong accent-[var(--accent)]';

function buildInitialRoute(m: ChannelMapping): MappingRouteValues {
  return {
    telegramAccountId: m.telegram_account_id,
    sourceChatId: String(m.source_chat_id),
    destChatId: String(m.dest_chat_id),
    sourceChatTitle: m.source_chat_title ?? '',
    destChatTitle: m.dest_chat_title ?? '',
    useManualIds: m.telegram_account_id == null,
  };
}

export function EditMappingDialog({ mapping, onClose }: Props) {
  const [name, setName] = useState(mapping.name ?? '');
  const [route, setRoute] = useState<MappingRouteValues>(() => buildInitialRoute(mapping));
  const [fieldErrors, setFieldErrors] = useState<MappingRouteFieldErrors>({});
  const [sendDelayMs, setSendDelayMs] = useState(String(mapping.send_delay_ms ?? 0));
  const [syncEdits, setSyncEdits] = useState(Boolean(mapping.sync_edits));
  const [syncDeletes, setSyncDeletes] = useState(Boolean(mapping.sync_deletes));
  const [editStrategy, setEditStrategy] = useState<'replace_text' | 'append_notice'>(
    mapping.edit_strategy === 'append_notice' ? 'append_notice' : 'replace_text'
  );
  const [copyWebhookUrl, setCopyWebhookUrl] = useState(mapping.copy_webhook_url ?? '');
  const [copyWebhookSecret, setCopyWebhookSecret] = useState('');
  const [copyWebhookPayloadTemplate, setCopyWebhookPayloadTemplate] = useState(
    mapping.copy_webhook_payload_template ?? ''
  );
  const [copyWebhookSecretMode, setCopyWebhookSecretMode] = useState(
    mapping.copy_webhook_secret_mode ?? 'hmac_sha256'
  );
  const [copyWebhookSecretHeaderName, setCopyWebhookSecretHeaderName] = useState(
    mapping.copy_webhook_secret_header_name ?? ''
  );
  const [copyWebhookSecretHeaderValue, setCopyWebhookSecretHeaderValue] = useState('');
  const [clearWebhookSecret, setClearWebhookSecret] = useState(false);
  const [clearWebhookHeaderSecret, setClearWebhookHeaderSecret] = useState(false);
  const [selectedWebhookToken, setSelectedWebhookToken] = useState(
    WEBHOOK_TEMPLATE_TOKENS[0]?.value ?? '{{event}}'
  );
  const payloadTemplateRef = useRef<HTMLTextAreaElement>(null);
  const webhookSecretPresent =
    Boolean(mapping.copy_webhook_secret?.trim()) || Boolean(mapping.webhook_secret_configured);
  const webhookHeaderSecretPresent = Boolean(mapping.webhook_secret_header_configured);
  const [error, setError] = useState('');
  const queryClient = useQueryClient();
  const { show: showToast } = useToast();

  const mutation = useMutation({
    mutationFn: async () => {
      const body: Record<string, unknown> = {};
      const nextName = name.trim() || null;
      if (nextName !== (mapping.name ?? null)) body.name = nextName;
      const src = parseChatId(route.sourceChatId);
      const dst = parseChatId(route.destChatId);
      if (src == null || dst == null) {
        throw new Error('Invalid chat IDs');
      }
      if (src !== mapping.source_chat_id) body.source_chat_id = src;
      if (dst !== mapping.dest_chat_id) body.dest_chat_id = dst;
      const srcTitle = route.sourceChatTitle.trim();
      const dstTitle = route.destChatTitle.trim();
      if (srcTitle !== (mapping.source_chat_title ?? '')) body.source_chat_title = srcTitle || null;
      if (dstTitle !== (mapping.dest_chat_title ?? '')) body.dest_chat_title = dstTitle || null;
      if (
        route.telegramAccountId != null &&
        route.telegramAccountId !== mapping.telegram_account_id
      ) {
        body.telegram_account_id = route.telegramAccountId;
      }

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
      const payloadTemplate = copyWebhookPayloadTemplate.trim();
      const origPayloadTemplate = (mapping.copy_webhook_payload_template ?? '').trim();
      if (payloadTemplate !== origPayloadTemplate) {
        body.copy_webhook_payload_template = payloadTemplate || null;
      }
      const secretMode = copyWebhookSecretMode.trim() || 'hmac_sha256';
      if (secretMode !== (mapping.copy_webhook_secret_mode ?? 'hmac_sha256')) {
        body.copy_webhook_secret_mode = secretMode;
      }
      const secretHeaderName = copyWebhookSecretHeaderName.trim();
      const origSecretHeaderName = (mapping.copy_webhook_secret_header_name ?? '').trim();
      if (secretHeaderName !== origSecretHeaderName) {
        body.copy_webhook_secret_header_name = secretHeaderName || null;
      }

      if (clearWebhookSecret) {
        body.copy_webhook_secret = '';
      } else if (copyWebhookSecret.trim()) {
        body.copy_webhook_secret = copyWebhookSecret.trim();
      }
      if (clearWebhookHeaderSecret) {
        body.copy_webhook_secret_header_value = '';
      } else if (copyWebhookSecretHeaderValue.trim()) {
        body.copy_webhook_secret_header_value = copyWebhookSecretHeaderValue.trim();
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
      // paginated `['mappings', ...]` cache so reopening Edit from the table shows saved toggles.
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
                  copy_webhook_payload_template: data.copy_webhook_payload_template,
                  copy_webhook_secret_header_name: data.copy_webhook_secret_header_name,
                  copy_webhook_secret_mode: data.copy_webhook_secret_mode,
                  webhook_secret_configured: Boolean(secretTrim),
                  webhook_secret_header_configured: Boolean(data.webhook_secret_header_configured),
                }
              : it
          ),
        };
      });
      queryClient.invalidateQueries({ queryKey: ['mappings'] });
      queryClient.invalidateQueries({ queryKey: ['mapping', String(mapping.id)] });
      showToast('Mapping updated. Workers are restarting to apply it.');
      onClose();
    },
    onError: (err: unknown) => {
      if (err instanceof Error && err.message.startsWith('Send delay')) {
        setError(err.message);
        return;
      }
      setError(errorMessage(err, 'We could not update this mapping.'));
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    const errors = validateMappingRoute(route);
    setFieldErrors(errors);
    if (hasRouteErrors(errors)) return;
    const delay = parseInt(sendDelayMs, 10);
    if (isNaN(delay) || delay < 0 || delay > MAX_SEND_DELAY_MS) {
      setError(`Send delay must be between 0 and ${MAX_SEND_DELAY_MS} ms`);
      return;
    }
    mutation.mutate();
  };

  useEffect(() => {
    setName(mapping.name ?? '');
    setRoute(buildInitialRoute(mapping));
    setFieldErrors({});
    setSendDelayMs(String(mapping.send_delay_ms ?? 0));
    setSyncEdits(Boolean(mapping.sync_edits));
    setSyncDeletes(Boolean(mapping.sync_deletes));
    setEditStrategy(mapping.edit_strategy === 'append_notice' ? 'append_notice' : 'replace_text');
    setCopyWebhookUrl(mapping.copy_webhook_url ?? '');
    setCopyWebhookSecret('');
    setCopyWebhookPayloadTemplate(mapping.copy_webhook_payload_template ?? '');
    setCopyWebhookSecretMode(mapping.copy_webhook_secret_mode ?? 'hmac_sha256');
    setCopyWebhookSecretHeaderName(mapping.copy_webhook_secret_header_name ?? '');
    setCopyWebhookSecretHeaderValue('');
    setClearWebhookSecret(false);
    setClearWebhookHeaderSecret(false);
    setError('');
  }, [mapping]);

  const insertWebhookToken = (token: string) => {
    const textarea = payloadTemplateRef.current;
    if (!textarea) {
      setCopyWebhookPayloadTemplate((prev) => `${prev}${token}`);
      return;
    }
    const start = textarea.selectionStart ?? copyWebhookPayloadTemplate.length;
    const end = textarea.selectionEnd ?? start;
    const next =
      copyWebhookPayloadTemplate.slice(0, start) + token + copyWebhookPayloadTemplate.slice(end);
    setCopyWebhookPayloadTemplate(next);
    requestAnimationFrame(() => {
      textarea.focus();
      const caret = start + token.length;
      textarea.setSelectionRange(caret, caret);
    });
  };

  return (
    <Modal
      title="Edit channel mapping"
      icon={<Pencil className="h-5 w-5 text-ink-subtle" strokeWidth={2} aria-hidden />}
      size="lg"
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" form="edit-mapping-form" isLoading={mutation.isPending}>
            Save changes
          </Button>
        </>
      }
    >
      <form id="edit-mapping-form" onSubmit={handleSubmit} className="space-y-4" noValidate>
        <FormError message={error} />
        <MappingRouteFields
          values={route}
          onChange={setRoute}
          errors={fieldErrors}
          name={name}
          onNameChange={setName}
          initialSourceChatId={mapping.source_chat_id}
          initialDestChatId={mapping.dest_chat_id}
          initialSourceTitle={mapping.source_chat_title}
          initialDestTitle={mapping.dest_chat_title}
        />

        <fieldset className="space-y-4 rounded-surface border border-line p-4">
          <legend className="px-1 text-sm font-medium text-ink">Advanced</legend>
          <Field
            label="Send delay (ms)"
            hint={`Extra delay before each forwarded message (0-${MAX_SEND_DELAY_MS} ms).`}
          >
            {(fieldProps) => (
              <Input
                {...fieldProps}
                type="number"
                min={0}
                max={MAX_SEND_DELAY_MS}
                value={sendDelayMs}
                onChange={(e) => setSendDelayMs(e.target.value)}
                className="max-w-xs tabular-nums"
              />
            )}
          </Field>
          <div className="flex flex-wrap gap-4">
            <label className="flex cursor-pointer items-center gap-2 text-sm text-ink">
              <input
                type="checkbox"
                checked={syncEdits}
                onChange={(e) => setSyncEdits(e.target.checked)}
                className={checkboxClass}
              />
              Sync edits to destination
            </label>
            <label className="flex cursor-pointer items-center gap-2 text-sm text-ink">
              <input
                type="checkbox"
                checked={syncDeletes}
                onChange={(e) => setSyncDeletes(e.target.checked)}
                className={checkboxClass}
              />
              Sync deletes to destination
            </label>
          </div>
          <fieldset>
            <legend className="mb-2 text-sm font-medium text-ink">Edit strategy</legend>
            <div className="flex flex-wrap gap-4 text-sm text-ink">
              <label className="flex cursor-pointer items-center gap-2">
                <input
                  type="radio"
                  name="edit_strategy"
                  checked={editStrategy === 'replace_text'}
                  onChange={() => setEditStrategy('replace_text')}
                  className={checkboxClass}
                />
                Replace destination text
              </label>
              <label className="flex cursor-pointer items-center gap-2">
                <input
                  type="radio"
                  name="edit_strategy"
                  checked={editStrategy === 'append_notice'}
                  onChange={() => setEditStrategy('append_notice')}
                  className={checkboxClass}
                />
                Append notice (new message)
              </label>
            </div>
            <p className="mt-1 text-xs text-ink-subtle">
              Use &quot;Append notice&quot; when destination messages cannot be edited (for example,
              some media-only posts).
            </p>
          </fieldset>
          <Field label="Copy webhook URL" hint="Optional.">
            {(fieldProps) => (
              <Input
                {...fieldProps}
                type="url"
                value={copyWebhookUrl}
                onChange={(e) => setCopyWebhookUrl(e.target.value)}
                className="font-mono"
                placeholder="https://"
              />
            )}
          </Field>
          <div className="space-y-2">
            <Field
              label="Webhook secret"
              hint={
                webhookSecretPresent
                  ? 'Leave blank to keep the stored secret. Enter a new value to rotate it.'
                  : 'Optional.'
              }
            >
              {(fieldProps) => (
                <Input
                  {...fieldProps}
                  type="password"
                  value={copyWebhookSecret}
                  onChange={(e) => setCopyWebhookSecret(e.target.value)}
                  className="font-mono"
                  autoComplete="off"
                />
              )}
            </Field>
            {webhookSecretPresent ? (
              <label className="flex cursor-pointer items-center gap-2 text-sm text-ink">
                <input
                  type="checkbox"
                  checked={clearWebhookSecret}
                  onChange={(e) => {
                    setClearWebhookSecret(e.target.checked);
                    if (e.target.checked) setCopyWebhookSecret('');
                  }}
                  className={checkboxClass}
                />
                Clear stored webhook secret
              </label>
            ) : null}
          </div>
          <Field
            label="Webhook payload template (JSON)"
            hint={`Available variables: ${WEBHOOK_TEMPLATE_TOKENS.map((t) => t.value).join(', ')}. Use quoted placeholders for string values and unquoted placeholders for numbers or arrays.`}
          >
            {(fieldProps) => (
              <>
                <div className="mb-2 flex flex-wrap gap-2">
                  <Select
                    aria-label="Select webhook template variable"
                    value={selectedWebhookToken}
                    onChange={(e) => setSelectedWebhookToken(e.target.value)}
                    className="font-mono"
                  >
                    {WEBHOOK_TEMPLATE_TOKENS.map((tok) => (
                      <option key={tok.value} value={tok.value}>
                        {tok.label}
                      </option>
                    ))}
                  </Select>
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    onClick={() => insertWebhookToken(selectedWebhookToken)}
                  >
                    Insert variable
                  </Button>
                </div>
                <Textarea
                  {...fieldProps}
                  ref={payloadTemplateRef}
                  value={copyWebhookPayloadTemplate}
                  onChange={(e) => setCopyWebhookPayloadTemplate(e.target.value)}
                  rows={5}
                  className="min-h-24 font-mono"
                  placeholder='{"event":"{{event}}","mapping_id":"{{mapping_id}}"}'
                />
              </>
            )}
          </Field>
          <Field label="Webhook secret mode">
            {(fieldProps) => (
              <Select
                {...fieldProps}
                value={copyWebhookSecretMode}
                onChange={(e) => setCopyWebhookSecretMode(e.target.value)}
                className="max-w-xs"
              >
                <option value="hmac_sha256">HMAC SHA-256 signature</option>
                <option value="header_value">Custom header value</option>
                <option value="none">No secret header</option>
              </Select>
            )}
          </Field>
          <Field label="Webhook secret header name">
            {(fieldProps) => (
              <Input
                {...fieldProps}
                type="text"
                value={copyWebhookSecretHeaderName}
                onChange={(e) => setCopyWebhookSecretHeaderName(e.target.value)}
                className="font-mono"
                placeholder="X-Webhook-Secret"
              />
            )}
          </Field>
          <div className="space-y-2">
            <Field
              label="Webhook secret header value"
              hint={
                webhookHeaderSecretPresent
                  ? 'Leave blank to keep the stored value. Enter a new value to rotate it.'
                  : 'Optional.'
              }
            >
              {(fieldProps) => (
                <Input
                  {...fieldProps}
                  type="password"
                  value={copyWebhookSecretHeaderValue}
                  onChange={(e) => setCopyWebhookSecretHeaderValue(e.target.value)}
                  className="font-mono"
                  autoComplete="off"
                />
              )}
            </Field>
            {webhookHeaderSecretPresent ? (
              <label className="flex cursor-pointer items-center gap-2 text-sm text-ink">
                <input
                  type="checkbox"
                  checked={clearWebhookHeaderSecret}
                  onChange={(e) => {
                    setClearWebhookHeaderSecret(e.target.checked);
                    if (e.target.checked) setCopyWebhookSecretHeaderValue('');
                  }}
                  className={checkboxClass}
                />
                Clear stored webhook header secret value
              </label>
            ) : null}
          </div>
        </fieldset>
      </form>
    </Modal>
  );
}
