import { Copy, KeyRound, Plus, Trash2 } from 'lucide-react';
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

/** Keep in sync with app.auth.scopes.SCOPE_CHOICES / API_KEY_SCOPES. */
export const API_KEY_SCOPE_CHOICES: { id: string; label: string }[] = [
  { id: 'mappings:read', label: 'Read mappings, filters, transforms, schedules, preview' },
  { id: 'mappings:write', label: 'Create and change mappings and nested rules' },
  { id: 'accounts:read', label: 'List accounts and dialogs' },
  { id: 'accounts:write', label: 'Add, edit, delete accounts and run login' },
  { id: 'workers:read', label: 'List workers' },
  { id: 'workers:write', label: 'Start and stop workers' },
  { id: 'logs:read', label: 'Read message, worker, webhook logs and message index' },
  { id: 'stats:read', label: 'Read dashboard stats' },
  { id: 'keys:read', label: 'List API keys' },
  { id: 'keys:write', label: 'Create and revoke API keys' },
  { id: 'webhooks:read', label: 'List alert webhooks' },
  { id: 'webhooks:write', label: 'Create and delete alert webhooks' },
];

const DEFAULT_SCOPES = new Set(['mappings:read', 'mappings:write']);

type ApiKeyItem = {
  id: number;
  name: string;
  scopes: string;
  created_at: string | null;
  last_used_at: string | null;
};

type CreatedKey = {
  id: number;
  name: string;
  scopes: string;
  plain_key: string;
  created_at: string | null;
};

