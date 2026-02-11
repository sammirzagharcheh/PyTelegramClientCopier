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
  };

  const EXAMPLES: { label: string; values: FilterFormValues }[] = [
    {
      label: 'Text only',
      values: {
        include_text: '',
        exclude_text: '',
        media_types: ['text'],
        regex_pattern: '',
      },
    },
    {
      label: 'Voice and video only',
      values: {
        include_text: '',
        exclude_text: '',
        media_types: ['voice', 'video'],
        regex_pattern: '',
      },
    },
    {
      label: 'Must contain "announcement", exclude "spam"',
      values: {
        include_text: 'announcement',
        exclude_text: 'spam',
        media_types: [],
        regex_pattern: '',
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
    if (!hasInclude && !hasExclude && !hasMedia && !hasRegex) {
      setError('At least one filter rule is required.');
      return;
    }
    onSubmit({
      include_text: includeText.trim() || '',
      exclude_text: excludeText.trim() || '',
      media_types: mediaTypes,
      regex_pattern: regexPattern.trim() || '',
    });
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
