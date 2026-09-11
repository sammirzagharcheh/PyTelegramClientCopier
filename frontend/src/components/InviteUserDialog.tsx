import { Copy, MailPlus } from 'lucide-react';
import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';
import { errorMessage } from '../lib/apiError';
import { useToast } from './Toast';
import { Button } from './ui/Button';
import { Field, Input, Select } from './ui/Field';
import { FormError } from './ui/FormError';
import { Modal } from './ui/Modal';

type Props = {
  onClose: () => void;
};

type CreatedInvite = {
  id: number;
  email: string;
  role: string;
  expires_at: string;
  invite_path: string;
  plain_token: string;
  created_at: string | null;
};

export function InviteUserDialog({ onClose }: Props) {
  const [email, setEmail] = useState('');
  const [role, setRole] = useState('user');
  const [error, setError] = useState('');
  const [created, setCreated] = useState<CreatedInvite | null>(null);
  const queryClient = useQueryClient();
  const { show: showToast } = useToast();

  const mutation = useMutation({
    mutationFn: async () => {
      return (
        await api.post<CreatedInvite>('/admin/invites', {
          email,
          role,
          expires_in_hours: 72,
        })
      ).data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'invites'] });
      setCreated(data);
      setError('');
    },
    onError: (err: unknown) => {
      setError(errorMessage(err, 'We could not create this invite.'));
    },
  });

  const inviteUrl = created
    ? `${window.location.origin}${created.invite_path}`
    : '';

  const copyLink = async () => {
    if (!inviteUrl) return;
    try {
      await navigator.clipboard.writeText(inviteUrl);
      showToast('Invite link copied', 'success');
    } catch {
      showToast('Copy failed', 'error');
    }
  };

  return (
    <Modal
      title={created ? 'Invite link ready' : 'Invite user'}
      icon={<MailPlus className="h-5 w-5 text-ink-subtle" strokeWidth={2} aria-hidden />}
      size="sm"
      onClose={onClose}
      footer={
        created ? (
          <Button onClick={onClose}>Done</Button>
        ) : (
          <>
            <Button variant="secondary" onClick={onClose}>
              Cancel
            </Button>
            <Button
              type="submit"
              form="invite-user-form"
              isLoading={mutation.isPending}
            >
              Create invite
            </Button>
          </>
        )
      }
    >
      {created ? (
        <div className="space-y-4" data-testid="invite-created">
          <p className="text-sm text-ink-muted">
            Copy this link now. It expires at {created.expires_at} and will not be shown again.
            Role: <span className="font-medium text-ink">{created.role}</span> for{' '}
            <span className="font-medium text-ink">{created.email}</span>.
          </p>
          <code className="block break-all rounded-control border border-line bg-surface-sunken px-3 py-2 text-sm text-ink">
            {inviteUrl}
          </code>
          <Button type="button" variant="secondary" icon={Copy} onClick={() => void copyLink()}>
            Copy link
          </Button>
        </div>
      ) : (
        <form
          id="invite-user-form"
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            setError('');
            mutation.mutate();
          }}
        >
          <FormError message={error} />
          <Field label="Email" required hint="They will set their own password from the invite link.">
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
          <Field
            label="Role"
            hint="Admins can manage every user, mapping, and worker. Viewers can look but not change."
          >
            {(fieldProps) => (
              <Select {...fieldProps} value={role} onChange={(e) => setRole(e.target.value)}>
                <option value="user">User</option>
                <option value="viewer">Viewer</option>
                <option value="admin">Admin</option>
              </Select>
            )}
          </Field>
        </form>
      )}
    </Modal>
  );
}
