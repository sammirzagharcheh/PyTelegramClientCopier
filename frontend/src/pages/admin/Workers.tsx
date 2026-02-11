import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { useAuth } from '../../store/AuthContext';

type Worker = {
  id: string;
  user_id: number;
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
  const { data: accounts } = useQuery({
    queryKey: ['accounts'],
    queryFn: async () => (await api.get('/accounts')).data,
  });
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

  if (isLoading) return <div className="animate-pulse h-32 bg-gray-200 dark:bg-gray-700 rounded" />;

  const userAccounts = (accounts ?? []).filter((a: { user_id: number }) =>
    user?.role === 'admin' ? true : a.user_id === user?.id
  );

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Workers</h1>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Running Workers</h2>
          <div className="space-y-2">
            {(workers ?? []).map((w) => (
              <div key={w.id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded">
                <div>
                  <span className="font-mono text-sm">User {w.user_id}</span>
                  <span className="text-gray-500 text-sm ml-2 truncate max-w-[200px] block">{w.session_path}</span>
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
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Start Worker</h2>
          <p className="text-sm text-gray-500 mb-4">Select an account with a session file to start a worker.</p>
          <div className="space-y-2">
            {userAccounts
              .filter((a: { type: string; session_path: string | null }) => a.type === 'user' && a.session_path)
              .map((a: { id: number; name: string; user_id: number }) => (
                <div key={a.id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded">
                  <span>{a.name || `Account ${a.id}`} (user {a.user_id})</span>
                  <button
                    onClick={() => handleStart(a.id, a.user_id)}
                    disabled={startMutation.isPending}
                    className="px-3 py-1 text-sm rounded bg-blue-600 text-white disabled:opacity-50"
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
