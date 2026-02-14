import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MappingScheduleForm, TEMPLATES, WEEKDAY_LABELS } from './MappingScheduleForm';

// Keep times as-is for predictable tests
vi.mock('../lib/formatDateTime', () => ({
  utcTimeToLocal: (t: string) => t,
  localTimeToUtc: (t: string) => t,
}));

describe('MappingScheduleForm', () => {
  const onSave = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders template buttons', () => {
    render(
      <MappingScheduleForm
        initialSchedule={null}
        timezone="UTC"
        onSave={onSave}
      />
    );
    for (const t of TEMPLATES) {
      expect(screen.getByRole('button', { name: t.label })).toBeInTheDocument();
    }
  });

  it('renders weekday time inputs', () => {
    render(
      <MappingScheduleForm
        initialSchedule={null}
        timezone="UTC"
        onSave={onSave}
      />
    );
    for (const d of Object.keys(WEEKDAY_LABELS)) {
      expect(screen.getByLabelText(`${WEEKDAY_LABELS[d]} start`)).toBeInTheDocument();
      expect(screen.getByLabelText(`${WEEKDAY_LABELS[d]} end`)).toBeInTheDocument();
    }
  });

  it('renders Save schedule button by default', () => {
    render(
      <MappingScheduleForm
        initialSchedule={null}
        timezone="UTC"
        onSave={onSave}
      />
    );
    expect(screen.getByRole('button', { name: 'Save schedule' })).toBeInTheDocument();
  });

  it('uses custom save label when provided', () => {
    render(
      <MappingScheduleForm
        initialSchedule={null}
        timezone="UTC"
        onSave={onSave}
        saveLabel="Update schedule"
      />
    );
    expect(screen.getByRole('button', { name: 'Update schedule' })).toBeInTheDocument();
  });

  it('hides description when showDescription is false', () => {
    render(
      <MappingScheduleForm
        initialSchedule={null}
        timezone="UTC"
        onSave={onSave}
        showDescription={false}
      />
    );
    expect(screen.queryByText(/All times shown in your timezone/)).not.toBeInTheDocument();
  });

  it('calls onSave with payload when Save clicked', () => {
    render(
      <MappingScheduleForm
        initialSchedule={null}
        timezone="UTC"
        onSave={onSave}
      />
    );
    fireEvent.click(screen.getByRole('button', { name: 'Save schedule' }));
    expect(onSave).toHaveBeenCalledTimes(1);
    const payload = onSave.mock.calls[0][0];
    expect(payload).toHaveProperty('mon_start_utc');
    expect(payload).toHaveProperty('sun_end_utc');
  });

  it('applies Business hours template when clicked', () => {
    render(
      <MappingScheduleForm
        initialSchedule={null}
        timezone="UTC"
        onSave={onSave}
      />
    );
    fireEvent.click(screen.getByRole('button', { name: /Business hours/ }));
    fireEvent.click(screen.getByRole('button', { name: 'Save schedule' }));
    const payload = onSave.mock.calls[0][0];
    expect(payload.mon_start_utc).toBe('09:00');
    expect(payload.mon_end_utc).toBe('17:00');
    expect(payload.sat_start_utc).toBeNull();
    expect(payload.sat_end_utc).toBeNull();
  });

  it('disables Save button when isSaving is true', () => {
    render(
      <MappingScheduleForm
        initialSchedule={null}
        timezone="UTC"
        onSave={onSave}
        isSaving={true}
      />
    );
    expect(screen.getByRole('button', { name: 'Save schedule' })).toBeDisabled();
  });

  it('initializes form from initialSchedule', () => {
    render(
      <MappingScheduleForm
        initialSchedule={{
          mon_start_utc: '09:00',
          mon_end_utc: '17:00',
          tue_start_utc: null,
          tue_end_utc: null,
        }}
        timezone="UTC"
        onSave={onSave}
      />
    );
    expect(screen.getByLabelText('Monday start')).toHaveValue('09:00');
    expect(screen.getByLabelText('Monday end')).toHaveValue('17:00');
  });
});
