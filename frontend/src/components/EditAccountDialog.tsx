import { Pencil, Smartphone } from 'lucide-react';
import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';
import { useToast } from './Toast';

export type Account = {
  id: number;
  user_id: number;
  name: string | null;
  type: string;
  status: string;
  created_at: string | null;
};

type Props = {
  account: Account;
  onClose: () => void;
};

export function EditAccountDialog({ account, onClose }: Props) {
  const [name, setName] = useState(account.name ?? '');
  const [status, setStatus] = useState(account.status || 'active');
  const [error, setError] = useState('');
  const queryClient = useQueryClient();
  const { show: showToast } = useToast();

  const mutation = useMutation({
    mutationFn: async () => {
      return (
        await api.patch(`/accounts/${account.id}`, {
          name: name || undefined,
          status: status || undefined,
        })
      ).data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
      showToast('Account updated');
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
          : 'Failed to update account'
      );
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    mutation.mutate();
  };

  const inputClass = 'w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700';

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <div
        className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 max-w-md w-full"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-2 mb-4">
          <Pencil className="h-5 w-5 text-blue-600 dark:text-blue-400" />
          <h2 className="text-xl font-bold">Edit Telegram Account</h2>
        </div>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-4 flex items-center gap-2">
          <Smartphone className="h-4 w-4" />
          Type: {account.type} (read-only)
        </p>
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="p-3 rounded bg-red-50 dark:bg-red-900/20 text-red-600 text-sm">{error}</div>
          )}
          <div>
            <label className="block text-sm font-medium mb-1">Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className={inputClass}
              placeholder="Account name"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Status</label>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className={inputClass}
            >
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
          </div>
          <div className="flex gap-2 justify-end">
            <button type="button" onClick={onClose} className="px-4 py-2 rounded border border-gray-300">
              Cancel
            </button>
            <button
              type="submit"
              disabled={mutation.isPending}
              className="px-4 py-2 rounded bg-blue-600 text-white disabled:opacity-50"
            >
              {mutation.isPending ? 'Saving…' : 'Save'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
