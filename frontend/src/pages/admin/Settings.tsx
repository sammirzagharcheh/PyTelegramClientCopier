import { Settings as SettingsIcon } from 'lucide-react';
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { PageHeader } from '../../components/PageHeader';

type SettingsData = {
  mongo_uri: string;
  mongo_uri_set: boolean;
  mongo_db: string;
  mongo_db_set: boolean;
};

export function Settings() {
  const [mongoUri, setMongoUri] = useState('');
  const [mongoDb, setMongoDb] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const queryClient = useQueryClient();

  const { data: settings, isLoading } = useQuery({
    queryKey: ['admin', 'settings'],
    queryFn: async () => (await api.get<SettingsData>('/admin/settings')).data,
  });

  const updateMutation = useMutation({
    mutationFn: async (updates: { mongo_uri?: string; mongo_db?: string }) => {
      return (await api.patch('/admin/settings', updates)).data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'settings'] });
      setSuccess('Settings saved. Use "Test connection" to verify.');
      setError('');
    },
    onError: (err: unknown) => {
      setError(
        err && typeof err === 'object' && 'response' in err && err.response && typeof err.response === 'object' && 'data' in err.response && (err.response.data as { detail?: string })?.detail
          ? (err.response.data as { detail: string }).detail
          : 'Failed to save'
      );
    },
  });

  const testMutation = useMutation({
    mutationFn: async () => (await api.post('/admin/settings/test-mongo')).data,
    onSuccess: () => setSuccess('MongoDB connection OK'),
    onError: (err: unknown) => {
      setError(
        err && typeof err === 'object' && 'response' in err && err.response && typeof err.response === 'object' && 'data' in err.response && (err.response.data as { detail?: string })?.detail
          ? (err.response.data as { detail: string }).detail
          : 'Connection failed'
      );
    },
  });

  const handleSave = () => {
    setSuccess('');
    setError('');
    const updates: { mongo_uri?: string; mongo_db?: string } = {};
    if (mongoUri.trim()) updates.mongo_uri = mongoUri.trim();
    // Include mongo_db: empty string clears override → falls back to MONGO_DB from .env
    if (mongoDb.trim()) {
      updates.mongo_db = mongoDb.trim();
    } else if (settings?.mongo_db_set) {
      updates.mongo_db = '';  // Clear override to use .env
    }
    if (Object.keys(updates).length === 0) {
      setError('Change MongoDB URI and/or database name to save');
      return;
    }
    updateMutation.mutate(updates);
  };

  if (isLoading || !settings) return <div className="animate-pulse h-32 bg-gray-200 dark:bg-gray-700 rounded" />;

  return (
    <div>
      <PageHeader
        title="Settings"
        icon={SettingsIcon}
        subtitle="Configure MongoDB connection. Stored values override environment variables. The URI is masked when displayed."
      />

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 max-w-2xl transition-shadow hover:shadow-lg">
        {error && (
          <div className="mb-4 p-3 rounded bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm">
            {error}
          </div>
        )}
        {success && (
          <div className="mb-4 p-3 rounded bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400 text-sm">
            {success}
          </div>
        )}

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">MongoDB URI</label>
            <input
              type="password"
              value={mongoUri}
              onChange={(e) => setMongoUri(e.target.value)}
              placeholder={settings.mongo_uri}
              className="w-full px-4 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 font-mono text-sm"
            />
            <p className="mt-1 text-xs text-gray-500">
              Current: {settings.mongo_uri} {settings.mongo_uri_set ? '(from settings)' : '(from env)'}
            </p>
            <p className="mt-1 text-xs text-gray-500">
              Use mongodb:// or mongodb+srv:// for Atlas. Leave empty to keep current.
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">MongoDB Database Name</label>
            <input
              type="text"
              value={mongoDb}
              onChange={(e) => setMongoDb(e.target.value)}
              placeholder={settings.mongo_db}
              className="w-full px-4 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700"
            />
            <p className="mt-1 text-xs text-gray-500">
              Current: {settings.mongo_db} {settings.mongo_db_set ? '(from settings)' : '(from env)'}
            </p>
            <p className="mt-1 text-xs text-gray-500">
              Leave empty to use MONGO_DB from .env. Clear and save to reset override.
            </p>
          </div>

          <div className="flex gap-3">
            <button
              onClick={handleSave}
              disabled={updateMutation.isPending}
              className="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
            >
              Save
            </button>
            <button
              onClick={() => testMutation.mutate()}
              disabled={testMutation.isPending}
              className="px-4 py-2 rounded border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              Test connection
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
