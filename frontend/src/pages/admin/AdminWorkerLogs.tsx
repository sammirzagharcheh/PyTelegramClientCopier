import { Filter, Inbox, ScrollText } from 'lucide-react';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { formatLocalDateTime } from '../../lib/formatDateTime';
import { PageHeader } from '../../components/PageHeader';
import { Pagination } from '../../components/Pagination';
import { LogLevelBadge } from '../../components/LogLevelBadge';

type WorkerLog = {
  user_id: number;
  account_id: number | null;
  level: string;
  message: string;
  timestamp: string;
};

type User = { id: number; email: string; name: string | null };
type PaginatedWorkerLogs = {
  items: WorkerLog[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};
type PaginatedUsers = { items: User[]; total: number };

export function AdminWorkerLogs() {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [userId, setUserId] = useState<number | null>(null);
  const [levelFilter, setLevelFilter] = useState<string>('');

  const { data: usersData } = useQuery({
    queryKey: ['admin', 'users', 'list'],
    queryFn: async () => (await api.get<PaginatedUsers>(`/admin/users?page=1&page_size=100`)).data,
    staleTime: 5 * 60 * 1000,
  });
  const users = usersData?.items ?? [];

  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  if (userId != null) params.set('user_id', String(userId));
  if (levelFilter) params.set('level', levelFilter);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['admin', 'worker-logs', page, pageSize, userId, levelFilter],
    queryFn: async () =>
      (await api.get<PaginatedWorkerLogs>(`/worker-logs?${params}`)).data,
  });

  if (isLoading)
    return <div className="animate-pulse h-32 bg-gray-200 dark:bg-gray-700 rounded" />;

  if (isError) {
    const msg =
      (error as { response?: { data?: { detail?: string } } })?.response?.data
        ?.detail ?? 'Failed to load worker logs.';
    return (
      <div>
        <PageHeader title="All Worker Logs" icon={ScrollText} subtitle="Worker process output across all users" />
        <div className="p-4 rounded-lg bg-amber-50 dark:bg-amber-900/30 text-amber-800 dark:text-amber-200 border border-amber-200 dark:border-amber-800">
          <p className="font-medium">Could not load logs</p>
          <p className="mt-1 text-sm">{msg}</p>
          <p className="mt-2 text-sm">Configure MongoDB URI in Admin Settings.</p>
        </div>
      </div>
    );
  }

  const items = (data?.items ?? []) as WorkerLog[];

  return (
    <div>
      <PageHeader title="All Worker Logs" icon={ScrollText} subtitle="Worker process output across all users" />
      <div className="mb-6 flex flex-wrap items-center gap-4 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-800/50 px-4 py-3">
        <Filter className="h-4 w-4 text-gray-500 dark:text-gray-400 shrink-0" />
        <label htmlFor="admin-worker-logs-user" className="text-sm font-medium">
          Filter by user
        </label>
        <select
          id="admin-worker-logs-user"
          value={userId ?? ''}
          onChange={(e) => {
            const v = e.target.value;
            setUserId(v === '' ? null : parseInt(v, 10));
            setPage(1);
          }}
          className="px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700"
        >
          <option value="">All users</option>
          {users.map((u) => (
            <option key={u.id} value={u.id}>
              User {u.id} ({u.email})
            </option>
          ))}
        </select>
        <label htmlFor="admin-worker-logs-level" className="text-sm font-medium">
          Level
        </label>
        <select
          id="admin-worker-logs-level"
          value={levelFilter}
          onChange={(e) => {
            setLevelFilter(e.target.value);
            setPage(1);
          }}
          className="px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700"
        >
          <option value="">All</option>
          <option value="DEBUG">DEBUG</option>
          <option value="INFO">INFO</option>
          <option value="WARNING">WARNING</option>
          <option value="ERROR">ERROR</option>
        </select>
      </div>
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden transition-shadow hover:shadow-lg">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-700">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                User
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                Time
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                Account
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                Level
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                Message
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {items.map((log, i) => (
              <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                <td className="px-6 py-4 text-sm">{log.user_id}</td>
                <td className="px-6 py-4 text-sm whitespace-nowrap" title={log.timestamp}>{formatLocalDateTime(log.timestamp)}</td>
                <td className="px-6 py-4 text-sm">
                  {log.account_id != null ? String(log.account_id) : '—'}
                </td>
                <td className="px-6 py-4 text-sm">
                  <LogLevelBadge level={log.level} />
                </td>
                <td className="px-6 py-4 text-sm break-all">{log.message}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {items.length === 0 && (
          <div className="p-8 text-center text-gray-500 flex flex-col items-center gap-2">
            <Inbox className="h-12 w-12 text-gray-400" />
            <p>No worker logs yet.</p>
          </div>
        )}
        {data && (
          <Pagination
            page={data.page}
            pageSize={data.page_size}
            total={data.total}
            totalPages={data.total_pages}
            onPageChange={setPage}
            onPageSizeChange={(n) => {
              setPageSize(n);
              setPage(1);
            }}
          />
        )}
      </div>
    </div>
  );
}
