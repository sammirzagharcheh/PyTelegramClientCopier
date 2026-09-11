import { Smartphone } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';
import { formatLocalDateTime } from '../lib/formatDateTime';
import { useAuth } from '../store/AuthContext';
import { AccountTypeBadge } from './AccountTypeBadge';
import { AccountStatusBadge } from './AccountStatusBadge';
import { Skeleton } from './Skeleton';
import { Button } from './ui/Button';
import { Modal } from './ui/Modal';
import { ErrorState } from './ui/States';

type AccountDetail = {
  id: number;
  user_id: number;
  name: string | null;
  type: string;
  session_path: string | null;
  phone: string | null;
  status: string;
  created_at: string | null;
};

type Props = {
  accountId: number;
  onClose: () => void;
};

function DetailRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-line py-2.5 last:border-b-0">
      <dt className="text-sm text-ink-subtle">{label}</dt>
      <dd className="text-sm font-medium text-ink">{children}</dd>
    </div>
  );
}

export function ViewAccountDialog({ accountId, onClose }: Props) {
  const { user } = useAuth();
  const {
    data: account,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ['account', accountId],
    queryFn: async () => (await api.get<AccountDetail>(`/accounts/${accountId}`)).data,
    enabled: !!accountId,
  });

  return (
    <Modal
      title="Account details"
      icon={<Smartphone className="h-5 w-5 text-ink-subtle" strokeWidth={2} aria-hidden />}
      size="sm"
      onClose={onClose}
      footer={
        <Button variant="secondary" onClick={onClose}>
          Close
        </Button>
      }
    >
      {isLoading ? (
        <div className="space-y-3" role="status" aria-label="Loading account">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="flex justify-between gap-4">
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-4 w-28" />
            </div>
          ))}
        </div>
      ) : isError ? (
        <ErrorState title="We couldn't load this account" error={error} onRetry={() => refetch()} />
      ) : account ? (
        <dl>
          <DetailRow label="Name">{account.name || 'Not set'}</DetailRow>
          <DetailRow label="Type">
            <AccountTypeBadge type={account.type} />
          </DetailRow>
          <DetailRow label="Status">
            <AccountStatusBadge status={account.status} />
          </DetailRow>
          {account.phone && (
            <DetailRow label="Phone">
              <span className="font-mono">{account.phone}</span>
            </DetailRow>
          )}
          <DetailRow label="Created">
            <time dateTime={account.created_at ?? undefined}>
              {formatLocalDateTime(account.created_at, user?.timezone ?? undefined)}
            </time>
          </DetailRow>
        </dl>
      ) : (
        <p className="text-sm text-ink-subtle">This account no longer exists.</p>
      )}
    </Modal>
  );
}
