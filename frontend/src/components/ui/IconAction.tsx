import { Link } from 'react-router-dom';
import type { LucideIcon } from 'lucide-react';

const base =
  'inline-flex h-8 w-8 items-center justify-center rounded-control text-ink-subtle ' +
  'transition-colors duration-150 active:translate-y-px hover:bg-surface-hover';

const tones = {
  default: 'hover:text-accent-ink',
  danger: 'hover:text-red-600 dark:hover:text-red-400',
};

type SharedProps = {
  icon: LucideIcon;
  /** Used as the accessible name and as the tooltip. */
  label: string;
  tone?: keyof typeof tones;
};

export function IconAction({
  icon: Icon,
  label,
  tone = 'default',
  onClick,
  disabled,
}: SharedProps & { onClick: () => void; disabled?: boolean }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={label}
      aria-label={label}
      className={`${base} ${tones[tone]} disabled:pointer-events-none disabled:opacity-40`}
    >
      <Icon className="h-4 w-4" strokeWidth={2} aria-hidden />
    </button>
  );
}

export function IconActionLink({ icon: Icon, label, tone = 'default', to }: SharedProps & { to: string }) {
  return (
    <Link to={to} title={label} aria-label={label} className={`${base} ${tones[tone]}`}>
      <Icon className="h-4 w-4" strokeWidth={2} aria-hidden />
    </Link>
  );
}

export function ActionDivider() {
  return <span className="mx-0.5 h-4 w-px bg-line" aria-hidden />;
}
