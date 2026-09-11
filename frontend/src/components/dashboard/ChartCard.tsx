import { BarChart3 } from 'lucide-react';
import { ChartSkeleton } from '../Skeleton';

type Props = {
  title: string;
  isLoading?: boolean;
  isEmpty?: boolean;
  children: React.ReactNode;
};

export function ChartCard({ title, isLoading, isEmpty, children }: Props) {
  return (
    <section className="rounded-surface border border-line bg-surface-raised p-5 shadow-surface">
      <h3 className="mb-4 text-sm font-semibold text-ink">{title}</h3>
      {isLoading ? (
        <ChartSkeleton />
      ) : isEmpty ? (
        <div className="flex h-48 flex-col items-center justify-center gap-2 text-ink-subtle">
          <BarChart3 className="h-8 w-8" strokeWidth={1.75} aria-hidden />
          <p className="text-sm">Nothing recorded for this period yet.</p>
        </div>
      ) : (
        children
      )}
    </section>
  );
}