export function ApiKeys() {
  const { user } = useAuth();
  const canWrite = Boolean(user && user.role !== 'viewer');
  const queryClient = useQueryClient();
  const { show: showToast } = useToast();
  const [name, setName] = useState('');
  const [selected, setSelected] = useState<Set<string>>(() => new Set(DEFAULT_SCOPES));
  const [formError, setFormError] = useState('');
  const [created, setCreated] = useState<CreatedKey | null>(null);
  const [keyToRevoke, setKeyToRevoke] = useState<ApiKeyItem | null>(null);

  const { data: keys = [], isLoading, isError, error, refetch } = useQuery({
    queryKey: ['api-keys'],
    queryFn: async () => (await api.get<ApiKeyItem[]>('/users/me/api-keys')).data,
  });

  const createMutation = useMutation({
    mutationFn: async () => {
      const scopes = [...selected].join(',');
      return (
        await api.post<CreatedKey>('/users/me/api-keys', {
          name: name.trim(),
          scopes,
        })
      ).data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] });
      setCreated(data);
      setName('');
      setSelected(new Set(DEFAULT_SCOPES));
      setFormError('');
      showToast('API key created', 'success');
    },
    onError: (err: unknown) => {
      setFormError(errorMessage(err, 'Creating the API key failed'));
    },
  });

  const revokeMutation = useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/users/me/api-keys/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] });
      setKeyToRevoke(null);
      showToast('API key revoked', 'success');
    },
    onError: (err: unknown) => {
      showToast(errorMessage(err, 'Revoking the key failed'), 'error');
    },
  });

  const selectedCount = selected.size;
  const canSubmit = canWrite && name.trim().length > 0 && selectedCount > 0 && !createMutation.isPending;

  const scopeHint =
    'Scopes limit what X-Api-Key clients can do. JWT panel sessions ignore scopes.';

  const toggleScope = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const copyPlain = async () => {
    if (!created?.plain_key) return;
    try {
      await navigator.clipboard.writeText(created.plain_key);
      showToast('Key copied', 'success');
    } catch {
      showToast('Copy failed', 'error');
    }
  };

  return (
    <div className="max-w-4xl">
      <PageHeader
        title="API Keys"
        icon={KeyRound}
        subtitle="Issue X-Api-Key credentials for external clients. Scopes are enforced on every key request."
      />

      {created && (
        <div data-testid="created-key-banner">
          <Card className="mb-4 border-amber-500/40">
            <CardHeader
              title="Copy your new key now"
              description="The plaintext key is shown once. Store it securely; you cannot retrieve it again."
            />
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
              <code className="flex-1 break-all rounded-control border border-line bg-surface-sunken px-3 py-2 text-sm text-ink">
                {created.plain_key}
              </code>
              <Button type="button" variant="secondary" icon={Copy} onClick={() => void copyPlain()}>
                Copy
              </Button>
              <Button type="button" variant="ghost" onClick={() => setCreated(null)}>
                Dismiss
              </Button>
            </div>
          </Card>
        </div>
      )}

      {canWrite && (
        <Card className="mb-4">
          <CardHeader title="Create a key" description={scopeHint} />
          <form
            className="space-y-4"
            onSubmit={(e) => {
              e.preventDefault();
              if (!canSubmit) return;
              createMutation.mutate();
            }}
          >
            <Field label="Name" required hint="A label for this key, shown in the list only.">
              {(fieldProps) => (
                <Input
                  {...fieldProps}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="CI bot"
                  autoComplete="off"
                />
              )}
            </Field>
            <fieldset>
              <legend className="mb-2 text-sm font-medium text-ink">Scopes</legend>
              <ul className="grid gap-2 sm:grid-cols-2">
                {API_KEY_SCOPE_CHOICES.map((scope) => (
                  <li key={scope.id}>
                    <label className="flex cursor-pointer items-start gap-2 rounded-control border border-line px-3 py-2 text-sm text-ink hover:bg-surface-hover">
                      <input
                        type="checkbox"
                        className="mt-0.5"
                        checked={selected.has(scope.id)}
                        onChange={() => toggleScope(scope.id)}
                        aria-label={scope.id}
                      />
                      <span>
                        <span className="font-medium">{scope.id}</span>
                        <span className="mt-0.5 block text-xs text-ink-muted">{scope.label}</span>
                      </span>
                    </label>
                  </li>
                ))}
              </ul>
            </fieldset>
            <FormError message={formError} />
            <Button type="submit" icon={Plus} disabled={!canSubmit} isLoading={createMutation.isPending}>
              Create key
            </Button>
          </form>
        </Card>
      )}

      {isLoading ? (
        <CardSkeleton />
      ) : isError ? (
        <ErrorState title="Could not load API keys" error={error} onRetry={() => void refetch()} />
      ) : keys.length === 0 ? (
        <EmptyState
          icon={KeyRound}
          title="No API keys yet"
          description={
            canWrite
              ? 'Create a key above to call the API with the X-Api-Key header.'
              : 'Ask a writer or admin to create keys for this account.'
          }
        />
      ) : (
        <ul className="space-y-3">
          {keys.map((key) => (
            <li key={key.id}>
              <Card>
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <h3 className="text-sm font-semibold text-ink">{key.name}</h3>
                    <p className="mt-1 break-all text-xs text-ink-muted">{key.scopes || '(none)'}</p>
                    <p className="mt-2 text-xs text-ink-subtle">
                      Created {key.created_at ?? 'unknown'}
                      {key.last_used_at ? ` · Last used ${key.last_used_at}` : ' · Never used'}
                    </p>
                  </div>
                  {canWrite && (
                    <Button
                      type="button"
                      variant="danger"
                      icon={Trash2}
                      onClick={() => setKeyToRevoke(key)}
                    >
                      Revoke
                    </Button>
                  )}
                </div>
              </Card>
            </li>
          ))}
        </ul>
      )}

      {keyToRevoke && (
        <ConfirmDialog
          title="Revoke API key?"
          message={`Revoke "${keyToRevoke.name}"? Clients using this key will fail immediately.`}
          confirmLabel="Revoke"
          variant="danger"
          onConfirm={() => revokeMutation.mutate(keyToRevoke.id)}
          onCancel={() => setKeyToRevoke(null)}
          isPending={revokeMutation.isPending}
        />
      )}
    </div>
  );
}
