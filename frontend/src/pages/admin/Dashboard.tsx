import { useQuery } from '@tanstack/react-query';
import { api } from '../../lib/api';

export function AdminDashboard() {
  const { data: users } = useQuery({
    queryKey: ['admin', 'users'],
    queryFn: async () => (await api.get('/admin/users')).data,
  });
  const { data: mappings } = useQuery({
    queryKey: ['mappings'],
    queryFn: async () => (await api.get('/mappings')).data,
  });

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Admin Dashboard</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-2">Users</h2>
          <p className="text-3xl font-bold text-blue-600">{(users as unknown[])?.length ?? 0}</p>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-2">Total Mappings</h2>
          <p className="text-3xl font-bold text-blue-600">{(mappings as unknown[])?.length ?? 0}</p>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-2">Workers</h2>
          <p className="text-3xl font-bold text-blue-600">—</p>
        </div>
      </div>
    </div>
  );
}
