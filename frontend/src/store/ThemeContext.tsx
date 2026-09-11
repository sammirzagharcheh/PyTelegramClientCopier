import { useTheme as useThemeBase } from '../theme/ThemeProvider';

export { ThemeProvider } from '../theme/ThemeProvider';
export type { ThemePreference } from '../theme/constants';

type ThemeContextValue = {
  preference: 'light' | 'dark' | 'system';
  resolved: 'light' | 'dark';
  resolvedDark: boolean;
  setPreference: (preference: 'light' | 'dark' | 'system') => void;
};

// Adapts the production theme provider (tg-copier-theme) to the restyle hook shape.
// eslint-disable-next-line react-refresh/only-export-components
export function useTheme(): ThemeContextValue {
  const { preference, setPreference, resolvedDark } = useThemeBase();
  return {
    preference,
    setPreference,
    resolvedDark,
    resolved: resolvedDark ? 'dark' : 'light',
  };
}
