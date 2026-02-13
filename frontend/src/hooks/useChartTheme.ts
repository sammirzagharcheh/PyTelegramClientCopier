import { useMemo, useEffect, useState } from 'react';

/** Detects if dark mode is active (class on html or system preference). */
function useIsDark(): boolean {
  const [isDark, setIsDark] = useState(() => {
    if (typeof document === 'undefined') return false;
    const el = document.documentElement;
    if (el.classList.contains('dark')) return true;
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  useEffect(() => {
    const el = document.documentElement;
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    const check = () => {
      setIsDark(el.classList.contains('dark') || media.matches);
    };
    const mo = new MutationObserver(check);
    mo.observe(el, { attributes: true, attributeFilter: ['class'] });
    media.addEventListener('change', check);
    return () => {
      mo.disconnect();
      media.removeEventListener('change', check);
    };
  }, []);

  return isDark;
}

export type ChartTheme = {
  isDark: boolean;
  stroke: string;
  fill: string;
  gridStroke: string;
  textColor: string;
  tooltipBg: string;
  tooltipBorder: string;
};

export function useChartTheme(): ChartTheme {
  const isDark = useIsDark();
  return useMemo(
    () =>
      isDark
        ? {
            isDark: true,
            stroke: 'rgb(96, 165, 250)',
            fill: 'rgba(96, 165, 250, 0.3)',
            gridStroke: 'rgb(75, 85, 99)',
            textColor: 'rgb(209, 213, 219)',
            tooltipBg: 'rgb(31, 41, 55)',
            tooltipBorder: 'rgb(75, 85, 99)',
          }
        : {
            isDark: false,
            stroke: 'rgb(59, 130, 246)',
            fill: 'rgba(59, 130, 246, 0.3)',
            gridStroke: 'rgb(229, 231, 235)',
            textColor: 'rgb(107, 114, 128)',
            tooltipBg: 'white',
            tooltipBorder: 'rgb(229, 231, 235)',
          },
    [isDark]
  );
}
