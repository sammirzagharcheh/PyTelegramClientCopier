import { AlertCircle, AlertTriangle, Info } from 'lucide-react';
import { Badge } from './ui/Badge';
import type { BadgeTone } from './ui/Badge';

type Level = 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR';

const levelTones: Record<Level, BadgeTone> = {
  ERROR: 'danger',
  WARNING: 'warning',
  INFO: 'info',
  DEBUG: 'neutral',
};

const levelIcons: Record<Level, typeof AlertCircle> = {
  ERROR: AlertCircle,
  WARNING: AlertTriangle,
  INFO: Info,
  DEBUG: Info,
};

type Props = {
  level: string;
  showIcon?: boolean;
};

export function LogLevelBadge({ level, showIcon = true }: Props) {
  const normalized = (level?.toUpperCase() || '') as Level;
  const tone = levelTones[normalized] ?? levelTones.DEBUG;
  const icon = levelIcons[normalized] ?? Info;

  return (
    <Badge tone={tone} icon={showIcon ? icon : undefined}>
      {level || 'Unknown'}
    </Badge>
  );
}
