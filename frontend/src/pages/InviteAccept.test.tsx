import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { InviteAccept } from '../pages/InviteAccept';

const mockApiGet = vi.fn();
const mockApiPost = vi.fn();
const mockEstablish = vi.fn();

vi.mock('../lib/api', () => ({
  api: {
    get: (...args: unknown[]) => mockApiGet(...args),
    post: (...args: unknown[]) => mockApiPost(...args),
  },
}));

vi.mock('../store/AuthContext', () => ({
  useAuth: () => ({
    establishSession: (...args: unknown[]) => mockEstablish(...args),
  }),
}));

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/invite/tok123']}>
        <Routes>
          <Route path="/invite/:token" element={<InviteAccept />} />
          <Route path="/" element={<div>home</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('InviteAccept', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockApiGet.mockResolvedValue({
      data: { email: 'new@test.com', role: 'user', expires_at: '2099-01-01T00:00:00Z' },
    });
    mockApiPost.mockResolvedValue({
      data: { access_token: 'a', refresh_token: 'r', token_type: 'bearer' },
    });
    mockEstablish.mockResolvedValue(undefined);
  });

  it('accepts invite and establishes session', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/new@test.com/)).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText(/Password/i), { target: { value: 'password12' } });
    fireEvent.click(screen.getByRole('button', { name: 'Create account' }));

    await waitFor(() => {
      expect(mockApiPost).toHaveBeenCalledWith('/auth/invites/tok123/accept', {
        password: 'password12',
        name: undefined,
      });
      expect(mockEstablish).toHaveBeenCalledWith('a', 'r');
    });
  });
});
