import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { Pagination } from '../../components/Pagination';

type WorkerLog = {
  user_id: number;
  account_id: number | null;
  level: string;
  message: string;
  timestamp: string;
};

type PaginatedWorkerLogs = {
  items: WorkerLog[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};

export function WorkerLogs() {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [levelFilter, setLevelFilter] = useState<string>('');

  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  if (levelFilter) params.set('level', levelFilter);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['worker-logs', page, pageSize, levelFilter],
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
        <h1 className="text-2xl font-bold mb-6">Worker Logs</h1>
        <div className="p-4 rounded-lg bg-amber-50 dark:bg-amber-900/30 text-amber-800 dark:text-amber-200 border border-amber-200 dark:border-amber-800">
          <p className="font-medium">Could not load logs</p>
          <p className="mt-1 text-sm">{msg}</p>
        </div>
      </div>
    );
  }

  const items = (data?.items ?? []) as WorkerLog[];

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Worker Logs</h1>
      <div className="mb-4 flex items-center gap-4">
        <label htmlFor="worker-logs-level" className="text-sm font-medium">
          Filter by level
        </label>
        <select
          id="worker-logs-level"
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
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-700">
            <tr>
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
              <tr key={i}>
                <td className="px-6 py-4 text-sm whitespace-nowrap">{log.timestamp}</td>
                <td className="px-6 py-4 text-sm">
                  {log.account_id != null ? String(log.account_id) : '—'}
                </td>
                <td className="px-6 py-4 text-sm">
                  <span
                    className={`px-2 py-1 rounded text-xs ${
                      log.level === 'ERROR'
                        ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
                        : log.level === 'WARNING'
                          ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400'
                          : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-400'
                    }`}
                  >
                    {log.level}
                  </span>
                </td>
                <td className="px-6 py-4 text-sm break-all">{log.message}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {items.length === 0 && (
          <div className="p-8 text-center text-gray-500">
            No worker logs yet. Start a worker to see logs.
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
