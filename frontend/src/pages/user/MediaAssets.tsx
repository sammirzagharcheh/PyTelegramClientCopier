import { Image, Trash2 } from 'lucide-react';
import { useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../../lib/api';
import type { MediaAsset } from '../../lib/api';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { useToast } from '../../components/Toast';
import { PageHeader } from '../../components/PageHeader';
import { CardSkeleton } from '../../components/Skeleton';
import { Button } from '../../components/ui/Button';
import { Card, CardHeader } from '../../components/ui/Card';
import { Field, Input, Select } from '../../components/ui/Field';
import { FormError } from '../../components/ui/FormError';
import { EmptyState, ErrorState } from '../../components/ui/States';
import { errorMessage } from '../../lib/apiError';

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function MediaAssets() {
  const queryClient = useQueryClient();
  const { show: showToast } = useToast();
  const [assetToDelete, setAssetToDelete] = useState<MediaAsset | null>(null);
  const [uploadName, setUploadName] = useState('');
  const [uploadKind, setUploadKind] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { data: assets = [], isLoading, isError, error, refetch } = useQuery({
    queryKey: ['media-assets'],
    queryFn: async () => (await api.get<MediaAsset[]>('/media-assets')).data,
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/media-assets/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['media-assets'] });
      setAssetToDelete(null);
      showToast('Media asset deleted', 'success');
    },
    onError: (err: unknown) => {
      showToast(errorMessage(err, 'Deleting the asset failed'), 'error');
    },
  });

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadError('');
    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      if (uploadName.trim()) formData.append('name', uploadName.trim());
      if (uploadKind.trim()) formData.append('media_kind', uploadKind.trim());
      await api.post('/media-assets', formData);
      queryClient.invalidateQueries({ queryKey: ['media-assets'] });
      showToast('Media asset uploaded', 'success');
      setUploadName('');
      setUploadKind('');
      if (fileInputRef.current) fileInputRef.current.value = '';
    } catch (err: unknown) {
      setUploadError(errorMessage(err, 'The upload failed'));
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="max-w-4xl">
      <PageHeader
        title="Media Assets"
        icon={Image}
        subtitle="Files you can swap in with a media replacement transform on any mapping."
      />

      <Card className="mb-4">
        <CardHeader
          title="Upload a new asset"
          description="Pick a file to upload it right away. Name and kind are optional."
        />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <Field label="File">
            {(fieldProps) => (
              <input
                {...fieldProps}
                ref={fileInputRef}
                type="file"
                onChange={handleUpload}
                disabled={isUploading}
                className="block w-full text-sm text-ink-muted file:mr-3 file:rounded-control file:border-0 file:bg-accent-soft file:px-3 file:py-2 file:text-sm file:font-medium file:text-accent-ink hover:file:bg-accent-soft/70 disabled:opacity-60"
              />
            )}
          </Field>
          <Field label="Name" hint="Defaults to the file name.">
            {(fieldProps) => (
              <Input
                {...fieldProps}
                type="text"
                value={uploadName}
                onChange={(e) => setUploadName(e.target.value)}
                placeholder="Display name"
                disabled={isUploading}
              />
            )}
          </Field>
          <Field label="Kind">
            {(fieldProps) => (
              <Select
                {...fieldProps}
                value={uploadKind}
                onChange={(e) => setUploadKind(e.target.value)}
                disabled={isUploading}
              >
                <option value="">Detect automatically</option>
                <option value="photo">Photo</option>
                <option value="video">Video</option>
                <option value="voice">Voice</option>
                <option value="other">Other</option>
              </Select>
            )}
          </Field>
        </div>
        <FormError message={uploadError} className="mt-3" />
        {isUploading && (
          <p className="mt-3 text-sm text-ink-subtle" role="status">
            Uploading your file
          </p>
        )}
      </Card>

      {isError ? (
        <ErrorState title="We couldn't load your media assets" error={error} onRetry={() => refetch()} />
      ) : isLoading ? (
        <CardSkeleton lines={4} />
      ) : (
        <Card flush>
          {assets.length === 0 ? (
            <EmptyState
              icon={Image}
              title="No media assets yet"
              description="Upload a file above, then reference it from a media replacement transform."
            />
          ) : (
            <ul className="divide-y divide-line">
              {assets.map((asset) => (
                <li
                  key={asset.id}
                  className="flex items-center justify-between gap-4 px-5 py-3.5 transition-colors hover:bg-surface-hover"
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-ink">{asset.name}</p>
                    <p className="mt-0.5 text-xs text-ink-subtle">
                      {asset.media_kind} · {formatBytes(asset.size_bytes)}
                      {asset.mime_type && ` · ${asset.mime_type}`}
                    </p>
                  </div>
                  <Button
                    variant="secondary"
                    size="sm"
                    icon={Trash2}
                    onClick={() => setAssetToDelete(asset)}
                    className="shrink-0"
                  >
                    Delete
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </Card>
      )}

      {assetToDelete && (
        <ConfirmDialog
          title="Delete media asset"
          message={
            <>
              Deleting <span className="font-medium text-ink">{assetToDelete.name}</span> cannot be
              undone. It will fail if a transform rule still points at this asset.
            </>
          }
          confirmLabel="Delete"
          variant="danger"
          icon={<Trash2 className="h-5 w-5" />}
          onConfirm={() => deleteMutation.mutate(assetToDelete.id)}
          onCancel={() => setAssetToDelete(null)}
          isPending={deleteMutation.isPending}
        />
      )}
    </div>
  );
}
