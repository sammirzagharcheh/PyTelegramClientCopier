import { Filter, Inbox, MessageSquare } from 'lucide-react';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { PageHeader } from '../../components/PageHeader';
import { Pagination } from '../../components/Pagination';
import { StatusBadge } from '../../components/StatusBadge';

type Log = {
  user_id: number;
  source_chat_id: number;
  source_msg_id: number;
  dest_chat_id: number;
  dest_msg_id: number;
  source_chat_title?: string | null;
  dest_chat_title?: string | null;
  timestamp: string;
  status: string;
};

type User = { id: number; email: string; name: string | null };
type PaginatedLogs = { items: Log[]; total: number; page: number; page_size: number; total_pages: number };
type PaginatedUsers = { items: User[]; total: number };

export function AdminLogs() {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [userId, setUserId] = useState<number | null>(null);

  const { data: usersData } = useQuery({
    queryKey: ['admin', 'users', 1, 100],
    queryFn: async () => (await api.get<PaginatedUsers>(`/admin/users?page=1&page_size=100`)).data,
  });
  const users = usersData?.items ?? [];

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['admin', 'message-logs', page, pageSize, userId],
    queryFn: async () => {
      const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
      if (userId != null) params.set('user_id', String(userId));
      return (await api.get<PaginatedLogs>(`/message-logs?${params}`)).data;
    },
  });

  if (isLoading) return <div className="animate-pulse h-32 bg-gray-200 dark:bg-gray-700 rounded" />;

  if (isError) {
    const msg =
      (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
      'Failed to load message logs.';
    return (
      <div>
        <PageHeader title="All Message Logs" icon={MessageSquare} subtitle="Forwarded message history across all users" />
        <div className="p-4 rounded-lg bg-amber-50 dark:bg-amber-900/30 text-amber-800 dark:text-amber-200 border border-amber-200 dark:border-amber-800">
          <p className="font-medium">Could not load logs</p>
          <p className="mt-1 text-sm">{msg}</p>
          <p className="mt-2 text-sm">Configure MongoDB URI with credentials in Admin Settings.</p>
        </div>
      </div>
    );
  }

  const items = (data?.items ?? []) as Log[];

  return (
    <div>
      <PageHeader title="All Message Logs" icon={MessageSquare} subtitle="Forwarded message history across all users" />
      <div className="mb-6 flex flex-wrap items-center gap-4 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-800/50 px-4 py-3">
        <Filter className="h-4 w-4 text-gray-500 dark:text-gray-400" />
        <label htmlFor="admin-logs-user-filter" className="text-sm font-medium">Filter by user</label>
        <select
          id="admin-logs-user-filter"
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
      </div>
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden transition-shadow hover:shadow-lg">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-700">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">User</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Source</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Dest</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Time</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {items.map((log, i) => (
              <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                <td className="px-6 py-4 text-sm">{log.user_id}</td>
                <td className="px-6 py-4 text-sm">
                  {log.source_chat_title ? (
                    <span title={`ID: ${log.source_chat_id}`}>{log.source_chat_title} <span className="font-mono text-gray-500">({log.source_chat_id} / {log.source_msg_id})</span></span>
                  ) : (
                    <span className="font-mono">{log.source_chat_id} / {log.source_msg_id}</span>
                  )}
                </td>
                <td className="px-6 py-4 text-sm">
                  {log.dest_chat_title ? (
                    <span title={`ID: ${log.dest_chat_id}`}>{log.dest_chat_title} <span className="font-mono text-gray-500">({log.dest_chat_id} / {log.dest_msg_id})</span></span>
                  ) : (
                    <span className="font-mono">{log.dest_chat_id} / {log.dest_msg_id}</span>
                  )}
                </td>
                <td className="px-6 py-4 text-sm">{log.timestamp}</td>
                <td className="px-6 py-4 text-sm">
                  <StatusBadge status={log.status ?? ''} variant="status" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {items.length === 0 && (
          <div className="p-8 text-center text-gray-500 flex flex-col items-center gap-2">
            <Inbox className="h-12 w-12 text-gray-400" />
            <p>No logs yet.</p>
          </div>
        )}
        {data && (
          <Pagination
            page={data.page}
            pageSize={data.page_size}
            total={data.total}
            totalPages={data.total_pages}
            onPageChange={setPage}
            onPageSizeChange={(n) => { setPageSize(n); setPage(1); }}
          />
        )}
      </div>
    </div>
  );
}
