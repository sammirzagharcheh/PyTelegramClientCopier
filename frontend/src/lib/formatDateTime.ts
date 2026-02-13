export function formatLocalDateTime(value: string | null | undefined): string {
  if (value == null || value === '') return '—';
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString();
}
