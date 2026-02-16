export function formatLocalDateTime(value: string | null | undefined, timezone?: string): string {
  if (value == null || value === '') return '—';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  try {
    return timezone
      ? d.toLocaleString(undefined, { timeZone: timezone })
      : d.toLocaleString();
  } catch {
    return d.toLocaleString();
  }
}

/**
 * Convert UTC HH:MM to local HH:MM in the given timezone.
 * @param utcHHMM - e.g. "14:00"
 * @param timezone - e.g. "America/New_York", defaults to browser timezone
 */
export function utcTimeToLocal(
  utcHHMM: string,
  timezone?: string
): string {
  const tz = timezone ?? Intl.DateTimeFormat().resolvedOptions().timeZone;
  const [h, m] = utcHHMM.split(':').map((x) => parseInt(x, 10));
  const date = new Date();
  const y = date.getUTCFullYear();
  const mo = date.getUTCMonth();
  const d = date.getUTCDate();
  const utcDate = new Date(Date.UTC(y, mo, d, h ?? 0, m ?? 0, 0, 0));
  return utcDate.toLocaleTimeString('en-CA', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    timeZone: tz,
  });
}

/**
 * Convert local HH:MM (in the given timezone) to UTC HH:MM.
 * @param localHHMM - e.g. "09:00"
 * @param timezone - e.g. "America/New_York"
 */
export function localTimeToUtc(
  localHHMM: string,
  timezone?: string
): string {
  const tz = timezone ?? Intl.DateTimeFormat().resolvedOptions().timeZone;
  const [h, m] = localHHMM.split(':').map((x) => parseInt(x, 10));
  const date = new Date();
  const y = date.getUTCFullYear();
  const mo = date.getUTCMonth();
  const d = date.getUTCDate();
  for (let uh = 0; uh < 24; uh++) {
    for (let um = 0; um < 60; um++) {
      const utcDate = new Date(Date.UTC(y, mo, d, uh, um, 0, 0));
      const formatted = utcDate.toLocaleTimeString('en-CA', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
        timeZone: tz,
      });
      const target = `${String(h ?? 0).padStart(2, '0')}:${String(m ?? 0).padStart(2, '0')}`;
      if (formatted === target) {
        return `${String(uh).padStart(2, '0')}:${String(um).padStart(2, '0')}`;
      }
    }
  }
  return '00:00';
}

const WEEKDAY_KEYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'] as const;

/**
 * Compute compact schedule label from 14 UTC fields.
 */
export function formatScheduleSummary(schedule: Record<string, string | null> | null | undefined): string {
  if (!schedule) return 'Default';
  const hasAny = WEEKDAY_KEYS.some(
    (d) => schedule[`${d}_start_utc`] != null || schedule[`${d}_end_utc`] != null
  );
  if (!hasAny) return 'Default';
  const isBiz =
    ['mon', 'tue', 'wed', 'thu', 'fri'].every(
      (d) =>
        schedule[`${d}_start_utc`] === '09:00' && schedule[`${d}_end_utc`] === '17:00'
    ) &&
    ['sat', 'sun'].every(
      (d) =>
        (schedule[`${d}_start_utc`] == null || schedule[`${d}_start_utc`] === '') &&
        (schedule[`${d}_end_utc`] == null || schedule[`${d}_end_utc`] === '')
    );
  if (isBiz) return 'Mon–Fri 9:00–17:00';
  return 'Custom';
}
