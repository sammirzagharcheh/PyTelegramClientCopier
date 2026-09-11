import { ScrollText } from 'lucide-react';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { formatLocalDateTime } from '../../lib/formatDateTime';
import { useAuth } from '../../store/AuthContext';
import { PageHeader } from '../../components/PageHeader';
import { Pagination } from '../../components/Pagination';
import { LogLevelBadge } from '../../components/LogLevelBadge';
import { TableSkeleton } from '../../components/Skeleton';
import { Field, Select } from '../../components/ui/Field';
import { EmptyState, ErrorState } from '../../components/ui/States';
import { TableShell, Tbody, Td, Th, Thead, Tr } from '../../components/ui/TableShell';

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
  const { user } = useAuth();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [levelFilter, setLevelFilter] = useState<string>('');

  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  if (levelFilter) params.set('level', levelFilter);

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['worker-logs', page, pageSize, levelFilter, user?.id],
    queryFn: async () =>
      (await api.get<PaginatedWorkerLogs>(`/worker-logs?${params}`)).data,
    enabled: user != null,
  });

  const rawItems = (data?.items ?? []) as WorkerLog[];
  const items =
    user?.role !== 'admin' && user?.id != null
      ? rawItems.filter((log) => Number(log.user_id) === Number(user.id))
      : rawItems;

  return (
    <div>
      <PageHeader title="Worker Logs" icon={ScrollText} subtitle="Worker process output" />

      <div className="mb-4 max-w-56">
        <Field label="Filter by level">
          {(fieldProps) => (
            <Select
              {...fieldProps}
              value={levelFilter}
              onChange={(e) => {
                setLevelFilter(e.target.value);
                setPage(1);
              }}
            >
              <option value="">All levels</option>
              <option value="DEBUG">Debug</option>
              <option value="INFO">Info</option>
              <option value="WARNING">Warning</option>
              <option value="ERROR">Error</option>
            </Select>
          )}
        </Field>
      </div>

      {isError ? (
        <ErrorState title="We couldn't load the worker logs" error={error} onRetry={() => refetch()} />
      ) : isLoading ? (
        <TableSkeleton columns={4} rows={8} />
      ) : (
        <TableShell
          caption="Worker process output"
          footer={
            items.length === 0 ? (
              <EmptyState
                icon={ScrollText}
                title={levelFilter ? `No ${levelFilter.toLowerCase()} entries` : 'No worker logs yet'}
                description={
                  levelFilter
                    ? 'Try a different level, or clear the filter to see everything.'
                    : 'Start a worker and its output will show up here.'
                }
              />
            ) : (
              data && (
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
              )
            )
          }
        >
          <Thead>
            <tr>
              <Th>Time</Th>
              <Th>Account</Th>
              <Th>Level</Th>
              <Th>Message</Th>
            </tr>
          </Thead>
          <Tbody>
            {items.map((log, i) => (
              <Tr key={`${log.timestamp}-${i}`}>
                <Td className="whitespace-nowrap text-ink-muted">
                  <time dateTime={log.timestamp}>
                    {formatLocalDateTime(log.timestamp, user?.timezone ?? undefined)}
                  </time>
                </Td>
                <Td className="tabular-nums text-ink-muted">
                  {log.account_id != null ? String(log.account_id) : 'Not set'}
                </Td>
                <Td>
                  <LogLevelBadge level={log.level} />
                </Td>
                <Td className="font-mono text-xs break-words">{log.message}</Td>
              </Tr>
            ))}
          </Tbody>
        </TableShell>
      )}
    </div>
  );
}
