import { Suspense, lazy } from 'react';
import {
  Smartphone,
  GitBranch,
  MessageSquare,
  Link2,
  RefreshCw,
  LayoutDashboard,
  Webhook,
  CircleX,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
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
const BarChartCard = lazy(() => import('../../components/dashboard/BarChartCard').then((m) => ({ default: m.BarChartCard })));
const WebhookTrendChartCard = lazy(() => import('../../components/dashboard/WebhookTrendChartCard').then((m) => ({ default: m.WebhookTrendChartCard })));

type DashboardStats = {
  messages_last_7d: number;
  messages_prev_7d: number;
  messages_by_day: { date: string; count: number }[];
  status_breakdown: { status: string; count: number }[];
  account_status: Record<string, number>;
  mappings_total: number;
  mappings_enabled: number;
  accounts_total: number;
  webhook_attempts_last_7d: number;
  webhook_attempts_prev_7d: number;
  webhook_success_last_7d: number;
  webhook_failed_last_7d: number;
  webhook_success_rate: number;
  webhook_by_day: { date: string; success: number; failed: number }[];
  top_failing_mappings: { name: string; mapping_name?: string; count: number }[];
  webhook_failure_reasons: { name: string; count: number }[];
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
  const navigate = useNavigate();
  const { data: stats, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ['stats', 'dashboard'],
    queryFn: async () => (await api.get<DashboardStats>('/stats/dashboard')).data,
    staleTime: 2 * 60 * 1000,
  });

  const messagesTrend = stats
    ? computeTrend(stats.messages_last_7d, stats.messages_prev_7d)
    : undefined;
  const webhookTrend = stats
    ? computeTrend(stats.webhook_attempts_last_7d, stats.webhook_attempts_prev_7d)
    : undefined;

  const accountChartData = stats?.account_status
    ? Object.entries(stats.account_status).map(([name, value]) => ({ name, value }))
    : [];

  const statusChartData = stats?.status_breakdown
    ? stats.status_breakdown.map(({ status, count }) => ({ name: status, value: count }))
    : [];
  const webhookFailureReasonData = stats?.webhook_failure_reasons
    ? stats.webhook_failure_reasons.map(({ name, count }) => ({ name, value: count }))
    : [];
  const reasonToParam: Record<string, string> = {
    'HTTP 401': 'http_401',
    'HTTP 403': 'http_403',
    'HTTP 404': 'http_404',
    'HTTP 429': 'http_429',
    'HTTP 5xx': 'http_5xx',
    Timeout: 'timeout',
    'Network/Connection': 'network_connection',
    Other: 'other',
  };

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
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {isLoading ? (
              <>
                <StatCardSkeleton />
                <StatCardSkeleton />
                <StatCardSkeleton />
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
                <StatCard
                  title="Webhook Attempts (7 days)"
                  value={stats?.webhook_attempts_last_7d ?? 0}
                  icon={Webhook}
                  trend={
                    webhookTrend != null
                      ? { value: webhookTrend, label: 'prev 7d' }
                      : undefined
                  }
                />
                <StatCard
                  title="Webhook Success Rate"
                  value={`${stats?.webhook_success_rate ?? 0}%`}
                  icon={Webhook}
                />
                <StatCard
                  title="Webhook Failures (7 days)"
                  value={stats?.webhook_failed_last_7d ?? 0}
                  icon={CircleX}
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
              <WebhookTrendChartCard
                title="Webhook success vs failure trend (7 days)"
                data={stats?.webhook_by_day ?? []}
                isLoading={isLoading}
              />
              <BarChartCard
                title="Top failing mappings"
                data={stats?.top_failing_mappings ?? []}
                isLoading={isLoading}
                dataKey="count"
                tooltipLabelKey="mapping_name"
              />
              <PieChartCard
                title="Webhook failure reasons"
                data={webhookFailureReasonData}
                isLoading={isLoading}
                nameKey="name"
                valueKey="value"
                onSliceClick={(point) => {
                  const reason = reasonToParam[point.name];
                  if (!reason) return;
                  navigate(`/webhook-logs?success=false&failure_reason=${encodeURIComponent(reason)}`);
                }}
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
