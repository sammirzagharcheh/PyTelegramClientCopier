import type { LucideIcon } from 'lucide-react';

type CardProps = {
  children: React.ReactNode;
  className?: string;
  /** Drop the default padding when the card holds a table or a divided list. */
  flush?: boolean;
};

export function Card({ children, className = '', flush = false }: CardProps) {
  return (
    <section
      className={`rounded-surface border border-line bg-surface-raised shadow-surface ${
        flush ? '' : 'p-5'
      } ${className}`.trim()}
    >
      {children}
    </section>
  );
}

type CardHeaderProps = {
  title: string;
  icon?: LucideIcon;
  description?: string;
  actions?: React.ReactNode;
  /** Set when the card is `flush`, to keep the header inset from the edges. */
  inset?: boolean;
};

export function CardHeader({ title, icon: Icon, description, actions, inset = false }: CardHeaderProps) {
  return (
    <div
      className={`flex flex-wrap items-start justify-between gap-3 ${
        inset ? 'border-b border-line px-5 py-4' : 'mb-4'
      }`}
    >
      <div className="min-w-0">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-ink">
          {Icon && <Icon className="h-4 w-4 shrink-0 text-ink-subtle" strokeWidth={2} aria-hidden />}
          {title}
        </h2>
        {description && <p className="mt-1 text-sm text-ink-subtle">{description}</p>}
      </div>
      {actions && <div className="shrink-0">{actions}</div>}
    </div>
  );
}
