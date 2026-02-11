import { useQuery } from '@tanstack/react-query';
import { api } from '../../lib/api';

export function AdminDashboard() {
  const { data: usersData } = useQuery({
    queryKey: ['admin', 'users', 1, 1],
    queryFn: async () => (await api.get<{ total: number }>('/admin/users?page=1&page_size=1')).data,
  });
  const { data: mappingsData } = useQuery({
    queryKey: ['mappings', 1, 1],
    queryFn: async () => (await api.get<{ total: number }>('/mappings?page=1&page_size=1')).data,
  });

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Admin Dashboard</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-2">Users</h2>
          <p className="text-3xl font-bold text-blue-600">{usersData?.total ?? 0}</p>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-2">Total Mappings</h2>
          <p className="text-3xl font-bold text-blue-600">{mappingsData?.total ?? 0}</p>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-2">Workers</h2>
          <p className="text-3xl font-bold text-blue-600">—</p>
        </div>
      </div>
    </div>
  );
}
