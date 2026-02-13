import type { LucideIcon } from 'lucide-react';
import { TrendingUp, TrendingDown } from 'lucide-react';
import { Skeleton } from './Skeleton';

type ColorVariant = 'blue' | 'violet' | 'emerald' | 'amber';

const variantStyles: Record<ColorVariant, { bg: string; iconBg: string; iconColor: string; border: string }> = {
  blue: {
    bg: 'bg-blue-50 dark:bg-blue-900/20',
    iconBg: 'bg-blue-100 dark:bg-blue-900/40',
    iconColor: 'text-blue-600 dark:text-blue-400',
    border: 'border-l-blue-500',
  },
  violet: {
    bg: 'bg-violet-50 dark:bg-violet-900/20',
    iconBg: 'bg-violet-100 dark:bg-violet-900/40',
    iconColor: 'text-violet-600 dark:text-violet-400',
    border: 'border-l-violet-500',
  },
  emerald: {
    bg: 'bg-emerald-50 dark:bg-emerald-900/20',
    iconBg: 'bg-emerald-100 dark:bg-emerald-900/40',
    iconColor: 'text-emerald-600 dark:text-emerald-400',
    border: 'border-l-emerald-500',
  },
  amber: {
    bg: 'bg-amber-50 dark:bg-amber-900/20',
    iconBg: 'bg-amber-100 dark:bg-amber-900/40',
    iconColor: 'text-amber-600 dark:text-amber-400',
    border: 'border-l-amber-500',
  },
};

type Props = {
  title: string;
  value: string | number;
  icon: LucideIcon;
  colorVariant: ColorVariant;
  trend?: { value: number; label?: string };
  isLoading?: boolean;
};

export function StatCard({ title, value, icon: Icon, colorVariant, trend, isLoading }: Props) {
  const styles = variantStyles[colorVariant];
  const trendUp = trend != null && trend.value > 0;
  const trendDown = trend != null && trend.value < 0;

  return (
    <div
      className={`${styles.bg} border-l-4 ${styles.border} rounded-lg shadow p-6 transition-shadow hover:shadow-lg dark:border-gray-700`}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-600 dark:text-gray-400">{title}</p>
          {isLoading ? (
            <Skeleton className="mt-2 h-9 w-16" />
          ) : (
            <p className="mt-2 text-3xl font-bold text-gray-900 dark:text-gray-100">{value}</p>
          )}
          {trend != null && !isLoading && (trendUp || trendDown) && (
            <div
              className={`mt-1 flex items-center gap-1 text-xs font-medium ${
                trendUp ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'
              }`}
            >
              {trendUp ? (
                <TrendingUp className="h-3.5 w-3.5" />
              ) : (
                <TrendingDown className="h-3.5 w-3.5" />
              )}
              <span>
                {trendUp ? '+' : ''}{trend.value}% vs {trend.label ?? 'last period'}
              </span>
            </div>
          )}
        </div>
        <div className={`rounded-lg p-3 shrink-0 ${styles.iconBg} ${styles.iconColor}`}>
          <Icon className="h-6 w-6" strokeWidth={2} />
        </div>
      </div>
    </div>
  );
}
