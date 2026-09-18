import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Logs } from './Logs';
import { api } from '../../lib/api';

vi.mock('../../store/AuthContext', () => ({
  useAuth: () => ({ user: { id: 1, role: 'user', timezone: 'UTC' } }),
}));

vi.mock('../../lib/api', () => ({
  api: {
    get: vi.fn(),
  },
}));

function renderLogs() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <Logs />
    </QueryClientProvider>
  );
}

describe('Logs', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows skip reason column and status filter', async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: {
        items: [
          {
            user_id: 1,
            mapping_id: 3,
            source_chat_id: 10,
            source_msg_id: 100,
            dest_chat_id: 20,
            dest_msg_id: null,
            source_chat_title: 'Src',
            dest_chat_title: 'Dst',
            timestamp: '2026-09-18T12:00:00+00:00',
            status: 'skipped',
            skip_reason: 'filter',
            skip_detail: 'exclude_text',
          },
        ],
        total: 1,
        page: 1,
        page_size: 50,
        total_pages: 1,
      },
    });
    renderLogs();
    await screen.findByText('Reason');
    expect(screen.getByText(/filter · exclude_text/)).toBeInTheDocument();
    const select = screen.getByLabelText('Filter by status');
    fireEvent.change(select, { target: { value: 'skipped' } });
    expect(api.get).toHaveBeenCalledWith(expect.stringContaining('status=skipped'));
  });
});
