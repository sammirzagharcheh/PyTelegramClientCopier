import { Eye, GitBranch, Inbox, Plus } from 'lucide-react';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { api } from '../../lib/api';
import { AddMappingDialog } from '../../components/AddMappingDialog';
import { PageHeader } from '../../components/PageHeader';
import { SortableTh } from '../../components/SortableTh';
import { StatusBadge } from '../../components/StatusBadge';
import { Pagination } from '../../components/Pagination';

type Mapping = {
  id: number;
  user_id: number;
  source_chat_id: number;
  dest_chat_id: number;
  name: string | null;
  enabled: boolean;
};

type PaginatedMappings = { items: Mapping[]; total: number; page: number; page_size: number; total_pages: number };

export function Mappings() {
  const [showAdd, setShowAdd] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [sortBy, setSortBy] = useState<string>('id');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const { data, isLoading } = useQuery({
    queryKey: ['mappings', page, pageSize, sortBy, sortOrder],
    queryFn: async () =>
      (await api.get<PaginatedMappings>(`/mappings?page=${page}&page_size=${pageSize}&sort_by=${sortBy}&sort_order=${sortOrder}`)).data,
  });
  const mappings = data?.items ?? [];

  if (isLoading) return <div className="animate-pulse h-32 bg-gray-200 dark:bg-gray-700 rounded" />;

  return (
    <div>
      <PageHeader
        title="Channel Mappings"
        icon={GitBranch}
        subtitle="Configure source and destination channel connections"
        actions={
          <button onClick={() => setShowAdd(true)} className="flex items-center gap-2 px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700">
            <Plus className="h-4 w-4" />
            Add Mapping
          </button>
        }
      />
      {showAdd && <AddMappingDialog onClose={() => setShowAdd(false)} />}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden transition-shadow hover:shadow-lg">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-700">
            <tr>
              <SortableTh label="Name" sortKey="name" currentSort={sortBy} currentOrder={sortOrder} onSort={(k, o) => { setSortBy(k); setSortOrder(o); setPage(1); }} />
              <SortableTh label="Source" sortKey="source_chat_id" currentSort={sortBy} currentOrder={sortOrder} onSort={(k, o) => { setSortBy(k); setSortOrder(o); setPage(1); }} />
              <SortableTh label="Dest" sortKey="dest_chat_id" currentSort={sortBy} currentOrder={sortOrder} onSort={(k, o) => { setSortBy(k); setSortOrder(o); setPage(1); }} />
              <SortableTh label="Status" sortKey="enabled" currentSort={sortBy} currentOrder={sortOrder} onSort={(k, o) => { setSortBy(k); setSortOrder(o); setPage(1); }} />
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {mappings.map((m) => (
              <tr key={m.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                <td className="px-6 py-4 text-sm">{m.name || `Mapping ${m.id}`}</td>
                <td className="px-6 py-4 text-sm font-mono">{m.source_chat_id}</td>
                <td className="px-6 py-4 text-sm font-mono">{m.dest_chat_id}</td>
                <td className="px-6 py-4 text-sm">
                  <StatusBadge status={m.enabled ? 'Enabled' : 'Disabled'} variant="enabled" />
                </td>
                <td className="px-6 py-4 text-sm">
                  <Link to={`/mappings/${m.id}`} className="inline-flex items-center gap-1 text-blue-600 hover:underline font-medium">
                    <Eye className="h-3 w-3" />
                    View
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {mappings.length === 0 && (
          <div className="p-8 text-center text-gray-500 flex flex-col items-center gap-2">
            <Inbox className="h-12 w-12 text-gray-400" />
            <p>No mappings yet.</p>
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
