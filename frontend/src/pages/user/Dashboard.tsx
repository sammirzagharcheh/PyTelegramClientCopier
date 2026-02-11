import { useQuery } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { useAuth } from '../../store/AuthContext';

export function UserDashboard() {
  const { user } = useAuth();
  const { data: accounts } = useQuery({
    queryKey: ['accounts'],
    queryFn: async () => (await api.get('/accounts')).data,
  });
  const { data: mappings } = useQuery({
    queryKey: ['mappings'],
    queryFn: async () => (await api.get('/mappings')).data,
  });

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>
      <p className="mb-6 text-gray-600 dark:text-gray-400">Welcome, {user?.name || user?.email}</p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-2">Telegram Accounts</h2>
          <p className="text-3xl font-bold text-blue-600">{(accounts as unknown[])?.length ?? 0}</p>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-2">Channel Mappings</h2>
          <p className="text-3xl font-bold text-blue-600">{(mappings as unknown[])?.length ?? 0}</p>
        </div>
      </div>
    </div>
  );
}
