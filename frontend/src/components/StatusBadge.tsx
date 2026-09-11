import { CheckCircle, Shield, XCircle } from 'lucide-react';

type Variant = 'success' | 'warning' | 'error' | 'neutral' | 'role-admin' | 'role-user';

const variantStyles: Record<Variant, string> = {
  success:
    'bg-emerald-100 text-emerald-800 dark:bg-emerald-500/15 dark:text-emerald-300',
  warning: 'bg-amber-100 text-amber-900 dark:bg-amber-500/15 dark:text-amber-300',
  error: 'bg-red-100 text-red-800 dark:bg-red-500/15 dark:text-red-300',
  neutral: 'bg-surface-sunken text-ink-muted',
  'role-admin': 'bg-violet-100 text-violet-800 dark:bg-violet-500/15 dark:text-violet-300',
  'role-user': 'bg-accent-soft text-accent-ink',
};

function getVariant(status: string, field?: 'status' | 'role' | 'type' | 'enabled'): Variant {
  const s = String(status).toLowerCase();
  if (field === 'role') {
    if (s === 'admin') return 'role-admin';
    return 'role-user';
  }
  if (field === 'enabled') {
    if (s === 'true' || s === 'enabled' || s === '1') return 'success';
    if (s === 'false' || s === 'disabled' || s === '0') return 'neutral';
    return 'neutral';
  }
  if (field === 'type') {
    if (s === 'user') return 'role-user';
    if (s === 'admin') return 'role-admin';
    return 'neutral';
  }
  if (s === 'active' || s === 'enabled' || s === 'ok' || s === 'success') return 'success';
  if (s === 'inactive') return 'warning';
  if (s === 'failed' || s === 'error') return 'error';
  if (s === 'disabled' || s === 'skipped') return 'neutral';
  return 'neutral';
}

type Props = {
  status: string;
  variant?: 'status' | 'role' | 'type' | 'enabled';
  showIcon?: boolean;
};

export function StatusBadge({ status, variant = 'status', showIcon = false }: Props) {
  const v = getVariant(status, variant);
  const displayText = status || 'Unknown';
  const Icon =
    v === 'success' ? CheckCircle : v === 'error' || v === 'warning' ? XCircle : v === 'role-admin' ? Shield : null;

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium whitespace-nowrap ${variantStyles[v]}`}
    >
      {showIcon && Icon && <Icon className="h-3 w-3 shrink-0" aria-hidden />}
      {displayText}
    </span>
  );
}
