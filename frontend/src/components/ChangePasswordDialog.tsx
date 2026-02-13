import { useState } from 'react';
import { KeyRound } from 'lucide-react';
import { useMutation } from '@tanstack/react-query';
import { api } from '../lib/api';

type Props = {
  onClose: () => void;
};

const inputClass =
  'w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700';

export function ChangePasswordDialog({ onClose }: Props) {
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
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
      setSuccess(true);
      setTimeout(() => {
        setSuccess(false);
        onClose();
      }, 1500);
    },
    onError: (err: unknown) => {
      setSuccess(false);
      if (err instanceof Error) {
        setError(err.message);
      } else if (
        err &&
        typeof err === 'object' &&
        'response' in err &&
        err.response &&
        typeof err.response === 'object' &&
        'data' in err.response &&
        err.response.data &&
        typeof err.response.data === 'object' &&
        'detail' in err.response.data
      ) {
        setError(String((err.response.data as { detail: unknown }).detail));
      } else {
        setError('Failed to change password');
      }
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (newPassword !== confirmPassword) {
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
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <div
        className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 max-w-md w-full"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-2 mb-4">
          <KeyRound className="h-5 w-5 text-blue-600 dark:text-blue-400" strokeWidth={2} />
          <h2 className="text-xl font-bold">Change password</h2>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="p-3 rounded bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm">
              {error}
            </div>
          )}
          {success && (
            <div className="p-3 rounded bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400 text-sm">
              Password changed successfully.
            </div>
          )}
          <div>
            <label htmlFor="change-pwd-current" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Current password
            </label>
            <input
              id="change-pwd-current"
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              className={inputClass}
              required
              autoComplete="current-password"
              aria-label="Current password"
            />
          </div>
          <div>
            <label htmlFor="change-pwd-new" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              New password
            </label>
            <input
              id="change-pwd-new"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className={inputClass}
              required
              minLength={1}
              autoComplete="new-password"
              aria-label="New password"
            />
          </div>
          <div>
            <label htmlFor="change-pwd-confirm" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Confirm new password
            </label>
            <input
              id="change-pwd-confirm"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className={inputClass}
              required
              minLength={1}
              autoComplete="new-password"
              aria-label="Confirm new password"
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
              {mutation.isPending ? 'Changing…' : 'Change password'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
