import { useEffect, useMemo, useRef, useState } from 'react';

export function getTimezoneUtcOffset(tz: string): string {
  try {
    const formatter = new Intl.DateTimeFormat('en', {
      timeZone: tz,
      timeZoneName: 'longOffset',
    });
    const str = formatter.format(new Date());
    const match = str.match(/GMT([+-]\d{1,2}:\d{2})/);
    return match ? `UTC${match[1]}` : '';
  } catch {
    return '';
  }
}

export const DEVICE_TZ_VALUE = '__device__';

type Option = { value: string; label: string };

type Props = {
  value: string;
  onChange: (value: string) => void;
  timezones: string[];
  id?: string;
  'aria-label'?: string;
  disabled?: boolean;
};

export function SearchableTimezoneSelect({
  value,
  onChange,
  timezones,
  id,
  'aria-label': ariaLabel = 'Timezone',
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
    return options.filter((opt) =>
      opt.label.toLowerCase().includes(q) || opt.value.toLowerCase().includes(q)
    );
  }, [options, query]);

  const selectedLabel = useMemo(() => {
    const opt = options.find((o) => o.value === value);
    return opt?.label ?? value;
  }, [options, value]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isOpen]);

  const inputClass =
    'w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-left';

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
          className={inputClass}
          placeholder="Search timezone..."
          autoComplete="off"
        />
      {isOpen && (
        <div
          id="tz-listbox"
          role="listbox"
          className="absolute z-50 mt-1 max-h-60 w-full overflow-auto rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 shadow-lg"
        >
          {filteredOptions.length === 0 ? (
            <div className="px-3 py-2 text-sm text-gray-500 dark:text-gray-400">No matches</div>
          ) : (
            filteredOptions.map((opt) => (
              <div
                key={opt.value}
                role="option"
                aria-selected={opt.value === value ? 'true' : 'false'}
                className={`cursor-pointer px-3 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700 ${
                  opt.value === value ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300' : ''
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
