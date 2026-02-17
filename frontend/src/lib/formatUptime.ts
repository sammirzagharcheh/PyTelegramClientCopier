/**
 * Format uptime duration from an ISO timestamp.
 * Returns human-readable string like "2h 15m" or "45m".
 */
export function formatUptime(iso: string | null | undefined): string {
  if (iso == null || iso === '') return '—';
  const started = new Date(iso);
  if (Number.isNaN(started.getTime())) return '—';
  const now = Date.now();
  const sec = Math.floor((now - started.getTime()) / 1000);
  if (sec < 0) return '—';
  if (sec < 60) return `${sec}s`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m`;
  const h = Math.floor(min / 60);
  const m = min % 60;
  if (h < 24) return m > 0 ? `${h}h ${m}m` : `${h}h`;
  const d = Math.floor(h / 24);
  const hr = h % 24;
  if (hr > 0 || m > 0) {
    const parts = [`${d}d`];
    if (hr > 0) parts.push(`${hr}h`);
    if (m > 0) parts.push(`${m}m`);
    return parts.join(' ');
  }
  return `${d}d`;
}
