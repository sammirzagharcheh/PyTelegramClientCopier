import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import type { MediaAsset, Transform, TransformCreate } from '../lib/api';
import {
  transformFormSchema,
  type TransformFormValues,
  RULE_TYPES,
  MEDIA_TYPE_OPTIONS,
  REGEX_FLAGS,
  TEMPLATE_VARIABLES,
} from '../lib/transformTypes';
import { mediaArrayToString, stringToMediaArray } from './FilterForm';

type Props = {
  initialValues?: Transform | null;
  mediaAssets: MediaAsset[];
  onSubmit: (values: TransformCreate) => void | Promise<void>;
  onCancel?: () => void;
  submitLabel?: string;
  isSubmitting?: boolean;
};

export function TransformForm({
  initialValues,
  mediaAssets,
  onSubmit,
  onCancel,
  submitLabel = 'Save',
  isSubmitting = false,
}: Props) {
  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors },
  } = useForm<TransformFormValues>({
    resolver: zodResolver(transformFormSchema),
    defaultValues: {
      rule_type: initialValues?.rule_type ?? 'text',
      find_text: initialValues?.find_text ?? '',
      replace_text: initialValues?.replace_text ?? '',
      regex_pattern: initialValues?.regex_pattern ?? '',
      regex_flags: initialValues?.regex_flags ?? '',
      replacement_media_asset_id: initialValues?.replacement_media_asset_id ?? null,
      apply_to_media_types: initialValues?.apply_to_media_types ?? '',
      enabled: initialValues?.enabled ?? true,
      priority: initialValues?.priority ?? 100,
    },
  });

  const ruleType = watch('rule_type');
  const applyToMediaTypes = watch('apply_to_media_types');
  const mediaTypesArr = stringToMediaArray(applyToMediaTypes ?? null);

  useEffect(() => {
    if (initialValues) {
      reset({
        rule_type: initialValues.rule_type as TransformFormValues['rule_type'],
        find_text: initialValues.find_text ?? '',
        replace_text: initialValues.replace_text ?? '',
        regex_pattern: initialValues.regex_pattern ?? '',
        regex_flags: initialValues.regex_flags ?? '',
        replacement_media_asset_id: initialValues.replacement_media_asset_id ?? null,
        apply_to_media_types: initialValues.apply_to_media_types ?? '',
        enabled: initialValues.enabled,
        priority: initialValues.priority,
      });
    }
  }, [initialValues, reset]);

  const toggleMediaType = (value: string) => {
    const next = mediaTypesArr.includes(value)
      ? mediaTypesArr.filter((v) => v !== value)
      : [...mediaTypesArr, value];
    setValue('apply_to_media_types', mediaArrayToString(next) || undefined);
  };

  const toggleRegexFlag = (value: string) => {
    const current = watch('regex_flags') ?? '';
    const arr = current.split('').filter(Boolean);
    const next = arr.includes(value)
      ? arr.filter((c) => c !== value)
      : [...arr, value].sort();
    setValue('regex_flags', next.join('') || undefined);
  };

  const buildPayload = (values: TransformFormValues): TransformCreate => {
    const base: TransformCreate = {
      rule_type: values.rule_type,
      enabled: values.enabled,
      priority: values.priority,
    };
    if (values.rule_type === 'text' || values.rule_type === 'emoji') {
      base.find_text = values.find_text?.trim() || null;
      base.replace_text = values.replace_text?.trim() || null;
    }
    if (values.rule_type === 'regex') {
      base.regex_pattern = values.regex_pattern?.trim() || null;
      base.replace_text = values.replace_text?.trim() || null;
      base.regex_flags = values.regex_flags?.trim() || null;
    }
    if (values.rule_type === 'template') {
      base.replace_text = values.replace_text?.trim() || null;
      base.apply_to_media_types = values.apply_to_media_types?.trim() || null;
    }
    if (values.rule_type === 'media') {
      const aid = values.replacement_media_asset_id;
      base.replacement_media_asset_id =
        aid != null && !Number.isNaN(aid) && aid > 0 ? aid : null;
      base.apply_to_media_types = values.apply_to_media_types?.trim() || null;
    }
    return base;
  };

  const handleFormSubmit = handleSubmit((values) => {
    onSubmit(buildPayload(values));
  });

  const showFindReplace = ruleType === 'text' || ruleType === 'emoji';
  const showRegex = ruleType === 'regex';
  const showMediaPicker = ruleType === 'media';
  const showTemplate = ruleType === 'template';
  const showApplyToMedia =
    ruleType === 'template' || ruleType === 'media';

  return (
    <form onSubmit={handleFormSubmit} className="space-y-4">
      {errors.root?.message && (
        <div className="p-3 rounded bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm">
          {errors.root.message}
        </div>
      )}

      <div>
        <label htmlFor="rule_type" className="block text-sm font-medium mb-1">
          Rule type
        </label>
        <select
          id="rule_type"
          {...register('rule_type')}
          className="w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700"
        >
          {RULE_TYPES.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>
      </div>

      {showFindReplace && (
        <>
          <div>
            <label htmlFor="find_text" className="block text-sm font-medium mb-1">
              Find text
              <span className="text-gray-400 ml-1" title="Exact text to find and replace">
                (?)
              </span>
            </label>
            <input
              id="find_text"
              type="text"
              {...register('find_text')}
              className="w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700"
              placeholder={ruleType === 'emoji' ? 'e.g. 🔥' : 'e.g. Sam channel'}
            />
            {errors.find_text && (
              <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.find_text.message}</p>
            )}
          </div>
          <div>
            <label htmlFor="replace_text_fr" className="block text-sm font-medium mb-1">
              Replace with
            </label>
            <input
              id="replace_text_fr"
              type="text"
              {...register('replace_text')}
              className="w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700"
              placeholder={ruleType === 'emoji' ? 'e.g. ⭐' : 'e.g. Tom channel'}
            />
          </div>
        </>
      )}

      {showRegex && (
        <>
          <div>
            <label htmlFor="regex_pattern" className="block text-sm font-medium mb-1">
              Regex pattern
            </label>
            <input
              id="regex_pattern"
              type="text"
              {...register('regex_pattern')}
              className="w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 font-mono text-sm"
              placeholder="e.g. #\d+"
            />
            {errors.regex_pattern && (
              <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.regex_pattern.message}</p>
            )}
          </div>
          <div>
            <label htmlFor="replace_text_re" className="block text-sm font-medium mb-1">
              Replace with
            </label>
            <input
              id="replace_text_re"
              type="text"
              {...register('replace_text')}
              className="w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700"
              placeholder="e.g. #XXX"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Flags</label>
            <div className="flex flex-wrap gap-2">
              {REGEX_FLAGS.map((f) => (
                <label key={f.value} className="flex items-center gap-1 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={(watch('regex_flags') ?? '').includes(f.value)}
                    onChange={() => toggleRegexFlag(f.value)}
                    className="rounded border-gray-300"
                  />
                  <span className="text-sm">{f.label}</span>
                </label>
              ))}
            </div>
          </div>
        </>
      )}

      {showMediaPicker && (
        <div>
          <label htmlFor="replacement_media_asset_id" className="block text-sm font-medium mb-1">
            Replacement media asset
          </label>
          <select
            id="replacement_media_asset_id"
            {...register('replacement_media_asset_id', { valueAsNumber: true })}
            className="w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700"
          >
            <option value="">-- Select asset --</option>
            {mediaAssets.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name} ({a.media_kind}, {(a.size_bytes / 1024).toFixed(1)} KB)
              </option>
            ))}
          </select>
          {mediaAssets.length === 0 && (
            <p className="mt-1 text-sm text-amber-600 dark:text-amber-400">
              No media assets. Upload assets on the Media Assets page first.
            </p>
          )}
          {errors.replacement_media_asset_id && (
            <p className="mt-1 text-sm text-red-600 dark:text-red-400">
              {errors.replacement_media_asset_id.message}
            </p>
          )}
        </div>
      )}

      {showTemplate && (
        <div>
          <label htmlFor="replace_text_tpl" className="block text-sm font-medium mb-1">
            Template
            <span
              className="text-gray-400 ml-1 cursor-help"
              title={`Variables: ${TEMPLATE_VARIABLES.join(', ')}`}
            >
              (?)
            </span>
          </label>
          <textarea
            id="replace_text_tpl"
            rows={3}
            {...register('replace_text')}
            className="w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 font-mono text-sm"
            placeholder="e.g. [{{source_chat_title}}] {{text}} (#{{message_id}})"
          />
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            Use {'{{'}variable{'}}'} placeholders: {TEMPLATE_VARIABLES.slice(0, 4).join(', ')}…
          </p>
          {errors.replace_text && (
            <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.replace_text.message}</p>
          )}
        </div>
      )}

      {showApplyToMedia && (
        <div>
          <label className="block text-sm font-medium mb-1">
            Apply to media types
            <span className="text-gray-400 ml-1" title="Leave empty to apply to all">
              (?)
            </span>
          </label>
          <div className="flex flex-wrap gap-2">
            {MEDIA_TYPE_OPTIONS.map((opt) => (
              <label key={opt.value} className="flex items-center gap-1 cursor-pointer">
                <input
                  type="checkbox"
                  checked={mediaTypesArr.includes(opt.value)}
                  onChange={() => toggleMediaType(opt.value)}
                  className="rounded border-gray-300"
                />
                <span className="text-sm">{opt.label}</span>
              </label>
            ))}
          </div>
        </div>
      )}

      <div className="flex gap-4">
        <div>
          <label htmlFor="priority" className="block text-sm font-medium mb-1">
            Priority
          </label>
          <input
            id="priority"
            type="number"
            min={0}
            {...register('priority', { valueAsNumber: true })}
            className="w-24 px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700"
          />
          <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">Lower runs first</p>
        </div>
        <div className="flex items-end pb-1">
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" {...register('enabled')} className="rounded border-gray-300" />
            <span className="text-sm">Enabled</span>
          </label>
        </div>
      </div>

      <div className="flex gap-2 justify-end pt-2">
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 rounded border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700"
          >
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
