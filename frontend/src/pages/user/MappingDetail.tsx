import { useQuery } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { api } from '../../lib/api';

type Filter = {
  id: number;
  mapping_id: number;
  include_text: string | null;
  exclude_text: string | null;
  media_types: string | null;
  regex_pattern: string | null;
};

export function MappingDetail() {
  const { id } = useParams<{ id: string }>();
  const { data: mapping } = useQuery({
    queryKey: ['mapping', id],
    queryFn: async () => (await api.get(`/mappings/${id}`)).data,
    enabled: !!id,
  });
  const { data: filters } = useQuery({
    queryKey: ['mapping', id, 'filters'],
    queryFn: async () => (await api.get<Filter[]>(`/mappings/${id}/filters`)).data,
    enabled: !!id,
  });

  if (!mapping) return null;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">{mapping.name || `Mapping ${id}`}</h1>
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 mb-6">
        <dl className="grid grid-cols-2 gap-4">
          <div>
            <dt className="text-sm text-gray-500">Source Chat ID</dt>
            <dd className="font-mono">{mapping.source_chat_id}</dd>
          </div>
          <div>
            <dt className="text-sm text-gray-500">Dest Chat ID</dt>
            <dd className="font-mono">{mapping.dest_chat_id}</dd>
          </div>
          <div>
            <dt className="text-sm text-gray-500">Status</dt>
            <dd>
              <span className={`px-2 py-1 rounded text-xs ${mapping.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
                {mapping.enabled ? 'Enabled' : 'Disabled'}
              </span>
            </dd>
          </div>
        </dl>
      </div>
      <h2 className="text-lg font-semibold mb-4">Filters</h2>
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-700">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Include</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Exclude</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Media</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Regex</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {(filters ?? []).map((f) => (
              <tr key={f.id}>
                <td className="px-6 py-4 text-sm">{f.include_text || '—'}</td>
                <td className="px-6 py-4 text-sm">{f.exclude_text || '—'}</td>
                <td className="px-6 py-4 text-sm">{f.media_types || '—'}</td>
                <td className="px-6 py-4 text-sm font-mono text-xs">{f.regex_pattern || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {(filters ?? []).length === 0 && (
          <div className="p-8 text-center text-gray-500">No filters. All messages pass through.</div>
        )}
      </div>
    </div>
  );
}
