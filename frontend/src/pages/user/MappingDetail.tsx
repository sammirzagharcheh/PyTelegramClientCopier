import { ArrowLeft, Clock, Eye, Filter, GitBranch, Pencil, Plus, RotateCcw, Sparkles, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams, Link, useNavigate, useLocation } from 'react-router-dom';
import { api } from '../../lib/api';
import type { ChannelMapping, MappingPreviewResponse, Transform, TransformCreate } from '../../lib/api';
import { coerceChannelMappingForEdit } from '../../lib/channelMappingDefaults';
import { PII_TRANSFORM_PRESETS } from '../../lib/piiTransformPresets';
import type { FilterFormValues } from '../../components/FilterForm';
import { EditMappingDialog } from '../../components/EditMappingDialog';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { MappingEnableToggle } from '../../components/MappingEnableToggle';
import { MappingScheduleForm } from '../../components/MappingScheduleForm';
import { useToast } from '../../components/Toast';
import { PageHeader } from '../../components/PageHeader';
import { useAuth } from '../../store/AuthContext';
import {
  FilterForm,
  formatMediaDisplay,
  mediaArrayToString,
  stringToMediaArray,
} from '../../components/FilterForm';
import { TransformForm } from '../../components/TransformForm';
import { formatScheduleSummary } from '../../lib/formatDateTime';

type Filter = {
  id: number;
  mapping_id: number;
  include_text: string | null;
  exclude_text: string | null;
  media_types: string | null;
  regex_pattern: string | null;
  or_group_id: number;
  allowed_sender_ids?: string | null;
  denied_usernames?: string | null;
  min_url_count?: number | null;
  max_url_count?: number | null;
  required_hashtags?: string | null;
};

function filterValuesToApiBody(values: FilterFormValues): Record<string, unknown> {
  const body: Record<string, unknown> = {
    include_text: values.include_text || null,
    exclude_text: values.exclude_text || null,
    media_types: mediaArrayToString(values.media_types) || null,
    regex_pattern: values.regex_pattern || null,
    allowed_sender_ids: values.allowed_sender_ids?.trim() || null,
    denied_usernames: values.denied_usernames?.trim() || null,
    required_hashtags: values.required_hashtags?.trim() || null,
  };
  const minS = values.min_url_count?.trim();
  const maxS = values.max_url_count?.trim();
  body.min_url_count = minS ? parseInt(minS, 10) : null;
  body.max_url_count = maxS ? parseInt(maxS, 10) : null;
  if (values.or_group_id !== undefined) {
    body.or_group_id = values.or_group_id;
  }
  return body;
}

function describeFilter(f: Filter): string[] {
  const parts: string[] = [];
  parts.push(`OR group ${f.or_group_id}`);
  if (f.include_text) parts.push(`Must contain "${f.include_text}"`);
  if (f.exclude_text) parts.push(`Must NOT contain "${f.exclude_text}"`);
  if (f.media_types) parts.push(`Media: ${formatMediaDisplay(f.media_types)}`);
  if (f.regex_pattern) parts.push(`Match regex: ${f.regex_pattern}`);
  if (f.allowed_sender_ids?.trim()) parts.push(`Allowed senders (IDs): ${f.allowed_sender_ids.trim()}`);
  if (f.denied_usernames?.trim()) parts.push(`Denied usernames: ${f.denied_usernames.trim()}`);
  if (f.min_url_count != null || f.max_url_count != null) {
    parts.push(`URL count: min ${f.min_url_count ?? '—'} max ${f.max_url_count ?? '—'}`);
  }
  if (f.required_hashtags?.trim()) parts.push(`Required hashtags: ${f.required_hashtags.trim()}`);
  return parts;
}

function describeTransform(t: Transform): string {
  const typeLabels: Record<string, string> = {
    text: 'Text',
    regex: 'Regex',
    emoji: 'Emoji',
    media: 'Media',
    template: 'Template',
  };
  const label = typeLabels[t.rule_type] ?? t.rule_type;
  if (t.rule_type === 'text' || t.rule_type === 'emoji') {
    return `${label}: "${t.find_text ?? ''}" → "${t.replace_text ?? ''}"`;
  }
  if (t.rule_type === 'regex') {
    return `${label}: /${t.regex_pattern ?? ''}/ → "${t.replace_text ?? ''}"`;
  }
  if (t.rule_type === 'media') {
    return `${label}: asset #${t.replacement_media_asset_id} (${t.apply_to_media_types ?? 'all'})`;
  }
  if (t.rule_type === 'template') {
    return `${label}: "${(t.replace_text ?? '').slice(0, 40)}${(t.replace_text ?? '').length > 40 ? '…' : ''}"`;
  }
  return label;
}

