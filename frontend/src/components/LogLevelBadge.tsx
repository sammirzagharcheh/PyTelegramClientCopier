import { AlertCircle, AlertTriangle, Info } from 'lucide-react';

type Level = 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR';

const levelStyles: Record<Level, string> = {
  ERROR: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  WARNING: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400',
  INFO: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  DEBUG: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-400',
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
  const style = levelStyles[normalized] ?? levelStyles.DEBUG;
  const Icon = levelIcons[normalized] ?? Info;

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium ${style}`}>
      {showIcon && <Icon className="h-3 w-3 shrink-0" />}
      {level || '—'}
    </span>
  );
}
