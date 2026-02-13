import { Bot, User } from 'lucide-react';

type Props = {
  type: 'user' | 'bot' | string;
};

export function AccountTypeBadge({ type }: Props) {
  const t = String(type).toLowerCase();
  const isUser = t === 'user';
  const isBot = t === 'bot';
  const label = isUser ? 'User' : isBot ? 'Bot' : type || '—';
  const Icon = isUser ? User : isBot ? Bot : User;
  const className = isUser
    ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
    : isBot
      ? 'bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400'
      : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-400';

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium ${className}`}
      title={label}
    >
      <Icon className="h-3.5 w-3.5 shrink-0" aria-hidden />
      {label}
    </span>
  );
}
