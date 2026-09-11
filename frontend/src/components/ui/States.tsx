import { AlertTriangle, RefreshCw } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { errorMessage } from '../../lib/apiError';
import { Button } from './Button';

type EmptyStateProps = {
  icon: LucideIcon;
  title: string;
  /** Say how to populate the view, not just that it is empty. */
  description?: string;
  action?: React.ReactNode;
};

export function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center gap-3 px-6 py-14 text-center">
      <span className="rounded-full bg-surface-sunken p-3 text-ink-subtle">
        <Icon className="h-6 w-6" strokeWidth={1.75} aria-hidden />
      </span>
      <div>
        <p className="text-sm font-medium text-ink">{title}</p>
        {description && (
          <p className="mx-auto mt-1 max-w-sm text-sm text-ink-subtle">{description}</p>
        )}
      </div>
      {action}
    </div>
  );
}

type ErrorStateProps = {
  title?: string;
  error?: unknown;
  onRetry?: () => void;
};

export function ErrorState({ title = "We couldn't load this", error, onRetry }: ErrorStateProps) {
  return (
    <div
      role="alert"
      className="flex flex-col items-center gap-3 rounded-surface border border-red-200 bg-red-50 px-6 py-10 text-center dark:border-red-900/60 dark:bg-red-950/30"
    >
      <span className="rounded-full bg-red-100 p-3 text-red-700 dark:bg-red-900/40 dark:text-red-300">
        <AlertTriangle className="h-6 w-6" strokeWidth={1.75} aria-hidden />
      </span>
      <div>
        <p className="text-sm font-medium text-red-900 dark:text-red-200">{title}</p>
        <p className="mx-auto mt-1 max-w-sm text-sm text-red-800 dark:text-red-300">
          {errorMessage(error)}
        </p>
      </div>
      {onRetry && (
        <Button variant="secondary" size="sm" icon={RefreshCw} onClick={onRetry}>
          Retry
        </Button>
      )}
    </div>
  );
}
