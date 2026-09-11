import { Clock, Copy } from 'lucide-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { PageHeader } from '../../components/PageHeader';
import { useToast } from '../../components/Toast';
import { MappingScheduleForm } from '../../components/MappingScheduleForm';
import { useAuth } from '../../store/AuthContext';
import { CardSkeleton } from '../../components/Skeleton';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { ErrorState } from '../../components/ui/States';

export function Schedule() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const { show: showToast } = useToast();
  const tz = user?.timezone ?? Intl.DateTimeFormat().resolvedOptions().timeZone;

  const { data: schedule, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['user-schedule'],
    queryFn: async () => (await api.get<Record<string, string | null>>('/users/me/schedule')).data,
  });

  const updateMutation = useMutation({
    mutationFn: async (payload: Record<string, string | null>) => {
      await api.patch('/users/me/schedule', payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user-schedule'] });
      showToast('Schedule saved', 'success');
    },
    onError: () => showToast('Saving the schedule failed', 'error'),
  });

  const bulkApplyMutation = useMutation({
    mutationFn: async () => {
      const res = await api.post<{ updated: number }>('/mappings/schedule/bulk-apply');
      return res.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['mappings'] });
      showToast(
        `Schedule applied to ${data.updated} ${data.updated === 1 ? 'mapping' : 'mappings'}`,
        'success'
      );
    },
    onError: () => showToast('Applying the schedule failed', 'error'),
  });

  const hasAny =
    schedule && Object.values(schedule).some((v) => v != null && v !== '');
  const isEmptySchedule = !hasAny;

  return (
    <div className="max-w-3xl">
      <PageHeader
        title="Schedule"
        icon={Clock}
        subtitle="Set the hours when messages are copied. With no schedule, copying runs 24/7."
      />

      {isError ? (
        <ErrorState title="We couldn't load your schedule" error={error} onRetry={() => refetch()} />
      ) : isLoading ? (
        <CardSkeleton lines={5} />
      ) : (
        <>
          <Card>
            <MappingScheduleForm
              initialSchedule={schedule ?? undefined}
              timezone={tz}
              onSave={(payload) => updateMutation.mutate(payload)}
              isSaving={updateMutation.isPending}
              saveLabel="Save schedule"
              showDescription={true}
            />
            <div className="mt-5 border-t border-line pt-4">
              <Button
                variant="secondary"
                icon={Copy}
                onClick={() => bulkApplyMutation.mutate()}
                isLoading={bulkApplyMutation.isPending}
              >
                Apply to all mappings
              </Button>
              <p className="mt-2 text-xs text-ink-subtle">
                Overwrites the schedule on every mapping you own with the one above.
              </p>
            </div>
          </Card>
          {isEmptySchedule && (
            <p className="mt-4 rounded-control bg-surface-sunken px-4 py-3 text-sm text-ink-muted">
              No schedule is set, so messages are copied 24/7. Add times above to restrict when
              copying runs.
            </p>
          )}
        </>
      )}
    </div>
  );
}
