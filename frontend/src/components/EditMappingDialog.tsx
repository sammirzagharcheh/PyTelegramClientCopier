import { Pencil } from 'lucide-react';
import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';
import { errorMessage } from '../lib/apiError';
import { MappingFormFields } from './MappingFormFields';
import { useToast } from './Toast';
import { Button } from './ui/Button';
import { FormError } from './ui/FormError';
import { Modal } from './ui/Modal';

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
  const [fieldErrors, setFieldErrors] = useState<{ sourceChatId?: string; destChatId?: string }>({});
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
      showToast('Mapping updated. Workers are restarting to apply it.');
      onClose();
    },
    onError: (err: unknown) => {
      setError(errorMessage(err, 'We could not update this mapping.'));
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    const src = parseInt(sourceChatId, 10);
    const dst = parseInt(destChatId, 10);
    const nextFieldErrors = {
      sourceChatId: isNaN(src) ? 'Enter a numeric chat ID.' : undefined,
      destChatId: isNaN(dst) ? 'Enter a numeric chat ID.' : undefined,
    };
    setFieldErrors(nextFieldErrors);
    if (nextFieldErrors.sourceChatId || nextFieldErrors.destChatId) return;
    mutation.mutate();
  };

  return (
    <Modal
      title="Edit channel mapping"
      icon={<Pencil className="h-5 w-5 text-ink-subtle" strokeWidth={2} aria-hidden />}
      size="sm"
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" form="edit-mapping-form" isLoading={mutation.isPending}>
            Save changes
          </Button>
        </>
      }
    >
      <form id="edit-mapping-form" onSubmit={handleSubmit} className="space-y-4" noValidate>
        <FormError message={error} />
        <MappingFormFields
          name={name}
          sourceChatId={sourceChatId}
          destChatId={destChatId}
          onNameChange={setName}
          onSourceChatIdChange={setSourceChatId}
          onDestChatIdChange={setDestChatId}
          errors={fieldErrors}
        />
      </form>
    </Modal>
  );
}
