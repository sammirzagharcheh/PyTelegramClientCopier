import { useState } from 'react';

const MEDIA_OPTIONS = [
  { value: 'text', label: 'Text' },
  { value: 'voice', label: 'Voice' },
  { value: 'video', label: 'Video' },
  { value: 'photo', label: 'Photo' },
  { value: 'other', label: 'Other' },
];

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

function mediaArrayToString(arr: string[]): string {
  return arr.filter(Boolean).join(',');
}

function stringToMediaArray(s: string | null): string[] {
  if (!s) return [];
  return s.split(',').map((x) => x.trim().toLowerCase()).filter(Boolean);
}

function formatMediaDisplay(s: string | null): string {
  if (!s) return '—';
  return stringToMediaArray(s)
    .map((v) => MEDIA_OPTIONS.find((o) => o.value === v)?.label ?? v)
    .join(', ');
}

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

  const EXAMPLES: { label: string; values: FilterFormValues }[] = [
    {
      label: 'Text only',
      values: {
        include_text: '',
        exclude_text: '',
        media_types: ['text'],
        regex_pattern: '',
        allowed_sender_ids: '',
        denied_usernames: '',
        min_url_count: '',
        max_url_count: '',
        required_hashtags: '',
      },
    },
    {
      label: 'Voice and video only',
      values: {
        include_text: '',
        exclude_text: '',
        media_types: ['voice', 'video'],
        regex_pattern: '',
        allowed_sender_ids: '',
        denied_usernames: '',
        min_url_count: '',
        max_url_count: '',
        required_hashtags: '',
      },
    },
    {
      label: 'Must contain "announcement", exclude "spam"',
      values: {
        include_text: 'announcement',
        exclude_text: 'spam',
        media_types: [],
        regex_pattern: '',
        allowed_sender_ids: '',
        denied_usernames: '',
        min_url_count: '',
        max_url_count: '',
        required_hashtags: '',
      },
    },
  ];

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
    if (!hasInclude && !hasExclude && !hasMedia && !hasRegex && !hasSenders && !hasDenied && !hasUrls && !hasTags) {
      setError('At least one filter rule is required.');
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
      {error && (
        <div className="p-3 rounded bg-red-50 dark:bg-red-900/20 text-red-600 text-sm">{error}</div>
      )}

      <div>
        <label className="flex items-center gap-2 text-sm font-medium mb-1">
          Message must contain
          <span
            title="Only copy messages that contain this text"
            className="text-gray-400 hover:text-gray-600 cursor-help"
          >
            (?)
          </span>
        </label>
        <input
          type="text"
          value={includeText}
          onChange={(e) => setIncludeText(e.target.value)}
          className="w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700"
          placeholder="e.g. announcement"
        />
      </div>

      <div>
        <label className="flex items-center gap-2 text-sm font-medium mb-1">
          Message must NOT contain
          <span
            title="Skip messages containing this text"
            className="text-gray-400 hover:text-gray-600 cursor-help"
          >
            (?)
          </span>
        </label>
        <input
          type="text"
          value={excludeText}
          onChange={(e) => setExcludeText(e.target.value)}
          className="w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700"
          placeholder="e.g. spam"
        />
      </div>

      <div>
        <label className="flex items-center gap-2 text-sm font-medium mb-1">
          Allowed media types
          <span
            title="Only copy messages of these types; leave all unchecked to allow any"
            className="text-gray-400 hover:text-gray-600 cursor-help"
          >
            (?)
          </span>
        </label>
        <div className="flex flex-wrap gap-2">
          {MEDIA_OPTIONS.map((opt) => (
            <label key={opt.value} className="flex items-center gap-1 cursor-pointer">
              <input
                type="checkbox"
                checked={mediaTypes.includes(opt.value)}
                onChange={() => toggleMedia(opt.value)}
                className="rounded border-gray-300"
              />
              <span className="text-sm">{opt.label}</span>
            </label>
          ))}
        </div>
      </div>

      <div>
        <label className="flex items-center gap-2 text-sm font-medium mb-1">
          Allowed sender IDs
          <span
            title="Comma-separated numeric Telegram user IDs; message must be from one of these senders"
            className="text-gray-400 hover:text-gray-600 cursor-help"
          >
            (?)
          </span>
        </label>
        <input
          type="text"
          value={allowedSenderIds}
          onChange={(e) => setAllowedSenderIds(e.target.value)}
          className="w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 font-mono text-sm"
          placeholder="e.g. 123456789, 987654321"
        />
      </div>

      <div>
        <label className="flex items-center gap-2 text-sm font-medium mb-1">
          Denied usernames
          <span title="Comma-separated usernames without @; skip if sender matches" className="text-gray-400 hover:text-gray-600 cursor-help">
            (?)
          </span>
        </label>
        <input
          type="text"
          value={deniedUsernames}
          onChange={(e) => setDeniedUsernames(e.target.value)}
          className="w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 font-mono text-sm"
          placeholder="e.g. spam_bot, bad_actor"
        />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-sm font-medium mb-1">Min URL count</label>
          <input
            type="number"
            min={0}
            value={minUrlCount}
            onChange={(e) => setMinUrlCount(e.target.value)}
            className="w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700"
            placeholder="optional"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Max URL count</label>
          <input
            type="number"
            min={0}
            value={maxUrlCount}
            onChange={(e) => setMaxUrlCount(e.target.value)}
            className="w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700"
            placeholder="optional"
          />
        </div>
      </div>

      <div>
        <label className="flex items-center gap-2 text-sm font-medium mb-1">
          Required hashtags
          <span title="Message must contain all listed tags; # is optional in the list" className="text-gray-400 hover:text-gray-600 cursor-help">
            (?)
          </span>
        </label>
        <input
          type="text"
          value={requiredHashtags}
          onChange={(e) => setRequiredHashtags(e.target.value)}
          className="w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700"
          placeholder="e.g. news, breaking"
        />
      </div>

      <div>
        <label className="flex items-center gap-2 text-sm font-medium mb-1">
          Regex pattern (advanced)
          <span
            title="Message text must match this regex; leave empty to allow any"
            className="text-gray-400 hover:text-gray-600 cursor-help"
          >
            (?)
          </span>
        </label>
        <input
          type="text"
          value={regexPattern}
          onChange={(e) => setRegexPattern(e.target.value)}
          className="w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 font-mono text-sm"
          placeholder="e.g. #[0-9]+"
        />
      </div>

      <div>
        <label className="flex items-center gap-2 text-sm font-medium mb-1">
          OR group
          <span
            title="Filters with the same group number match as OR (any can match). Different group numbers are combined with AND. Leave empty when adding a filter to start a new group."
            className="text-gray-400 hover:text-gray-600 cursor-help"
          >
            (?)
          </span>
        </label>
        <input
          type="number"
          min={0}
          value={orGroupId}
          onChange={(e) => setOrGroupId(e.target.value)}
          className="w-full max-w-[12rem] px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700"
          placeholder="e.g. 1 (optional)"
        />
        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
          Leave empty for a new filter: each filter gets its own group by default (same as AND across filters).
        </p>
      </div>

      <details className="border border-gray-200 dark:border-gray-600 rounded p-2">
        <summary className="cursor-pointer text-sm text-gray-600 dark:text-gray-400">
          Examples
        </summary>
        <div className="mt-2 space-y-1">
          {EXAMPLES.map((ex) => (
            <button
              key={ex.label}
              type="button"
              onClick={() => applyPreset(ex.values)}
              className="block w-full text-left px-2 py-1.5 text-sm rounded hover:bg-gray-100 dark:hover:bg-gray-700"
            >
              {ex.label}
            </button>
          ))}
        </div>
      </details>

      <div className="flex gap-2 justify-end pt-2">
        {onCancel && (
          <button type="button" onClick={onCancel} className="px-4 py-2 rounded border border-gray-300 dark:border-gray-600">
            Cancel
          </button>
        )}
        <button
          type="submit"
          disabled={isSubmitting}
          className="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {submitLabel}
        </button>
      </div>
    </form>
  );
}

export { formatMediaDisplay, mediaArrayToString, stringToMediaArray };
