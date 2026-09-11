import { ChevronDown, ChevronUp, ChevronsUpDown } from 'lucide-react';

type Props = {
  label: string;
  sortKey: string;
  currentSort: string;
  currentOrder: 'asc' | 'desc';
  onSort: (key: string, order: 'asc' | 'desc') => void;
  className?: string;
};

export function SortableTh({
  label,
  sortKey,
  currentSort,
  currentOrder,
  onSort,
  className = '',
}: Props) {
  const isActive = currentSort === sortKey;
  const handleClick = () => {
    onSort(sortKey, isActive && currentOrder === 'asc' ? 'desc' : 'asc');
  };

  const SortIcon = isActive ? (currentOrder === 'asc' ? ChevronUp : ChevronDown) : ChevronsUpDown;

  return (
    <th
      scope="col"
      aria-sort={isActive ? (currentOrder === 'asc' ? 'ascending' : 'descending') : 'none'}
      className={`p-0 text-xs font-semibold tracking-wide text-ink-subtle uppercase ${className}`.trim()}
    >
      {/* A real button, so the column is reachable and operable by keyboard. */}
      <button
        type="button"
        onClick={handleClick}
        className="flex w-full items-center gap-1.5 px-4 py-2.5 text-left uppercase transition-colors hover:bg-surface-hover hover:text-ink"
      >
        {label}
        <SortIcon
          className={`h-3.5 w-3.5 shrink-0 ${isActive ? 'text-accent-ink' : 'opacity-50'}`}
          aria-hidden
        />
      </button>
    </th>
  );
}
