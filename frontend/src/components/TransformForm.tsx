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
import { mediaArrayToString, stringToMediaArray } from '../lib/mediaTypes';
import { Button } from './ui/Button';
import { Field, Input, Select, Textarea } from './ui/Field';
import { FormError } from './ui/FormError';

type Props = {
  initialValues?: Transform | null;
  /** When adding a transform, pre-fill the form (e.g. PII regex presets). Ignored if `initialValues` is set. */
  createSeed?: TransformCreate | null;
  mediaAssets: MediaAsset[];
  onSubmit: (values: TransformCreate) => void | Promise<void>;
  onCancel?: () => void;
  submitLabel?: string;
  isSubmitting?: boolean;
};

const checkboxClass = 'h-4 w-4 rounded border-line-strong accent-[var(--accent)]';

const DEFAULT_FORM: TransformFormValues = {
  rule_type: 'text',
  find_text: '',
  replace_text: '',
  regex_pattern: '',
  regex_flags: '',
  replacement_media_asset_id: null,
  apply_to_media_types: '',
  enabled: true,
  priority: 100,
};

export function TransformForm({
  initialValues,
  createSeed = null,
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
      rule_type: initialValues?.rule_type ?? createSeed?.rule_type ?? DEFAULT_FORM.rule_type,
      find_text: initialValues?.find_text ?? createSeed?.find_text ?? DEFAULT_FORM.find_text,
      replace_text: initialValues?.replace_text ?? createSeed?.replace_text ?? DEFAULT_FORM.replace_text,
      regex_pattern: initialValues?.regex_pattern ?? createSeed?.regex_pattern ?? DEFAULT_FORM.regex_pattern,
      regex_flags: initialValues?.regex_flags ?? createSeed?.regex_flags ?? DEFAULT_FORM.regex_flags,
      replacement_media_asset_id:
        initialValues?.replacement_media_asset_id ??
        createSeed?.replacement_media_asset_id ??
        DEFAULT_FORM.replacement_media_asset_id,
      apply_to_media_types:
        initialValues?.apply_to_media_types ??
        createSeed?.apply_to_media_types ??
        DEFAULT_FORM.apply_to_media_types,
      enabled: initialValues?.enabled ?? createSeed?.enabled ?? DEFAULT_FORM.enabled,
      priority: initialValues?.priority ?? createSeed?.priority ?? DEFAULT_FORM.priority,
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
      return;
    }
    if (createSeed) {
      reset({
        rule_type: createSeed.rule_type as TransformFormValues['rule_type'],
        find_text: createSeed.find_text ?? '',
        replace_text: createSeed.replace_text ?? '',
        regex_pattern: createSeed.regex_pattern ?? '',
        regex_flags: createSeed.regex_flags ?? '',
        replacement_media_asset_id: createSeed.replacement_media_asset_id ?? null,
        apply_to_media_types: createSeed.apply_to_media_types ?? '',
        enabled: createSeed.enabled ?? true,
        priority: createSeed.priority ?? 100,
      });
    } else {
      reset({ ...DEFAULT_FORM });
    }
  }, [initialValues, createSeed, reset]);

  const toggleMediaType = (value: string) => {
    const next = mediaTypesArr.includes(value)
      ? mediaTypesArr.filter((v) => v !== value)
      : [...mediaTypesArr, value];
    setValue('apply_to_media_types', mediaArrayToString(next) || undefined);
  };

  const toggleRegexFlag = (value: string) => {
    const current = watch('regex_flags') ?? '';
    const arr = current.split('').filter(Boolean);
    const next = arr.includes(value) ? arr.filter((c) => c !== value) : [...arr, value].sort();
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
      base.replacement_media_asset_id = aid != null && !Number.isNaN(aid) && aid > 0 ? aid : null;
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
  const showApplyToMedia = ruleType === 'template' || ruleType === 'media';

  return (
    <form onSubmit={handleFormSubmit} className="space-y-4">
      <FormError message={errors.root?.message} />

      <Field label="Rule type">
        {(fieldProps) => (
          <Select {...fieldProps} {...register('rule_type')}>
            {RULE_TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </Select>
        )}
      </Field>

      {showFindReplace && (
        <>
          <Field
            label="Find text"
            hint="Matched exactly, as written."
            error={errors.find_text?.message}
          >
            {(fieldProps) => (
              <Input
                {...fieldProps}
                {...register('find_text')}
                type="text"
                invalid={Boolean(errors.find_text)}
                placeholder={ruleType === 'emoji' ? '🔥' : 'Sam channel'}
              />
            )}
          </Field>
          <Field label="Replace with">
            {(fieldProps) => (
              <Input
                {...fieldProps}
                {...register('replace_text')}
                type="text"
                placeholder={ruleType === 'emoji' ? '⭐' : 'Tom channel'}
              />
            )}
          </Field>
        </>
      )}

      {showRegex && (
        <>
          <Field label="Regex pattern" error={errors.regex_pattern?.message}>
            {(fieldProps) => (
              <Input
                {...fieldProps}
                {...register('regex_pattern')}
                type="text"
                className="font-mono"
                invalid={Boolean(errors.regex_pattern)}
                placeholder="#\\d+"
              />
            )}
          </Field>
          <Field label="Replace with">
            {(fieldProps) => (
              <Input
                {...fieldProps}
                {...register('replace_text')}
                type="text"
                placeholder="#XXX"
              />
            )}
          </Field>
          <fieldset>
            <legend className="mb-2 text-sm font-medium text-ink">Flags</legend>
            <div className="flex flex-wrap gap-x-4 gap-y-2">
              {REGEX_FLAGS.map((f) => (
                <label
                  key={f.value}
                  className="flex cursor-pointer items-center gap-2 text-sm text-ink"
                >
                  <input
                    type="checkbox"
                    checked={(watch('regex_flags') ?? '').includes(f.value)}
                    onChange={() => toggleRegexFlag(f.value)}
                    className={checkboxClass}
                  />
                  {f.label}
                </label>
              ))}
            </div>
          </fieldset>
        </>
      )}

      {showMediaPicker && (
        <Field
          label="Replacement media asset"
          error={errors.replacement_media_asset_id?.message}
          hint={
            mediaAssets.length === 0
              ? 'No assets yet. Upload one on the Media Assets page first.'
              : undefined
          }
        >
          {(fieldProps) => (
            <Select
              {...fieldProps}
              {...register('replacement_media_asset_id', { valueAsNumber: true })}
              invalid={Boolean(errors.replacement_media_asset_id)}
            >
              <option value="">Choose an asset</option>
              {mediaAssets.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name} ({a.media_kind}, {(a.size_bytes / 1024).toFixed(1)} KB)
                </option>
              ))}
            </Select>
          )}
        </Field>
      )}

      {showTemplate && (
        <Field
          label="Template"
          hint={`Placeholders: ${TEMPLATE_VARIABLES.map((v) => `{{${v}}}`).join(', ')}`}
          error={errors.replace_text?.message}
        >
          {(fieldProps) => (
            <Textarea
              {...fieldProps}
              {...register('replace_text')}
              rows={3}
              className="font-mono"
              invalid={Boolean(errors.replace_text)}
              placeholder="[{{source_chat_title}}] {{text}} (#{{message_id}})"
            />
          )}
        </Field>
      )}

      {showApplyToMedia && (
        <fieldset>
          <legend className="text-sm font-medium text-ink">Apply to media types</legend>
          <p className="mt-1 mb-2 text-xs text-ink-subtle">
            Leave every box clear to apply to all types.
          </p>
          <div className="flex flex-wrap gap-x-4 gap-y-2">
            {MEDIA_TYPE_OPTIONS.map((opt) => (
              <label
                key={opt.value}
                className="flex cursor-pointer items-center gap-2 text-sm text-ink"
              >
                <input
                  type="checkbox"
                  checked={mediaTypesArr.includes(opt.value)}
                  onChange={() => toggleMediaType(opt.value)}
                  className={checkboxClass}
                />
                {opt.label}
              </label>
            ))}
          </div>
        </fieldset>
      )}

      <div className="flex flex-wrap items-end gap-6">
        <Field label="Priority" hint="Lower numbers run first." className="w-28">
          {(fieldProps) => (
            <Input
              {...fieldProps}
              {...register('priority', { valueAsNumber: true })}
              type="number"
              min={0}
              className="tabular-nums"
            />
          )}
        </Field>
        <label className="flex cursor-pointer items-center gap-2 pb-1.5 text-sm text-ink">
          <input type="checkbox" {...register('enabled')} className={checkboxClass} />
          Enabled
        </label>
      </div>

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
