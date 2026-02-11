import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { Pagination } from '../../components/Pagination';

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

type PaginatedLogs = { items: Log[]; total: number; page: number; page_size: number; total_pages: number };

export function AdminLogs() {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['admin', 'message-logs', page, pageSize],
    queryFn: async () => (await api.get<PaginatedLogs>(`/message-logs?page=${page}&page_size=${pageSize}`)).data,
  });

  if (isLoading) return <div className="animate-pulse h-32 bg-gray-200 dark:bg-gray-700 rounded" />;

  if (isError) {
    const msg =
      (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
      'Failed to load message logs.';
    return (
      <div>
        <h1 className="text-2xl font-bold mb-6">All Message Logs</h1>
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
      <h1 className="text-2xl font-bold mb-6">All Message Logs</h1>
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
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
              <tr key={i}>
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
                <td className="px-6 py-4 text-sm">{log.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {items.length === 0 && (
          <div className="p-8 text-center text-gray-500">No logs yet.</div>
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
