import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { api } from '../../lib/api';
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

export function AdminMappings() {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const { data, isLoading } = useQuery({
    queryKey: ['mappings', page, pageSize],
    queryFn: async () => (await api.get<PaginatedMappings>(`/mappings?page=${page}&page_size=${pageSize}`)).data,
  });
  const mappings = data?.items ?? [];

  if (isLoading) return <div className="animate-pulse h-32 bg-gray-200 dark:bg-gray-700 rounded" />;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">All Mappings</h1>
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-700">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">User</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Name</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Source</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Dest</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {mappings.map((m) => (
              <tr key={m.id}>
                <td className="px-6 py-4 text-sm">{m.user_id}</td>
                <td className="px-6 py-4 text-sm">{m.name || `Mapping ${m.id}`}</td>
                <td className="px-6 py-4 text-sm font-mono">{m.source_chat_id}</td>
                <td className="px-6 py-4 text-sm font-mono">{m.dest_chat_id}</td>
                <td className="px-6 py-4 text-sm">
                  <span className={`px-2 py-1 rounded text-xs ${m.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
                    {m.enabled ? 'Enabled' : 'Disabled'}
                  </span>
                </td>
                <td className="px-6 py-4 text-sm">
                  <Link to={`/mappings/${m.id}`} className="text-blue-600 hover:underline">View</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {mappings.length === 0 && (
          <div className="p-8 text-center text-gray-500">No mappings yet.</div>
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
