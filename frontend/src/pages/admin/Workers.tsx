import { Activity, Zap } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { formatLocalDateTime } from '../../lib/formatDateTime';
import { formatUptime } from '../../lib/formatUptime';
import { useAuth } from '../../store/AuthContext';
import { PageHeader } from '../../components/PageHeader';
import { CardSkeleton } from '../../components/Skeleton';
import { Button } from '../../components/ui/Button';
import { Card, CardHeader } from '../../components/ui/Card';
import { EmptyState, ErrorState } from '../../components/ui/States';

type Worker = {
  id: string;
  user_id: number;
  account_id?: number;
  session_path: string;
  pid: number | null;
  running: boolean;
  started_at?: string | null;
  last_heartbeat_at?: string | null;
};

export function Workers() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const { data: workers, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['workers'],
    queryFn: async () => (await api.get<Worker[]>('/workers')).data,
    refetchInterval: 60_000,
  });
  const { data: accountsData } = useQuery({
    queryKey: ['accounts', 'list'],
    queryFn: async () =>
      (
        await api.get<{
          items: { id: number; name: string; user_id: number; type: string; session_path: string | null }[];
        }>('/accounts?page=1&page_size=100')
      ).data,
    staleTime: 5 * 60 * 1000,
  });
  const accounts = accountsData?.items ?? [];
  const startMutation = useMutation({
    mutationFn: async ({ account_id, user_id }: { account_id: number; user_id?: number }) => {
      const params = new URLSearchParams({ account_id: String(account_id) });
      if (user_id !== undefined) params.set('user_id', String(user_id));
      return (await api.post(`/workers/start?${params}`)).data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['workers'] }),
  });
  const stopMutation = useMutation({
    mutationFn: async (workerId: string) => {
      await api.post(`/workers/${workerId}/stop`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['workers'] }),
  });

  const handleStart = (accountId: number, accountUserId?: number) => {
    startMutation.mutate({
      account_id: accountId,
      user_id: user?.role === 'admin' && accountUserId ? accountUserId : undefined,
    });
  };

  const isAccountRunning = (accountId: number) =>
    (workers ?? []).some((w) => w.account_id === accountId && w.running);

  const userAccounts = accounts.filter((a: { user_id: number }) =>
    user?.role === 'admin' ? true : a.user_id === user?.id
  );
  const startable = userAccounts.filter(
    (a: { type: string; session_path: string | null }) => a.type === 'user' && a.session_path
  );
  const runningWorkers = workers ?? [];

  return (
    <div>
      <PageHeader
        title="Workers"
        icon={Activity}
        subtitle="Start and manage Telegram sync workers for all accounts"
      />

      {isError ? (
        <ErrorState title="We couldn't load the workers" error={error} onRetry={() => refetch()} />
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {isLoading ? (
            <>
              <CardSkeleton lines={3} />
              <CardSkeleton lines={3} />
            </>
          ) : (
            <>
              <Card flush>
                <CardHeader title="Running workers" icon={Activity} inset />
                {runningWorkers.length === 0 ? (
                  <EmptyState
                    icon={Activity}
                    title="No workers running"
                    description="Start one from the list on the right to begin copying messages."
                  />
                ) : (
                  <ul className="divide-y divide-line">
                    {runningWorkers.map((w) => (
                      <li
                        key={w.id}
                        className="flex flex-wrap items-center justify-between gap-3 px-5 py-3"
                      >
                        <div className="flex min-w-0 items-center gap-2.5">
                          <span
                            className={`h-2 w-2 shrink-0 rounded-full ${
                              w.running ? 'bg-emerald-500' : 'bg-ink-subtle'
                            }`}
                            aria-hidden
                          />
                          <span className="shrink-0 text-xs tabular-nums text-ink-subtle">
                            User {w.user_id}
                          </span>
                          <span className="truncate font-mono text-xs text-ink" title={w.session_path}>
                            {w.session_path}
                          </span>
                        </div>
                        <div className="flex shrink-0 items-center gap-3">
                          <span className="text-right text-xs text-ink-subtle">
                            {w.running ? (
                              <>
                                <span className="block">
                                  PID {w.pid} · {formatUptime(w.started_at)}
                                </span>
                                {w.last_heartbeat_at && (
                                  <span className="block">
                                    HB {formatLocalDateTime(w.last_heartbeat_at, user?.timezone ?? undefined)}
                                  </span>
                                )}
                              </>
                            ) : (
                              'Stopped'
                            )}
                          </span>
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => stopMutation.mutate(w.id)}
                            disabled={!w.running}
                            isLoading={stopMutation.isPending && stopMutation.variables === w.id}
                          >
                            Stop
                          </Button>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </Card>

              <Card flush>
                <CardHeader
                  title="Start a worker"
                  icon={Zap}
                  description="Select an account with a session file to start a worker."
                  inset
                />
                {startable.length === 0 ? (
                  <EmptyState
                    icon={Zap}
                    title="No account is ready to run"
                    description="User accounts need an uploaded session file before a worker can start."
                  />
                ) : (
                  <ul className="divide-y divide-line">
                    {startable.map((a: { id: number; name: string; user_id: number }) => {
                      const running = isAccountRunning(a.id);
                      return (
                        <li
                          key={a.id}
                          className="flex flex-wrap items-center justify-between gap-3 px-5 py-3"
                        >
                          <span className="min-w-0 truncate text-sm text-ink">
                            {a.name || `Account ${a.id}`}
                            <span className="ml-2 text-xs tabular-nums text-ink-subtle">
                              user {a.user_id}
                            </span>
                          </span>
                          <Button
                            size="sm"
                            onClick={() => handleStart(a.id, a.user_id)}
                            disabled={running}
                            isLoading={
                              startMutation.isPending && startMutation.variables?.account_id === a.id
                            }
                          >
                            {running ? 'Running' : 'Start'}
                          </Button>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </Card>
            </>
          )}
        </div>
      )}
    </div>
  );
}
