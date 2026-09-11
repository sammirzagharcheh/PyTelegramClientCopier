import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { MappingRouteFields } from './MappingRouteFields';
import type { MappingRouteValues } from '../lib/mappingValidation';

const accounts = [
  {
    id: 1,
    user_id: 1,
    name: 'Main',
    type: 'user',
    session_path: '/tmp/a.session',
    phone: null,
    status: 'active',
    created_at: null,
  },
];

const dialogs = [
  { chat_id: -10010, title: 'Src', username: null, dialog_type: 'channel' },
  { chat_id: -10020, title: 'Dst', username: null, dialog_type: 'group' },
];

vi.mock('../hooks/useActiveAccounts', () => ({
  useActiveAccounts: () => ({ data: accounts, isLoading: false }),
  formatAccountLabel: (a: { name: string }) => a.name,
}));

vi.mock('../hooks/useAccountDialogs', () => ({
  useAccountDialogs: (accountId: number | null) => ({
    data: accountId ? dialogs : [],
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
    isFetching: false,
  }),
}));

const baseValues: MappingRouteValues = {
  telegramAccountId: null,
  sourceChatId: '',
  destChatId: '',
  sourceChatTitle: '',
  destChatTitle: '',
  useManualIds: false,
};

function renderFields(
  values: MappingRouteValues,
  onChange: (v: MappingRouteValues) => void
) {
  return render(
    <MemoryRouter>
      <MappingRouteFields
        values={values}
        onChange={onChange}
        name=""
        onNameChange={vi.fn()}
      />
    </MemoryRouter>
  );
}

describe('MappingRouteFields', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows account select and disables chats until account chosen', () => {
    renderFields(baseValues, vi.fn());
    expect(screen.getByLabelText(/telegram account/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/source chat/i)).not.toBeInTheDocument();
  });

  it('shows chat pickers after account selected', () => {
    const onChange = vi.fn();
    renderFields({ ...baseValues, telegramAccountId: 1 }, onChange);
    expect(screen.getByLabelText(/source chat/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/destination chat/i)).toBeInTheDocument();
  });

  it('toggles manual id mode', () => {
    const onChange = vi.fn();
    renderFields({ ...baseValues, telegramAccountId: 1 }, onChange);
    fireEvent.click(screen.getByLabelText(/enter chat id manually/i));
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ useManualIds: true })
    );
  });
});
