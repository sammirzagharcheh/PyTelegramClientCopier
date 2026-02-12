import type { LucideIcon } from 'lucide-react';

type Props = {
  title: string;
  icon: LucideIcon;
  subtitle?: string;
  actions?: React.ReactNode;
};

export function PageHeader({ title, icon: Icon, subtitle, actions }: Props) {
  return (
    <div className="mb-8 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <div className="flex items-center gap-3">
          <div className="rounded-lg bg-blue-100 dark:bg-blue-900/40 p-2.5 text-blue-600 dark:text-blue-400">
            <Icon className="h-6 w-6" strokeWidth={2} />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">{title}</h1>
        </div>
        {subtitle && (
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">{subtitle}</p>
        )}
      </div>
      {actions && <div className="shrink-0">{actions}</div>}
    </div>
  );
}
