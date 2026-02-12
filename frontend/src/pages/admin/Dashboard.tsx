import { Users, Layers, Activity } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { ChangePasswordSection } from '../../components/ChangePasswordSection';
import { StatCard } from '../../components/StatCard';

export function AdminDashboard() {
  const { data: usersData } = useQuery({
    queryKey: ['admin', 'users', 1, 1],
    queryFn: async () => (await api.get<{ total: number }>('/admin/users?page=1&page_size=1')).data,
  });
  const { data: mappingsData } = useQuery({
    queryKey: ['mappings', 1, 1],
    queryFn: async () => (await api.get<{ total: number }>('/mappings?page=1&page_size=1')).data,
  });
  const { data: workers } = useQuery({
    queryKey: ['workers'],
    queryFn: async () => (await api.get<unknown[]>('/workers')).data,
  });

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Admin Dashboard</h1>
        <p className="mt-1 text-gray-600 dark:text-gray-400">Overview of your Telegram Copier instance</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCard
          title="Users"
          value={usersData?.total ?? 0}
          icon={Users}
          colorVariant="violet"
        />
        <StatCard
          title="Total Mappings"
          value={mappingsData?.total ?? 0}
          icon={Layers}
          colorVariant="emerald"
        />
        <StatCard
          title="Workers"
          value={workers?.length ?? 0}
          icon={Activity}
          colorVariant="amber"
        />
      </div>
      <div className="mt-8">
        <ChangePasswordSection />
      </div>
    </div>
  );
}
