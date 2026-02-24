import { z } from 'zod';

export const RULE_TYPES = [
  { value: 'text', label: 'Text replace' },
  { value: 'regex', label: 'Regex replace' },
  { value: 'emoji', label: 'Emoji replace' },
  { value: 'media', label: 'Media replacement' },
  { value: 'template', label: 'Template' },
] as const;

export const MEDIA_TYPE_OPTIONS = [
  { value: 'text', label: 'Text' },
  { value: 'photo', label: 'Photo' },
  { value: 'video', label: 'Video' },
  { value: 'voice', label: 'Voice' },
  { value: 'other', label: 'Other' },
  { value: 'any', label: 'Any' },
];

export const REGEX_FLAGS = [
  { value: 'i', label: 'Case insensitive' },
  { value: 'm', label: 'Multiline' },
  { value: 's', label: 'Dot matches newline' },
];

export const TEMPLATE_VARIABLES = [
  '{{original_text}}',
  '{{text}}',
  '{{source_chat_id}}',
  '{{dest_chat_id}}',
  '{{source_chat_title}}',
  '{{dest_chat_title}}',
  '{{message_id}}',
  '{{media_type}}',
  '{{date_utc}}',
];

const baseSchema = z.object({
  rule_type: z.enum(['text', 'regex', 'emoji', 'media', 'template']),
  enabled: z.boolean(),
  priority: z.number().int().min(0),
  find_text: z.string().optional(),
  replace_text: z.string().optional(),
  regex_pattern: z.string().optional(),
  regex_flags: z.string().optional(),
  replacement_media_asset_id: z.number().nullable().optional(),
  apply_to_media_types: z.string().optional(),
});

export const transformFormSchema = baseSchema
  .refine(
    (data) =>
      (data.rule_type !== 'text' && data.rule_type !== 'emoji') || !!data.find_text?.trim(),
    { message: 'Find text is required for text/emoji rules' }
  )
  .refine(
    (data) => data.rule_type !== 'regex' || !!data.regex_pattern?.trim(),
    { message: 'Regex pattern is required' }
  )
  .refine(
    (data) => data.rule_type !== 'template' || !!data.replace_text?.trim(),
    { message: 'Replace text (template) is required' }
  )
  .refine(
    (data) =>
      data.rule_type !== 'media' ||
      (data.replacement_media_asset_id != null && data.replacement_media_asset_id > 0),
    { message: 'Media asset is required for media replacement rules' }
  );

export type TransformFormValues = z.infer<typeof transformFormSchema>;
