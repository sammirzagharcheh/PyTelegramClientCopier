import { useEffect, useMemo, useState } from 'react';
import { Globe } from 'lucide-react';
import { useMutation } from '@tanstack/react-query';
import { api } from '../lib/api';
import { useAuth } from '../store/AuthContext';
import { useToast } from './Toast';
import { SearchableTimezoneSelect, DEVICE_TZ_VALUE } from './SearchableTimezoneSelect';

type Props = {
  onClose: () => void;
};

export function TimezonePreferencesDialog({ onClose }: Props) {
  const { user, refreshUser } = useAuth();
  const { show: showToast } = useToast();
  const [value, setValue] = useState(DEVICE_TZ_VALUE);
  const [error, setError] = useState('');

  const timezones = useMemo(() => {
    try {
      return Intl.supportedValuesOf('timeZone').sort();
    } catch {
      return ['UTC', 'America/New_York', 'Europe/London', 'Asia/Tokyo'];
    }
  }, []);

  useEffect(() => {
    setValue(user?.timezone ?? DEVICE_TZ_VALUE);
  }, [user?.timezone]);

  const mutation = useMutation({
    mutationFn: async () => {
      const payload =
        value === DEVICE_TZ_VALUE || value === '' ? { timezone: null } : { timezone: value };
      const { data } = await api.patch<{ timezone?: string | null }>('/auth/me', payload);
      return data;
    },
    onSuccess: async () => {
      await refreshUser();
      showToast('Timezone preference saved');
      onClose();
    },
    onError: (err: unknown) => {
      setError(
        err &&
          typeof err === 'object' &&
          'response' in err &&
          err.response &&
          typeof err.response === 'object' &&
          'data' in err.response &&
          err.response.data &&
          typeof err.response.data === 'object' &&
          'detail' in err.response.data
          ? String((err.response.data as { detail: unknown }).detail)
          : 'Failed to save timezone'
      );
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    mutation.mutate();
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <div
        className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 max-w-md w-full"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-2 mb-4">
          <Globe className="h-5 w-5 text-blue-600 dark:text-blue-400" strokeWidth={2} />
          <h2 className="text-xl font-bold">Timezone</h2>
        </div>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
          Times throughout the app will be displayed in your selected timezone.
        </p>
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="p-3 rounded bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm">
              {error}
            </div>
          )}
          <div>
            <label htmlFor="tz-select" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Timezone
            </label>
            <SearchableTimezoneSelect
              id="tz-select"
              value={value}
              onChange={setValue}
              timezones={timezones}
              aria-label="Timezone"
            />
          </div>
          <div className="flex gap-2 justify-end pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={mutation.isPending}
              className="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {mutation.isPending ? 'Saving…' : 'Save'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
