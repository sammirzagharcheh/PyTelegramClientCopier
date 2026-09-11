import { GitBranch } from 'lucide-react';
import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';
import { errorMessage } from '../lib/apiError';
import { MappingFormFields } from './MappingFormFields';
import { useToast } from './Toast';
import { Button } from './ui/Button';
import { FormError } from './ui/FormError';
import { Modal } from './ui/Modal';

type Props = {
  onClose: () => void;
};

export function AddMappingDialog({ onClose }: Props) {
  const [name, setName] = useState('');
  const [sourceChatId, setSourceChatId] = useState('');
  const [destChatId, setDestChatId] = useState('');
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState<{ sourceChatId?: string; destChatId?: string }>({});
  const queryClient = useQueryClient();
  const { show: showToast } = useToast();

  const mutation = useMutation({
    mutationFn: async () => {
      return (
        await api.post('/mappings', {
          name: name || undefined,
          source_chat_id: parseInt(sourceChatId, 10),
          dest_chat_id: parseInt(destChatId, 10),
        })
      ).data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mappings'] });
      showToast('Mapping created. Workers are restarting to apply it.');
      onClose();
    },
    onError: (err: unknown) => {
      setError(errorMessage(err, 'We could not create this mapping.'));
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
      title="Add channel mapping"
      description="Messages arriving in the source channel are copied to the destination."
      icon={<GitBranch className="h-5 w-5 text-ink-subtle" strokeWidth={2} aria-hidden />}
      size="sm"
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" form="add-mapping-form" isLoading={mutation.isPending}>
            Create mapping
          </Button>
        </>
      }
    >
      <form id="add-mapping-form" onSubmit={handleSubmit} className="space-y-4" noValidate>
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
