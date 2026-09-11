import { useState } from 'react';
import { MEDIA_OPTIONS, mediaArrayToString } from '../lib/mediaTypes';
import { Button } from './ui/Button';
import { Field, Input } from './ui/Field';
import { FormError } from './ui/FormError';

export type FilterFormValues = {
  include_text: string;
  exclude_text: string;
  media_types: string[];
  regex_pattern: string;
  /** Same number = OR within that group; different numbers = AND between groups. Omit on create for a new unique group. */
  or_group_id?: number;
  /** Comma-separated numeric sender IDs (Telegram user ids). */
  allowed_sender_ids: string;
  /** Comma-separated usernames without @; server matches case-insensitively. */
  denied_usernames: string;
  min_url_count: string;
  max_url_count: string;
  /** Comma-separated hashtags (with or without leading #; server normalizes). */
  required_hashtags: string;
};

export { formatMediaDisplay, mediaArrayToString, stringToMediaArray } from '../lib/mediaTypes';

const emptyExtra = {
  allowed_sender_ids: '',
  denied_usernames: '',
  min_url_count: '',
  max_url_count: '',
  required_hashtags: '',
};

const EXAMPLES: { label: string; values: FilterFormValues }[] = [
  {
    label: 'Text only',
    values: { include_text: '', exclude_text: '', media_types: ['text'], regex_pattern: '', ...emptyExtra },
  },
  {
    label: 'Voice and video only',
    values: {
      include_text: '',
      exclude_text: '',
      media_types: ['voice', 'video'],
      regex_pattern: '',
      ...emptyExtra,
    },
  },
  {
    label: 'Must contain "announcement", exclude "spam"',
    values: {
      include_text: 'announcement',
      exclude_text: 'spam',
      media_types: [],
      regex_pattern: '',
      ...emptyExtra,
    },
  },
];

type Props = {
  initialValues?: Partial<FilterFormValues>;
  onSubmit: (values: FilterFormValues) => void | Promise<void>;
  onCancel?: () => void;
  submitLabel?: string;
  isSubmitting?: boolean;
};

