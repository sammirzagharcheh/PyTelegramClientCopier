import { useMemo, useState } from 'react';
import { Globe } from 'lucide-react';
import { useMutation } from '@tanstack/react-query';
import { api } from '../lib/api';
import { errorMessage } from '../lib/apiError';
import { DEVICE_TZ_VALUE } from '../lib/timezones';
import { useAuth } from '../store/AuthContext';
import { useToast } from './Toast';
import { SearchableTimezoneSelect } from './SearchableTimezoneSelect';
import { Button } from './ui/Button';
import { Field } from './ui/Field';
import { FormError } from './ui/FormError';
import { Modal } from './ui/Modal';

type Props = {
  onClose: () => void;
};

export function TimezonePreferencesDialog({ onClose }: Props) {
  const { user, refreshUser } = useAuth();
  const { show: showToast } = useToast();
  const savedTimezone = user?.timezone ?? DEVICE_TZ_VALUE;
  // Reset the draft whenever the saved preference changes, without an effect.
  const [draft, setDraft] = useState<{ base: string; value: string } | null>(null);
  const value = draft?.base === savedTimezone ? draft.value : savedTimezone;
  const [error, setError] = useState('');

  const timezones = useMemo(() => {
    try {
      return Intl.supportedValuesOf('timeZone').sort();
    } catch {
      return ['UTC', 'America/New_York', 'Europe/London', 'Asia/Tokyo'];
    }
  }, []);

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
      setError(errorMessage(err, 'We could not save your timezone.'));
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    mutation.mutate();
  };

  return (
    <Modal
      title="Timezone"
      description="Every time in the app is shown in this timezone. Schedules are still stored in UTC."
      icon={<Globe className="h-5 w-5 text-ink-subtle" strokeWidth={2} aria-hidden />}
      size="sm"
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" form="timezone-form" isLoading={mutation.isPending}>
            Save
          </Button>
        </>
      }
    >
      <form id="timezone-form" onSubmit={handleSubmit} className="space-y-4">
        <FormError message={error} />
        <Field label="Timezone">
          {(fieldProps) => (
            <SearchableTimezoneSelect
              id={fieldProps.id}
              aria-describedby={fieldProps['aria-describedby']}
              value={value}
              onChange={(next) => setDraft({ base: savedTimezone, value: next })}
              timezones={timezones}
              aria-label="Timezone"
            />
          )}
        </Field>
      </form>
    </Modal>
  );
}
