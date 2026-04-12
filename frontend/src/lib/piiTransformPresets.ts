import type { TransformCreate } from './api';

export type PiiTransformPreset = {
  id: string;
  label: string;
  description: string;
  payload: TransformCreate;
};

/** Client-side helpers only: each preset becomes a normal `regex` transform via the API. Patterns may false-positive; tune as needed. */
export const PII_TRANSFORM_PRESETS: PiiTransformPreset[] = [
  {
    id: 'email',
    label: 'Redact emails',
    description: 'Masks common email shapes (may match non-emails).',
    payload: {
      rule_type: 'regex',
      regex_pattern: String.raw`[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}`,
      replace_text: '[redacted-email]',
      regex_flags: 'i',
      enabled: true,
      priority: 100,
    },
  },
  {
    id: 'phone',
    label: 'Redact phone-like numbers',
    description: 'Loose digit runs with separators; review before production traffic.',
    payload: {
      rule_type: 'regex',
      regex_pattern: String.raw`\+?\d[\d\s().-]{7,}\d`,
      replace_text: '[redacted-phone]',
      regex_flags: '',
      enabled: true,
      priority: 101,
    },
  },
  {
    id: 'api_key',
    label: 'Redact API key hints',
    description: 'Matches common `key=` / `token=` style assignments; high false-positive risk.',
    payload: {
      rule_type: 'regex',
      regex_pattern: String.raw`(?i)\b(api[_-]?key|secret|token|password)\s*[:=]\s*['"]?[\w-]{8,}['"]?`,
      replace_text: '[redacted-secret]',
      regex_flags: '',
      enabled: true,
      priority: 102,
    },
  },
];
