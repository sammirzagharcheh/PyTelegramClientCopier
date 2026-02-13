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
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 border border-gray-200 dark:border-gray-700">
      <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">{title}</h3>
      {isLoading ? (
        <ChartSkeleton />
      ) : isEmpty ? (
        <div className="h-48 flex flex-col items-center justify-center gap-2 text-gray-500 dark:text-gray-400">
          <BarChart3 className="h-12 w-12 opacity-50" />
          <span className="text-sm">No data yet</span>
        </div>
      ) : (
        children
      )}
    </div>
  );
}
