import { ChevronDown, ChevronUp, ChevronsUpDown } from 'lucide-react';

type Props = {
  label: string;
  sortKey: string;
  currentSort: string;
  currentOrder: 'asc' | 'desc';
  onSort: (key: string, order: 'asc' | 'desc') => void;
};

export function SortableTh({ label, sortKey, currentSort, currentOrder, onSort }: Props) {
  const isActive = currentSort === sortKey;
  const handleClick = () => {
    if (isActive) {
      onSort(sortKey, currentOrder === 'asc' ? 'desc' : 'asc');
    } else {
      onSort(sortKey, 'asc');
    }
  };

  return (
    <th
      role="columnheader"
      className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase cursor-pointer select-none hover:bg-gray-100 dark:hover:bg-gray-600"
      onClick={handleClick}
    >
      <div className="flex items-center gap-1">
        {label}
        {isActive ? (
          currentOrder === 'asc' ? (
            <ChevronUp className="h-4 w-4" />
          ) : (
            <ChevronDown className="h-4 w-4" />
          )
        ) : (
          <ChevronsUpDown className="h-4 w-4 opacity-50" />
        )}
      </div>
    </th>
  );
}
