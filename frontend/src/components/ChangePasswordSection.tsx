import { useState } from 'react';
import { ChevronDown, ChevronUp, KeyRound } from 'lucide-react';
import { useMutation } from '@tanstack/react-query';
import { api } from '../lib/api';

type Props = {
  defaultExpanded?: boolean;
};

export function ChangePasswordSection({ defaultExpanded = false }: Props) {
  const [expanded, setExpanded] = useState(defaultExpanded);
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
      return (await api.post('/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword,
      })).data;
    },
    onSuccess: () => {
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setError('');
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
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
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 border-l-4 border-l-gray-300 dark:border-l-gray-600 transition-shadow hover:shadow-lg">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="flex justify-between items-center w-full text-left gap-2"
      >
        <div className="flex items-center gap-2">
          <KeyRound className="h-5 w-5 text-gray-500 dark:text-gray-400" strokeWidth={2} />
          <h2 className="text-lg font-semibold">Change password</h2>
        </div>
        {expanded ? (
          <ChevronUp className="h-5 w-5 text-gray-500 dark:text-gray-400" />
        ) : (
          <ChevronDown className="h-5 w-5 text-gray-500 dark:text-gray-400" />
        )}
      </button>
      {expanded && (
        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          {error && (
            <div className="p-3 rounded bg-red-50 dark:bg-red-900/20 text-red-600 text-sm">{error}</div>
          )}
          {success && (
            <div className="p-3 rounded bg-green-50 dark:bg-green-900/20 text-green-600 text-sm">
              Password changed successfully.
            </div>
          )}
          <div>
            <label className="block text-sm font-medium mb-1">Current password</label>
            <input
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              className="w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700"
              required
              autoComplete="current-password"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">New password</label>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700"
              required
              minLength={1}
              autoComplete="new-password"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Confirm new password</label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700"
              required
              minLength={1}
              autoComplete="new-password"
            />
          </div>
          <button
            type="submit"
            disabled={mutation.isPending}
            className="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
          >
            Change password
          </button>
        </form>
      )}
    </div>
  );
}
