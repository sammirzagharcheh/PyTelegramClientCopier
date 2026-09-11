import { useEffect, useMemo, useRef, useState } from 'react';
import { DEVICE_TZ_VALUE, getTimezoneUtcOffset } from '../lib/timezones';

type Option = { value: string; label: string };

type Props = {
  value: string;
  onChange: (value: string) => void;
  timezones: string[];
  id?: string;
  'aria-label'?: string;
  'aria-describedby'?: string;
  disabled?: boolean;
};

export function SearchableTimezoneSelect({
  value,
  onChange,
  timezones,
  id,
  'aria-label': ariaLabel = 'Timezone',
  'aria-describedby': ariaDescribedBy,
  disabled = false,
}: Props) {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const containerRef = useRef<HTMLDivElement>(null);

  const options: Option[] = useMemo(() => {
    const deviceOption: Option = {
      value: DEVICE_TZ_VALUE,
      label: 'Use my device timezone',
    };
    const tzOptions: Option[] = timezones.map((tz) => ({
      value: tz,
      label: `${tz} (${getTimezoneUtcOffset(tz)})`,
    }));
    return [deviceOption, ...tzOptions];
  }, [timezones]);

  const filteredOptions = useMemo(() => {
    if (!query.trim()) return options;
    const q = query.toLowerCase();
    return options.filter(
      (opt) => opt.label.toLowerCase().includes(q) || opt.value.toLowerCase().includes(q)
    );
  }, [options, query]);

  const selectedLabel = useMemo(() => {
    const opt = options.find((o) => o.value === value);
    return opt?.label ?? value;
  }, [options, value]);

  useEffect(() => {
    if (!isOpen) return;
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  return (
    <div ref={containerRef} className="relative">
      <input
        id={id}
        type="text"
        role="combobox"
        aria-expanded={isOpen ? 'true' : 'false'}
        aria-haspopup="listbox"
        aria-controls="tz-listbox"
        aria-label={ariaLabel}
        aria-describedby={ariaDescribedBy}
        value={isOpen ? query : selectedLabel}
        onChange={(e) => {
          setQuery(e.target.value);
          if (!isOpen) setIsOpen(true);
        }}
        onFocus={() => {
          setIsOpen(true);
          setQuery('');
        }}
        onKeyDown={(e) => {
          if (e.key === 'Escape') {
            setIsOpen(false);
            setQuery('');
          }
        }}
        disabled={disabled}
        className="h-9.5 w-full rounded-control border border-line-strong bg-surface-raised px-3 text-left text-sm text-ink transition-colors placeholder:text-ink-subtle hover:border-ink-subtle disabled:cursor-not-allowed disabled:opacity-60"
        placeholder="Search timezone"
        autoComplete="off"
      />
      {isOpen && (
        <div
          id="tz-listbox"
          role="listbox"
          className="absolute z-dropdown mt-1 max-h-60 w-full overflow-auto rounded-control border border-line bg-surface-raised py-1 shadow-raised"
        >
          {filteredOptions.length === 0 ? (
            <p className="px-3 py-2 text-sm text-ink-subtle">No timezone matches that search.</p>
          ) : (
            filteredOptions.map((opt) => (
              <div
                key={opt.value}
                role="option"
                aria-selected={opt.value === value ? 'true' : 'false'}
                className={`cursor-pointer px-3 py-1.5 text-sm transition-colors ${
                  opt.value === value
                    ? 'bg-accent-soft font-medium text-accent-ink'
                    : 'text-ink-muted hover:bg-surface-hover hover:text-ink'
                }`}
                onClick={() => {
                  onChange(opt.value);
                  setIsOpen(false);
                  setQuery('');
                }}
              >
                {opt.label}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
