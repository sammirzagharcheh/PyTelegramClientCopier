import { useQuery } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { useAuth } from '../../store/AuthContext';
import { ChangePasswordSection } from '../../components/ChangePasswordSection';

export function UserDashboard() {
  const { user } = useAuth();
  const { data: accountsData } = useQuery({
    queryKey: ['accounts', 1, 1],
    queryFn: async () => (await api.get<{ total: number }>('/accounts?page=1&page_size=1')).data,
  });
  const { data: mappingsData } = useQuery({
    queryKey: ['mappings', 1, 1],
    queryFn: async () => (await api.get<{ total: number }>('/mappings?page=1&page_size=1')).data,
  });

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>
      <p className="mb-6 text-gray-600 dark:text-gray-400">Welcome, {user?.name || user?.email}</p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-2">Telegram Accounts</h2>
          <p className="text-3xl font-bold text-blue-600">{accountsData?.total ?? 0}</p>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-2">Channel Mappings</h2>
          <p className="text-3xl font-bold text-blue-600">{mappingsData?.total ?? 0}</p>
        </div>
      </div>
      <div className="mt-6">
        <ChangePasswordSection />
      </div>
    </div>
  );
}
