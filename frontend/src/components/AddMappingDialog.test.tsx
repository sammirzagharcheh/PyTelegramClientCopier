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
      expect(screen.getAllByText(/chat id, @username, or t\.me link/i).length).toBeGreaterThan(0);
    });
    expect(api.post).not.toHaveBeenCalled();
  });

  it('resolves @username then posts integer chat ids', async () => {
    vi.mocked(api.post).mockImplementation(async (url, body) => {
      if (String(url).includes('resolve-peer')) {
        const query = (body as { query: string }).query;
        if (query === '@srcchan') {
          return {
            data: {
              chat_id: -100111,
              title: 'Src',
              username: 'srcchan',
              dialog_type: 'channel',
            },
          };
        }
        return {
          data: {
            chat_id: -100222,
            title: 'Dst',
            username: 'dstchan',
            dialog_type: 'channel',
          },
        };
      }
      if (url === '/mappings') {
        return { data: { id: 9 } };
      }
      throw new Error(`unexpected ${url}`);
    });

    renderDialog();
    fireEvent.change(screen.getByLabelText(/telegram account/i), { target: { value: '1' } });
    fireEvent.click(screen.getByLabelText(/enter chat id manually/i));
    fireEvent.change(screen.getByLabelText(/source chat id/i), { target: { value: '@srcchan' } });
    fireEvent.change(screen.getByLabelText(/destination chat id/i), { target: { value: '@dstchan' } });
    fireEvent.click(screen.getByRole('button', { name: /create/i }));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith(
        '/mappings',
        expect.objectContaining({
          source_chat_id: -100111,
          dest_chat_id: -100222,
          telegram_account_id: 1,
          source_chat_title: 'Src',
          dest_chat_title: 'Dst',
        })
      );
    });
    expect(api.post).toHaveBeenCalledWith('/accounts/1/resolve-peer', { query: '@srcchan' });
    expect(api.post).toHaveBeenCalledWith('/accounts/1/resolve-peer', { query: '@dstchan' });
  });
});
