import { CheckCircle2, PlugZap, Settings as SettingsIcon } from 'lucide-react';
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { PageHeader } from '../../components/PageHeader';
import { CardSkeleton } from '../../components/Skeleton';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Field, Input } from '../../components/ui/Field';
import { FormError } from '../../components/ui/FormError';
import { ErrorState } from '../../components/ui/States';
import { errorMessage } from '../../lib/apiError';

type SettingsData = {
  mongo_uri: string;
  mongo_uri_set: boolean;
  mongo_db: string;
  mongo_db_set: boolean;
};

function sourceLabel(isSet: boolean) {
  return isSet ? 'set here' : 'from environment';
}

export function Settings() {
  const [mongoUri, setMongoUri] = useState('');
  const [mongoDb, setMongoDb] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const queryClient = useQueryClient();

  const {
    data: settings,
    isLoading,
    isError,
    error: loadError,
    refetch,
  } = useQuery({
    queryKey: ['admin', 'settings'],
    queryFn: async () => (await api.get<SettingsData>('/admin/settings')).data,
  });

  const updateMutation = useMutation({
    mutationFn: async (updates: { mongo_uri?: string; mongo_db?: string }) => {
      return (await api.patch('/admin/settings', updates)).data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'settings'] });
      setSuccess('Settings saved. Run "Test connection" to verify them.');
      setError('');
      setMongoUri('');
      setMongoDb('');
    },
    onError: (err: unknown) => {
      setSuccess('');
      setError(errorMessage(err, 'Saving the settings failed'));
    },
  });

  const testMutation = useMutation({
    mutationFn: async () => (await api.post('/admin/settings/test-mongo')).data,
    onSuccess: () => {
      setError('');
      setSuccess('Connected to MongoDB successfully.');
    },
    onError: (err: unknown) => {
      setSuccess('');
      setError(errorMessage(err, 'The connection attempt failed'));
    },
  });

  const handleSave = () => {
    setSuccess('');
    setError('');
    const updates: { mongo_uri?: string; mongo_db?: string } = {};
    if (mongoUri.trim()) updates.mongo_uri = mongoUri.trim();
    if (mongoDb.trim()) updates.mongo_db = mongoDb.trim();
    if (Object.keys(updates).length === 0) {
      setError('Enter a MongoDB URI or a database name before saving.');
      return;
    }
    updateMutation.mutate(updates);
  };

  return (
    <div className="max-w-2xl">
      <PageHeader
        title="Settings"
        icon={SettingsIcon}
        subtitle="Configure the MongoDB connection. Values stored here override environment variables, and the URI is masked when displayed."
      />

      {isError ? (
        <ErrorState title="We couldn't load the settings" error={loadError} onRetry={() => refetch()} />
      ) : isLoading || !settings ? (
        <CardSkeleton lines={5} />
      ) : (
        <Card>
          <FormError message={error} className="mb-4" />
          {success && (
            <div
              role="status"
              className="mb-4 flex items-start gap-2 rounded-control border border-emerald-300 bg-emerald-50 px-3 py-2.5 text-sm text-emerald-900 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200"
            >
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
              <span className="min-w-0">{success}</span>
            </div>
          )}

          <div className="space-y-5">
            <Field
              label="MongoDB URI"
              hint={`Currently ${settings.mongo_uri} (${sourceLabel(settings.mongo_uri_set)}). Use mongodb:// or mongodb+srv:// for Atlas. Leave blank to keep the current value.`}
            >
              {(fieldProps) => (
                <Input
                  {...fieldProps}
                  type="password"
                  value={mongoUri}
                  onChange={(e) => setMongoUri(e.target.value)}
                  placeholder={settings.mongo_uri}
                  autoComplete="off"
                  className="font-mono"
                />
              )}
            </Field>

            <Field
              label="Database name"
              hint={`Currently ${settings.mongo_db} (${sourceLabel(settings.mongo_db_set)}).`}
            >
              {(fieldProps) => (
                <Input
                  {...fieldProps}
                  type="text"
                  value={mongoDb}
                  onChange={(e) => setMongoDb(e.target.value)}
                  placeholder={settings.mongo_db}
                  autoComplete="off"
                />
              )}
            </Field>

            <div className="flex flex-wrap gap-2 border-t border-line pt-4">
              <Button onClick={handleSave} isLoading={updateMutation.isPending}>
                Save
              </Button>
              <Button
                variant="secondary"
                icon={PlugZap}
                onClick={() => testMutation.mutate()}
                isLoading={testMutation.isPending}
              >
                Test connection
              </Button>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
