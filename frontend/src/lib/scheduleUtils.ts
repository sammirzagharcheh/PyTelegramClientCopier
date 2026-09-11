import { localTimeToUtc, utcTimeToLocal } from './formatDateTime';

export const WEEKDAYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'] as const;

export const WEEKDAY_LABELS: Record<string, string> = {
  mon: 'Monday',
  tue: 'Tuesday',
  wed: 'Wednesday',
  thu: 'Thursday',
  fri: 'Friday',
  sat: 'Saturday',
  sun: 'Sunday',
};

export const TEMPLATES: {
  id: string;
  label: string;
  schedule: Record<string, { start: string; end: string } | null>;
}[] = [
  {
    id: '247',
    label: '24/7 (no restrictions)',
    schedule: Object.fromEntries(WEEKDAYS.map((d) => [d, null])),
  },
  {
    id: 'business',
    label: 'Business hours (Mon to Fri, 9:00 to 17:00)',
    schedule: Object.fromEntries([
      ...['mon', 'tue', 'wed', 'thu', 'fri'].map((d) => [d, { start: '09:00', end: '17:00' }]),
      ...['sat', 'sun'].map((d) => [d, null]),
    ]),
  },
  {
    id: 'weekends',
    label: 'Weekends only',
    schedule: Object.fromEntries([
      ...['mon', 'tue', 'wed', 'thu', 'fri'].map((d) => [d, null]),
      ...['sat', 'sun'].map((d) => [d, { start: '00:00', end: '23:59' }]),
    ]),
  },
];

export type ScheduleData = Record<string, { start: string | null; end: string | null }>;

/**
 * The backend stores schedules as UTC `HH:MM` columns while the UI works in the
 * user's timezone, so every read and write has to cross that boundary here.
 */
export function toUtcPayload(form: ScheduleData, tz?: string): Record<string, string | null> {
  const out: Record<string, string | null> = {};
  for (const d of WEEKDAYS) {
    const s = form[d]?.start;
    const e = form[d]?.end;
    if (s) {
      out[`${d}_start_utc`] = localTimeToUtc(s, tz);
    } else {
      out[`${d}_start_utc`] = null;
    }
    if (e) {
      out[`${d}_end_utc`] = localTimeToUtc(e, tz);
    } else {
      out[`${d}_end_utc`] = null;
    }
  }
  return out;
}

export function fromUtcResponse(
  data: Record<string, string | null>,
  tz?: string
): ScheduleData {
  const form: ScheduleData = {};
  for (const d of WEEKDAYS) {
    const start = data[`${d}_start_utc`];
    const end = data[`${d}_end_utc`];
    form[d] = {
      start: start ? utcTimeToLocal(start, tz) : null,
      end: end ? utcTimeToLocal(end, tz) : null,
    };
  }
  return form;
}
