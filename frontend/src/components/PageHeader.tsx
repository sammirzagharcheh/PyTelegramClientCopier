import type { LucideIcon } from 'lucide-react';

type Props = {
  title: string;
  icon: LucideIcon;
  subtitle?: string;
  actions?: React.ReactNode;
};

export function PageHeader({ title, icon: Icon, subtitle, actions }: Props) {
  return (
    <header className="mb-6 flex flex-col gap-3 border-b border-line pb-5 sm:flex-row sm:items-start sm:justify-between">
      <div className="flex min-w-0 items-start gap-3">
        <span className="mt-0.5 shrink-0 rounded-control bg-accent-soft p-2 text-accent-ink">
          <Icon className="h-5 w-5" strokeWidth={2} aria-hidden />
        </span>
        <div className="min-w-0">
          <h1 className="text-xl font-semibold text-ink sm:text-2xl">{title}</h1>
          {subtitle && <p className="mt-1 max-w-prose text-sm text-ink-subtle">{subtitle}</p>}
        </div>
      </div>
      {actions && <div className="flex shrink-0 flex-wrap gap-2">{actions}</div>}
    </header>
  );
}
