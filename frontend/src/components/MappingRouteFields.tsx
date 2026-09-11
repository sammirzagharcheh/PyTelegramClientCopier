import { Link } from 'react-router-dom';
import { useMemo, useState } from 'react';
import { SearchableChatSelect } from './SearchableChatSelect';
import { useActiveAccounts, formatAccountLabel } from '../hooks/useActiveAccounts';
import { useAccountDialogs } from '../hooks/useAccountDialogs';
import type { MappingRouteFieldErrors, MappingRouteValues } from '../lib/mappingValidation';

const inputClass =
  'w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700';

type Props = {
  values: MappingRouteValues;
  onChange: (values: MappingRouteValues) => void;
  errors?: MappingRouteFieldErrors;
  name: string;
  onNameChange: (value: string) => void;
  nameError?: string;
  initialSourceChatId?: number;
  initialDestChatId?: number;
  initialSourceTitle?: string | null;
  initialDestTitle?: string | null;
};

export function MappingRouteFields({
  values,
  onChange,
  errors = {},
  name,
  onNameChange,
  nameError,
  initialSourceChatId,
  initialDestChatId,
  initialSourceTitle,
  initialDestTitle,
}: Props) {
  const { data: accounts = [], isLoading: accountsLoading } = useActiveAccounts();
  const {
    data: dialogs = [],
    isLoading: dialogsLoading,
    isError: dialogsError,
    error: dialogsQueryError,
    refetch: refetchDialogs,
    isFetching: dialogsFetching,
  } = useAccountDialogs(values.telegramAccountId);

  const [accountConfirmPending, setAccountConfirmPending] = useState<number | null>(null);

  const dialogsErrorDetail = useMemo(() => {
    if (!dialogsQueryError || typeof dialogsQueryError !== 'object' || !('response' in dialogsQueryError)) {
      return null;
    }
    const resp = dialogsQueryError.response;
    if (!resp || typeof resp !== 'object' || !('data' in resp) || !('status' in resp)) return null;
    const data = resp.data as { detail?: unknown };
    const status = (resp as { status: number }).status;
    const detail = data?.detail != null ? String(data.detail) : 'Could not load chats';
    return { status, detail };
  }, [dialogsQueryError]);

  const sourceStale =
    values.telegramAccountId != null &&
    !values.useManualIds &&
    values.sourceChatId &&
    !dialogsLoading &&
    !dialogs.some((d) => String(d.chat_id) === values.sourceChatId);

  const destStale =
    values.telegramAccountId != null &&
    !values.useManualIds &&
    values.destChatId &&
    !dialogsLoading &&
    !dialogs.some((d) => String(d.chat_id) === values.destChatId);

  const handleAccountChange = (nextId: number) => {
    const hasRoute =
      values.sourceChatId.trim() !== '' ||
      values.destChatId.trim() !== '' ||
      (values.telegramAccountId != null && values.telegramAccountId !== nextId);
    if (hasRoute && values.telegramAccountId != null && values.telegramAccountId !== nextId) {
      setAccountConfirmPending(nextId);
      return;
    }
    applyAccountChange(nextId);
  };

  const applyAccountChange = (nextId: number) => {
    setAccountConfirmPending(null);
    onChange({
      ...values,
      telegramAccountId: nextId,
      sourceChatId: '',
      destChatId: '',
      sourceChatTitle: '',
      destChatTitle: '',
    });
  };

  const destExclude = values.sourceChatId ? [values.sourceChatId] : [];

  return (
    <div className="space-y-4">
      <div>
        <label htmlFor="mapping-name" className="block text-sm font-medium mb-1">
          Name (optional)
        </label>
        <input
          id="mapping-name"
          type="text"
          value={name}
          onChange={(e) => onNameChange(e.target.value)}
          className={inputClass}
          placeholder="Source to Dest"
          aria-invalid={!!nameError}
        />
        {nameError && <p className="text-xs text-red-600 mt-1">{nameError}</p>}
      </div>

      <div>
        <label htmlFor="mapping-account" className="block text-sm font-medium mb-1">
          Telegram account
        </label>
        {accountsLoading ? (
          <div className="h-10 animate-pulse rounded bg-gray-200 dark:bg-gray-700" />
        ) : accounts.length === 0 ? (
          <p className="text-sm text-gray-600 dark:text-gray-400">
            No active connected accounts.{' '}
            <Link to="/accounts" className="text-blue-600 hover:underline">
              Add an account
            </Link>
          </p>
        ) : (
          <select
            id="mapping-account"
            value={values.telegramAccountId ?? ''}
            onChange={(e) => {
              const v = e.target.value;
              if (!v) {
                onChange({ ...values, telegramAccountId: null });
                return;
              }
              handleAccountChange(Number(v));
            }}
            className={inputClass}
            aria-invalid={!!errors.telegramAccountId}
            required
          >
            <option value="">Select account…</option>
            {accounts.map((acc) => (
              <option key={acc.id} value={acc.id}>
                {formatAccountLabel(acc)} ({acc.type})
              </option>
            ))}
          </select>
        )}
        {errors.telegramAccountId && (
          <p className="text-xs text-red-600 mt-1">{errors.telegramAccountId}</p>
        )}
        {accountConfirmPending != null && (
          <div className="mt-2 p-3 rounded border border-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/20 text-sm">
            <p className="mb-2">Changing account clears source and destination. Continue?</p>
            <div className="flex gap-2">
              <button
                type="button"
                className="px-3 py-1 rounded bg-amber-600 text-white text-sm"
                onClick={() => applyAccountChange(accountConfirmPending)}
              >
                Yes, change account
              </button>
              <button
                type="button"
                className="px-3 py-1 rounded border border-gray-300 text-sm"
                onClick={() => setAccountConfirmPending(null)}
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>

      {values.telegramAccountId != null && (
        <>
          {dialogsError && dialogsErrorDetail && (
            <div className="p-3 rounded bg-red-50 dark:bg-red-900/20 text-red-600 text-sm space-y-2">
              <p>{dialogsErrorDetail.detail}</p>
              {dialogsErrorDetail.status === 409 && (
                <p>
                  <Link to="/workers" className="underline">
                    Stop the worker
                  </Link>{' '}
                  for this account, then retry.
                </p>
              )}
              <button
                type="button"
                className="text-sm underline"
                onClick={() => refetchDialogs()}
                disabled={dialogsFetching}
              >
                Retry
              </button>
            </div>
          )}

          {!values.useManualIds ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label htmlFor="mapping-source-chat" className="block text-sm font-medium mb-1">
                  Source chat
                </label>
                {dialogsLoading ? (
                  <div className="h-10 animate-pulse rounded bg-gray-200 dark:bg-gray-700" />
                ) : (
                  <SearchableChatSelect
                    id="mapping-source-chat"
                    aria-label="Source chat"
                    value={values.sourceChatId}
                    onChange={(id, chat) =>
                      onChange({
                        ...values,
                        sourceChatId: id,
                        sourceChatTitle: chat?.title ?? '',
                      })
                    }
                    chats={dialogs}
                    disabled={dialogsError}
                    staleChatId={
                      initialSourceChatId != null ? String(initialSourceChatId) : undefined
                    }
                    staleTitle={initialSourceTitle}
                    error={errors.sourceChatId}
                  />
                )}
                {sourceStale && (
                  <p className="text-xs text-amber-600 dark:text-amber-400 mt-1">
                    Chat not in latest list; re-select or use manual ID.
                  </p>
                )}
              </div>
              <div>
                <label htmlFor="mapping-dest-chat" className="block text-sm font-medium mb-1">
                  Destination chat
                </label>
                {dialogsLoading ? (
                  <div className="h-10 animate-pulse rounded bg-gray-200 dark:bg-gray-700" />
                ) : (
                  <SearchableChatSelect
                    id="mapping-dest-chat"
                    aria-label="Destination chat"
                    value={values.destChatId}
                    onChange={(id, chat) =>
                      onChange({
                        ...values,
                        destChatId: id,
                        destChatTitle: chat?.title ?? '',
                      })
                    }
                    chats={dialogs}
                    excludeChatIds={destExclude}
                    disabled={dialogsError}
                    staleChatId={
                      initialDestChatId != null ? String(initialDestChatId) : undefined
                    }
                    staleTitle={initialDestTitle}
                    error={errors.destChatId}
                  />
                )}
                {destStale && (
                  <p className="text-xs text-amber-600 dark:text-amber-400 mt-1">
                    Chat not in latest list; re-select or use manual ID.
                  </p>
                )}
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label htmlFor="mapping-source-id-manual" className="block text-sm font-medium mb-1">
                  Source Chat ID
                </label>
                <input
                  id="mapping-source-id-manual"
                  type="text"
                  value={values.sourceChatId}
                  onChange={(e) =>
                    onChange({
                      ...values,
                      sourceChatId: e.target.value,
                    })
                  }
                  className={inputClass}
                  placeholder="-1001234567890"
                  aria-invalid={!!errors.sourceChatId}
                />
                {errors.sourceChatId && (
                  <p className="text-xs text-red-600 mt-1">{errors.sourceChatId}</p>
                )}
              </div>
              <div>
                <label htmlFor="mapping-dest-id-manual" className="block text-sm font-medium mb-1">
                  Destination Chat ID
                </label>
                <input
                  id="mapping-dest-id-manual"
                  type="text"
                  value={values.destChatId}
                  onChange={(e) =>
                    onChange({
                      ...values,
                      destChatId: e.target.value,
                    })
                  }
                  className={inputClass}
                  placeholder="-1009876543210"
                  aria-invalid={!!errors.destChatId}
                />
                {errors.destChatId && (
                  <p className="text-xs text-red-600 mt-1">{errors.destChatId}</p>
                )}
              </div>
            </div>
          )}

          {!values.useManualIds && (
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={values.useManualIds}
                onChange={(e) => onChange({ ...values, useManualIds: e.target.checked })}
                className="rounded border-gray-300"
              />
              Enter chat ID manually instead
            </label>
          )}
          {values.useManualIds && (
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={values.useManualIds}
                onChange={(e) => onChange({ ...values, useManualIds: e.target.checked })}
                className="rounded border-gray-300"
              />
              Use chat picker from account
            </label>
          )}
        </>
      )}
    </div>
  );
}
