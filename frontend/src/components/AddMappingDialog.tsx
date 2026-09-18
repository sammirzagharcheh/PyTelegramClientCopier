import { GitBranch } from 'lucide-react';
import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';
import { invalidateDashboardStats } from '../lib/queryClient';
import { errorMessage } from '../lib/apiError';
import { resolveMappingRouteChats } from '../lib/peerResolve';
import { MappingRouteFields } from './MappingRouteFields';
import { useToast } from './Toast';
import { Button } from './ui/Button';
import { FormError } from './ui/FormError';
import { Modal } from './ui/Modal';
import {
  hasRouteErrors,
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
      const resolved = await resolveMappingRouteChats(
        route.telegramAccountId!,
        route.sourceChatId,
        route.destChatId,
        route.sourceChatTitle,
        route.destChatTitle
      );
      return (
        await api.post('/mappings', {
          name: name.trim() || undefined,
          source_chat_id: resolved.source_chat_id,
          dest_chat_id: resolved.dest_chat_id,
          telegram_account_id: route.telegramAccountId,
          source_chat_title: resolved.source_chat_title || undefined,
          dest_chat_title: resolved.dest_chat_title || undefined,
        })
      ).data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mappings'] });
      invalidateDashboardStats(queryClient);
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
    const errors = validateMappingRoute(route);
    setFieldErrors(errors);
    if (hasRouteErrors(errors)) return;
    mutation.mutate();
  };

  return (
    <Modal
      title="Add channel mapping"
      description="Messages arriving in the source channel are copied to the destination."
      icon={<GitBranch className="h-5 w-5 text-ink-subtle" strokeWidth={2} aria-hidden />}
      size="md"
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="submit"
            form="add-mapping-form"
            isLoading={mutation.isPending}
            disabled={route.telegramAccountId == null}
          >
            Create mapping
          </Button>
        </>
      }
    >
      <form id="add-mapping-form" onSubmit={handleSubmit} className="space-y-4" noValidate>
        <FormError message={error} />
        <MappingRouteFields
          values={route}
          onChange={setRoute}
          errors={fieldErrors}
          name={name}
          onNameChange={setName}
        />
      </form>
    </Modal>
  );
}
