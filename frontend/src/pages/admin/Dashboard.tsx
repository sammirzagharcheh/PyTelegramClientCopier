import { Suspense, lazy } from 'react';
import {
  Users,
  Layers,
  Activity,
  MessageSquare,
  Smartphone,
  RefreshCw,
  LayoutDashboard,
} from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { PageHeader } from '../../components/PageHeader';
import { StatCard } from '../../components/StatCard';
import { StatCardSkeleton, ChartSkeleton } from '../../components/Skeleton';
import { Button } from '../../components/ui/Button';
import { ErrorState } from '../../components/ui/States';
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
  top_mappings: { name: string; mapping_name?: string; count: number }[];
  worker_log_levels: { level: string; count: number }[];
};

function ChartFallback() {
  return (
    <div className="rounded-surface border border-line bg-surface-raised p-5 shadow-surface">
      <ChartSkeleton />
    </div>
  );
}

export function AdminDashboard() {
  const { data: stats, isLoading, isError, error, refetch, isFetching } = useQuery({
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
      <PageHeader
        title="Admin Dashboard"
        icon={LayoutDashboard}
        subtitle="Overview of your Telegram Copier instance"
        actions={
          <Button
            variant="secondary"
            icon={RefreshCw}
            iconClassName={isFetching ? 'animate-spin' : undefined}
            onClick={() => refetch()}
            disabled={isFetching}
          >
            Refresh
          </Button>
        }
      />

      {isError ? (
        <ErrorState
          title="We couldn't load the instance overview"
          error={error}
          onRetry={() => refetch()}
        />
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
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
                <StatCard title="Users" value={stats?.users_total ?? 0} icon={Users} />
                <StatCard
                  title="Total Mappings"
                  value={stats?.mappings_total ?? 0}
                  icon={Layers}
                />
                <StatCard title="Workers" value={stats?.workers_count ?? 0} icon={Activity} />
                <StatCard
                  title="Messages (7 days)"
                  value={stats?.messages_last_7d ?? 0}
                  icon={MessageSquare}
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
                />
              </>
            )}
          </div>

          <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Suspense fallback={<ChartFallback />}>
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
              />
              <BarChartCard
                title="Top mappings by volume"
                data={topMappingsData}
                isLoading={isLoading}
                dataKey="count"
                tooltipLabelKey="mapping_name"
              />
            </Suspense>
          </div>
        </>
      )}
    </div>
  );
}
