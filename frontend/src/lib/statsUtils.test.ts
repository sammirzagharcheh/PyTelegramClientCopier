import { describe, it, expect } from 'vitest';
import { computeTrend } from './statsUtils';

describe('computeTrend', () => {
  it('returns 100 when prev is 0 and current > 0', () => {
    expect(computeTrend(10, 0)).toBe(100);
  });

  it('returns undefined when prev is 0 and current is 0', () => {
    expect(computeTrend(0, 0)).toBeUndefined();
  });

  it('returns undefined when change is 0%', () => {
    expect(computeTrend(50, 50)).toBeUndefined();
  });

  it('returns positive percent when current > prev', () => {
    expect(computeTrend(60, 50)).toBe(20);
    expect(computeTrend(150, 100)).toBe(50);
  });

  it('returns negative percent when current < prev', () => {
    expect(computeTrend(40, 50)).toBe(-20);
    expect(computeTrend(50, 100)).toBe(-50);
  });

  it('rounds to nearest integer', () => {
    expect(computeTrend(33, 100)).toBe(-67);
    expect(computeTrend(166, 100)).toBe(66);
  });
});
