import { Filter, Inbox, Webhook } from 'lucide-react';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { PageHeader } from '../../components/PageHeader';
import { Pagination } from '../../components/Pagination';
import { api } from '../../lib/api';
import { formatLocalDateTime } from '../../lib/formatDateTime';
import { useAuth } from '../../store/AuthContext';

type WebhookLog = {
  timestamp: string;
  mapping_id: number;
  source_chat_id: number;
  dest_chat_id: number;
  source_chat_title?: string | null;
  dest_chat_title?: string | null;
  event: string | null;
  request_url: string | null;
  request_method: string;
  payload_size_bytes: number | null;
  request_body_preview: string | null;
  success: boolean;
  status_code: number | null;
  status_text: string | null;
  latency_ms: number | null;
  response_content_type: string | null;
  error: string | null;
  response_body: string | null;
  response_body_truncated: boolean;
};

type PaginatedWebhookLogs = {
  items: WebhookLog[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};

function SuccessBadge({ success }: { success: boolean }) {
  const classes = success
    ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200'
    : 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200';
  return (
    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${classes}`}>
      {success ? 'Success' : 'Failed'}
    </span>
  );
}

export function WebhookLogs() {
  const { user } = useAuth();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [mappingId, setMappingId] = useState<string>('');
  const [successFilter, setSuccessFilter] = useState<string>('');

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['webhook-logs', page, pageSize, mappingId, successFilter, user?.id],
    queryFn: async () => {
      const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
      if (mappingId.trim()) params.set('mapping_id', mappingId.trim());
      if (successFilter) params.set('success', successFilter);
      return (await api.get<PaginatedWebhookLogs>(`/webhook-logs?${params}`)).data;
    },
    enabled: user != null,
  });

  if (isLoading) return <div className="animate-pulse h-32 bg-gray-200 dark:bg-gray-700 rounded" />;

  if (isError) {
    const rawMsg =
      (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
      'Failed to load webhook logs.';
    const msg =
      rawMsg.toLowerCase().includes('admin access required')
        ? 'Unable to load webhook logs for this session. Please refresh or sign in again.'
        : rawMsg;
    return (
      <div>
        <PageHeader title="Webhook Logs" icon={Webhook} subtitle="Copy webhook delivery attempts for your active mappings" />
        <div className="p-4 rounded-lg bg-amber-50 dark:bg-amber-900/30 text-amber-800 dark:text-amber-200 border border-amber-200 dark:border-amber-800">
          <p className="font-medium">Could not load logs</p>
          <p className="mt-1 text-sm">{msg}</p>
        </div>
      </div>
    );
  }

  const items = data?.items ?? [];
  return (
    <div>
      <PageHeader title="Webhook Logs" icon={Webhook} subtitle="Copy webhook delivery attempts for your active mappings" />
      <div className="mb-6 flex flex-wrap items-center gap-4 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-800/50 px-4 py-3">
        <Filter className="h-4 w-4 text-gray-500 dark:text-gray-400 shrink-0" />
        <label htmlFor="webhook-logs-mapping" className="text-sm font-medium">
          Mapping ID
        </label>
        <input
          id="webhook-logs-mapping"
          value={mappingId}
          onChange={(e) => {
            setMappingId(e.target.value);
            setPage(1);
          }}
          placeholder="e.g. 42"
          className="w-28 px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700"
        />
        <label htmlFor="webhook-logs-result" className="text-sm font-medium">
          Result
        </label>
        <select
          id="webhook-logs-result"
          value={successFilter}
          onChange={(e) => {
            setSuccessFilter(e.target.value);
            setPage(1);
          }}
          className="px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700"
        >
          <option value="">All</option>
          <option value="true">Success</option>
          <option value="false">Failed</option>
        </select>
      </div>
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden transition-shadow hover:shadow-lg">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-700">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Time</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Mapping</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Route</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Request</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Response</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Result</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {items.map((log, i) => (
              <tr key={`${log.timestamp}-${log.mapping_id}-${i}`} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                <td className="px-6 py-4 text-sm whitespace-nowrap" title={log.timestamp}>
                  {formatLocalDateTime(log.timestamp, user?.timezone ?? undefined)}
                </td>
                <td className="px-6 py-4 text-sm">
                  <div className="font-medium">M{log.mapping_id}</div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">{log.event ?? 'message_copied'}</div>
                </td>
                <td className="px-6 py-4 text-sm">
                  <div title={log.source_chat_title ?? undefined}>{log.source_chat_title || log.source_chat_id}</div>
                  <div className="text-xs text-gray-500 dark:text-gray-400" title={log.dest_chat_title ?? undefined}>
                    → {log.dest_chat_title || log.dest_chat_id}
                  </div>
                </td>
                <td className="px-6 py-4 text-sm">
                  <div className="break-all">{log.request_url || '—'}</div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">
                    {log.request_method} {log.payload_size_bytes != null ? `· ${log.payload_size_bytes} B` : ''}
                  </div>
                  {log.request_body_preview ? (
                    <details className="mt-1 text-xs">
                      <summary className="cursor-pointer text-blue-600 dark:text-blue-300">Request body</summary>
                      <pre className="mt-1 whitespace-pre-wrap break-all text-gray-600 dark:text-gray-300">{log.request_body_preview}</pre>
                    </details>
                  ) : null}
                </td>
                <td className="px-6 py-4 text-sm">
                  <div>
                    {log.status_code != null
                      ? `HTTP ${log.status_code}${log.status_text ? ` ${log.status_text}` : ''}`
                      : 'No status'}
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">
                    {log.latency_ms != null ? `${log.latency_ms} ms` : '—'}
                    {log.response_content_type ? ` · ${log.response_content_type}` : ''}
                  </div>
                  {log.response_body ? (
                    <details className="mt-1 text-xs">
                      <summary className="cursor-pointer text-blue-600 dark:text-blue-300">
                        Response body{log.response_body_truncated ? ' (truncated)' : ''}
                      </summary>
                      <pre className="mt-1 whitespace-pre-wrap break-all text-gray-600 dark:text-gray-300">{log.response_body}</pre>
                    </details>
                  ) : null}
                </td>
                <td className="px-6 py-4 text-sm">
                  <SuccessBadge success={log.success} />
                  {log.error && <div className="mt-1 text-xs text-red-600 dark:text-red-300 break-all">{log.error}</div>}
                  {!log.error && !log.success && log.response_body && (
                    <div className="mt-1 text-xs text-gray-600 dark:text-gray-300 break-all">{log.response_body}</div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {items.length === 0 && (
          <div className="p-8 text-center text-gray-500 flex flex-col items-center gap-2">
            <Inbox className="h-12 w-12 text-gray-400" />
            <p>No webhook logs yet for your active mappings.</p>
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
