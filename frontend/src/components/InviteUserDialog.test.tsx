import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { InviteUserDialog } from './InviteUserDialog';

const mockApiPost = vi.fn();

vi.mock('../lib/api', () => ({
  api: {
    post: (...args: unknown[]) => mockApiPost(...args),
  },
}));

vi.mock('./Toast', () => ({
  useToast: () => ({ show: vi.fn() }),
}));

function renderDialog() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <InviteUserDialog onClose={vi.fn()} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('InviteUserDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockApiPost.mockResolvedValue({
      data: {
        id: 1,
        email: 'new@test.com',
        role: 'user',
        expires_at: '2099-01-01T00:00:00+00:00',
        invite_path: '/invite/plain-token',
        plain_token: 'plain-token',
        created_at: '2020-01-01',
      },
    });
  });

  it('creates an invite and shows the link once', async () => {
    renderDialog();
    fireEvent.change(screen.getByLabelText(/Email/i), { target: { value: 'new@test.com' } });
    fireEvent.click(screen.getByRole('button', { name: 'Create invite' }));

    await waitFor(() => {
      expect(mockApiPost).toHaveBeenCalledWith('/admin/invites', {
        email: 'new@test.com',
        role: 'user',
        expires_in_hours: 72,
      });
    });

    expect(await screen.findByTestId('invite-created')).toBeInTheDocument();
    expect(screen.getByText(/\/invite\/plain-token/)).toBeInTheDocument();
  });
});
