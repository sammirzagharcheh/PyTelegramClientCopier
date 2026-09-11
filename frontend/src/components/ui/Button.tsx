import { Loader2 } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';
export type ButtonSize = 'sm' | 'md';

const base =
  'inline-flex items-center justify-center gap-2 rounded-control font-medium ' +
  'transition-[background-color,border-color,color,transform] duration-150 ' +
  'active:translate-y-px disabled:pointer-events-none disabled:opacity-50';

const variants: Record<ButtonVariant, string> = {
  primary: 'bg-accent text-accent-fg hover:bg-accent-hover',
  secondary:
    'border border-line-strong bg-surface-raised text-ink hover:bg-surface-hover',
  ghost: 'text-ink-muted hover:bg-surface-hover hover:text-ink',
  danger: 'bg-red-600 text-white hover:bg-red-700',
};

const sizes: Record<ButtonSize, string> = {
  sm: 'h-8 px-3 text-sm',
  md: 'h-9.5 px-4 text-sm',
};

const iconOnlySizes: Record<ButtonSize, string> = {
  sm: 'h-8 w-8 p-0',
  md: 'h-9.5 w-9.5 p-0',
};

type Props = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
  icon?: LucideIcon;
  /** Renders a square button. Pass `aria-label` when using this. */
  iconOnly?: boolean;
  isLoading?: boolean;
};

export function Button({
  variant = 'primary',
  size = 'md',
  icon: Icon,
  iconOnly = false,
  isLoading = false,
  disabled,
  className = '',
  children,
  type = 'button',
  ...rest
}: Props) {
  const iconSize = size === 'sm' ? 'h-3.5 w-3.5' : 'h-4 w-4';
  return (
    <button
      type={type}
      disabled={disabled || isLoading}
      aria-busy={isLoading || undefined}
      className={`${base} ${variants[variant]} ${
        iconOnly ? iconOnlySizes[size] : sizes[size]
      } ${className}`.trim()}
      {...rest}
    >
      {isLoading ? (
        <Loader2 className={`${iconSize} shrink-0 animate-spin`} aria-hidden />
      ) : (
        Icon && <Icon className={`${iconSize} shrink-0`} strokeWidth={2} aria-hidden />
      )}
      {children}
    </button>
  );
}
