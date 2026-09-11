import { UserCog } from 'lucide-react';
import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';
import { errorMessage } from '../lib/apiError';
import { Button } from './ui/Button';
import { Field, Input, Select } from './ui/Field';
import { FormError } from './ui/FormError';
import { Modal } from './ui/Modal';

type User = {
  id: number;
  email: string;
  name: string | null;
  role: string;
  status: string;
};

type Props = {
  user: User;
  onClose: () => void;
};

export function EditUserDialog({ user, onClose }: Props) {
  const [name, setName] = useState(user.name ?? '');
  const [role, setRole] = useState(user.role);
  const [status, setStatus] = useState(user.status);
  const [newPassword, setNewPassword] = useState('');
  const [error, setError] = useState('');
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: async () => {
      const body: { name?: string; role?: string; status?: string; password?: string } = {
        name: name || undefined,
        role,
        status,
      };
      if (newPassword.trim()) {
        body.password = newPassword;
      }
      return (await api.patch(`/admin/users/${user.id}`, body)).data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'users'] });
      onClose();
    },
    onError: (err: unknown) => {
      setError(errorMessage(err, 'We could not update this user.'));
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    mutation.mutate();
  };

  return (
    <Modal
      title="Edit user"
      description={user.email}
      icon={<UserCog className="h-5 w-5 text-ink-subtle" strokeWidth={2} aria-hidden />}
      size="sm"
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" form="edit-user-form" isLoading={mutation.isPending}>
            Save changes
          </Button>
        </>
      }
    >
      <form id="edit-user-form" onSubmit={handleSubmit} className="space-y-4">
        <FormError message={error} />
        <Field label="Name" hint="Optional.">
          {(fieldProps) => (
            <Input
              {...fieldProps}
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          )}
        </Field>
        <Field label="Role">
          {(fieldProps) => (
            <Select {...fieldProps} value={role} onChange={(e) => setRole(e.target.value)}>
              <option value="user">User</option>
              <option value="viewer">Viewer</option>
              <option value="admin">Admin</option>
            </Select>
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
        <Field label="New password" hint="Leave blank to keep the current password.">
          {(fieldProps) => (
            <Input
              {...fieldProps}
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              autoComplete="new-password"
            />
          )}
        </Field>
      </form>
    </Modal>
  );
}
