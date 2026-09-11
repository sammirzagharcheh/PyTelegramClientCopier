import type { LucideIcon } from 'lucide-react';
import { TrendingDown, TrendingUp } from 'lucide-react';
import { Skeleton } from './Skeleton';

/**
 * Retained so existing dashboards keep compiling. The accent is locked to one
 * colour now, so the variant no longer tints the card: colour in this app means
 * status, not decoration.
 */
export type ColorVariant = 'blue' | 'violet' | 'emerald' | 'amber';

type Props = {
  title: string;
  value: string | number;
  icon: LucideIcon;
  colorVariant?: ColorVariant;
  trend?: { value: number; label?: string };
  isLoading?: boolean;
};

export function StatCard({ title, value, icon: Icon, trend, isLoading }: Props) {
  const trendUp = trend != null && trend.value > 0;
  const trendDown = trend != null && trend.value < 0;

  return (
    <div className="rounded-surface border border-line bg-surface-raised p-5 shadow-surface">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-ink-subtle">{title}</p>
          {isLoading ? (
            <Skeleton className="mt-3 h-8 w-16" />
          ) : (
            <p className="mt-2 text-3xl font-semibold tracking-tight text-ink tabular-nums">
              {value}
            </p>
          )}
          {trend != null && !isLoading && (trendUp || trendDown) && (
            <p
              className={`mt-1.5 flex items-center gap-1 text-xs font-medium ${
                trendUp ? 'text-emerald-700 dark:text-emerald-400' : 'text-red-700 dark:text-red-400'
              }`}
            >
              {trendUp ? (
                <TrendingUp className="h-3.5 w-3.5 shrink-0" aria-hidden />
              ) : (
                <TrendingDown className="h-3.5 w-3.5 shrink-0" aria-hidden />
              )}
              <span className="tabular-nums">
                {trendUp ? '+' : ''}
                {trend.value}%
              </span>
              <span className="text-ink-subtle">vs {trend.label ?? 'last period'}</span>
            </p>
          )}
        </div>
        <span className="shrink-0 rounded-control bg-surface-sunken p-2 text-ink-subtle">
          <Icon className="h-4.5 w-4.5" strokeWidth={2} aria-hidden />
        </span>
      </div>
    </div>
  );
}