export function MappingDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const { show: showToast } = useToast();
  const isAdminView = location.pathname.startsWith('/admin/mappings/');
  const tz = user?.timezone ?? Intl.DateTimeFormat().resolvedOptions().timeZone;
  const [filterModalOpen, setFilterModalOpen] = useState<'add' | number | null>(null);
  const [transformModalOpen, setTransformModalOpen] = useState<'add' | number | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null);
  const [transformDeleteConfirm, setTransformDeleteConfirm] = useState<number | null>(null);
  const [editingMapping, setEditingMapping] = useState<boolean>(false);
  const [mappingToDelete, setMappingToDelete] = useState<boolean>(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewSampleText, setPreviewSampleText] = useState('');
  const [previewMediaType, setPreviewMediaType] = useState('text');
  const [previewSenderId, setPreviewSenderId] = useState('');
  const [previewSenderUsername, setPreviewSenderUsername] = useState('');
  const [previewResult, setPreviewResult] = useState<MappingPreviewResponse | null>(null);
  const [previewError, setPreviewError] = useState('');
  const [previewLoading, setPreviewLoading] = useState(false);
  const [transformCreateSeed, setTransformCreateSeed] = useState<TransformCreate | null>(null);

  const canWrite = Boolean(user && user.role !== 'viewer');

  const { data: mapping } = useQuery({
    queryKey: ['mapping', id],
    queryFn: async () => (await api.get<ChannelMapping>(`/mappings/${id}`)).data,
    enabled: !!id,
  });
  const { data: filters } = useQuery({
    queryKey: ['mapping', id, 'filters'],
    queryFn: async () => (await api.get<Filter[]>(`/mappings/${id}/filters`)).data,
    enabled: !!id,
  });
  const { data: mappingSchedule } = useQuery({
    queryKey: ['mapping', id, 'schedule'],
    queryFn: async () => (await api.get<Record<string, string | null>>(`/mappings/${id}/schedule`)).data,
    enabled: !!id,
  });
  const { data: userSchedule } = useQuery({
    queryKey: ['user-schedule'],
    queryFn: async () => (await api.get<Record<string, string | null>>('/users/me/schedule')).data,
    enabled: !!id && !!user && mapping?.user_id === user.id,
  });
  const { data: transforms, isLoading: transformsLoading } = useQuery({
    queryKey: ['mapping', id, 'transforms'],
    queryFn: async () => (await api.get<Transform[]>(`/mappings/${id}/transforms`)).data,
    enabled: !!id,
  });
  const { data: mediaAssets } = useQuery({
    queryKey: ['media-assets', mapping?.user_id],
    queryFn: async () => {
      // Always filter by mapping owner: transforms require assets to belong to the mapping owner.
      // Without this, admins get all users' assets and the backend rejects non-owner assets with 400.
      const url =
        mapping?.user_id != null
          ? `/media-assets?user_id=${mapping.user_id}`
          : '/media-assets';
      return (await api.get(url)).data;
    },
    enabled: !!id && !!mapping,
  });

  const createMutation = useMutation({
    mutationFn: async (values: FilterFormValues) => {
      const body = filterValuesToApiBody(values);
      return (await api.post(`/mappings/${id}/filters`, body)).data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mapping', id, 'filters'] });
      setFilterModalOpen(null);
    },
    onError: (err: unknown) => {
      console.error(err);
    },
  });

  const updateMutation = useMutation({
    mutationFn: async ({
      filterId,
      values,
    }: {
      filterId: number;
      values: FilterFormValues;
    }) => {
      const body = filterValuesToApiBody(values);
      return (await api.patch(`/mappings/${id}/filters/${filterId}`, body)).data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mapping', id, 'filters'] });
      setFilterModalOpen(null);
    },
  });

  const filterDeleteMutation = useMutation({
    mutationFn: async (filterId: number) => {
      await api.delete(`/mappings/${id}/filters/${filterId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mapping', id, 'filters'] });
      setDeleteConfirm(null);
    },
  });

  const mappingDeleteMutation = useMutation({
    mutationFn: async () => {
      await api.delete(`/mappings/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mappings'] });
      setMappingToDelete(false);
      showToast('Mapping deleted. Workers restarting to apply changes.');
      navigate('/mappings');
    },
  });

  const enableMutation = useMutation({
    mutationFn: async (enabled: boolean) => {
      return (await api.patch<ChannelMapping>(`/mappings/${id}`, { enabled })).data;
    },
    onSuccess: (data, enabledFlag) => {
      if (data) {
        queryClient.setQueryData<ChannelMapping>(['mapping', id], data);
      }
      queryClient.invalidateQueries({ queryKey: ['mapping', id] });
      showToast(
        (enabledFlag ? 'Mapping enabled' : 'Mapping disabled') + '. Workers restarting to apply changes.'
      );
    },
  });

  const scheduleSaveMutation = useMutation({
    mutationFn: async (payload: Record<string, string | null>) => {
      await api.put(`/mappings/${id}/schedule`, payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mapping', id, 'schedule'] });
      queryClient.invalidateQueries({ queryKey: ['mappings'] });
      showToast('Schedule saved. Workers restarting to apply changes.');
    },
    onError: () => showToast('Failed to save schedule'),
  });

  const scheduleDeleteMutation = useMutation({
    mutationFn: async () => {
      await api.delete(`/mappings/${id}/schedule`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mapping', id, 'schedule'] });
      queryClient.invalidateQueries({ queryKey: ['mappings'] });
      showToast('Using default schedule. Workers restarting to apply changes.');
    },
    onError: () => showToast('Failed to remove schedule override'),
  });

  const transformCreateMutation = useMutation({
    mutationFn: async (payload: TransformCreate) => {
      return (await api.post(`/mappings/${id}/transforms`, payload)).data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mapping', id, 'transforms'] });
      setTransformCreateSeed(null);
      setTransformModalOpen(null);
      showToast('Transform added. Workers restarting to apply changes.');
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      showToast(msg ?? 'Failed to add transform');
    },
  });

  const transformUpdateMutation = useMutation({
    mutationFn: async ({ transformId, payload }: { transformId: number; payload: TransformCreate }) => {
      return (await api.patch(`/mappings/${id}/transforms/${transformId}`, payload)).data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mapping', id, 'transforms'] });
      setTransformCreateSeed(null);
      setTransformModalOpen(null);
      showToast('Transform updated. Workers restarting to apply changes.');
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      showToast(msg ?? 'Failed to update transform');
    },
  });

  const transformDeleteMutation = useMutation({
    mutationFn: async (transformId: number) => {
      await api.delete(`/mappings/${id}/transforms/${transformId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mapping', id, 'transforms'] });
      setTransformDeleteConfirm(null);
      showToast('Transform removed. Workers restarting to apply changes.');
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      showToast(msg ?? 'Failed to remove transform');
    },
  });

  const handleFilterSubmit = (values: FilterFormValues) => {
    if (filterModalOpen === 'add') {
      createMutation.mutate(values);
    } else if (typeof filterModalOpen === 'number') {
      updateMutation.mutate({ filterId: filterModalOpen, values });
    }
  };

  const handleTransformSubmit = (values: TransformCreate) => {
    if (transformModalOpen === 'add') {
      transformCreateMutation.mutate(values);
    } else if (typeof transformModalOpen === 'number') {
      transformUpdateMutation.mutate({ transformId: transformModalOpen, payload: values });
    }
  };

  const editingFilter = typeof filterModalOpen === 'number' ? filters?.find((f) => f.id === filterModalOpen) : null;
  const editingTransform = typeof transformModalOpen === 'number' ? transforms?.find((t) => t.id === transformModalOpen) : null;

  const mappingForEdit = mapping ? coerceChannelMappingForEdit(mapping) : null;

  const runPreview = async () => {
    if (!id) return;
    setPreviewError('');
    setPreviewLoading(true);
    setPreviewResult(null);
    try {
      const payload: Record<string, unknown> = {
        sample_text: previewSampleText,
        media_type: previewMediaType || 'text',
      };
      const sid = previewSenderId.trim();
      if (sid !== '') {
        const n = parseInt(sid, 10);
        if (!Number.isNaN(n)) payload.sender_id = n;
      }
      const su = previewSenderUsername.trim();
      if (su !== '') payload.sender_username = su;
      const { data } = await api.post<MappingPreviewResponse>(`/mappings/${id}/preview`, payload);
      setPreviewResult(data);
    } catch (e: unknown) {
      const msg =
        e && typeof e === 'object' && 'response' in e
          ? String((e as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? 'Preview failed')
          : 'Preview failed';
      setPreviewError(msg);
    } finally {
      setPreviewLoading(false);
    }
  };

  if (!mapping) return null;

  const sourceLabel = mapping.source_chat_title
    ? `${mapping.source_chat_title} (${mapping.source_chat_id})`
    : String(mapping.source_chat_id);
  const destLabel = mapping.dest_chat_title
    ? `${mapping.dest_chat_title} (${mapping.dest_chat_id})`
    : String(mapping.dest_chat_id);

  return (
    <div>
      <PageHeader
        title={mapping.name || `Mapping ${id}`}
        icon={GitBranch}
        subtitle={`Source: ${sourceLabel} → Dest: ${destLabel}`}
        actions={
          <div className="flex items-center gap-3">
            {canWrite ? (
              <button
                type="button"
                onClick={() => setEditingMapping(true)}
                className="flex items-center gap-2 text-sm text-blue-600 hover:underline"
              >
                <Pencil className="h-4 w-4" />
                Edit
              </button>
            ) : null}
            {canWrite ? (
              <button
                type="button"
                onClick={() => setMappingToDelete(true)}
                className="flex items-center gap-2 text-sm text-red-600 hover:underline"
              >
                <Trash2 className="h-4 w-4" />
                Delete
              </button>
            ) : null}
            <Link
              to={isAdminView ? '/admin/mappings' : '/mappings'}
              className="flex items-center gap-2 text-sm text-blue-600 hover:underline"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to mappings
            </Link>
          </div>
        }
      />

      {editingMapping && mappingForEdit && (
        <EditMappingDialog mapping={mappingForEdit} onClose={() => setEditingMapping(false)} />
      )}
      {mappingToDelete && (
        <ConfirmDialog
          title="Delete Channel Mapping"
          message={
            <>
              Are you sure you want to delete the mapping{' '}
              <span className="font-semibold">{mapping.name || `Mapping ${id}`}</span>? This will also
              remove all associated filters. This action cannot be undone.
            </>
          }
          confirmLabel="Delete mapping"
          variant="danger"
          icon={<Trash2 className="h-5 w-5 text-red-600" />}
          onConfirm={() => mappingDeleteMutation.mutate()}
          onCancel={() => setMappingToDelete(false)}
          isPending={mappingDeleteMutation.isPending}
        />
      )}
      {transformDeleteConfirm !== null && (
        <ConfirmDialog
          title="Delete transform"
          message="Are you sure you want to remove this transform rule? Workers will restart to apply the change."
          confirmLabel="Delete"
          variant="danger"
          icon={<Trash2 className="h-5 w-5 text-red-600" />}
          onConfirm={() => transformDeleteMutation.mutate(transformDeleteConfirm)}
          onCancel={() => setTransformDeleteConfirm(null)}
          isPending={transformDeleteMutation.isPending}
        />
      )}

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6 transition-shadow hover:shadow-lg">
        <dl className="grid grid-cols-2 gap-4">
          <div>
            <dt className="text-sm text-gray-500">Source channel</dt>
            <dd className="font-mono">{sourceLabel}</dd>
          </div>
          <div>
            <dt className="text-sm text-gray-500">Destination channel</dt>
            <dd className="font-mono">{destLabel}</dd>
          </div>
          <div>
            <dt className="text-sm text-gray-500">Status</dt>
            <dd>
              <MappingEnableToggle
                enabled={mapping.enabled}
                onToggle={() => enableMutation.mutate(!mapping.enabled)}
                isPending={enableMutation.isPending}
                disabled={!canWrite}
              />
            </dd>
          </div>
          <div>
            <dt className="text-sm text-gray-500">Send delay</dt>
            <dd className="font-mono text-sm">{mapping.send_delay_ms ?? 0} ms</dd>
          </div>
          <div>
            <dt className="text-sm text-gray-500">Sync edits / deletes</dt>
            <dd className="text-sm">
              {mapping.sync_edits ? 'Edits on' : 'Edits off'} · {mapping.sync_deletes ? 'Deletes on' : 'Deletes off'}{' '}
              · strategy: {mapping.edit_strategy || 'replace_text'}
            </dd>
          </div>
          <div className="col-span-2">
            <dt className="text-sm text-gray-500">Copy webhook</dt>
            <dd className="text-sm font-mono break-all">
              {mapping.copy_webhook_url?.trim() ? mapping.copy_webhook_url : '—'}
              {mapping.copy_webhook_secret ? ' · secret stored' : ''}
            </dd>
          </div>
        </dl>
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-600 flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={() => {
              setPreviewOpen(true);
              setPreviewResult(null);
              setPreviewError('');
            }}
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded border border-gray-300 dark:border-gray-600 text-sm hover:bg-gray-50 dark:hover:bg-gray-700"
          >
            <Eye className="h-4 w-4" />
            Preview pipeline
          </button>
          {!canWrite ? (
            <span className="text-xs text-gray-500 dark:text-gray-400">Viewer: mapping details are read-only.</span>
          ) : null}
        </div>
      </div>

      <div className="mb-4">
        <h2 className="text-lg font-semibold mb-1">Schedule</h2>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
          When to copy messages for this mapping. Use default (global) or set a custom schedule.
        </p>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden transition-shadow hover:shadow-lg mb-6">
        {(() => {
          const hasCustomSchedule =
            mappingSchedule && Object.values(mappingSchedule).some((v) => v != null && v !== '');
          const ownsMapping = user && mapping.user_id === user.id;

          if (hasCustomSchedule) {
            return (
              <div className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    Custom schedule for this mapping
                  </span>
                  <button
                    type="button"
                    onClick={() => scheduleDeleteMutation.mutate()}
                    disabled={scheduleDeleteMutation.isPending || !canWrite}
                    className="flex items-center gap-1 text-sm text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400"
                  >
                    <RotateCcw className="h-4 w-4" />
                    Switch to default
                  </button>
                </div>
                <MappingScheduleForm
                  initialSchedule={mappingSchedule}
                  timezone={tz}
                  onSave={(payload) => scheduleSaveMutation.mutate(payload)}
                  isSaving={scheduleSaveMutation.isPending}
                  saveLabel="Save schedule"
                  showDescription={false}
                  readOnly={!canWrite}
                />
              </div>
            );
          }

          return (
            <div className="p-6">
              <div className="flex flex-wrap items-center gap-3">
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4 text-gray-500" />
                  <span className="text-sm">
                    {ownsMapping && userSchedule
                      ? formatScheduleSummary(userSchedule)
                      : 'Default'}
                  </span>
                </div>
                {ownsMapping && (
                  <Link to="/schedule" className="text-sm text-blue-600 hover:underline">
                    Configure global schedule
                  </Link>
                )}
                <button
                  type="button"
                  disabled={!canWrite}
                  onClick={async () => {
                    const hasUserSchedule =
                      userSchedule && Object.values(userSchedule).some((v) => v != null && v !== '');
                    const payload = hasUserSchedule
                      ? userSchedule!
                      : {
                          mon_start_utc: '09:00',
                          mon_end_utc: '17:00',
                          tue_start_utc: '09:00',
                          tue_end_utc: '17:00',
                          wed_start_utc: '09:00',
                          wed_end_utc: '17:00',
                          thu_start_utc: '09:00',
                          thu_end_utc: '17:00',
                          fri_start_utc: '09:00',
                          fri_end_utc: '17:00',
                          sat_start_utc: null,
                          sat_end_utc: null,
                          sun_start_utc: null,
                          sun_end_utc: null,
                        };
                    await api.put(`/mappings/${id}/schedule`, payload);
                    queryClient.invalidateQueries({ queryKey: ['mapping', id, 'schedule'] });
                    queryClient.invalidateQueries({ queryKey: ['mappings'] });
                    showToast('Now using custom schedule. Edit below and save.');
                  }}
                  className="flex items-center gap-1 px-3 py-1.5 rounded border border-gray-300 dark:border-gray-600 text-sm hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
                >
                  Switch to custom
                </button>
              </div>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
                {ownsMapping
                  ? 'Uses your global schedule from the Schedule page.'
                  : "Uses the mapping owner's default schedule."}
              </p>
            </div>
          );
        })()}
      </div>

      <div className="mb-4">
        <h2 className="text-lg font-semibold mb-1">Transforms</h2>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
          Transform copied messages before sending: replace text, regex patterns, emojis; use templates; or replace media with uploaded assets. Rules are applied by priority (lower first).
        </p>
        <div className="flex flex-wrap items-center gap-2 mb-2">
          {canWrite ? (
            <button
              type="button"
              onClick={() => {
                setTransformCreateSeed(null);
                setTransformModalOpen('add');
              }}
              className="flex items-center gap-2 px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700 text-sm"
            >
              <Plus className="h-4 w-4" />
              Add transform
            </button>
          ) : null}
          {canWrite ? (
            <span className="text-xs text-gray-500 dark:text-gray-400 mr-1">PII presets (regex):</span>
          ) : null}
          {canWrite
            ? PII_TRANSFORM_PRESETS.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  title={p.description}
                  onClick={() => {
                    setTransformCreateSeed(p.payload);
                    setTransformModalOpen('add');
                  }}
                  className="px-2 py-1 text-xs rounded border border-amber-300 dark:border-amber-700 text-amber-900 dark:text-amber-100 bg-amber-50 dark:bg-amber-950/40 hover:bg-amber-100 dark:hover:bg-amber-900/50"
                >
                  {p.label}
                </button>
              ))
            : null}
        </div>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden transition-shadow hover:shadow-lg mb-6">
        {transformsLoading ? (
          <div className="p-8 animate-pulse">
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-4" />
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2 mb-4" />
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-5/6" />
          </div>
        ) : (
          <>
            <div className="divide-y divide-gray-200 dark:divide-gray-700">
              {(transforms ?? []).map((t) => (
                <div key={t.id} className="p-4 flex items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span
                        className={`text-xs font-medium px-2 py-0.5 rounded ${
                          !t.enabled ? 'bg-gray-200 dark:bg-gray-600 text-gray-600 dark:text-gray-400' : 'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300'
                        }`}
                      >
                        {t.rule_type}
                      </span>
                      <span className="text-xs text-gray-500 dark:text-gray-400">priority {t.priority}</span>
                    </div>
                    <p className="text-sm mt-1">{describeTransform(t)}</p>
                  </div>
                  <div className="flex gap-2 shrink-0">
                    {canWrite ? (
                      <button
                        type="button"
                        onClick={() => {
                          setTransformCreateSeed(null);
                          setTransformModalOpen(t.id);
                        }}
                        className="px-3 py-1 text-sm rounded border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700"
                      >
                        Edit
                      </button>
                    ) : null}
                    {canWrite ? (
                      <button
                        type="button"
                        onClick={() => setTransformDeleteConfirm(t.id)}
                        className="px-3 py-1 text-sm rounded border border-red-300 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 dark:border-red-800"
                      >
                        Delete
                      </button>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
            {(transforms ?? []).length === 0 && (
              <div className="p-8 text-center text-gray-500 dark:text-gray-400">
                No transforms. Messages are copied as-is.
                {canWrite ? (
                  <button
                    type="button"
                    onClick={() => {
                      setTransformCreateSeed(null);
                      setTransformModalOpen('add');
                    }}
                    className="ml-2 inline-flex items-center gap-1 text-blue-600 dark:text-blue-400 hover:underline"
                  >
                    <Plus className="h-4 w-4" /> Add your first transform
                  </button>
                ) : null}
              </div>
            )}
          </>
        )}
      </div>

      {transformModalOpen !== null && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
          role="dialog"
          aria-modal="true"
          aria-labelledby="transform-dialog-title"
          onClick={() => {
            setTransformCreateSeed(null);
            setTransformModalOpen(null);
          }}
          onKeyDown={(e) => {
            if (e.key === 'Escape') {
              setTransformCreateSeed(null);
              setTransformModalOpen(null);
            }
          }}
        >
          <div
            className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 max-w-lg w-full max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-2 mb-4">
              <Sparkles className="h-5 w-5 text-amber-600 dark:text-amber-400" />
              <h2 id="transform-dialog-title" className="text-xl font-bold">
                {transformModalOpen === 'add' ? 'Add transform' : 'Edit transform'}
              </h2>
            </div>
            <TransformForm
              key={
                transformModalOpen === 'add'
                  ? `new-${transformCreateSeed?.regex_pattern ?? 'plain'}`
                  : transformModalOpen
              }
              initialValues={editingTransform ?? undefined}
              createSeed={transformModalOpen === 'add' ? transformCreateSeed : null}
              mediaAssets={mediaAssets ?? []}
              onSubmit={handleTransformSubmit}
              onCancel={() => {
                setTransformCreateSeed(null);
                setTransformModalOpen(null);
              }}
              submitLabel={transformModalOpen === 'add' ? 'Add' : 'Save'}
              isSubmitting={transformCreateMutation.isPending || transformUpdateMutation.isPending}
            />
          </div>
        </div>
      )}

      <div className="mb-4">
        <h2 className="text-lg font-semibold mb-1">Filters</h2>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
          Filters determine which messages are copied from source to destination. Within one filter row, every rule
          must pass (AND). Filters that share the same OR group number match as OR (any of them can satisfy that
          group). Different OR group numbers are combined with AND (each group must be satisfied).
        </p>
        {canWrite ? (
          <button
            type="button"
            onClick={() => setFilterModalOpen('add')}
            className="flex items-center gap-2 px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700 text-sm"
          >
            <Plus className="h-4 w-4" />
            Add filter
          </button>
        ) : null}
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden transition-shadow hover:shadow-lg">
        <div className="divide-y divide-gray-200 dark:divide-gray-700">
          {(filters ?? []).map((f) => (
            <div key={f.id} className="p-4 flex items-start justify-between gap-4">
              <div className="min-w-0 flex-1">
                {describeFilter(f).length > 0 ? (
                  <ul className="text-sm space-y-0.5">
                    {describeFilter(f).map((line, i) => (
                      <li key={i}>{line}</li>
                    ))}
                  </ul>
                ) : (
                  <span className="text-gray-500 text-sm">No rules (all messages pass)</span>
                )}
              </div>
              <div className="flex gap-2 shrink-0">
                {canWrite ? (
                  <button
                    type="button"
                    onClick={() => setFilterModalOpen(f.id)}
                    className="px-3 py-1 text-sm rounded border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700"
                  >
                    Edit
                  </button>
                ) : null}
                {canWrite && deleteConfirm === f.id ? (
                  <div className="flex gap-1">
                    <button
                      type="button"
                      onClick={() => filterDeleteMutation.mutate(f.id)}
                      disabled={filterDeleteMutation.isPending}
                      className="px-3 py-1 text-sm rounded bg-red-600 text-white hover:bg-red-700 disabled:opacity-50"
                    >
                      Confirm
                    </button>
                    <button
                      type="button"
                      onClick={() => setDeleteConfirm(null)}
                      className="px-3 py-1 text-sm rounded border border-gray-300 dark:border-gray-600"
                    >
                      Cancel
                    </button>
                  </div>
                ) : canWrite ? (
                  <button
                    type="button"
                    onClick={() => setDeleteConfirm(f.id)}
                    className="px-3 py-1 text-sm rounded border border-red-300 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 dark:border-red-800"
                  >
                    Delete
                  </button>
                ) : null}
              </div>
            </div>
          ))}
        </div>
        {(filters ?? []).length === 0 && (
          <div className="p-8 text-center text-gray-500">
            No filters. All messages pass through.
            {canWrite ? (
              <button
                type="button"
                onClick={() => setFilterModalOpen('add')}
                className="ml-2 inline-flex items-center gap-1 text-blue-600 hover:underline"
              >
                <Plus className="h-4 w-4" /> Add your first filter
              </button>
            ) : null}
          </div>
        )}
      </div>

      {filterModalOpen !== null && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
          role="dialog"
          aria-modal="true"
          aria-labelledby="filter-dialog-title"
          onClick={() => setFilterModalOpen(null)}
          onKeyDown={(e) => e.key === 'Escape' && setFilterModalOpen(null)}
        >
          <div
            className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 max-w-lg w-full max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-2 mb-4">
              <Filter className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
              <h2 id="filter-dialog-title" className="text-xl font-bold">
                {filterModalOpen === 'add' ? 'Add filter' : 'Edit filter'}
              </h2>
            </div>
            <FilterForm
              key={filterModalOpen === 'add' ? 'new' : filterModalOpen}
              isSubmitting={createMutation.isPending || updateMutation.isPending}
              initialValues={
                editingFilter
                  ? {
                      include_text: editingFilter.include_text ?? '',
                      exclude_text: editingFilter.exclude_text ?? '',
                      media_types: stringToMediaArray(editingFilter.media_types),
                      regex_pattern: editingFilter.regex_pattern ?? '',
                      or_group_id: editingFilter.or_group_id,
                      allowed_sender_ids: editingFilter.allowed_sender_ids ?? '',
                      denied_usernames: editingFilter.denied_usernames ?? '',
                      min_url_count:
                        editingFilter.min_url_count != null ? String(editingFilter.min_url_count) : '',
                      max_url_count:
                        editingFilter.max_url_count != null ? String(editingFilter.max_url_count) : '',
                      required_hashtags: editingFilter.required_hashtags ?? '',
                    }
                  : undefined
              }
              onSubmit={handleFilterSubmit}
              onCancel={() => setFilterModalOpen(null)}
              submitLabel={filterModalOpen === 'add' ? 'Add' : 'Save'}
            />
          </div>
        </div>
      )}

      {previewOpen && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="preview-dialog-title"
          onClick={() => setPreviewOpen(false)}
          onKeyDown={(e) => e.key === 'Escape' && setPreviewOpen(false)}
        >
          <div
            className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 max-w-lg w-full max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 id="preview-dialog-title" className="text-xl font-bold mb-4 flex items-center gap-2">
              <Eye className="h-5 w-5" />
              Preview pipeline
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              Simulate one message through this mapping&apos;s filters, schedule check, and transforms (no Telegram send).
            </p>
            <div className="space-y-3 mb-4">
              <div>
                <label className="block text-sm font-medium mb-1">Sample text</label>
                <textarea
                  aria-label="Sample message text for preview"
                  value={previewSampleText}
                  onChange={(e) => setPreviewSampleText(e.target.value)}
                  rows={3}
                  className="w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-sm"
                />
              </div>
              <div>
                <label htmlFor="preview-media-type" className="block text-sm font-medium mb-1">
                  Media type
                </label>
                <select
                  id="preview-media-type"
                  value={previewMediaType}
                  onChange={(e) => setPreviewMediaType(e.target.value)}
                  className="w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-sm"
                >
                  {['text', 'photo', 'video', 'voice', 'other'].map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-sm font-medium mb-1">Sender ID (optional)</label>
                  <input
                    type="text"
                    value={previewSenderId}
                    onChange={(e) => setPreviewSenderId(e.target.value)}
                    className="w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-sm font-mono"
                    placeholder="numeric"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Sender username (optional)</label>
                  <input
                    type="text"
                    value={previewSenderUsername}
                    onChange={(e) => setPreviewSenderUsername(e.target.value)}
                    className="w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-sm"
                    placeholder="without @"
                  />
                </div>
              </div>
            </div>
            {previewError ? (
              <div className="mb-3 p-2 rounded bg-red-50 dark:bg-red-900/20 text-red-600 text-sm">{previewError}</div>
            ) : null}
            {previewResult ? (
              <dl className="text-sm space-y-1 mb-4 border border-gray-200 dark:border-gray-600 rounded p-3">
                <div className="flex justify-between gap-2">
                  <dt className="text-gray-500">Passes filters</dt>
                  <dd className="font-medium">{previewResult.passes_filters ? 'Yes' : 'No'}</dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-gray-500">Passes schedule</dt>
                  <dd className="font-medium">{previewResult.passes_schedule ? 'Yes' : 'No'}</dd>
                </div>
                <div>
                  <dt className="text-gray-500 mb-1">Transformed text</dt>
                  <dd className="font-mono text-xs whitespace-pre-wrap break-words bg-gray-50 dark:bg-gray-900/50 p-2 rounded">
                    {previewResult.transformed_text || '(empty)'}
                  </dd>
                </div>
              </dl>
            ) : null}
            <div className="flex flex-wrap gap-2 justify-end">
              <button
                type="button"
                onClick={() => setPreviewOpen(false)}
                className="px-4 py-2 rounded border border-gray-300 dark:border-gray-600"
              >
                Close
              </button>
              <button
                type="button"
                disabled={previewLoading}
                onClick={() => void runPreview()}
                className="px-4 py-2 rounded bg-blue-600 text-white disabled:opacity-50"
              >
                {previewLoading ? 'Running…' : 'Run preview'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
