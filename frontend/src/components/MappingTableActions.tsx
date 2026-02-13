import { Eye, Pencil, Trash2 } from 'lucide-react';
import { Link } from 'react-router-dom';

type Props = {
  mappingId: number;
  onEdit: () => void;
  onDelete: () => void;
};

const iconButtonBase =
  'p-2 rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 dark:focus:ring-offset-gray-800';

export function MappingTableActions({ mappingId, onEdit, onDelete }: Props) {
  return (
    <div className="flex items-center justify-end gap-1">
      <button
        type="button"
        onClick={onEdit}
        title="Edit"
        aria-label="Edit mapping"
        className={`${iconButtonBase} text-gray-500 hover:bg-gray-100 hover:text-blue-600 dark:hover:bg-gray-700 dark:hover:text-blue-400`}
      >
        <Pencil className="h-4 w-4" />
      </button>
      <button
        type="button"
        onClick={onDelete}
        title="Delete"
        aria-label="Delete mapping"
        className={`${iconButtonBase} text-gray-500 hover:bg-gray-100 hover:text-red-600 dark:hover:bg-gray-700 dark:hover:text-red-500`}
      >
        <Trash2 className="h-4 w-4" />
      </button>
      <span className="mx-0.5 h-4 w-px bg-gray-200 dark:bg-gray-600" aria-hidden />
      <Link
        to={`/mappings/${mappingId}`}
        title="View details"
        aria-label="View details"
        className={`${iconButtonBase} text-gray-500 hover:bg-gray-100 hover:text-blue-600 dark:hover:bg-gray-700 dark:hover:text-blue-400`}
      >
        <Eye className="h-4 w-4" />
      </Link>
    </div>
  );
}
