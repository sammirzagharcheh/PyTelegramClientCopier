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
import { UserFilterSelect } from '../../components/UserFilterSelect';
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
  const { user } = useAuth();
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

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['admin', 'worker-logs', page, pageSize, userId, levelFilter],
    queryFn: async () =>
      (await api.get<PaginatedWorkerLogs>(`/worker-logs?${params}`)).data,
  });

  const items = (data?.items ?? []) as WorkerLog[];
  const isFiltered = userId != null || levelFilter !== '';

  return (
    <div>
      <PageHeader
        title="All Worker Logs"
        icon={ScrollText}
        subtitle="Worker process output across all users"
      />

      <div className="mb-4 flex flex-wrap items-end gap-4">
        <UserFilterSelect
          users={users}
          value={userId}
          onChange={(next) => {
            setUserId(next);
            setPage(1);
          }}
          className="w-72"
        />
        <Field label="Level" className="w-40">
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
        <ErrorState
          title="We couldn't load the worker logs"
          error={error}
          onRetry={() => refetch()}
        />
      ) : isLoading ? (
        <TableSkeleton columns={5} rows={8} />
      ) : (
        <TableShell
          caption="Worker logs for all users"
          footer={
            items.length === 0 ? (
              <EmptyState
                icon={ScrollText}
                title={isFiltered ? 'No logs match these filters' : 'No worker logs yet'}
                description={
                  isFiltered
                    ? 'Clear the user or level filter to see the rest. If nothing appears at all, check that MongoDB is configured in Settings.'
                    : 'Start a worker and its output will show up here. If this stays empty, check that MongoDB is configured in Settings.'
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
              <Th>User</Th>
              <Th>Time</Th>
              <Th>Account</Th>
              <Th>Level</Th>
              <Th>Message</Th>
            </tr>
          </Thead>
          <Tbody>
            {items.map((log, i) => (
              <Tr key={`${log.user_id}-${log.timestamp}-${i}`}>
                <Td className="tabular-nums text-ink-subtle">{log.user_id}</Td>
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
