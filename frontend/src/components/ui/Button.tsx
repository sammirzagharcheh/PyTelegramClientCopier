import { Loader2 } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { LinkProps } from 'react-router-dom';

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

function classesFor(
  variant: ButtonVariant,
  size: ButtonSize,
  iconOnly: boolean,
  className: string
) {
  const sizing = iconOnly ? iconOnlySizes[size] : sizes[size];
  return `${base} ${variants[variant]} ${sizing} ${className}`.trim();
}

function iconSizeFor(size: ButtonSize) {
  return size === 'sm' ? 'h-3.5 w-3.5' : 'h-4 w-4';
}

type SharedProps = {
  variant?: ButtonVariant;
  size?: ButtonSize;
  icon?: LucideIcon;
  /** Extra classes for the icon, e.g. `animate-spin` while refreshing. */
  iconClassName?: string;
  /** Renders a square button. Pass `aria-label` when using this. */
  iconOnly?: boolean;
};

type Props = React.ButtonHTMLAttributes<HTMLButtonElement> &
  SharedProps & {
    isLoading?: boolean;
  };

export function Button({
  variant = 'primary',
  size = 'md',
  icon: Icon,
  iconClassName = '',
  iconOnly = false,
  isLoading = false,
  disabled,
  className = '',
  children,
  type = 'button',
  ...rest
}: Props) {
  const iconSize = iconSizeFor(size);
  return (
    <button
      type={type}
      disabled={disabled || isLoading}
      aria-busy={isLoading || undefined}
      className={classesFor(variant, size, iconOnly, className)}
      {...rest}
    >
      {isLoading ? (
        <Loader2 className={`${iconSize} shrink-0 animate-spin`} aria-hidden />
      ) : (
        Icon && (
          <Icon
            className={`${iconSize} shrink-0 ${iconClassName}`.trim()}
            strokeWidth={2}
            aria-hidden
          />
        )
      )}
      {children}
    </button>
  );
}

/** A router link that carries button affordances. Use for navigation, not actions. */
export function ButtonLink({
  variant = 'secondary',
  size = 'md',
  icon: Icon,
  iconClassName = '',
  iconOnly = false,
  className = '',
  children,
  ...rest
}: LinkProps & SharedProps) {
  const iconSize = iconSizeFor(size);
  return (
    <Link className={classesFor(variant, size, iconOnly, className)} {...rest}>
      {Icon && (
        <Icon
          className={`${iconSize} shrink-0 ${iconClassName}`.trim()}
          strokeWidth={2}
          aria-hidden
        />
      )}
      {children}
    </Link>
  );
}
