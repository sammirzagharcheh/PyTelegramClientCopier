export const MEDIA_OPTIONS = [
  { value: 'text', label: 'Text' },
  { value: 'voice', label: 'Voice' },
  { value: 'video', label: 'Video' },
  { value: 'photo', label: 'Photo' },
  { value: 'other', label: 'Other' },
];

export function mediaArrayToString(arr: string[]): string {
  return arr.filter(Boolean).join(',');
}

export function stringToMediaArray(s: string | null): string[] {
  if (!s) return [];
  return s
    .split(',')
    .map((x) => x.trim().toLowerCase())
    .filter(Boolean);
}

export function formatMediaDisplay(s: string | null): string {
  if (!s) return 'Any';
  return stringToMediaArray(s)
    .map((v) => MEDIA_OPTIONS.find((o) => o.value === v)?.label ?? v)
    .join(', ');
}
