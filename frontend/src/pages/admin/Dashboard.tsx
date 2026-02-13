import { Suspense, lazy } from 'react';
import { Users, Layers, Activity, MessageSquare, Smartphone, RefreshCw } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { StatCard } from '../../components/StatCard';
import { StatCardSkeleton, ChartSkeleton } from '../../components/Skeleton';
import { computeTrend } from '../../lib/statsUtils';

const AreaChartCard = lazy(() => import('../../components/dashboard/AreaChartCard').then((m) => ({ default: m.AreaChartCard })));
const PieChartCard = lazy(() => import('../../components/dashboard/PieChartCard').then((m) => ({ default: m.PieChartCard })));
const BarChartCard = lazy(() => import('../../components/dashboard/BarChartCard').then((m) => ({ default: m.BarChartCard })));

type AdminDashboardStats = {
  users_total: number;
  mappings_total: number;
  mappings_enabled: number;
  workers_count: number;
  active_accounts: number;
  messages_last_7d: number;
  messages_prev_7d: number;
  messages_by_day: { date: string; count: number }[];
  status_breakdown: { status: string; count: number }[];
  top_mappings: { name: string; count: number }[];
  worker_log_levels: { level: string; count: number }[];
};

export function AdminDashboard() {
  const { data: stats, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['admin', 'stats', 'dashboard'],
    queryFn: async () =>
      (await api.get<AdminDashboardStats>('/admin/stats/dashboard')).data,
    staleTime: 2 * 60 * 1000,
  });

  const messagesTrend = stats
    ? computeTrend(stats.messages_last_7d, stats.messages_prev_7d)
    : undefined;

  const statusChartData = stats?.status_breakdown
    ? stats.status_breakdown.map(({ status, count }) => ({ name: status, value: count }))
    : [];

  const workerLevelData = stats?.worker_log_levels
    ? stats.worker_log_levels.map(({ level, count }) => ({ name: level, value: count }))
    : [];

  const topMappingsData = stats?.top_mappings ?? [];

  return (
    <div>
      <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            Admin Dashboard
          </h1>
          <p className="mt-1 text-gray-600 dark:text-gray-400">
            Overview of your Telegram Copier instance
          </p>
        </div>
        <button
          type="button"
          onClick={() => refetch()}
          disabled={isFetching}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 text-sm font-medium transition-colors"
        >
          <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-6">
        {isLoading ? (
          <>
            <StatCardSkeleton />
            <StatCardSkeleton />
            <StatCardSkeleton />
            <StatCardSkeleton />
            <StatCardSkeleton />
          </>
        ) : (
          <>
            <StatCard
              title="Users"
              value={stats?.users_total ?? 0}
              icon={Users}
              colorVariant="violet"
            />
            <StatCard
              title="Total Mappings"
              value={stats?.mappings_total ?? 0}
              icon={Layers}
              colorVariant="emerald"
            />
            <StatCard
              title="Workers"
              value={stats?.workers_count ?? 0}
              icon={Activity}
              colorVariant="amber"
            />
            <StatCard
              title="Messages (7 days)"
              value={stats?.messages_last_7d ?? 0}
              icon={MessageSquare}
              colorVariant="blue"
              trend={
                messagesTrend != null
                  ? { value: messagesTrend, label: 'prev 7d' }
                  : undefined
              }
            />
            <StatCard
              title="Active Accounts"
              value={stats?.active_accounts ?? 0}
              icon={Smartphone}
              colorVariant="emerald"
            />
          </>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
        <Suspense fallback={<div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-6"><ChartSkeleton /></div>}>
          <AreaChartCard
            title="Messages over time (last 7 days)"
            data={stats?.messages_by_day ?? []}
            isLoading={isLoading}
          />
          <PieChartCard
            title="Message status"
            data={statusChartData}
            isLoading={isLoading}
            nameKey="name"
            valueKey="value"
          />
          <BarChartCard
            title="Worker log levels (7 days)"
            data={workerLevelData}
            isLoading={isLoading}
            dataKey="value"
            color="#f59e0b"
          />
          <BarChartCard
            title="Top mappings by volume"
            data={topMappingsData}
            isLoading={isLoading}
            dataKey="count"
            color="#10b981"
          />
        </Suspense>
      </div>

    </div>
  );
}
