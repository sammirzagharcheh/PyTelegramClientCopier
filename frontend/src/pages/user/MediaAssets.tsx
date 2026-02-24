import { Image, Trash2 } from 'lucide-react';
import { useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../../lib/api';
import type { MediaAsset } from '../../lib/api';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { useToast } from '../../components/Toast';
import { PageHeader } from '../../components/PageHeader';

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

  const { data: assets = [], isLoading } = useQuery({
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
      showToast('Media asset deleted');
    },
    onError: (err: unknown) => {
      const res = (err as { response?: { status?: number; data?: { detail?: string } } })?.response;
      if (res?.status === 409) {
        showToast(res.data?.detail ?? 'Asset is in use by a transform rule');
      } else {
        showToast((res?.data?.detail as string) ?? 'Failed to delete asset');
      }
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
      showToast('Media asset uploaded');
      setUploadName('');
      setUploadKind('');
      if (fileInputRef.current) fileInputRef.current.value = '';
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setUploadError(msg ?? 'Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  if (isLoading) {
    return (
      <div>
        <PageHeader title="Media Assets" icon={Image} subtitle="Upload files for media replacement transforms" />
        <div className="animate-pulse h-32 bg-gray-200 dark:bg-gray-700 rounded" />
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Media Assets"
        icon={Image}
        subtitle="Upload files for media replacement transforms. Use these in mapping transforms to replace source media."
      />

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
        <h3 className="text-sm font-semibold mb-3">Upload new asset</h3>
        <div className="flex flex-wrap items-end gap-4">
          <div>
            <label htmlFor="upload-file" className="block text-sm text-gray-600 dark:text-gray-400 mb-1">
              File
            </label>
            <input
              id="upload-file"
              ref={fileInputRef}
              type="file"
              onChange={handleUpload}
              disabled={isUploading}
              className="block text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 dark:file:bg-blue-900/30 dark:file:text-blue-300"
            />
          </div>
          <div>
            <label htmlFor="upload-name" className="block text-sm text-gray-600 dark:text-gray-400 mb-1">
              Name (optional)
            </label>
            <input
              id="upload-name"
              type="text"
              value={uploadName}
              onChange={(e) => setUploadName(e.target.value)}
              placeholder="Display name"
              className="px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-sm"
            />
          </div>
          <div>
            <label htmlFor="upload-kind" className="block text-sm text-gray-600 dark:text-gray-400 mb-1">
              Kind (optional)
            </label>
            <select
              id="upload-kind"
              value={uploadKind}
              onChange={(e) => setUploadKind(e.target.value)}
              className="px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-sm"
            >
              <option value="">Auto-detect</option>
              <option value="photo">Photo</option>
              <option value="video">Video</option>
              <option value="voice">Voice</option>
              <option value="other">Other</option>
            </select>
          </div>
        </div>
        {uploadError && (
          <p className="mt-2 text-sm text-red-600 dark:text-red-400">{uploadError}</p>
        )}
        {isUploading && (
          <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">Uploading…</p>
        )}
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden">
        <div className="divide-y divide-gray-200 dark:divide-gray-700">
          {assets.map((asset) => (
            <div
              key={asset.id}
              className="p-4 flex items-center justify-between gap-4 hover:bg-gray-50 dark:hover:bg-gray-700/30"
            >
              <div className="min-w-0 flex-1">
                <p className="font-medium truncate">{asset.name}</p>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {asset.media_kind} · {formatBytes(asset.size_bytes)}
                  {asset.mime_type && ` · ${asset.mime_type}`}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setAssetToDelete(asset)}
                className="px-3 py-1 text-sm rounded border border-red-300 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 dark:border-red-800 shrink-0"
              >
                Delete
              </button>
            </div>
          ))}
        </div>
        {assets.length === 0 && (
          <div className="p-8 text-center text-gray-500 dark:text-gray-400">
            No media assets yet. Upload a file above to get started.
          </div>
        )}
      </div>

      {assetToDelete && (
        <ConfirmDialog
          title="Delete media asset"
          message={
            <>
              Are you sure you want to delete <span className="font-semibold">{assetToDelete.name}</span>?
              This will fail if the asset is in use by a transform rule.
            </>
          }
          confirmLabel="Delete"
          variant="danger"
          icon={<Trash2 className="h-5 w-5 text-red-600" />}
          onConfirm={() => deleteMutation.mutate(assetToDelete.id)}
          onCancel={() => setAssetToDelete(null)}
          isPending={deleteMutation.isPending}
        />
      )}
    </div>
  );
}
