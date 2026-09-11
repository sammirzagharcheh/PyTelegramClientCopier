import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SearchableChatSelect } from './SearchableChatSelect';

const chats = [
  { chat_id: -100111, title: 'Source Chan', username: 'src', dialog_type: 'channel' },
  { chat_id: -100222, title: 'Dest Group', username: null, dialog_type: 'group' },
];

describe('SearchableChatSelect', () => {
  it('filters options when typing', () => {
    const onChange = vi.fn();
    render(
      <SearchableChatSelect
        value=""
        onChange={onChange}
        chats={chats}
        aria-label="Source chat"
      />
    );
    fireEvent.focus(screen.getByRole('combobox', { name: /source chat/i }));
    fireEvent.change(screen.getByRole('combobox', { name: /source chat/i }), {
      target: { value: 'Dest' },
    });
    const options = screen.getAllByRole('option');
    expect(options).toHaveLength(1);
    expect(options[0].textContent).toContain('Dest Group');
  });

  it('excludes chat ids from list', () => {
    render(
      <SearchableChatSelect
        value=""
        onChange={vi.fn()}
        chats={chats}
        excludeChatIds={['-100111']}
        aria-label="Destination chat"
      />
    );
    fireEvent.focus(screen.getByRole('combobox', { name: /destination chat/i }));
    const options = screen.getAllByRole('option');
    expect(options).toHaveLength(1);
    expect(options[0].textContent).toContain('Dest Group');
  });

  it('calls onChange when option clicked', () => {
    const onChange = vi.fn();
    render(
      <SearchableChatSelect value="" onChange={onChange} chats={chats} aria-label="Source chat" />
    );
    fireEvent.focus(screen.getByRole('combobox', { name: /source chat/i }));
    fireEvent.click(screen.getByRole('option', { name: /Source Chan/ }));
    expect(onChange).toHaveBeenCalledWith(
      '-100111',
      expect.objectContaining({ chat_id: -100111 })
    );
  });
});
