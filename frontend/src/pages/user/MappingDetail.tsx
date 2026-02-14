import { ArrowLeft, Clock, Filter, GitBranch, Pencil, Plus, RotateCcw, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams, Link, useNavigate, useLocation } from 'react-router-dom';
import { api } from '../../lib/api';
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
import { formatScheduleSummary } from '../../lib/formatDateTime';

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

export function MappingDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const { show: showToast } = useToast();
  const isAdminView = location.pathname.startsWith('/admin/mappings/');
  const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
  const [filterModalOpen, setFilterModalOpen] = useState<'add' | number | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null);
  const [editingMapping, setEditingMapping] = useState<boolean>(false);
  const [mappingToDelete, setMappingToDelete] = useState<boolean>(false);

  const { data: mapping } = useQuery({
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
      showToast('Mapping deleted. Workers restarting to apply changes.');
      navigate('/mappings');
    },
  });

  const enableMutation = useMutation({
    mutationFn: async (enabled: boolean) => {
      return (await api.patch(`/mappings/${id}`, { enabled })).data;
    },
    onSuccess: (enabled) => {
      queryClient.invalidateQueries({ queryKey: ['mapping', id] });
      showToast(
        (enabled ? 'Mapping enabled' : 'Mapping disabled') + '. Workers restarting to apply changes.'
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

  const handleFilterSubmit = (values: FilterFormValues) => {
    if (filterModalOpen === 'add') {
      createMutation.mutate(values);
    } else if (typeof filterModalOpen === 'number') {
      updateMutation.mutate({ filterId: filterModalOpen, values });
    }
  };

  const editingFilter = typeof filterModalOpen === 'number' ? filters?.find((f) => f.id === filterModalOpen) : null;

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
            <button
              type="button"
              onClick={() => setEditingMapping(true)}
              className="flex items-center gap-2 text-sm text-blue-600 hover:underline"
            >
              <Pencil className="h-4 w-4" />
              Edit
            </button>
            <button
              type="button"
              onClick={() => setMappingToDelete(true)}
              className="flex items-center gap-2 text-sm text-red-600 hover:underline"
            >
              <Trash2 className="h-4 w-4" />
              Delete
            </button>
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
              />
            </dd>
          </div>
        </dl>
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
                    disabled={scheduleDeleteMutation.isPending}
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
                  className="flex items-center gap-1 px-3 py-1.5 rounded border border-gray-300 dark:border-gray-600 text-sm hover:bg-gray-50 dark:hover:bg-gray-700"
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
        <h2 className="text-lg font-semibold mb-1">Filters</h2>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
          Filters determine which messages are copied from source to destination. All rules in each filter must pass
          (AND). With multiple filters, a message is copied if it passes every filter.
        </p>
        <button
          type="button"
          onClick={() => setFilterModalOpen('add')}
          className="flex items-center gap-2 px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700 text-sm"
        >
          <Plus className="h-4 w-4" />
          Add filter
        </button>
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
                <button
                  type="button"
                  onClick={() => setFilterModalOpen(f.id)}
                  className="px-3 py-1 text-sm rounded border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700"
                >
                  Edit
                </button>
                {deleteConfirm === f.id ? (
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
                ) : (
                  <button
                    type="button"
                    onClick={() => setDeleteConfirm(f.id)}
                    className="px-3 py-1 text-sm rounded border border-red-300 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 dark:border-red-800"
                  >
                    Delete
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
        {(filters ?? []).length === 0 && (
          <div className="p-8 text-center text-gray-500">
            No filters. All messages pass through.
            <button
              type="button"
              onClick={() => setFilterModalOpen('add')}
              className="ml-2 inline-flex items-center gap-1 text-blue-600 hover:underline"
            >
              <Plus className="h-4 w-4" /> Add your first filter
            </button>
          </div>
        )}
      </div>

      {filterModalOpen !== null && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
          onClick={() => setFilterModalOpen(null)}
        >
          <div
            className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 max-w-md w-full"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-2 mb-4">
              <Filter className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
              <h2 className="text-xl font-bold">
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
    </div>
  );
}
