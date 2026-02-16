import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SearchableTimezoneSelect, getTimezoneUtcOffset, DEVICE_TZ_VALUE } from './SearchableTimezoneSelect';

describe('SearchableTimezoneSelect', () => {
  const timezones = ['America/New_York', 'Europe/London', 'Asia/Tokyo', 'UTC'];

  it('renders combobox with placeholder when closed', () => {
    const onChange = vi.fn();
    render(
      <SearchableTimezoneSelect
        value={DEVICE_TZ_VALUE}
        onChange={onChange}
        timezones={timezones}
        aria-label="Timezone"
      />
    );
    const combobox = screen.getByRole('combobox', { name: /timezone/i });
    expect(combobox).toBeInTheDocument();
    expect(combobox).toHaveAttribute('placeholder', 'Search timezone...');
  });

  it('shows selected label with UTC offset when value is set', () => {
    render(
      <SearchableTimezoneSelect
        value="America/New_York"
        onChange={vi.fn()}
        timezones={timezones}
      />
    );
    const combobox = screen.getByRole('combobox');
    expect(combobox.value).toContain('America/New_York');
    expect(combobox.value).toMatch(/\(UTC[+-]\d{1,2}:\d{2}\)$/);
  });

  it('opens listbox on focus and shows options with UTC offset', () => {
    render(
      <SearchableTimezoneSelect
        value={DEVICE_TZ_VALUE}
        onChange={vi.fn()}
        timezones={timezones}
      />
    );
    fireEvent.focus(screen.getByRole('combobox'));
    expect(screen.getByRole('listbox')).toBeInTheDocument();
    expect(screen.getByRole('option', { name: /Use my device timezone/i })).toBeInTheDocument();
    const nyOption = screen.getByRole('option', { name: /America\/New_York/ });
    expect(nyOption).toBeInTheDocument();
    expect(nyOption.textContent).toMatch(/UTC/);
  });

  it('filters options when typing', () => {
    render(
      <SearchableTimezoneSelect
        value={DEVICE_TZ_VALUE}
        onChange={vi.fn()}
        timezones={timezones}
      />
    );
    fireEvent.focus(screen.getByRole('combobox'));
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'Asia' } });
    const options = screen.getAllByRole('option');
    expect(options).toHaveLength(1);
    expect(options[0].textContent).toContain('Asia/Tokyo');
  });

  it('calls onChange when option is clicked', () => {
    const onChange = vi.fn();
    render(
      <SearchableTimezoneSelect
        value={DEVICE_TZ_VALUE}
        onChange={onChange}
        timezones={timezones}
      />
    );
    fireEvent.focus(screen.getByRole('combobox'));
    fireEvent.click(screen.getByRole('option', { name: /America\/New_York/ }));
    expect(onChange).toHaveBeenCalledWith('America/New_York');
  });

  it('calls onChange with device value when Use my device is clicked', () => {
    const onChange = vi.fn();
    render(
      <SearchableTimezoneSelect
        value="America/New_York"
        onChange={onChange}
        timezones={timezones}
      />
    );
    fireEvent.focus(screen.getByRole('combobox'));
    fireEvent.click(screen.getByRole('option', { name: /Use my device timezone/i }));
    expect(onChange).toHaveBeenCalledWith(DEVICE_TZ_VALUE);
  });
});

describe('getTimezoneUtcOffset', () => {
  it('returns UTC offset string for valid timezone', () => {
    const result = getTimezoneUtcOffset('America/New_York');
    expect(result).toMatch(/^UTC[+-]\d{2}:\d{2}$/);
  });

  it('returns empty string for invalid timezone', () => {
    const result = getTimezoneUtcOffset('Invalid/Zone');
    expect(result).toBe('');
  });
});
