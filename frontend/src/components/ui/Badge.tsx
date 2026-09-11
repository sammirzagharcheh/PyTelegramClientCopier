import type { LucideIcon } from 'lucide-react';

/**
 * Tones map to meaning, not to decoration: `accent` and `info` are the product
 * accent, `neutral` is the absence of state, and the rest are real statuses.
 */
export type BadgeTone = 'neutral' | 'success' | 'warning' | 'danger' | 'info' | 'accent';

const tones: Record<BadgeTone, string> = {
  neutral: 'bg-surface-sunken text-ink-muted',
  success: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-500/15 dark:text-emerald-300',
  warning: 'bg-amber-100 text-amber-900 dark:bg-amber-500/15 dark:text-amber-300',
  danger: 'bg-red-100 text-red-800 dark:bg-red-500/15 dark:text-red-300',
  info: 'bg-accent-soft text-accent-ink',
  accent: 'bg-violet-100 text-violet-800 dark:bg-violet-500/15 dark:text-violet-300',
};

type Props = {
  children: React.ReactNode;
  tone?: BadgeTone;
  icon?: LucideIcon;
  className?: string;
};

export function Badge({ children, tone = 'neutral', icon: Icon, className = '' }: Props) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium whitespace-nowrap ${tones[tone]} ${className}`.trim()}
    >
      {Icon && <Icon className="h-3.5 w-3.5 shrink-0" strokeWidth={2} aria-hidden />}
      {children}
    </span>
  );
}