export function FilterForm({
  initialValues,
  onSubmit,
  onCancel,
  submitLabel = 'Save',
  isSubmitting = false,
}: Props) {
  const [includeText, setIncludeText] = useState(initialValues?.include_text ?? '');
  const [excludeText, setExcludeText] = useState(initialValues?.exclude_text ?? '');
  const [mediaTypes, setMediaTypes] = useState<string[]>(
    initialValues?.media_types?.length ? initialValues.media_types : []
  );
  const [regexPattern, setRegexPattern] = useState(initialValues?.regex_pattern ?? '');
  const [allowedSenderIds, setAllowedSenderIds] = useState(initialValues?.allowed_sender_ids ?? '');
  const [deniedUsernames, setDeniedUsernames] = useState(initialValues?.denied_usernames ?? '');
  const [minUrlCount, setMinUrlCount] = useState(
    initialValues?.min_url_count != null && initialValues.min_url_count !== ''
      ? String(initialValues.min_url_count)
      : ''
  );
  const [maxUrlCount, setMaxUrlCount] = useState(
    initialValues?.max_url_count != null && initialValues.max_url_count !== ''
      ? String(initialValues.max_url_count)
      : ''
  );
  const [requiredHashtags, setRequiredHashtags] = useState(initialValues?.required_hashtags ?? '');
  const [orGroupId, setOrGroupId] = useState(
    () =>
      initialValues?.or_group_id != null && initialValues.or_group_id !== undefined
        ? String(initialValues.or_group_id)
        : ''
  );
  const [error, setError] = useState('');

  const toggleMedia = (value: string) => {
    setMediaTypes((prev) =>
      prev.includes(value) ? prev.filter((v) => v !== value) : [...prev, value]
    );
  };

  const applyPreset = (preset: FilterFormValues) => {
    setIncludeText(preset.include_text);
    setExcludeText(preset.exclude_text);
    setMediaTypes(preset.media_types);
    setRegexPattern(preset.regex_pattern);
    setAllowedSenderIds(preset.allowed_sender_ids ?? '');
    setDeniedUsernames(preset.denied_usernames ?? '');
    setMinUrlCount(preset.min_url_count ?? '');
    setMaxUrlCount(preset.max_url_count ?? '');
    setRequiredHashtags(preset.required_hashtags ?? '');
    if (preset.or_group_id != null) setOrGroupId(String(preset.or_group_id));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    const mediaStr = mediaArrayToString(mediaTypes);
    const hasInclude = includeText.trim().length > 0;
    const hasExclude = excludeText.trim().length > 0;
    const hasMedia = mediaStr.length > 0;
    const hasRegex = regexPattern.trim().length > 0;
    const hasSenders = allowedSenderIds.trim().length > 0;
    const hasDenied = deniedUsernames.trim().length > 0;
    const hasUrls = minUrlCount.trim().length > 0 || maxUrlCount.trim().length > 0;
    const hasTags = requiredHashtags.trim().length > 0;
    if (
      !hasInclude &&
      !hasExclude &&
      !hasMedia &&
      !hasRegex &&
      !hasSenders &&
      !hasDenied &&
      !hasUrls &&
      !hasTags
    ) {
      setError('Set at least one rule, otherwise this filter would do nothing.');
      return;
    }
    let minU: number | undefined;
    let maxU: number | undefined;
    if (minUrlCount.trim() !== '') {
      const n = parseInt(minUrlCount.trim(), 10);
      if (Number.isNaN(n) || n < 0) {
        setError('Min URL count must be a non-negative integer.');
        return;
      }
      minU = n;
    }
    if (maxUrlCount.trim() !== '') {
      const n = parseInt(maxUrlCount.trim(), 10);
      if (Number.isNaN(n) || n < 0) {
        setError('Max URL count must be a non-negative integer.');
        return;
      }
      maxU = n;
    }
    if (minU !== undefined && maxU !== undefined && minU > maxU) {
      setError('Min URL count cannot be greater than max URL count.');
      return;
    }
    if (hasRegex) {
      try {
        new RegExp(regexPattern.trim());
      } catch {
        setError('Invalid regex pattern.');
        return;
      }
    }
    let parsedGroup: number | undefined;
    const g = orGroupId.trim();
    if (g !== '') {
      const n = parseInt(g, 10);
      if (Number.isNaN(n) || n < 0) {
        setError('OR group must be a non-negative integer.');
        return;
      }
      parsedGroup = n;
    } else if (initialValues?.or_group_id != null) {
      parsedGroup = initialValues.or_group_id;
    }
    const payload: FilterFormValues = {
      include_text: includeText.trim() || '',
      exclude_text: excludeText.trim() || '',
      media_types: mediaTypes,
      regex_pattern: regexPattern.trim() || '',
      allowed_sender_ids: allowedSenderIds.trim(),
      denied_usernames: deniedUsernames.trim(),
      min_url_count: minUrlCount.trim(),
      max_url_count: maxUrlCount.trim(),
      required_hashtags: requiredHashtags.trim(),
    };
    if (parsedGroup !== undefined) {
      payload.or_group_id = parsedGroup;
    }
    onSubmit(payload);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <FormError message={error} />

      <Field label="Message must contain" hint="Only copy messages containing this text.">
        {(fieldProps) => (
          <Input
            {...fieldProps}
            type="text"
            value={includeText}
            onChange={(e) => setIncludeText(e.target.value)}
            placeholder="announcement"
          />
        )}
      </Field>

      <Field label="Message must not contain" hint="Skip messages containing this text.">
        {(fieldProps) => (
          <Input
            {...fieldProps}
            type="text"
            value={excludeText}
            onChange={(e) => setExcludeText(e.target.value)}
            placeholder="spam"
          />
        )}
      </Field>

      <fieldset>
        <legend className="text-sm font-medium text-ink">Allowed media types</legend>
        <p className="mt-1 mb-2 text-xs text-ink-subtle">
          Leave every box clear to allow any type.
        </p>
        <div className="flex flex-wrap gap-x-4 gap-y-2">
          {MEDIA_OPTIONS.map((opt) => (
            <label key={opt.value} className="flex cursor-pointer items-center gap-2 text-sm text-ink">
              <input
                type="checkbox"
                checked={mediaTypes.includes(opt.value)}
                onChange={() => toggleMedia(opt.value)}
                className="h-4 w-4 rounded border-line-strong accent-[var(--accent)]"
              />
              {opt.label}
            </label>
          ))}
        </div>
      </fieldset>

      <Field
        label="Allowed sender IDs"
        hint="Comma-separated numeric Telegram user IDs. The message must be from one of these senders."
      >
        {(fieldProps) => (
          <Input
            {...fieldProps}
            type="text"
            value={allowedSenderIds}
            onChange={(e) => setAllowedSenderIds(e.target.value)}
            className="font-mono"
            placeholder="123456789, 987654321"
          />
        )}
      </Field>

      <Field
        label="Denied usernames"
        hint="Comma-separated usernames without @. Skip the message if the sender matches."
      >
        {(fieldProps) => (
          <Input
            {...fieldProps}
            type="text"
            value={deniedUsernames}
            onChange={(e) => setDeniedUsernames(e.target.value)}
            className="font-mono"
            placeholder="spam_bot, bad_actor"
          />
        )}
      </Field>

      <div className="grid grid-cols-2 gap-3">
        <Field label="Min URL count">
          {(fieldProps) => (
            <Input
              {...fieldProps}
              type="number"
              min={0}
              value={minUrlCount}
              onChange={(e) => setMinUrlCount(e.target.value)}
              placeholder="optional"
              className="tabular-nums"
            />
          )}
        </Field>
        <Field label="Max URL count">
          {(fieldProps) => (
            <Input
              {...fieldProps}
              type="number"
              min={0}
              value={maxUrlCount}
              onChange={(e) => setMaxUrlCount(e.target.value)}
              placeholder="optional"
              className="tabular-nums"
            />
          )}
        </Field>
      </div>

      <Field
        label="Required hashtags"
        hint="The message must contain all listed tags. A leading # is optional."
      >
        {(fieldProps) => (
          <Input
            {...fieldProps}
            type="text"
            value={requiredHashtags}
            onChange={(e) => setRequiredHashtags(e.target.value)}
            placeholder="news, breaking"
          />
        )}
      </Field>

      <Field
        label="Regex pattern"
        hint="Advanced. Message text must match this pattern. Leave empty to allow any."
      >
        {(fieldProps) => (
          <Input
            {...fieldProps}
            type="text"
            value={regexPattern}
            onChange={(e) => setRegexPattern(e.target.value)}
            className="font-mono"
            placeholder="#[0-9]+"
          />
        )}
      </Field>

      <Field
        label="OR group"
        hint="Filters with the same group number match as OR (any can match). Different group numbers are combined with AND. Leave empty when adding a filter to start a new group."
      >
        {(fieldProps) => (
          <Input
            {...fieldProps}
            type="number"
            min={0}
            value={orGroupId}
            onChange={(e) => setOrGroupId(e.target.value)}
            className="max-w-[12rem] tabular-nums"
            placeholder="1 (optional)"
          />
        )}
      </Field>

      <details className="rounded-control border border-line">
        <summary className="cursor-pointer px-3 py-2 text-sm text-ink-muted">
          Start from an example
        </summary>
        <div className="border-t border-line p-1.5">
          {EXAMPLES.map((ex) => (
            <button
              key={ex.label}
              type="button"
              onClick={() => applyPreset(ex.values)}
              className="block w-full rounded-control px-2.5 py-1.5 text-left text-sm text-ink-muted transition-colors hover:bg-surface-hover hover:text-ink"
            >
              {ex.label}
            </button>
          ))}
        </div>
      </details>

      <div className="flex justify-end gap-2 pt-1">
        {onCancel && (
          <Button variant="secondary" onClick={onCancel}>
            Cancel
          </Button>
        )}
        <Button type="submit" isLoading={isSubmitting}>
          {submitLabel}
        </Button>
      </div>
    </form>
  );
}
