type Props = {
  className?: string;
  style?: React.CSSProperties;
};

export function Skeleton({ className = '', style }: Props) {
  return (
    <div
      className={`animate-pulse rounded bg-gray-200 dark:bg-gray-600 ${className}`}
      style={style}
      aria-hidden
    />
  );
}

export function StatCardSkeleton() {
  return (
    <div className="bg-gray-50 dark:bg-gray-800/50 border-l-4 border-gray-300 dark:border-gray-600 rounded-lg shadow p-6">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-9 w-16 mt-3" />
        </div>
        <Skeleton className="h-12 w-12 rounded-lg shrink-0" />
      </div>
    </div>
  );
}

export function ChartSkeleton() {
  return (
    <div className="h-48 flex items-end gap-1">
      {[40, 65, 45, 80, 55, 70, 50, 60, 45].map((h, i) => (
        <Skeleton key={i} className="flex-1 min-h-2" style={{ height: `${h}%` }} />
      ))}
    </div>
  );
}
