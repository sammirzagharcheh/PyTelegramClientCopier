import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { ApiKeys } from './ApiKeys';

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
        <ApiKeys />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('ApiKeys', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockApiGet.mockResolvedValue({ data: [] });
    mockApiPost.mockResolvedValue({
      data: {
        id: 1,
        name: 'CI bot',
        scopes: 'mappings:read,mappings:write',
        plain_key: 'plain-secret-key',
        created_at: '2020-01-01T00:00:00Z',
      },
    });
  });

  it('lists empty state and creates a key with scopes', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('No API keys yet')).toBeInTheDocument();
    });

    fireEvent.change(screen.getByPlaceholderText('CI bot'), { target: { value: 'CI bot' } });
    fireEvent.click(screen.getByRole('button', { name: 'Create key' }));

    await waitFor(() => {
      expect(mockApiPost).toHaveBeenCalledWith('/users/me/api-keys', {
        name: 'CI bot',
        scopes: expect.stringContaining('mappings:read'),
      });
    });

    expect(await screen.findByTestId('created-key-banner')).toBeInTheDocument();
    expect(screen.getByText('plain-secret-key')).toBeInTheDocument();
  });

  it('revokes an existing key', async () => {
    mockApiGet.mockResolvedValue({
      data: [
        {
          id: 9,
          name: 'old',
          scopes: 'logs:read',
          created_at: '2020-01-01',
          last_used_at: null,
        },
      ],
    });
    mockApiDelete.mockResolvedValue({ data: { status: 'ok' } });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('old')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: 'Revoke' }));
    const confirmButtons = screen.getAllByRole('button', { name: 'Revoke' });
    fireEvent.click(confirmButtons[confirmButtons.length - 1]);

    await waitFor(() => {
      expect(mockApiDelete).toHaveBeenCalledWith('/users/me/api-keys/9');
    });
  });
});
