import { useState } from 'react';
import { AlertTriangle, CheckCircle2, KeyRound } from 'lucide-react';
import { useMutation } from '@tanstack/react-query';
import { api } from '../lib/api';
import { Button } from './ui/Button';
import { Field, Input } from './ui/Field';
import { Modal } from './ui/Modal';
import { errorMessage } from '../lib/apiError';

type Props = {
  onClose: () => void;
};

export function ChangePasswordDialog({ onClose }: Props) {
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [mismatch, setMismatch] = useState(false);
  const [success, setSuccess] = useState(false);

  const mutation = useMutation({
    mutationFn: async () => {
      if (newPassword !== confirmPassword) {
        throw new Error('New password and confirmation do not match');
      }
      return (
        await api.post('/auth/change-password', {
          current_password: currentPassword,
          new_password: newPassword,
        })
      ).data;
    },
    onSuccess: () => {
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setError('');
      setMismatch(false);
      setSuccess(true);
      setTimeout(() => {
        setSuccess(false);
        onClose();
      }, 1500);
    },
    onError: (err: unknown) => {
      setSuccess(false);
      setError(errorMessage(err, 'We could not change your password.'));
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setMismatch(false);
    if (newPassword !== confirmPassword) {
      setMismatch(true);
      setError('New password and confirmation do not match');
      return;
    }
    if (newPassword.length < 1) {
      setError('New password is required');
      return;
    }
    mutation.mutate();
  };

  return (
    <Modal
      title="Change password"
      icon={<KeyRound className="h-5 w-5 text-ink-subtle" strokeWidth={2} aria-hidden />}
      size="sm"
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="submit"
            form="change-password-form"
            isLoading={mutation.isPending}
          >
            Change password
          </Button>
        </>
      }
    >
      <form id="change-password-form" onSubmit={handleSubmit} className="space-y-4" noValidate>
        {error && (
          <div
            role="alert"
            className="flex items-start gap-2 rounded-control border border-red-300 bg-red-50 px-3 py-2.5 text-sm text-red-900 dark:border-red-800 dark:bg-red-950/50 dark:text-red-200"
          >
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
            <span>{error}</span>
          </div>
        )}
        {success && (
          <div
            role="status"
            className="flex items-start gap-2 rounded-control border border-emerald-300 bg-emerald-50 px-3 py-2.5 text-sm text-emerald-900 dark:border-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-200"
          >
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
            <span>Password changed.</span>
          </div>
        )}
        <Field label="Current password" required>
          {(fieldProps) => (
            <Input
              {...fieldProps}
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
          )}
        </Field>
        <Field label="New password" required>
          {(fieldProps) => (
            <Input
              {...fieldProps}
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
              minLength={1}
              autoComplete="new-password"
              invalid={mismatch}
            />
          )}
        </Field>
        <Field
          label="Confirm new password"
          required
          error={mismatch ? 'This does not match the new password.' : undefined}
        >
          {(fieldProps) => (
            <Input
              {...fieldProps}
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              minLength={1}
              autoComplete="new-password"
              invalid={mismatch}
            />
          )}
        </Field>
      </form>
    </Modal>
  );
}
