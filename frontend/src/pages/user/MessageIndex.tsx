import { useQuery } from '@tanstack/react-query';
import { api } from '../../lib/api';

type IndexEntry = {
  user_id: number;
  source_chat_id: number;
  source_msg_id: number;
  dest_chat_id: number;
  dest_msg_id: number;
};

export function MessageIndex() {
  const { data, isLoading } = useQuery({
    queryKey: ['message-index'],
    queryFn: async () => (await api.get<{ items: IndexEntry[] }>('/message-index')).data,
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
      </div>
    </div>
  );
}
