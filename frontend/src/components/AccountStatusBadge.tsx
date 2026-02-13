import { AlertCircle, CheckCircle, CircleSlash, Pause, XCircle } from 'lucide-react';

type Props = {
  status: string;
};

function getStatusConfig(status: string) {
  const s = String(status).toLowerCase();
  if (s === 'active' || s === 'enabled' || s === 'ok' || s === 'success') {
    return { icon: CheckCircle, label: 'Active', className: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400' };
  }
  if (s === 'inactive') {
    return { icon: Pause, label: 'Inactive', className: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400' };
  }
  if (s === 'failed' || s === 'error') {
    return { icon: XCircle, label: 'Failed', className: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400' };
  }
  if (s === 'disabled' || s === 'skipped') {
    return { icon: CircleSlash, label: 'Disabled', className: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-400' };
  }
  return { icon: AlertCircle, label: status || '—', className: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-400' };
}

export function AccountStatusBadge({ status }: Props) {
  const { icon: Icon, label, className } = getStatusConfig(status);
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium ${className}`}
      title={label}
    >
      <Icon className="h-3.5 w-3.5 shrink-0" aria-hidden />
      {label}
    </span>
  );
}
