import { Pencil } from 'lucide-react';
import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';
import { useToast } from './Toast';
import { AccountTypeBadge } from './AccountTypeBadge';
import { Button } from './ui/Button';
import { Field, Input, Select } from './ui/Field';
import { Modal } from './ui/Modal';
import { FormError } from './ui/FormError';
import { errorMessage } from '../lib/apiError';

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
      setError(errorMessage(err, 'We could not update this account.'));
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    mutation.mutate();
  };

  return (
    <Modal
      title="Edit Telegram account"
      icon={<Pencil className="h-5 w-5 text-ink-subtle" strokeWidth={2} aria-hidden />}
      size="sm"
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" form="edit-account-form" isLoading={mutation.isPending}>
            Save changes
          </Button>
        </>
      }
    >
      <form id="edit-account-form" onSubmit={handleSubmit} className="space-y-4">
        <FormError message={error} />
        <div className="flex items-center gap-2 rounded-control bg-surface-sunken px-3 py-2.5">
          <span className="text-sm text-ink-subtle">Account type</span>
          <AccountTypeBadge type={account.type} />
          <span className="ml-auto text-xs text-ink-subtle">Cannot be changed</span>
        </div>
        <Field label="Name" hint="Shown in lists and worker logs.">
          {(fieldProps) => (
            <Input
              {...fieldProps}
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Account name"
            />
          )}
        </Field>
        <Field label="Status">
          {(fieldProps) => (
            <Select {...fieldProps} value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </Select>
          )}
        </Field>
      </form>
    </Modal>
  );
}
