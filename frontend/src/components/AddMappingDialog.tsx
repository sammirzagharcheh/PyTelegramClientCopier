import { GitBranch } from 'lucide-react';
import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';
import { MappingRouteFields } from './MappingRouteFields';
import { useToast } from './Toast';
import {
  hasRouteErrors,
  parseChatId,
  validateMappingRoute,
  type MappingRouteFieldErrors,
  type MappingRouteValues,
} from '../lib/mappingValidation';

type Props = {
  onClose: () => void;
};

const initialRoute: MappingRouteValues = {
  telegramAccountId: null,
  sourceChatId: '',
  destChatId: '',
  sourceChatTitle: '',
  destChatTitle: '',
  useManualIds: false,
};

export function AddMappingDialog({ onClose }: Props) {
  const [name, setName] = useState('');
  const [route, setRoute] = useState<MappingRouteValues>(initialRoute);
  const [fieldErrors, setFieldErrors] = useState<MappingRouteFieldErrors>({});
  const [error, setError] = useState('');
  const queryClient = useQueryClient();
  const { show: showToast } = useToast();

  const mutation = useMutation({
    mutationFn: async () => {
      const src = parseChatId(route.sourceChatId)!;
      const dst = parseChatId(route.destChatId)!;
      return (
        await api.post('/mappings', {
          name: name.trim() || undefined,
          source_chat_id: src,
          dest_chat_id: dst,
          telegram_account_id: route.telegramAccountId,
          source_chat_title: route.sourceChatTitle || undefined,
          dest_chat_title: route.destChatTitle || undefined,
        })
      ).data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mappings'] });
      showToast('Mapping created. Workers restarting to apply changes.');
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
          : 'Failed to create mapping'
      );
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    const errors = validateMappingRoute(route);
    setFieldErrors(errors);
    if (hasRouteErrors(errors)) return;
    mutation.mutate();
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <div
        className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 max-w-lg w-full max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-2 mb-4">
          <GitBranch className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
          <h2 className="text-xl font-bold">Add Channel Mapping</h2>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="p-3 rounded bg-red-50 dark:bg-red-900/20 text-red-600 text-sm">{error}</div>
          )}
          <MappingRouteFields
            values={route}
            onChange={setRoute}
            errors={fieldErrors}
            name={name}
            onNameChange={setName}
          />
          <div className="flex gap-2 justify-end">
            <button type="button" onClick={onClose} className="px-4 py-2 rounded border border-gray-300">
              Cancel
            </button>
            <button
              type="submit"
              disabled={mutation.isPending || route.telegramAccountId == null}
              className="px-4 py-2 rounded bg-blue-600 text-white disabled:opacity-50"
            >
              Create
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
