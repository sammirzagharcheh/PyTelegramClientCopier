import { ArrowLeft, Clock, Filter, GitBranch, Pencil, Plus, RotateCcw, Sparkles, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { api } from '../../lib/api';
import type { FilterFormValues } from '../../components/FilterForm';
import { EditMappingDialog } from '../../components/EditMappingDialog';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { MappingEnableToggle } from '../../components/MappingEnableToggle';
import { MappingScheduleForm } from '../../components/MappingScheduleForm';
import { useToast } from '../../components/Toast';
import { PageHeader } from '../../components/PageHeader';
import { useAuth } from '../../store/AuthContext';
import { FilterForm } from '../../components/FilterForm';
import {
  formatMediaDisplay,
  mediaArrayToString,
  stringToMediaArray,
} from '../../lib/mediaTypes';
import { TransformForm } from '../../components/TransformForm';
import { formatScheduleSummary } from '../../lib/formatDateTime';
import type { Transform, TransformCreate } from '../../lib/api';
import { CardSkeleton } from '../../components/Skeleton';
import { Button, ButtonLink } from '../../components/ui/Button';
import { Card, CardHeader } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Modal } from '../../components/ui/Modal';
import { EmptyState, ErrorState } from '../../components/ui/States';
import { errorMessage } from '../../lib/apiError';

type Filter = {
  id: number;
  mapping_id: number;
  include_text: string | null;
  exclude_text: string | null;
  media_types: string | null;
  regex_pattern: string | null;
};

