/**
 * Shared utilities for dashboard stats (trend computation, etc.).
 */

export function computeTrend(current: number, prev: number): number | undefined {
  if (prev === 0) return current > 0 ? 100 : undefined;
  const pct = Math.round(((current - prev) / prev) * 100);
  return pct === 0 ? undefined : pct;
}
