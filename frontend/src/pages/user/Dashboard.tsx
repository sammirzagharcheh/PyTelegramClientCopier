import { Smartphone, GitBranch } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { useAuth } from '../../store/AuthContext';
import { ChangePasswordSection } from '../../components/ChangePasswordSection';
import { StatCard } from '../../components/StatCard';

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
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Dashboard</h1>
        <p className="mt-1 text-gray-600 dark:text-gray-400">
          Welcome back, {user?.name || user?.email}
        </p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <StatCard
          title="Telegram Accounts"
          value={accountsData?.total ?? 0}
          icon={Smartphone}
          colorVariant="blue"
        />
        <StatCard
          title="Channel Mappings"
          value={mappingsData?.total ?? 0}
          icon={GitBranch}
          colorVariant="emerald"
        />
      </div>
      <div className="mt-8">
        <ChangePasswordSection />
      </div>
    </div>
  );
}
