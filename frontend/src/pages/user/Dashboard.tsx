import { Suspense, lazy } from 'react';
import { Smartphone, GitBranch, MessageSquare, Link2, RefreshCw, Webhook, CircleX } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { useAuth } from '../../store/AuthContext';
import { StatCard } from '../../components/StatCard';
import { StatCardSkeleton, ChartSkeleton } from '../../components/Skeleton';
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
  unmapped_source_chats: { chat_id: string; count: number }[];
};

export function UserDashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { data: stats, isLoading, refetch, isFetching, isError, error } = useQuery({
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
  const unmappedSourceChartData = stats?.unmapped_source_chats
    ? stats.unmapped_source_chats.map(({ chat_id, count }) => ({ name: chat_id, count }))
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

      {isError && (
        <div className="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950/30 dark:text-red-300">
          Failed to load dashboard data. Please log in again or refresh. {String((error as Error)?.message ?? '')}
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
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
            <StatCard
              title="Webhook Attempts (7 days)"
              value={stats?.webhook_attempts_last_7d ?? 0}
              icon={Webhook}
              colorVariant="blue"
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
              colorVariant="emerald"
            />
            <StatCard
              title="Webhook Failures (7 days)"
              value={stats?.webhook_failed_last_7d ?? 0}
              icon={CircleX}
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
            color="#ef4444"
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
          <BarChartCard
            title="Unmapped source chats seen (7 days)"
            data={unmappedSourceChartData}
            isLoading={isLoading}
            dataKey="count"
            color="#f59e0b"
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
