import { useEffect, useMemo, useRef, useState } from 'react';
import type { TelegramDialog } from '../lib/api';

const DIALOG_TYPE_LABEL: Record<string, string> = {
  channel: 'Channel',
  group: 'Group',
  user: 'User',
  bot: 'Bot',
};

function formatChatLabel(chat: TelegramDialog): string {
  const typeLabel = DIALOG_TYPE_LABEL[chat.dialog_type] ?? chat.dialog_type;
  const handle = chat.username ? ` @${chat.username}` : '';
  return `${chat.title}${handle} (${chat.chat_id}) · ${typeLabel}`;
}

type Props = {
  value: string;
  onChange: (chatId: string, chat: TelegramDialog | null) => void;
  chats: TelegramDialog[];
  excludeChatIds?: string[];
  id?: string;
  'aria-label'?: string;
  disabled?: boolean;
  placeholder?: string;
  staleChatId?: string;
  staleTitle?: string | null;
  error?: string;
};

export function SearchableChatSelect({
  value,
  onChange,
  chats,
  excludeChatIds = [],
  id,
  'aria-label': ariaLabel = 'Chat',
  disabled = false,
  placeholder = 'Search chats...',
  staleChatId,
  staleTitle,
  error,
}: Props) {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const containerRef = useRef<HTMLDivElement>(null);

  const options = useMemo(() => {
    const exclude = new Set(excludeChatIds);
    const base = chats.filter((c) => !exclude.has(String(c.chat_id)));
    if (
      staleChatId &&
      staleChatId.trim() &&
      !base.some((c) => String(c.chat_id) === staleChatId)
    ) {
      base.unshift({
        chat_id: Number(staleChatId),
        title: staleTitle?.trim() || 'Unknown chat',
        username: null,
        dialog_type: 'unknown',
      });
    }
    return base.map((chat) => ({
      chat,
      value: String(chat.chat_id),
      label: formatChatLabel(chat),
    }));
  }, [chats, excludeChatIds, staleChatId, staleTitle]);

  const filteredOptions = useMemo(() => {
    if (!query.trim()) return options;
    const q = query.toLowerCase();
    return options.filter(
      (opt) =>
        opt.label.toLowerCase().includes(q) ||
        opt.value.includes(q) ||
        (opt.chat.username?.toLowerCase().includes(q) ?? false)
    );
  }, [options, query]);

  const selectedLabel = useMemo(() => {
    const opt = options.find((o) => o.value === value);
    if (opt) return opt.label;
    if (value && staleTitle) return `${staleTitle} (${value})`;
    if (value) return `Unknown chat (${value})`;
    return '';
  }, [options, value, staleTitle]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isOpen]);

  const inputClass =
    'w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-left';

  return (
    <div ref={containerRef} className="relative">
      <input
        id={id}
        type="text"
        role="combobox"
        aria-expanded={isOpen ? 'true' : 'false'}
        aria-haspopup="listbox"
        aria-controls={id ? `${id}-listbox` : undefined}
        aria-label={ariaLabel}
        aria-invalid={error ? 'true' : 'false'}
        aria-describedby={error && id ? `${id}-error` : undefined}
        value={isOpen ? query : selectedLabel}
        onChange={(e) => {
          setQuery(e.target.value);
          if (!isOpen) setIsOpen(true);
        }}
        onFocus={() => {
          if (!disabled) {
            setIsOpen(true);
            setQuery('');
          }
        }}
        onKeyDown={(e) => {
          if (e.key === 'Escape') {
            setIsOpen(false);
            setQuery('');
          }
          if (e.key === 'Enter' && isOpen && filteredOptions.length === 1) {
            e.preventDefault();
            const opt = filteredOptions[0];
            onChange(opt.value, opt.chat);
            setIsOpen(false);
            setQuery('');
          }
        }}
        disabled={disabled}
        className={inputClass}
        placeholder={placeholder}
        autoComplete="off"
      />
      {isOpen && !disabled && (
        <div
          id={id ? `${id}-listbox` : undefined}
          role="listbox"
          className="absolute z-50 mt-1 max-h-60 w-full overflow-auto rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 shadow-lg"
        >
          {filteredOptions.length === 0 ? (
            <div className="px-3 py-2 text-sm text-gray-500 dark:text-gray-400">No matches</div>
          ) : (
            filteredOptions.map((opt) => (
              <div
                key={opt.value}
                role="option"
                aria-selected={opt.value === value ? 'true' : 'false'}
                className={`cursor-pointer px-3 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700 ${
                  opt.value === value
                    ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
                    : ''
                }`}
                onClick={() => {
                  onChange(opt.value, opt.chat);
                  setIsOpen(false);
                  setQuery('');
                }}
              >
                {opt.label}
              </div>
            ))
          )}
        </div>
      )}
      {error && (
        <p id={id ? `${id}-error` : undefined} className="text-xs text-red-600 mt-1">
          {error}
        </p>
      )}
    </div>
  );
}

export { formatChatLabel };
