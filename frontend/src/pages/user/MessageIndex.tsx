import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { Pagination } from '../../components/Pagination';

type IndexEntry = {
  user_id: number;
  source_chat_id: number;
  source_msg_id: number;
  dest_chat_id: number;
  dest_msg_id: number;
};

type PaginatedIndex = { items: IndexEntry[]; total: number; page: number; page_size: number; total_pages: number };

export function MessageIndex() {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const { data, isLoading } = useQuery({
    queryKey: ['message-index', page, pageSize],
    queryFn: async () => (await api.get<PaginatedIndex>(`/message-index?page=${page}&page_size=${pageSize}`)).data,
  });

  if (isLoading) return <div className="animate-pulse h-32 bg-gray-200 dark:bg-gray-700 rounded" />;

  const items = (data?.items ?? []) as IndexEntry[];

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Message Index</h1>
      <p className="mb-4 text-gray-600 dark:text-gray-400 text-sm">
        Maps source message IDs to destination message IDs for reply threading.
      </p>
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-700">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Source Chat</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Source Msg</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Dest Chat</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Dest Msg</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {items.map((e, i) => (
              <tr key={i}>
                <td className="px-6 py-4 text-sm font-mono">{e.source_chat_id}</td>
                <td className="px-6 py-4 text-sm font-mono">{e.source_msg_id}</td>
                <td className="px-6 py-4 text-sm font-mono">{e.dest_chat_id}</td>
                <td className="px-6 py-4 text-sm font-mono">{e.dest_msg_id}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {items.length === 0 && (
          <div className="p-8 text-center text-gray-500">No index entries yet.</div>
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
