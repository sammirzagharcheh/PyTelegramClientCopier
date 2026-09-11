type Props = {
  className?: string;
  style?: React.CSSProperties;
};

export function Skeleton({ className = '', style }: Props) {
  return (
    <div
      className={`animate-pulse rounded bg-surface-sunken ${className}`}
      style={style}
      aria-hidden
    />
  );
}

export function StatCardSkeleton() {
  return (
    <div className="rounded-surface border border-line bg-surface-raised p-5 shadow-surface">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <Skeleton className="h-3.5 w-24" />
          <Skeleton className="mt-3 h-8 w-16" />
        </div>
        <Skeleton className="h-9 w-9 shrink-0 rounded-control" />
      </div>
    </div>
  );
}

export function ChartSkeleton() {
  return (
    <div className="flex h-48 items-end gap-1.5" aria-hidden>
      {[40, 65, 45, 80, 55, 70, 50, 60, 45].map((h, i) => (
        <Skeleton key={i} className="min-h-2 flex-1" style={{ height: `${h}%` }} />
      ))}
    </div>
  );
}

/**
 * Placeholder shaped like the table it replaces, so the layout does not jump
 * when data arrives.
 */
export function TableSkeleton({ columns, rows = 5 }: { columns: number; rows?: number }) {
  return (
    <div
      className="overflow-hidden rounded-surface border border-line bg-surface-raised"
      role="status"
      aria-label="Loading"
    >
      <div className="flex gap-4 border-b border-line bg-surface-sunken px-4 py-3">
        {Array.from({ length: columns }).map((_, i) => (
          <Skeleton key={i} className="h-3 flex-1" />
        ))}
      </div>
      <div className="divide-y divide-line">
        {Array.from({ length: rows }).map((_, rowIndex) => (
          <div key={rowIndex} className="flex gap-4 px-4 py-3.5">
            {Array.from({ length: columns }).map((_, colIndex) => (
              <Skeleton key={colIndex} className="h-4 flex-1" />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

/** Generic block placeholder for card-shaped content. */
export function CardSkeleton({ lines = 3, className = '' }: { lines?: number; className?: string }) {
  return (
    <div
      className={`rounded-surface border border-line bg-surface-raised p-5 shadow-surface ${className}`.trim()}
      role="status"
      aria-label="Loading"
    >
      <Skeleton className="h-4 w-40" />
      <div className="mt-4 space-y-2.5">
        {Array.from({ length: lines }).map((_, i) => (
          <Skeleton key={i} className="h-3.5" style={{ width: `${100 - i * 12}%` }} />
        ))}
      </div>
    </div>
  );
}
