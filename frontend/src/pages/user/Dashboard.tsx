import { Suspense, lazy } from 'react';
import {
  Smartphone,
  GitBranch,
  MessageSquare,
  Link2,
  RefreshCw,
  LayoutDashboard,
} from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { useAuth } from '../../store/AuthContext';
import { PageHeader } from '../../components/PageHeader';
import { StatCard } from '../../components/StatCard';
import { StatCardSkeleton, ChartSkeleton } from '../../components/Skeleton';
import { Button, ButtonLink } from '../../components/ui/Button';
import { ErrorState } from '../../components/ui/States';
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

function ChartFallback() {
  return (
    <div className="rounded-surface border border-line bg-surface-raised p-5 shadow-surface">
      <ChartSkeleton />
    </div>
  );
}

export function UserDashboard() {
  const { user } = useAuth();
  const { data: stats, isLoading, isError, error, refetch, isFetching } = useQuery({
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
      <PageHeader
        title="Dashboard"
        icon={LayoutDashboard}
        subtitle={`Welcome back, ${user?.name || user?.email}`}
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
          title="We couldn't load your dashboard"
          error={error}
          onRetry={() => refetch()}
        />
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
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
                />
                <StatCard
                  title="Channel Mappings"
                  value={stats?.mappings_total ?? 0}
                  icon={GitBranch}
                />
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
                  title="Enabled Mappings"
                  value={stats?.mappings_enabled ?? 0}
                  icon={Link2}
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
              <PieChartCard
                title="Account status"
                data={accountChartData}
                isLoading={isLoading}
                nameKey="name"
                valueKey="value"
              />
            </Suspense>
          </div>

          <div className="mt-6 flex flex-wrap gap-2">
            <ButtonLink to="/logs" icon={MessageSquare}>
              View message logs
            </ButtonLink>
            <ButtonLink to="/mappings" icon={GitBranch}>
              Manage mappings
            </ButtonLink>
          </div>
        </>
      )}
    </div>
  );
}
