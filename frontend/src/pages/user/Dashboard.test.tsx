import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { UserDashboard } from './Dashboard';
import { api } from '../../lib/api';

vi.mock('../../store/AuthContext', () => ({
  useAuth: () => ({ user: { name: 'Test', email: 'test@test.com' } }),
}));

vi.mock('../../lib/api', () => ({
  api: {
    get: vi.fn(),
  },
}));

function renderDashboard() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <UserDashboard />
      </BrowserRouter>
    </QueryClientProvider>
  );
}

const baseStats = {
  messages_last_7d: 42,
  messages_prev_7d: 30,
  messages_by_day: Array.from({ length: 7 }, (_, i) => ({
    date: `2025-02-1${i}`,
    count: 5 + i,
  })),
  status_breakdown: [{ status: 'ok', count: 40 }],
  account_status: { active: 2 },
  mappings_total: 1,
  mappings_enabled: 1,
  accounts_total: 2,
  webhook_attempts_last_7d: 0,
  webhook_attempts_prev_7d: 0,
  webhook_success_last_7d: 0,
  webhook_failed_last_7d: 0,
  webhook_success_rate: 0,
  webhook_by_day: [],
  top_failing_mappings: [],
  webhook_failure_reasons: [],
};

describe('UserDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders Refresh button', async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: {
        ...baseStats,
        setup: {
          account: true,
          mapping: true,
          worker: false,
          first_copy: false,
          complete: false,
        },
      },
    });
    renderDashboard();
    await screen.findByRole('button', { name: /refresh/i });
    expect(screen.getByRole('button', { name: /refresh/i })).toBeInTheDocument();
  });

  it('shows setup checklist when incomplete and hides webhook charts', async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: {
        ...baseStats,
        setup: {
          account: true,
          mapping: true,
          worker: false,
          first_copy: false,
          complete: false,
        },
      },
    });
    renderDashboard();
    await screen.findByTestId('setup-checklist');
    expect(screen.getByText('Get copying')).toBeInTheDocument();
    expect(screen.getByText('Start a worker')).toBeInTheDocument();
    expect(screen.queryByText('Webhook Success Rate')).not.toBeInTheDocument();
  });

  it('hides checklist and shows webhook stats when setup is complete', async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: {
        ...baseStats,
        setup: {
          account: true,
          mapping: true,
          worker: true,
          first_copy: true,
          complete: true,
        },
      },
    });
    renderDashboard();
    await screen.findByText('42');
    expect(screen.queryByTestId('setup-checklist')).not.toBeInTheDocument();
    expect(screen.getByText('Webhook Success Rate')).toBeInTheDocument();
  });

  it('renders stat cards when data is loaded', async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: {
        ...baseStats,
        setup: {
          account: true,
          mapping: true,
          worker: false,
          first_copy: false,
          complete: false,
        },
      },
    });
    renderDashboard();
    expect(await screen.findByText('Telegram Accounts')).toBeInTheDocument();
    expect(screen.getByText('Channel Mappings')).toBeInTheDocument();
    expect(screen.getByText('42')).toBeInTheDocument();
  });
});
