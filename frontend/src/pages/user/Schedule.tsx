import { Clock, Copy } from 'lucide-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { PageHeader } from '../../components/PageHeader';
import { useToast } from '../../components/Toast';
import { MappingScheduleForm } from '../../components/MappingScheduleForm';
import { useAuth } from '../../store/AuthContext';

export function Schedule() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const { show: showToast } = useToast();
  const tz = user?.timezone ?? Intl.DateTimeFormat().resolvedOptions().timeZone;

  const { data: schedule, isLoading } = useQuery({
    queryKey: ['user-schedule'],
    queryFn: async () => (await api.get<Record<string, string | null>>('/users/me/schedule')).data,
  });

  const updateMutation = useMutation({
    mutationFn: async (payload: Record<string, string | null>) => {
      await api.patch('/users/me/schedule', payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user-schedule'] });
      showToast('Schedule saved');
    },
    onError: () => showToast('Failed to save schedule'),
  });

  const bulkApplyMutation = useMutation({
    mutationFn: async () => {
      const res = await api.post<{ updated: number }>('/mappings/schedule/bulk-apply');
      return res.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['mappings'] });
      showToast(`Applied to ${data.updated} mapping(s)`);
    },
    onError: () => showToast('Failed to apply'),
  });

  const hasAny =
    schedule && Object.values(schedule).some((v) => v != null && v !== '');
  const isEmptySchedule = !hasAny;

  if (isLoading) return <div className="animate-pulse h-32 bg-gray-200 dark:bg-gray-700 rounded" />;

  return (
    <div>
      <PageHeader
        title="Schedule"
        icon={Clock}
        subtitle="Set when messages are copied. No schedule = 24/7."
      />
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
        <MappingScheduleForm
          initialSchedule={schedule ?? undefined}
          timezone={tz}
          onSave={(payload) => updateMutation.mutate(payload)}
          isSaving={updateMutation.isPending}
          saveLabel="Save schedule"
          showDescription={true}
        />
        <div className="mt-4">
          <button
            type="button"
            onClick={() => bulkApplyMutation.mutate()}
            disabled={bulkApplyMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 rounded border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700"
          >
            <Copy className="h-4 w-4" />
            Apply to all mappings
          </button>
        </div>
      </div>
      {isEmptySchedule && (
        <div className="text-sm text-gray-500 dark:text-gray-400 p-3 rounded bg-gray-50 dark:bg-gray-800/50">
          No schedule set = copies 24/7. Add times above to restrict when messages are copied.
        </div>
      )}
    </div>
  );
}
