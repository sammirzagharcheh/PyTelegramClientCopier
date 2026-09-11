import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { MappingRouteFields } from './MappingRouteFields';

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
    data: [],
    isLoading: false,
    isError: true,
    error: { response: { status: 409, data: { detail: 'Account session is in use' } } },
    refetch: vi.fn(),
    isFetching: false,
  }),
}));

describe('MappingRouteFields dialog errors', () => {
  it('shows session locked message with worker link', () => {
    render(
      <MemoryRouter>
        <MappingRouteFields
          values={{
            telegramAccountId: 1,
            sourceChatId: '',
            destChatId: '',
            sourceChatTitle: '',
            destChatTitle: '',
            useManualIds: false,
          }}
          onChange={vi.fn()}
          name=""
          onNameChange={vi.fn()}
        />
      </MemoryRouter>
    );
    expect(screen.getByText(/session is in use/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /stop the worker/i })).toHaveAttribute('href', '/workers');
  });
});
