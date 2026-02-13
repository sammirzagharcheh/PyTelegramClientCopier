import { Suspense, lazy } from 'react';
import { Smartphone, GitBranch, MessageSquare, Link2, RefreshCw } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { useAuth } from '../../store/AuthContext';
import { StatCard } from '../../components/StatCard';
import { StatCardSkeleton, ChartSkeleton } from '../../components/Skeleton';
import { computeTrend } from '../../lib/statsUtils';

const AreaChartCard = lazy(() => import('../../components/dashboard/AreaChartCard').then((m) => ({ default: m.AreaChartCard })));
const PieChartCard = lazy(() => import('../../components/dashboard/PieChartCard').then((m) => ({ default: m.PieChartCard })));

type DashboardStats = {
  messages_last_7d: number;
  messages_prev_7d: number;
  messages_by_day: { date: string; count: number }[];
  status_breakdown: { status: string; count: number }[];
  account_status: Record<string, number>;
  mappings_total: number;
  mappings_enabled: number;
  accounts_total: number;
};

export function UserDashboard() {
  const { user } = useAuth();
  const { data: stats, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['stats', 'dashboard'],
    queryFn: async () => (await api.get<DashboardStats>('/stats/dashboard')).data,
    staleTime: 2 * 60 * 1000,
  });

  const messagesTrend = stats
    ? computeTrend(stats.messages_last_7d, stats.messages_prev_7d)
    : undefined;

  const accountChartData = stats?.account_status
    ? Object.entries(stats.account_status).map(([name, value]) => ({ name, value }))
    : [];

  const statusChartData = stats?.status_breakdown
    ? stats.status_breakdown.map(({ status, count }) => ({ name: status, value: count }))
    : [];

  return (
    <div>
      <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Dashboard</h1>
          <p className="mt-1 text-gray-600 dark:text-gray-400">
            Welcome back, {user?.name || user?.email}
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

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {isLoading ? (
          <>
            <StatCardSkeleton />
            <StatCardSkeleton />
            <StatCardSkeleton />
            <StatCardSkeleton />
          </>
        ) : (
          <>
            <StatCard
              title="Telegram Accounts"
              value={stats?.accounts_total ?? 0}
              icon={Smartphone}
              colorVariant="blue"
            />
            <StatCard
              title="Channel Mappings"
              value={stats?.mappings_total ?? 0}
              icon={GitBranch}
              colorVariant="emerald"
            />
            <StatCard
              title="Messages (7 days)"
              value={stats?.messages_last_7d ?? 0}
              icon={MessageSquare}
              colorVariant="violet"
              trend={
                messagesTrend != null
                  ? { value: messagesTrend, label: 'prev 7d' }
                  : undefined
              }
            />
            <StatCard
              title="Enabled Mappings"
              value={stats?.mappings_enabled ?? 0}
              icon={Link2}
              colorVariant="amber"
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
          <PieChartCard
            title="Account status"
            data={accountChartData}
            isLoading={isLoading}
            nameKey="name"
            valueKey="value"
          />
        </Suspense>
      </div>

      <div className="mt-6 flex flex-wrap gap-3">
        <Link
          to="/logs"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 hover:bg-blue-200 dark:hover:bg-blue-900/50 text-sm font-medium transition-colors"
        >
          View Message Logs
        </Link>
        <Link
          to="/mappings"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300 hover:bg-emerald-200 dark:hover:bg-emerald-900/50 text-sm font-medium transition-colors"
        >
          Add Mapping
        </Link>
      </div>
    </div>
  );
}