function describeFilter(f: Filter): string[] {
  const parts: string[] = [];
  if (f.include_text) parts.push(`Must contain "${f.include_text}"`);
  if (f.exclude_text) parts.push(`Must NOT contain "${f.exclude_text}"`);
  if (f.media_types) parts.push(`Media: ${formatMediaDisplay(f.media_types)}`);
  if (f.regex_pattern) parts.push(`Match regex: ${f.regex_pattern}`);
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

  const {
    data: mapping,
    isLoading: mappingLoading,
    isError: mappingError,
    error: mappingLoadError,
    refetch: refetchMapping,
  } = useQuery({
    queryKey: ['mapping', id],
    queryFn: async () => (await api.get(`/mappings/${id}`)).data,
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
      return (
        await api.post(`/mappings/${id}/filters`, {
          include_text: values.include_text || null,
          exclude_text: values.exclude_text || null,
          media_types: mediaArrayToString(values.media_types) || null,
          regex_pattern: values.regex_pattern || null,
        })
      ).data;
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
      return (
        await api.patch(`/mappings/${id}/filters/${filterId}`, {
          include_text: values.include_text || null,
          exclude_text: values.exclude_text || null,
          media_types: mediaArrayToString(values.media_types) || null,
          regex_pattern: values.regex_pattern || null,
        })
      ).data;
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
      showToast('Mapping deleted. Workers are restarting to apply it.', 'success');
      navigate(isAdminView ? '/admin/mappings' : '/mappings');
    },
  });

  const enableMutation = useMutation({
    mutationFn: async (enabled: boolean) => {
      return (await api.patch(`/mappings/${id}`, { enabled })).data;
    },
    onSuccess: (enabled) => {
      queryClient.invalidateQueries({ queryKey: ['mapping', id] });
      showToast(
        (enabled ? 'Mapping enabled' : 'Mapping disabled') +
          '. Workers are restarting to apply it.',
        'success'
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
      showToast('Schedule saved. Workers are restarting to apply it.', 'success');
    },
    onError: () => showToast('Saving the schedule failed', 'error'),
  });

  const scheduleDeleteMutation = useMutation({
    mutationFn: async () => {
      await api.delete(`/mappings/${id}/schedule`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mapping', id, 'schedule'] });
      queryClient.invalidateQueries({ queryKey: ['mappings'] });
      showToast('Using the default schedule. Workers are restarting to apply it.', 'success');
    },
    onError: () => showToast('Removing the schedule override failed', 'error'),
  });

  const transformCreateMutation = useMutation({
    mutationFn: async (payload: TransformCreate) => {
      return (await api.post(`/mappings/${id}/transforms`, payload)).data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mapping', id, 'transforms'] });
      setTransformModalOpen(null);
      showToast('Transform added. Workers are restarting to apply it.', 'success');
    },
    onError: (err: unknown) => {
      showToast(errorMessage(err, 'Adding the transform failed'), 'error');
    },
  });

  const transformUpdateMutation = useMutation({
    mutationFn: async ({ transformId, payload }: { transformId: number; payload: TransformCreate }) => {
      return (await api.patch(`/mappings/${id}/transforms/${transformId}`, payload)).data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mapping', id, 'transforms'] });
      setTransformModalOpen(null);
      showToast('Transform updated. Workers are restarting to apply it.', 'success');
    },
    onError: (err: unknown) => {
      showToast(errorMessage(err, 'Updating the transform failed'), 'error');
    },
  });

  const transformDeleteMutation = useMutation({
    mutationFn: async (transformId: number) => {
      await api.delete(`/mappings/${id}/transforms/${transformId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mapping', id, 'transforms'] });
      setTransformDeleteConfirm(null);
      showToast('Transform removed. Workers are restarting to apply it.', 'success');
    },
    onError: (err: unknown) => {
      showToast(errorMessage(err, 'Removing the transform failed'), 'error');
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

  const mappingForEdit = mapping
    ? {
        id: mapping.id,
        user_id: mapping.user_id,
        source_chat_id: mapping.source_chat_id,
        dest_chat_id: mapping.dest_chat_id,
        name: mapping.name,
        source_chat_title: mapping.source_chat_title,
        dest_chat_title: mapping.dest_chat_title,
        enabled: mapping.enabled,
      }
    : null;

  if (mappingError) {
    return (
      <ErrorState
        title="We couldn't load this mapping"
        error={mappingLoadError}
        onRetry={() => refetchMapping()}
      />
    );
  }

  if (mappingLoading || !mapping) {
    return (
      <div className="space-y-4">
        <CardSkeleton lines={2} />
        <CardSkeleton lines={4} />
        <CardSkeleton lines={3} />
      </div>
    );
  }

  const sourceLabel = mapping.source_chat_title
    ? `${mapping.source_chat_title} (${mapping.source_chat_id})`
    : String(mapping.source_chat_id);
  const destLabel = mapping.dest_chat_title
    ? `${mapping.dest_chat_title} (${mapping.dest_chat_id})`
    : String(mapping.dest_chat_id);

  const hasCustomSchedule =
    mappingSchedule && Object.values(mappingSchedule).some((v) => v != null && v !== '');
  const ownsMapping = Boolean(user && mapping.user_id === user.id);
  const listPath = isAdminView ? '/admin/mappings' : '/mappings';

  const switchToCustom = async () => {
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
    showToast('Now using a custom schedule. Edit below and save.', 'success');
  };

  return (
    <div>
      <PageHeader
        title={mapping.name || `Mapping ${id}`}
        icon={GitBranch}
        subtitle={`Source: ${sourceLabel} to dest: ${destLabel}`}
        actions={
          <>
            <Button variant="secondary" size="sm" icon={Pencil} onClick={() => setEditingMapping(true)}>
              Edit
            </Button>
            <Button variant="secondary" size="sm" icon={Trash2} onClick={() => setMappingToDelete(true)}>
              Delete
            </Button>
            <ButtonLink to={listPath} size="sm" icon={ArrowLeft}>
              Back to mappings
            </ButtonLink>
          </>
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
              Deleting{' '}
              <span className="font-medium text-ink">{mapping.name || `Mapping ${id}`}</span> also
              removes all of its filters and transformations. This cannot be undone.
            </>
          }
          confirmLabel="Delete mapping"
          variant="danger"
          icon={<Trash2 className="h-5 w-5" />}
          onConfirm={() => mappingDeleteMutation.mutate()}
          onCancel={() => setMappingToDelete(false)}
          isPending={mappingDeleteMutation.isPending}
        />
      )}
      {transformDeleteConfirm !== null && (
        <ConfirmDialog
          title="Delete transform"
          message="Removing this transform rule will restart workers so the change takes effect."
          confirmLabel="Delete"
          variant="danger"
          icon={<Trash2 className="h-5 w-5" />}
          onConfirm={() => transformDeleteMutation.mutate(transformDeleteConfirm)}
          onCancel={() => setTransformDeleteConfirm(null)}
          isPending={transformDeleteMutation.isPending}
        />
      )}
      {deleteConfirm !== null && (
        <ConfirmDialog
          title="Delete filter"
          message="Messages that only this filter was holding back will start copying again."
          confirmLabel="Delete"
          variant="danger"
          icon={<Trash2 className="h-5 w-5" />}
          onConfirm={() => filterDeleteMutation.mutate(deleteConfirm)}
          onCancel={() => setDeleteConfirm(null)}
          isPending={filterDeleteMutation.isPending}
        />
      )}

      <Card className="mb-4">
        <dl className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-ink-subtle">Source channel</dt>
            <dd className="mt-1 font-mono text-sm text-ink">{sourceLabel}</dd>
          </div>
          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-ink-subtle">Destination channel</dt>
            <dd className="mt-1 font-mono text-sm text-ink">{destLabel}</dd>
          </div>
          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-ink-subtle">Status</dt>
            <dd className="mt-1">
              <MappingEnableToggle
                enabled={mapping.enabled}
                onToggle={() => enableMutation.mutate(!mapping.enabled)}
                isPending={enableMutation.isPending}
              />
            </dd>
          </div>
        </dl>
      </Card>

      <Card className="mb-4">
        <CardHeader
          title="Schedule"
          icon={Clock}
          description="When to copy messages for this mapping. Use the default (global) schedule, or set a custom one."
        />
        {hasCustomSchedule ? (
          <div>
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <span className="text-sm font-medium text-ink">Custom schedule for this mapping</span>
              <Button
                variant="ghost"
                size="sm"
                icon={RotateCcw}
                onClick={() => scheduleDeleteMutation.mutate()}
                disabled={scheduleDeleteMutation.isPending}
                isLoading={scheduleDeleteMutation.isPending}
              >
                Switch to default
              </Button>
            </div>
            <MappingScheduleForm
              initialSchedule={mappingSchedule}
              timezone={tz}
              onSave={(payload) => scheduleSaveMutation.mutate(payload)}
              isSaving={scheduleSaveMutation.isPending}
              saveLabel="Save schedule"
              showDescription={false}
            />
          </div>
        ) : (
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <div className="flex items-center gap-2 text-sm text-ink">
                <Clock className="h-4 w-4 text-ink-subtle" aria-hidden />
                <span>
                  {ownsMapping && userSchedule ? formatScheduleSummary(userSchedule) : 'Default'}
                </span>
              </div>
              {ownsMapping && (
                <ButtonLink to="/schedule" variant="ghost" size="sm">
                  Configure global schedule
                </ButtonLink>
              )}
              <Button variant="secondary" size="sm" onClick={() => void switchToCustom()}>
                Switch to custom
              </Button>
            </div>
            <p className="mt-2 text-sm text-ink-subtle">
              {ownsMapping
                ? 'Uses your global schedule from the Schedule page.'
                : "Uses the mapping owner's default schedule."}
            </p>
          </div>
        )}
      </Card>

      <Card flush className="mb-4">
        <CardHeader
          title="Transforms"
          icon={Sparkles}
          description="Rewrite copied messages before they are sent: replace text, regex, or emoji; apply a template; or swap media for an uploaded asset. Rules run by priority, lowest first."
          actions={
            <Button size="sm" icon={Plus} onClick={() => setTransformModalOpen('add')}>
              Add transform
            </Button>
          }
          inset
        />
        {transformsLoading ? (
          <div className="px-5 py-6">
            <CardSkeleton lines={3} className="border-0 p-0 shadow-none" />
          </div>
        ) : (transforms ?? []).length === 0 ? (
          <EmptyState
            icon={Sparkles}
            title="No transforms"
            description="Messages are copied as they arrived. Add a rule to rewrite text, emoji, or media."
            action={
              <Button size="sm" icon={Plus} onClick={() => setTransformModalOpen('add')}>
                Add your first transform
              </Button>
            }
          />
        ) : (
          <ul className="divide-y divide-line">
            {(transforms ?? []).map((t) => (
              <li key={t.id} className="flex items-start justify-between gap-4 px-5 py-3.5">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone={t.enabled ? 'info' : 'neutral'}>{t.rule_type}</Badge>
                    <span className="text-xs tabular-nums text-ink-subtle">priority {t.priority}</span>
                  </div>
                  <p className="mt-1 text-sm text-ink">{describeTransform(t)}</p>
                </div>
                <div className="flex shrink-0 gap-2">
                  <Button variant="secondary" size="sm" onClick={() => setTransformModalOpen(t.id)}>
                    Edit
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => setTransformDeleteConfirm(t.id)}
                  >
                    Delete
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>

      {transformModalOpen !== null && (
        <Modal
          title={transformModalOpen === 'add' ? 'Add transform' : 'Edit transform'}
          icon={<Sparkles className="h-5 w-5" />}
          onClose={() => setTransformModalOpen(null)}
          size="lg"
        >
          <TransformForm
            key={transformModalOpen === 'add' ? 'new' : transformModalOpen}
            initialValues={editingTransform ?? undefined}
            mediaAssets={mediaAssets ?? []}
            onSubmit={handleTransformSubmit}
            onCancel={() => setTransformModalOpen(null)}
            submitLabel={transformModalOpen === 'add' ? 'Add' : 'Save'}
            isSubmitting={transformCreateMutation.isPending || transformUpdateMutation.isPending}
          />
        </Modal>
      )}

      <Card flush>
        <CardHeader
          title="Filters"
          icon={Filter}
          description="Filters decide which messages are copied. Every rule in a filter must pass (AND). With several filters, a message is copied only if it passes every one of them."
          actions={
            <Button size="sm" icon={Plus} onClick={() => setFilterModalOpen('add')}>
              Add filter
            </Button>
          }
          inset
        />
        {(filters ?? []).length === 0 ? (
          <EmptyState
            icon={Filter}
            title="No filters"
            description="All messages pass through. Add a filter to include or exclude by text, media type, or regex."
            action={
              <Button size="sm" icon={Plus} onClick={() => setFilterModalOpen('add')}>
                Add your first filter
              </Button>
            }
          />
        ) : (
          <ul className="divide-y divide-line">
            {(filters ?? []).map((f) => {
              const lines = describeFilter(f);
              return (
                <li key={f.id} className="flex items-start justify-between gap-4 px-5 py-3.5">
                  <div className="min-w-0 flex-1">
                    {lines.length > 0 ? (
                      <ul className="space-y-0.5 text-sm text-ink">
                        {lines.map((line) => (
                          <li key={line}>{line}</li>
                        ))}
                      </ul>
                    ) : (
                      <span className="text-sm text-ink-subtle">No rules (all messages pass)</span>
                    )}
                  </div>
                  <div className="flex shrink-0 gap-2">
                    <Button variant="secondary" size="sm" onClick={() => setFilterModalOpen(f.id)}>
                      Edit
                    </Button>
                    <Button variant="secondary" size="sm" onClick={() => setDeleteConfirm(f.id)}>
                      Delete
                    </Button>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </Card>

      {filterModalOpen !== null && (
        <Modal
          title={filterModalOpen === 'add' ? 'Add filter' : 'Edit filter'}
          icon={<Filter className="h-5 w-5" />}
          onClose={() => setFilterModalOpen(null)}
          size="sm"
        >
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
                  }
                : undefined
            }
            onSubmit={handleFilterSubmit}
            onCancel={() => setFilterModalOpen(null)}
            submitLabel={filterModalOpen === 'add' ? 'Add' : 'Save'}
          />
        </Modal>
      )}
    </div>
  );
}
