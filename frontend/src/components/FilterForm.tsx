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
};

const EXAMPLES: { label: string; values: FilterFormValues }[] = [
  {
    label: 'Text only',
    values: { include_text: '', exclude_text: '', media_types: ['text'], regex_pattern: '' },
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

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    const mediaStr = mediaArrayToString(mediaTypes);
    const hasInclude = includeText.trim().length > 0;
    const hasExclude = excludeText.trim().length > 0;
    const hasMedia = mediaStr.length > 0;
    const hasRegex = regexPattern.trim().length > 0;
    if (!hasInclude && !hasExclude && !hasMedia && !hasRegex) {
      setError('Set at least one rule, otherwise this filter would do nothing.');
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
