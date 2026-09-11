import { useMemo, useState } from 'react';
import {
  TEMPLATES,
  WEEKDAYS,
  WEEKDAY_LABELS,
  fromUtcResponse,
  toUtcPayload,
} from '../lib/scheduleUtils';
import type { ScheduleData } from '../lib/scheduleUtils';
import { Button } from './ui/Button';

type Props = {
  initialSchedule: Record<string, string | null> | null | undefined;
  timezone: string;
  onSave: (payload: Record<string, string | null>) => void | Promise<void>;
  isSaving?: boolean;
  saveLabel?: string;
  showDescription?: boolean;
  readOnly?: boolean;
};

export function MappingScheduleForm({
  initialSchedule,
  timezone,
  onSave,
  isSaving = false,
  saveLabel = 'Save schedule',
  showDescription = true,
  readOnly = false,
}: Props) {
  const serverForm = useMemo<ScheduleData>(
    () => (initialSchedule ? fromUtcResponse(initialSchedule, timezone) : {}),
    [initialSchedule, timezone]
  );
  // Local edits shadow the server value until the server value itself changes,
  // which is how a fresh fetch discards a stale draft without an effect.
  const [edits, setEdits] = useState<{ base: ScheduleData; value: ScheduleData } | null>(null);
  const form = edits?.base === serverForm ? edits.value : serverForm;

  const updateForm = (next: ScheduleData) => setEdits({ base: serverForm, value: next });

  const setDay = (day: string, patch: { start?: string | null; end?: string | null }) => {
    updateForm({
      ...form,
      [day]: {
        start: patch.start !== undefined ? patch.start : (form[day]?.start ?? null),
        end: patch.end !== undefined ? patch.end : (form[day]?.end ?? null),
      },
    });
  };

  const applyTemplate = (t: (typeof TEMPLATES)[0]) => {
    const next: ScheduleData = {};
    for (const d of WEEKDAYS) {
      const slot = t.schedule[d];
      next[d] = slot ? { start: slot.start, end: slot.end } : { start: null, end: null };
    }
    updateForm(next);
  };

  const handleSave = () => {
    onSave(toUtcPayload(form, timezone));
  };

  const timeInputClass =
    'rounded-control border border-line-strong bg-surface-raised px-2 py-1 text-sm text-ink tabular-nums transition-colors hover:border-ink-subtle';

  return (
    <div>
      {showDescription && (
        <p className="mb-4 text-sm text-ink-subtle">
          All times shown in your timezone ({timezone}). Messages outside this schedule are not
          copied.
        </p>
      )}

      <fieldset className="mb-5">
        <legend className="mb-2 text-sm font-medium text-ink">Presets</legend>
        <div className="flex flex-wrap gap-2">
          {TEMPLATES.map((t) => (
            <Button
              key={t.id}
              variant="secondary"
              size="sm"
              disabled={readOnly}
              onClick={() => applyTemplate(t)}
            >
              {t.label}
            </Button>
          ))}
        </div>
      </fieldset>

      <div className="divide-y divide-line rounded-surface border border-line">
        {WEEKDAYS.map((d) => (
          <div key={d} className="flex flex-wrap items-center gap-3 px-3 py-2.5">
            <span className="w-24 shrink-0 text-sm font-medium text-ink">{WEEKDAY_LABELS[d]}</span>
            <input
              type="time"
              aria-label={`${WEEKDAY_LABELS[d]} start`}
              title={`${WEEKDAY_LABELS[d]} start`}
              disabled={readOnly}
              value={form[d]?.start ?? ''}
              onChange={(e) => setDay(d, { start: e.target.value || null })}
              className={timeInputClass}
            />
            <span className="text-ink-subtle" aria-hidden>
              to
            </span>
            <input
              type="time"
              aria-label={`${WEEKDAY_LABELS[d]} end`}
              title={`${WEEKDAY_LABELS[d]} end`}
              disabled={readOnly}
              value={form[d]?.end ?? ''}
              onChange={(e) => setDay(d, { end: e.target.value || null })}
              className={timeInputClass}
            />
            {!form[d]?.start && !form[d]?.end && (
              <span className="text-xs text-ink-subtle">No limit, copies all day</span>
            )}
          </div>
        ))}
      </div>

      <div className="mt-5">
        <Button onClick={handleSave} isLoading={isSaving} disabled={readOnly}>
          {saveLabel}
        </Button>
      </div>
    </div>
  );
}
