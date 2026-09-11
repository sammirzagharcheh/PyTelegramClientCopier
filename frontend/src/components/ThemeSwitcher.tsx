import { Monitor, Moon, Sun } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { useTheme } from '../theme/ThemeProvider';
import type { ThemePreference } from '../theme/constants';

const options: { value: ThemePreference; label: string; Icon: LucideIcon }[] = [
  { value: 'light', label: 'Light theme', Icon: Sun },
  { value: 'system', label: 'Use system theme', Icon: Monitor },
  { value: 'dark', label: 'Dark theme', Icon: Moon },
];

export function ThemeSwitcher() {
  const { preference, setPreference } = useTheme();

  return (
    <div
      className="inline-flex gap-0.5 rounded-control border border-line bg-surface-sunken p-0.5"
      role="radiogroup"
      aria-label="Colour theme"
    >
      {options.map(({ value, label, Icon }) => {
        const active = preference === value;
        return (
          <button
            key={value}
            type="button"
            role="radio"
            aria-checked={active}
            title={label}
            aria-label={label}
            onClick={() => setPreference(value)}
            className={`flex h-8 w-8 items-center justify-center rounded-[0.3rem] transition-colors ${
              active
                ? 'bg-surface-raised text-ink shadow-surface'
                : 'text-ink-subtle hover:text-ink'
            }`}
          >
            <Icon className="h-4 w-4" strokeWidth={2} aria-hidden />
          </button>
        );
      })}
    </div>
  );
}
