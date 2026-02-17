import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { formatUptime } from './formatUptime';

describe('formatUptime', () => {
  const base = new Date('2025-02-17T12:00:00Z');

  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(base);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('returns — for null or empty', () => {
    expect(formatUptime(null)).toBe('—');
    expect(formatUptime(undefined)).toBe('—');
    expect(formatUptime('')).toBe('—');
  });

  it('returns — for invalid ISO', () => {
    expect(formatUptime('not-a-date')).toBe('—');
  });

  it('formats seconds', () => {
    vi.setSystemTime(new Date('2025-02-17T12:00:00Z'));
    expect(formatUptime('2025-02-17T12:00:00Z')).toBe('0s');
    expect(formatUptime('2025-02-17T11:59:58Z')).toBe('2s');
  });

  it('formats minutes', () => {
    expect(formatUptime('2025-02-17T11:30:00Z')).toBe('30m');
  });

  it('formats hours', () => {
    expect(formatUptime('2025-02-17T10:00:00Z')).toBe('2h');
  });

  it('formats hours and minutes', () => {
    expect(formatUptime('2025-02-17T09:45:00Z')).toBe('2h 15m');
  });

  it('formats days', () => {
    expect(formatUptime('2025-02-16T12:00:00Z')).toBe('1d');
  });

  it('formats days with hours', () => {
    expect(formatUptime('2025-02-15T10:00:00Z')).toBe('2d 2h');
  });

  it('returns — for future dates', () => {
    expect(formatUptime('2025-02-18T12:00:00Z')).toBe('—');
  });
});
