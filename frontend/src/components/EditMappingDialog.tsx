import { Pencil } from 'lucide-react';
import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';
import { MappingFormFields } from './MappingFormFields';
import { useToast } from './Toast';

export type Mapping = {
  id: number;
  user_id: number;
  source_chat_id: number;
  dest_chat_id: number;
  name: string | null;
  source_chat_title?: string | null;
  dest_chat_title?: string | null;
  enabled: boolean;
};

type Props = {
  mapping: Mapping;
  onClose: () => void;
};

export function EditMappingDialog({ mapping, onClose }: Props) {
  const [name, setName] = useState(mapping.name ?? '');
  const [sourceChatId, setSourceChatId] = useState(String(mapping.source_chat_id));
  const [destChatId, setDestChatId] = useState(String(mapping.dest_chat_id));
  const [error, setError] = useState('');
  const queryClient = useQueryClient();
  const { show: showToast } = useToast();

  const mutation = useMutation({
    mutationFn: async () => {
      return (
        await api.patch(`/mappings/${mapping.id}`, {
          name: name || undefined,
          source_chat_id: parseInt(sourceChatId, 10),
          dest_chat_id: parseInt(destChatId, 10),
        })
      ).data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mappings'] });
      queryClient.invalidateQueries({ queryKey: ['mapping', String(mapping.id)] });
      showToast('Mapping updated. Workers restarting to apply changes.');
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
          : 'Failed to update mapping'
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
      <div
        className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 max-w-md w-full"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-2 mb-4">
          <Pencil className="h-5 w-5 text-blue-600 dark:text-blue-400" />
          <h2 className="text-xl font-bold">Edit Channel Mapping</h2>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="p-3 rounded bg-red-50 dark:bg-red-900/20 text-red-600 text-sm">{error}</div>
          )}
          <MappingFormFields
            name={name}
            sourceChatId={sourceChatId}
            destChatId={destChatId}
            onNameChange={setName}
            onSourceChatIdChange={setSourceChatId}
            onDestChatIdChange={setDestChatId}
          />
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
