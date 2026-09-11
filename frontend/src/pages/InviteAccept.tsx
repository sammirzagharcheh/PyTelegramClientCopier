import { AlertTriangle } from 'lucide-react';
import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router-dom';
import { api } from '../lib/api';
import { errorMessage } from '../lib/apiError';
import { useAuth } from '../store/AuthContext';
import { Button } from '../components/ui/Button';
import { Field, Input } from '../components/ui/Field';
import { FormError } from '../components/ui/FormError';
import { CardSkeleton } from '../components/Skeleton';

type InvitePreview = {
  email: string;
  role: string;
  expires_at: string;
};

type TokenPair = {
  access_token: string;
  refresh_token: string;
};

export function InviteAccept() {
  const { token = '' } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const { establishSession } = useAuth();
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [formError, setFormError] = useState('');

  const previewQuery = useQuery({
    queryKey: ['invite-preview', token],
    queryFn: async () => (await api.get<InvitePreview>(`/auth/invites/${token}`)).data,
    enabled: Boolean(token),
    retry: false,
  });

  const acceptMutation = useMutation({
    mutationFn: async () => {
      return (
        await api.post<TokenPair>(`/auth/invites/${token}/accept`, {
          password,
          name: name.trim() || undefined,
        })
      ).data;
    },
    onSuccess: async (data) => {
      await establishSession(data.access_token, data.refresh_token);
      navigate('/');
    },
    onError: (err: unknown) => {
      setFormError(errorMessage(err, 'Accepting the invite failed'));
    },
  });

  if (previewQuery.isLoading) {
    return <CardSkeleton />;
  }

  if (previewQuery.isError || !previewQuery.data) {
    return (
      <div className="rounded-surface border border-line bg-surface-raised p-6 shadow-surface">
        <div
          role="alert"
          className="flex items-start gap-2 rounded-control border border-red-300 bg-red-50 px-3 py-2.5 text-sm text-red-900 dark:border-red-800 dark:bg-red-950/50 dark:text-red-200"
        >
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
          <span>{errorMessage(previewQuery.error, 'This invite is invalid or expired.')}</span>
        </div>
      </div>
    );
  }

  const invite = previewQuery.data;

  return (
    <div className="rounded-surface border border-line bg-surface-raised p-6 shadow-surface">
      <h1 className="text-lg font-semibold text-ink">Accept invite</h1>
      <p className="mt-1 text-sm text-ink-subtle">
        Create a password for <span className="font-medium text-ink">{invite.email}</span> (
        {invite.role}).
      </p>

      <form
        className="mt-6 space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          setFormError('');
          acceptMutation.mutate();
        }}
      >
        <FormError message={formError} />
        <Field label="Name" hint="Optional.">
          {(fieldProps) => (
            <Input
              {...fieldProps}
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoComplete="name"
            />
          )}
        </Field>
        <Field label="Password" required hint="At least 8 characters.">
          {(fieldProps) => (
            <Input
              {...fieldProps}
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password"
              required
              minLength={8}
            />
          )}
        </Field>
        <Button type="submit" className="w-full" isLoading={acceptMutation.isPending}>
          Create account
        </Button>
      </form>
    </div>
  );
}
