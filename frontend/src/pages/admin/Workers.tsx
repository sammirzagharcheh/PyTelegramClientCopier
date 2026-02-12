import { Activity, Zap } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { useAuth } from '../../store/AuthContext';
import { PageHeader } from '../../components/PageHeader';

type Worker = {
  id: string;
  user_id: number;
  account_id?: number;
  session_path: string;
  pid: number | null;
  running: boolean;
};

export function Workers() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const { data: workers, isLoading } = useQuery({
    queryKey: ['workers'],
    queryFn: async () => (await api.get<Worker[]>('/workers')).data,
  });
  const { data: accountsData } = useQuery({
    queryKey: ['accounts', 1, 100],
    queryFn: async () => (await api.get<{ items: { id: number; name: string; user_id: number; type: string; session_path: string | null }[] }>('/accounts?page=1&page_size=100')).data,
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

  if (isLoading) return <div className="animate-pulse h-32 bg-gray-200 dark:bg-gray-700 rounded" />;

  const userAccounts = accounts.filter((a: { user_id: number }) =>
    user?.role === 'admin' ? true : a.user_id === user?.id
  );

  return (
    <div>
      <PageHeader
        title="Workers"
        icon={Activity}
        subtitle="Start and manage Telegram sync workers for all accounts"
      />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 transition-shadow hover:shadow-lg">
          <div className="flex items-center gap-2 mb-4">
            <Activity className="h-5 w-5 text-amber-500" />
            <h2 className="text-lg font-semibold">Running Workers</h2>
          </div>
          <div className="space-y-2">
            {(workers ?? []).map((w) => (
              <div key={w.id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded">
                <div className="flex items-center gap-2 min-w-0">
                  {w.running && <span className="h-2 w-2 shrink-0 rounded-full bg-green-500" title="Running" />}
                  <span className="font-mono text-sm">User {w.user_id}</span>
                  <span className="text-gray-500 text-sm truncate max-w-[200px]">{w.session_path}</span>
                </div>
                <div className="flex items-center gap-2">
                  {w.running && <span className="text-green-600 text-sm">PID {w.pid}</span>}
                  <button
                    onClick={() => stopMutation.mutate(w.id)}
                    disabled={!w.running}
                    className="px-3 py-1 text-sm rounded bg-red-600 text-white disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Stop
                  </button>
                </div>
              </div>
            ))}
            {(workers ?? []).length === 0 && (
              <p className="text-gray-500 text-sm">No workers running.</p>
            )}
          </div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 transition-shadow hover:shadow-lg">
          <div className="flex items-center gap-2 mb-4">
            <Zap className="h-5 w-5 text-blue-500" />
            <h2 className="text-lg font-semibold">Start Worker</h2>
          </div>
          <p className="text-sm text-gray-500 mb-4">Select an account with a session file to start a worker.</p>
          <div className="space-y-2">
            {userAccounts
              .filter((a: { type: string; session_path: string | null }) => a.type === 'user' && a.session_path)
              .map((a: { id: number; name: string; user_id: number }) => (
                <div key={a.id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded">
                  <span>{a.name || `Account ${a.id}`} (user {a.user_id})</span>
                  <button
                    onClick={() => handleStart(a.id, a.user_id)}
                    disabled={startMutation.isPending || isAccountRunning(a.id)}
                    className="px-3 py-1 text-sm rounded bg-blue-600 text-white disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Start
                  </button>
                </div>
              ))}
            {userAccounts.filter((a: { type: string }) => a.type === 'user').length === 0 && (
              <p className="text-gray-500 text-sm">No user accounts with sessions.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
