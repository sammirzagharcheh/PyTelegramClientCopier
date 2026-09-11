import { Bell, Plus, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { PageHeader } from '../../components/PageHeader';
import { useToast } from '../../components/Toast';
import { CardSkeleton } from '../../components/Skeleton';
import { Button } from '../../components/ui/Button';
import { Card, CardHeader } from '../../components/ui/Card';
import { Field, Input } from '../../components/ui/Field';
import { FormError } from '../../components/ui/FormError';
import { EmptyState, ErrorState } from '../../components/ui/States';
import { errorMessage } from '../../lib/apiError';
import { useAuth } from '../../store/AuthContext';

type AlertWebhook = {
  id: number;
  url: string;
  enabled: boolean;
  created_at: string | null;
};

export function AlertWebhooks() {
  const { user } = useAuth();
  const canWrite = Boolean(user && user.role !== 'viewer');
  const queryClient = useQueryClient();
  const { show: showToast } = useToast();
  const [url, setUrl] = useState('');
  const [secret, setSecret] = useState('');
  const [formError, setFormError] = useState('');
  const [hookToDelete, setHookToDelete] = useState<AlertWebhook | null>(null);

  const { data: hooks = [], isLoading, isError, error, refetch } = useQuery({
    queryKey: ['alert-webhooks'],
    queryFn: async () => (await api.get<AlertWebhook[]>('/users/me/alert-webhooks')).data,
  });

  const createMutation = useMutation({
    mutationFn: async () => {
      const payload: { url: string; secret?: string } = { url: url.trim() };
      if (secret.trim()) payload.secret = secret.trim();
      return (await api.post<AlertWebhook>('/users/me/alert-webhooks', payload)).data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alert-webhooks'] });
      setUrl('');
      setSecret('');
      setFormError('');
      showToast('Alert webhook added', 'success');
    },
    onError: (err: unknown) => {
      setFormError(errorMessage(err, 'Adding the alert webhook failed'));
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/users/me/alert-webhooks/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alert-webhooks'] });
      setHookToDelete(null);
      showToast('Alert webhook removed', 'success');
    },
    onError: (err: unknown) => {
      showToast(errorMessage(err, 'Removing the webhook failed'), 'error');
    },
  });

  const canSubmit = canWrite && url.trim().length > 0 && !createMutation.isPending;

  return (
    <div className="max-w-4xl">
      <PageHeader
        title="Alert webhooks"
        icon={Bell}
        subtitle="HTTP endpoints notified when a worker goes stale. Separate from per-mapping copy webhooks and webhook delivery logs."
      />

      {canWrite && (
        <Card className="mb-4">
          <CardHeader
            title="Add an alert URL"
            description="Optional shared secret is stored server-side and never shown again."
          />
          <form
            className="space-y-4"
            onSubmit={(e) => {
              e.preventDefault();
              if (!canSubmit) return;
              createMutation.mutate();
            }}
          >
            <Field label="Webhook URL" required hint="Must be an absolute https URL.">
              {(fieldProps) => (
                <Input
                  {...fieldProps}
                  type="url"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://example.com/hooks/worker-alert"
                  autoComplete="off"
                />
              )}
            </Field>
            <Field label="Secret" hint="Optional. Used when signing or authenticating the alert.">
              {(fieldProps) => (
                <Input
                  {...fieldProps}
                  type="password"
                  value={secret}
                  onChange={(e) => setSecret(e.target.value)}
                  placeholder="Optional"
                  autoComplete="new-password"
                />
              )}
            </Field>
            <FormError message={formError} />
            <Button type="submit" icon={Plus} disabled={!canSubmit} isLoading={createMutation.isPending}>
              Add webhook
            </Button>
          </form>
        </Card>
      )}

      {isLoading ? (
        <CardSkeleton />
      ) : isError ? (
        <ErrorState title="Could not load alert webhooks" error={error} onRetry={() => void refetch()} />
      ) : hooks.length === 0 ? (
        <EmptyState
          icon={Bell}
          title="No alert webhooks yet"
          description={
            canWrite
              ? 'Add a URL above to get notified when a worker heartbeat goes stale.'
              : 'Ask a writer or admin to configure alert webhooks for this account.'
          }
        />
      ) : (
        <ul className="space-y-3">
          {hooks.map((hook) => (
            <li key={hook.id}>
              <Card>
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0">
                    <p className="break-all text-sm font-medium text-ink">{hook.url}</p>
                    <p className="mt-2 text-xs text-ink-subtle">
                      {hook.enabled ? 'Enabled' : 'Disabled'}
                      {hook.created_at ? ` · Created ${hook.created_at}` : ''}
                    </p>
                  </div>
                  {canWrite && (
                    <Button
                      type="button"
                      variant="danger"
                      icon={Trash2}
                      onClick={() => setHookToDelete(hook)}
                    >
                      Remove
                    </Button>
                  )}
                </div>
              </Card>
            </li>
          ))}
        </ul>
      )}

      {hookToDelete && (
        <ConfirmDialog
          title="Remove alert webhook?"
          message={`Stop sending stale-worker alerts to ${hookToDelete.url}?`}
          confirmLabel="Remove"
          variant="danger"
          onConfirm={() => deleteMutation.mutate(hookToDelete.id)}
          onCancel={() => setHookToDelete(null)}
          isPending={deleteMutation.isPending}
        />
      )}
    </div>
  );
}
