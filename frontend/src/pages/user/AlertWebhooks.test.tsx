import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { AlertWebhooks } from './AlertWebhooks';

const mockApiGet = vi.fn();
const mockApiPost = vi.fn();
const mockApiDelete = vi.fn();

vi.mock('../../lib/api', () => ({
  api: {
    get: (...args: unknown[]) => mockApiGet(...args),
    post: (...args: unknown[]) => mockApiPost(...args),
    delete: (...args: unknown[]) => mockApiDelete(...args),
  },
}));

vi.mock('../../store/AuthContext', () => ({
  useAuth: () => ({ user: { id: 1, name: 'Test', email: 'test@test.com', role: 'user' } }),
}));

vi.mock('../../components/Toast', () => ({
  useToast: () => ({ show: vi.fn() }),
}));

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <AlertWebhooks />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('AlertWebhooks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockApiGet.mockResolvedValue({ data: [] });
    mockApiPost.mockResolvedValue({
      data: {
        id: 1,
        url: 'https://example.com/hook',
        enabled: true,
        created_at: '2020-01-01T00:00:00Z',
      },
    });
  });

  it('creates an alert webhook', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('No alert webhooks yet')).toBeInTheDocument();
    });

    fireEvent.change(screen.getByPlaceholderText('https://example.com/hooks/worker-alert'), {
      target: { value: 'https://example.com/hook' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Add webhook' }));

    await waitFor(() => {
      expect(mockApiPost).toHaveBeenCalledWith('/users/me/alert-webhooks', {
        url: 'https://example.com/hook',
      });
    });
  });

  it('removes an alert webhook', async () => {
    mockApiGet.mockResolvedValue({
      data: [
        {
          id: 5,
          url: 'https://hooks.example/a',
          enabled: true,
          created_at: '2020-01-01',
        },
      ],
    });
    mockApiDelete.mockResolvedValue({ data: { status: 'ok' } });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('https://hooks.example/a')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: 'Remove' }));
    const confirms = screen.getAllByRole('button', { name: 'Remove' });
    fireEvent.click(confirms[confirms.length - 1]);

    await waitFor(() => {
      expect(mockApiDelete).toHaveBeenCalledWith('/users/me/alert-webhooks/5');
    });
  });
});
