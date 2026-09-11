import { AlertCircle, CheckCircle, CircleSlash, Pause, XCircle } from 'lucide-react';
import { Badge } from './ui/Badge';
import type { BadgeTone } from './ui/Badge';

type Props = {
  status: string;
};

function getStatusConfig(status: string): {
  icon: typeof CheckCircle;
  label: string;
  tone: BadgeTone;
} {
  const s = String(status).toLowerCase();
  if (s === 'active' || s === 'enabled' || s === 'ok' || s === 'success') {
    return { icon: CheckCircle, label: 'Active', tone: 'success' };
  }
  if (s === 'inactive') {
    return { icon: Pause, label: 'Inactive', tone: 'warning' };
  }
  if (s === 'failed' || s === 'error') {
    return { icon: XCircle, label: 'Failed', tone: 'danger' };
  }
  if (s === 'disabled' || s === 'skipped') {
    return { icon: CircleSlash, label: 'Disabled', tone: 'neutral' };
  }
  return { icon: AlertCircle, label: status || 'Unknown', tone: 'neutral' };
}

export function AccountStatusBadge({ status }: Props) {
  const { icon, label, tone } = getStatusConfig(status);
  return (
    <Badge tone={tone} icon={icon}>
      {label}
    </Badge>
  );
}
