type Props = {
  title: string;
  message: React.ReactNode;
  confirmLabel: string;
  variant?: 'danger' | 'neutral';
  onConfirm: () => void;
  onCancel: () => void;
  isPending?: boolean;
  icon?: React.ReactNode;
};

export function ConfirmDialog({
  title,
  message,
  confirmLabel,
  variant = 'neutral',
  onConfirm,
  onCancel,
  isPending = false,
  icon,
}: Props) {
  const confirmButtonClass =
    variant === 'danger'
      ? 'px-4 py-2 rounded bg-red-600 text-white hover:bg-red-700 disabled:opacity-50'
      : 'px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50';

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onCancel}>
      <div
        className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 max-w-md w-full"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-2 mb-4">
          {icon}
          <h2 className="text-xl font-bold">{title}</h2>
        </div>
        <p className="text-sm text-gray-600 dark:text-gray-300 mb-4">{message}</p>
        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 rounded border border-gray-300 dark:border-gray-600 disabled:opacity-50"
            disabled={isPending}
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isPending}
            className={confirmButtonClass}
          >
            {isPending ? 'Processing…' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
