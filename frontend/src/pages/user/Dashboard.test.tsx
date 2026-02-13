import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { UserDashboard } from './Dashboard';

vi.mock('../../store/AuthContext', () => ({
  useAuth: () => ({ user: { name: 'Test', email: 'test@test.com' } }),
}));

vi.mock('../../lib/api', () => ({
  api: {
    get: vi.fn().mockResolvedValue({
      data: {
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
      },
    }),
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

describe('UserDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders Refresh button', async () => {
    renderDashboard();
    await screen.findByRole('button', { name: /refresh/i });
    expect(screen.getByRole('button', { name: /refresh/i })).toBeInTheDocument();
  });

  it('renders stat cards when data is loaded', async () => {
    renderDashboard();
    await screen.findByText('42');
    expect(screen.getByText('Telegram Accounts')).toBeInTheDocument();
    expect(screen.getByText('Channel Mappings')).toBeInTheDocument();
  });
});
