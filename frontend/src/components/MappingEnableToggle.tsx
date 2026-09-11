type Props = {
  enabled: boolean;
  onToggle: () => void;
  isPending?: boolean;
  disabled?: boolean;
};

export function MappingEnableToggle({ enabled, onToggle, isPending = false, disabled = false }: Props) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={enabled}
      aria-label={enabled ? 'Disable mapping' : 'Enable mapping'}
      disabled={isPending || disabled}
      onClick={onToggle}
      className={`relative inline-flex h-5.5 w-10 shrink-0 rounded-full border-2 border-transparent transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
        enabled ? 'bg-emerald-600' : 'bg-line-strong'
      }`}
    >
      <span
        className={`pointer-events-none inline-block h-4.5 w-4.5 transform rounded-full bg-white shadow-surface transition-transform ${
          enabled ? 'translate-x-4.5' : 'translate-x-0'
        }`}
      />
    </button>
  );
}
