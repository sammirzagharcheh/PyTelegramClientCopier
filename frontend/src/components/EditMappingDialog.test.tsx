import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { EditMappingDialog } from './EditMappingDialog';
import type { ChannelMapping } from '../lib/api';

vi.mock('../lib/api', () => ({
  api: { patch: vi.fn() },
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
    data: [{ chat_id: -10010, title: 'Src', username: null, dialog_type: 'channel' }],
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
    isFetching: false,
  }),
}));

const mapping: ChannelMapping = {
  id: 1,
  user_id: 1,
  source_chat_id: -10010,
  dest_chat_id: -10020,
  name: 'Route',
  source_chat_title: 'Src',
  dest_chat_title: 'Dst',
  enabled: true,
  telegram_account_id: 1,
  created_at: null,
  send_delay_ms: 0,
  sync_edits: false,
  edit_strategy: 'replace_text',
  sync_deletes: false,
  copy_webhook_url: null,
  copy_webhook_secret: null,
  copy_webhook_payload_template: null,
  copy_webhook_secret_header_name: null,
  copy_webhook_secret_mode: 'hmac_sha256',
};

describe('EditMappingDialog', () => {
  it('pre-fills account and shows stale warning for dest not in dialog list', () => {
    const client = new QueryClient();
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <EditMappingDialog mapping={mapping} onClose={vi.fn()} />
        </MemoryRouter>
      </QueryClientProvider>
    );
    expect(screen.getByLabelText(/telegram account/i)).toHaveValue('1');
    expect(screen.getByText(/not in latest list/i)).toBeInTheDocument();
  });
});
