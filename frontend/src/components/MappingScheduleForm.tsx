import { useEffect, useState } from 'react';
import { utcTimeToLocal, localTimeToUtc } from '../lib/formatDateTime';

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
    label: 'Business hours (Mon–Fri 9:00–17:00)',
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

type Props = {
  initialSchedule: Record<string, string | null> | null | undefined;
  timezone: string;
  onSave: (payload: Record<string, string | null>) => void | Promise<void>;
  isSaving?: boolean;
  saveLabel?: string;
  showDescription?: boolean;
};

export function MappingScheduleForm({
  initialSchedule,
  timezone,
  onSave,
  isSaving = false,
  saveLabel = 'Save schedule',
  showDescription = true,
}: Props) {
  const [form, setForm] = useState<ScheduleData>({});

  useEffect(() => {
    if (initialSchedule) {
      setForm(fromUtcResponse(initialSchedule, timezone));
    }
  }, [initialSchedule, timezone]);

  const applyTemplate = (t: (typeof TEMPLATES)[0]) => {
    const next: ScheduleData = {};
    for (const d of WEEKDAYS) {
      const slot = t.schedule[d];
      next[d] = slot ? { start: slot.start, end: slot.end } : { start: null, end: null };
    }
    setForm(next);
  };

  const handleSave = () => {
    const payload = toUtcPayload(form, timezone);
    onSave(payload);
  };

  return (
    <div>
      {showDescription && (
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
          All times shown in your timezone ({timezone}). Messages outside this schedule are not copied.
        </p>
      )}
      <div className="mb-4">
        <label className="block text-sm font-medium mb-2">Presets</label>
        <div className="flex flex-wrap gap-2">
          {TEMPLATES.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => applyTemplate(t)}
              className="px-3 py-1.5 rounded border border-gray-300 dark:border-gray-600 text-sm hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>
      <div className="space-y-3">
        {WEEKDAYS.map((d) => (
          <div key={d} className="flex items-center gap-4">
            <span className="w-24 text-sm">{WEEKDAY_LABELS[d]}</span>
            <input
              type="time"
              aria-label={`${WEEKDAY_LABELS[d]} start`}
              title={`${WEEKDAY_LABELS[d]} start`}
              value={form[d]?.start ?? ''}
              onChange={(e) =>
                setForm((prev) => ({
                  ...prev,
                  [d]: { ...prev[d], start: e.target.value || null, end: prev[d]?.end ?? null },
                }))
              }
              className="rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-2 py-1 text-sm"
            />
            <span className="text-gray-400">–</span>
            <input
              type="time"
              aria-label={`${WEEKDAY_LABELS[d]} end`}
              title={`${WEEKDAY_LABELS[d]} end`}
              value={form[d]?.end ?? ''}
              onChange={(e) =>
                setForm((prev) => ({
                  ...prev,
                  [d]: { ...prev[d], start: prev[d]?.start ?? null, end: e.target.value || null },
                }))
              }
              className="rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-2 py-1 text-sm"
            />
            <span className="text-gray-500 text-xs">(local)</span>
          </div>
        ))}
      </div>
      <div className="mt-6">
        <button
          type="button"
          onClick={handleSave}
          disabled={isSaving}
          className="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {saveLabel}
        </button>
      </div>
    </div>
  );
}
