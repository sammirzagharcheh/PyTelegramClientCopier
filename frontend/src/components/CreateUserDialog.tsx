import { UserPlus } from 'lucide-react';
import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';
import { errorMessage } from '../lib/apiError';
import { Button } from './ui/Button';
import { Field, Input, Select } from './ui/Field';
import { FormError } from './ui/FormError';
import { Modal } from './ui/Modal';

type Props = {
  onClose: () => void;
};

export function CreateUserDialog({ onClose }: Props) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [role, setRole] = useState('user');
  const [error, setError] = useState('');
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: async () => {
      return (await api.post('/admin/users', { email, password, name: name || undefined, role }))
        .data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'users'] });
      onClose();
    },
    onError: (err: unknown) => {
      setError(errorMessage(err, 'We could not create this user.'));
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    mutation.mutate();
  };

  return (
    <Modal
      title="Create user"
      icon={<UserPlus className="h-5 w-5 text-ink-subtle" strokeWidth={2} aria-hidden />}
      size="sm"
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" form="create-user-form" isLoading={mutation.isPending}>
            Create user
          </Button>
        </>
      }
    >
      <form id="create-user-form" onSubmit={handleSubmit} className="space-y-4">
        <FormError message={error} />
        <Field label="Email" required>
          {(fieldProps) => (
            <Input
              {...fieldProps}
              type="email"
              autoComplete="off"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          )}
        </Field>
        <Field label="Password" required>
          {(fieldProps) => (
            <Input
              {...fieldProps}
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          )}
        </Field>
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
        <Field label="Role" hint="Admins can manage every user, mapping, and worker.">
          {(fieldProps) => (
            <Select {...fieldProps} value={role} onChange={(e) => setRole(e.target.value)}>
              <option value="user">User</option>
              <option value="admin">Admin</option>
            </Select>
          )}
        </Field>
      </form>
    </Modal>
  );
}
