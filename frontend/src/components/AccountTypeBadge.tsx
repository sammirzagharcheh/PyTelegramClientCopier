import { Bot, User } from 'lucide-react';
import { Badge } from './ui/Badge';
import type { BadgeTone } from './ui/Badge';

type Props = {
  type: 'user' | 'bot' | string;
};

export function AccountTypeBadge({ type }: Props) {
  const t = String(type).toLowerCase();
  const isUser = t === 'user';
  const isBot = t === 'bot';
  const label = isUser ? 'User' : isBot ? 'Bot' : type || 'Unknown';
  const tone: BadgeTone = isUser ? 'info' : isBot ? 'accent' : 'neutral';

  return (
    <Badge tone={tone} icon={isBot ? Bot : User}>
      {label}
    </Badge>
  );
}
