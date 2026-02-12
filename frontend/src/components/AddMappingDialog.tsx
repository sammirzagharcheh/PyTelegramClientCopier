import { GitBranch } from 'lucide-react';
import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';

type Props = {
  onClose: () => void;
};

export function AddMappingDialog({ onClose }: Props) {
  const [name, setName] = useState('');
  const [sourceChatId, setSourceChatId] = useState('');
  const [destChatId, setDestChatId] = useState('');
  const [error, setError] = useState('');
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: async () => {
      return (await api.post('/mappings', {
        name: name || undefined,
        source_chat_id: parseInt(sourceChatId, 10),
        dest_chat_id: parseInt(destChatId, 10),
      })).data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mappings'] });
      onClose();
    },
    onError: (err: unknown) => {
      setError(
        err && typeof err === 'object' && 'response' in err && err.response && typeof err.response === 'object' && 'data' in err.response && err.response.data && typeof err.response.data === 'object' && 'detail' in err.response.data
          ? String((err.response.data as { detail: unknown }).detail)
          : 'Failed to create mapping'
      );
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    const src = parseInt(sourceChatId, 10);
    const dst = parseInt(destChatId, 10);
    if (isNaN(src) || isNaN(dst)) {
      setError('Invalid chat IDs');
      return;
    }
    mutation.mutate();
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 max-w-md w-full" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-2 mb-4">
          <GitBranch className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
          <h2 className="text-xl font-bold">Add Channel Mapping</h2>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="p-3 rounded bg-red-50 dark:bg-red-900/20 text-red-600 text-sm">{error}</div>
          )}
          <div>
            <label className="block text-sm font-medium mb-1">Name (optional)</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700"
              placeholder="Source to Dest"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Source Chat ID</label>
            <input
              type="text"
              value={sourceChatId}
              onChange={(e) => setSourceChatId(e.target.value)}
              className="w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700"
              placeholder="-1001234567890"
              required
            />
            <p className="text-xs text-gray-500 mt-1">Use @userinfobot to get chat IDs</p>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Destination Chat ID</label>
            <input
              type="text"
              value={destChatId}
              onChange={(e) => setDestChatId(e.target.value)}
              className="w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700"
              placeholder="-1009876543210"
              required
            />
          </div>
          <div className="flex gap-2 justify-end">
            <button type="button" onClick={onClose} className="px-4 py-2 rounded border border-gray-300">
              Cancel
            </button>
            <button type="submit" disabled={mutation.isPending} className="px-4 py-2 rounded bg-blue-600 text-white disabled:opacity-50">
              Create
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
