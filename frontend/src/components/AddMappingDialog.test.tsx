import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { AddMappingDialog } from './AddMappingDialog';

vi.mock('../lib/api', () => ({
  api: {
    post: vi.fn(),
    get: vi.fn(),
  },
}));

vi.mock('../hooks/useActiveAccounts', () => ({
  useActiveAccounts: () => ({
    data: [
      {
        id: 1,
        user_id: 1,
        name: 'Acc',
        type: 'user',
        session_path: '/s',
        phone: null,
        status: 'active',
        created_at: null,
      },
    ],
    isLoading: false,
  }),
  formatAccountLabel: () => 'Acc',
}));

vi.mock('../hooks/useAccountDialogs', () => ({
  useAccountDialogs: () => ({
    data: [
      { chat_id: -1001, title: 'S', username: null, dialog_type: 'channel' },
      { chat_id: -1002, title: 'D', username: null, dialog_type: 'group' },
    ],
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
    isFetching: false,
  }),
}));

import { api } from '../lib/api';

function renderDialog() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <AddMappingDialog onClose={vi.fn()} />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe('AddMappingDialog', () => {
  beforeEach(() => {
    vi.mocked(api.post).mockReset();
  });

  it('shows validation when submitting without route', async () => {
    renderDialog();
    fireEvent.change(screen.getByLabelText(/telegram account/i), { target: { value: '1' } });
    fireEvent.click(screen.getByRole('button', { name: /create/i }));
    await waitFor(() => {
      expect(screen.getByText(/valid source chat/i)).toBeInTheDocument();
    });
    expect(api.post).not.toHaveBeenCalled();
  });
});
