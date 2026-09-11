import { useEffect, useMemo, useState } from 'react';
import { useTheme } from '../store/ThemeContext';

export type ChartTheme = {
  isDark: boolean;
  /** Primary series colour. */
  stroke: string;
  gridStroke: string;
  textColor: string;
  tooltipBg: string;
  tooltipBorder: string;
  tooltipInk: string;
  /** Categorical palette, ordered so neighbouring slices stay distinguishable. */
  series: string[];
};

/**
 * Recharts paints to SVG attributes, so it cannot read `var(--token)`.
 * These fallbacks mirror the light-mode values in index.css and are only used
 * before the stylesheet resolves (or under jsdom, where computed custom
 * properties come back empty).
 */
const FALLBACK: Record<string, string> = {
  '--accent': '#2563eb',
  '--ink-subtle': '#676d77',
  '--ink': '#17191d',
  '--line': '#e2e5ea',
  '--surface-raised': '#fcfcfd',
  '--line-strong': '#cbd0d8',
  '--chart-1': '#2563eb',
  '--chart-2': '#0d9488',
  '--chart-3': '#d97706',
  '--chart-4': '#7c3aed',
  '--chart-5': '#db2777',
};

function readTokens(): Record<string, string> {
  if (typeof window === 'undefined' || typeof document === 'undefined') {
    return FALLBACK;
  }
  const computed = window.getComputedStyle(document.documentElement);
  const resolved: Record<string, string> = {};
  for (const name of Object.keys(FALLBACK)) {
    const value = computed.getPropertyValue(name).trim();
    resolved[name] = value || FALLBACK[name];
  }
  return resolved;
}

export function useChartTheme(): ChartTheme {
  const { resolved } = useTheme();
  const [tokens, setTokens] = useState<Record<string, string>>(readTokens);

  // The class swap on <html> happens in an effect, so re-read afterwards to
  // pick up the dark-mode values rather than the ones painted a tick earlier.
  useEffect(() => {
    setTokens(readTokens());
  }, [resolved]);

  return useMemo(
    () => ({
      isDark: resolved === 'dark',
      stroke: tokens['--accent'],
      gridStroke: tokens['--line'],
      textColor: tokens['--ink-subtle'],
      tooltipBg: tokens['--surface-raised'],
      tooltipBorder: tokens['--line-strong'],
      tooltipInk: tokens['--ink'],
      series: [
        tokens['--chart-1'],
        tokens['--chart-2'],
        tokens['--chart-3'],
        tokens['--chart-4'],
        tokens['--chart-5'],
      ],
    }),
    [resolved, tokens]
  );
}
