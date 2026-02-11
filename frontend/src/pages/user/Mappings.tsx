import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { api } from '../../lib/api';
import { AddMappingDialog } from '../../components/AddMappingDialog';

type Mapping = {
  id: number;
  user_id: number;
  source_chat_id: number;
  dest_chat_id: number;
  name: string | null;
  enabled: boolean;
};

export function Mappings() {
  const [showAdd, setShowAdd] = useState(false);
  const { data: mappings, isLoading } = useQuery({
    queryKey: ['mappings'],
    queryFn: async () => (await api.get<Mapping[]>('/mappings')).data,
  });

  if (isLoading) return <div className="animate-pulse h-32 bg-gray-200 dark:bg-gray-700 rounded" />;

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Channel Mappings</h1>
        <button onClick={() => setShowAdd(true)} className="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700">
          Add Mapping
        </button>
      </div>
      {showAdd && <AddMappingDialog onClose={() => setShowAdd(false)} />}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-700">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Name</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Source</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Dest</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {(mappings ?? []).map((m) => (
              <tr key={m.id}>
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
        {(mappings ?? []).length === 0 && (
          <div className="p-8 text-center text-gray-500">No mappings yet.</div>
        )}
      </div>
    </div>
  );
}
