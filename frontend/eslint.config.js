import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    rules: {
      // Context/provider modules and shared helpers commonly co-export with components.
      'react-refresh/only-export-components': 'off',
      // Allow controlled form reset patterns used across dialogs.
      'react-hooks/set-state-in-effect': 'off',
      // Gradual typing cleanup; do not block CI on legacy `any` usage.
      '@typescript-eslint/no-explicit-any': 'warn',
      // React Hook Form watch() is flagged by React Compiler lint; keep as warning.
      'react-hooks/incompatible-library': 'warn',
    },
  },
])
