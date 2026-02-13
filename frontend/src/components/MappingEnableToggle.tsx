type Props = {
  enabled: boolean;
  onToggle: () => void;
  isPending?: boolean;
};

export function MappingEnableToggle({ enabled, onToggle, isPending = false }: Props) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={enabled}
      aria-label={enabled ? 'Disable mapping' : 'Enable mapping'}
      disabled={isPending}
      onClick={onToggle}
      className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800 disabled:opacity-50 disabled:cursor-not-allowed ${
        enabled
          ? 'bg-emerald-500 dark:bg-emerald-600'
          : 'bg-gray-200 dark:bg-gray-600'
      }`}
    >
      <span
        className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition-transform ${
          enabled ? 'translate-x-5' : 'translate-x-0.5'
        }`}
      />
    </button>
  );
}
