import { useMemo } from 'react';
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
 * Values are kept in lockstep with the semantic tokens in index.css.
 */
const LIGHT: Record<string, string> = {
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

const DARK: Record<string, string> = {
  '--accent': '#2563eb',
  '--ink-subtle': '#89909b',
  '--ink': '#e8eaee',
  '--line': '#272c36',
  '--surface-raised': '#171a21',
  '--line-strong': '#3a4150',
  '--chart-1': '#60a5fa',
  '--chart-2': '#2dd4bf',
  '--chart-3': '#fbbf24',
  '--chart-4': '#a78bfa',
  '--chart-5': '#f472b6',
};

export function useChartTheme(): ChartTheme {
  const { resolved } = useTheme();
  const isDark = resolved === 'dark';

  return useMemo(() => {
    const tokens = isDark ? DARK : LIGHT;
    return {
      isDark,
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
    };
  }, [isDark]);
}
