import { KeyRound, Smartphone, Upload } from 'lucide-react';
import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';
import { Button } from './ui/Button';
import { Field, Input, Select } from './ui/Field';
import { FormError } from './ui/FormError';
import { Modal } from './ui/Modal';
import { errorMessage } from '../lib/apiError';

type Props = {
  onClose: () => void;
};

type Mode = 'phone' | 'upload';

/** Reads the structured `detail` object FastAPI returns for the 2FA challenge. */
function readDetail(err: unknown): { code?: string; message?: string } | string | undefined {
  if (
    err &&
    typeof err === 'object' &&
    'response' in err &&
    err.response &&
    typeof err.response === 'object' &&
    'data' in err.response &&
    err.response.data &&
    typeof err.response.data === 'object' &&
    'detail' in err.response.data
  ) {
    return (err.response.data as { detail: { code?: string; message?: string } | string }).detail;
  }
  return undefined;
}

export function AddAccountDialog({ onClose }: Props) {
  const [name, setName] = useState('');
  const [type, setType] = useState<'user' | 'bot'>('user');
  const [mode, setMode] = useState<Mode>('phone');
  const [botToken, setBotToken] = useState('');
  const [sessionFile, setSessionFile] = useState<File | null>(null);
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [loginSessionId, setLoginSessionId] = useState<number | null>(null);
  const [step, setStep] = useState<'method' | 'phone' | 'code'>('method');
  const [password, setPassword] = useState('');
  const [needsPassword, setNeedsPassword] = useState(false);
  const [error, setError] = useState('');
  const queryClient = useQueryClient();

  const uploadMutation = useMutation({
    mutationFn: async () => {
      const formData = new FormData();
      formData.append('name', name || 'Account');
      formData.append('type', type);
      if (type === 'bot') {
        formData.append('bot_token', botToken);
      } else if (sessionFile) {
        formData.append('session_file', sessionFile);
      }
      return (
        await api.post('/accounts', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })
      ).data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
      onClose();
    },
    onError: (err: unknown) => {
      setError(errorMessage(err, 'We could not add this account.'));
    },
  });

  const beginLoginMutation = useMutation({
    mutationFn: async () => {
      const { data } = await api.post<{ login_session_id: number }>('/accounts/login/begin', {
        phone,
      });
      return data;
    },
    onSuccess: (data) => {
      setLoginSessionId(data.login_session_id);
      setStep('code');
      setError('');
    },
    onError: (err: unknown) => {
      setError(errorMessage(err, 'We could not send a login code to that number.'));
    },
  });

  const completeLoginMutation = useMutation({
    mutationFn: async () => {
      const { data } = await api.post('/accounts/login/complete', {
        login_session_id: loginSessionId,
        code,
        password: needsPassword ? password : undefined,
        account_name: name || undefined,
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
      onClose();
    },
    onError: (err: unknown) => {
      const detail = readDetail(err);

      if (detail && typeof detail === 'object' && detail.code === '2FA_REQUIRED') {
        setNeedsPassword(true);
        setError(detail.message || 'This account needs its two-factor password.');
        return;
      }

      if (detail && typeof detail === 'object' && detail.message) {
        setError(detail.message);
        return;
      }

      setError(errorMessage(err, 'Login failed.'));
    },
  });

  const cancelLoginMutation = useMutation({
    mutationFn: async () => {
      if (!loginSessionId) return;
      await api.post('/accounts/login/cancel', { login_session_id: loginSessionId });
    },
    onSuccess: () => {
      setLoginSessionId(null);
      setPhone('');
      setCode('');
      setPassword('');
      setNeedsPassword(false);
      setStep('method');
      setError('');
    },
  });

  const handleUploadSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (type === 'user' && !sessionFile) {
      setError('Choose a .session file to upload.');
      return;
    }
    if (type === 'bot' && !botToken) {
      setError('Enter the bot token.');
      return;
    }
    uploadMutation.mutate();
  };

  const showUploadForm =
    type === 'bot' || (type === 'user' && (mode === 'upload' || (step !== 'phone' && step !== 'code')));

  const renderUserPhoneFlow = () => {
    if (step === 'method') {
      return (
        <fieldset className="space-y-2">
          <legend className="mb-2 text-sm font-medium text-ink">
            How do you want to connect this account?
          </legend>
          <button
            type="button"
            onClick={() => {
              setMode('phone');
              setStep('phone');
            }}
            className="flex w-full items-start gap-3 rounded-control border border-line-strong px-3 py-3 text-left transition-colors hover:border-accent hover:bg-accent-soft/50"
          >
            <KeyRound className="mt-0.5 h-4 w-4 shrink-0 text-accent-ink" aria-hidden />
            <span>
              <span className="block text-sm font-medium text-ink">Phone and login code</span>
              <span className="block text-xs text-ink-subtle">
                Recommended. Telegram sends a code to the number.
              </span>
            </span>
          </button>
          <button
            type="button"
            onClick={() => {
              setMode('upload');
              setStep('method');
            }}
            className="flex w-full items-start gap-3 rounded-control border border-line-strong px-3 py-3 text-left transition-colors hover:border-accent hover:bg-accent-soft/50"
          >
            <Upload className="mt-0.5 h-4 w-4 shrink-0 text-ink-subtle" aria-hidden />
            <span>
              <span className="block text-sm font-medium text-ink">Upload a .session file</span>
              <span className="block text-xs text-ink-subtle">
                Advanced. For sessions created outside this app.
              </span>
            </span>
          </button>
        </fieldset>
      );
    }

    if (step === 'phone') {
      return (
        <div className="space-y-4">
          <Field label="Phone number" hint="Include the country code." required>
            {(fieldProps) => (
              <Input
                {...fieldProps}
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="+14155551234"
                required
              />
            )}
          </Field>
          <div className="flex flex-wrap justify-end gap-2">
            <Button variant="ghost" onClick={() => setStep('method')}>
              Back
            </Button>
            {loginSessionId && (
              <Button
                variant="secondary"
                onClick={() => cancelLoginMutation.mutate()}
                isLoading={cancelLoginMutation.isPending}
              >
                Cancel login
              </Button>
            )}
            <Button
              onClick={() => {
                setError('');
                beginLoginMutation.mutate();
              }}
              isLoading={beginLoginMutation.isPending}
            >
              Send code
            </Button>
          </div>
        </div>
      );
    }

    if (step === 'code') {
      return (
        <div className="space-y-4">
          <Field
            label="Login code"
            hint="Telegram sent this to the account you are connecting."
            required
          >
            {(fieldProps) => (
              <Input
                {...fieldProps}
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="12345"
                required
              />
            )}
          </Field>
          {needsPassword && (
            <Field
              label="Two-factor password"
              hint="This account has two-step verification enabled."
              required
            >
              {(fieldProps) => (
                <Input
                  {...fieldProps}
                  type="password"
                  autoComplete="off"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              )}
            </Field>
          )}
          <div className="flex flex-wrap justify-end gap-2">
            <Button variant="ghost" onClick={() => setStep('phone')}>
              Back
            </Button>
            {loginSessionId && (
              <Button
                variant="secondary"
                onClick={() => cancelLoginMutation.mutate()}
                isLoading={cancelLoginMutation.isPending}
              >
                Cancel login
              </Button>
            )}
            <Button
              onClick={() => {
                setError('');
                completeLoginMutation.mutate();
              }}
              isLoading={completeLoginMutation.isPending}
            >
              Complete login
            </Button>
          </div>
        </div>
      );
    }

    return null;
  };

  return (
    <Modal
      title="Add Telegram account"
      icon={<Smartphone className="h-5 w-5 text-ink-subtle" strokeWidth={2} aria-hidden />}
      size="sm"
      onClose={onClose}
      footer={
        showUploadForm ? (
          <>
            <Button variant="secondary" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" form="add-account-form" isLoading={uploadMutation.isPending}>
              Add account
            </Button>
          </>
        ) : (
          <Button variant="secondary" onClick={onClose}>
            Close
          </Button>
        )
      }
    >
      <div className="space-y-4">
        <FormError message={error} />

        <Field label="Name" hint="Optional. Defaults to Account.">
          {(fieldProps) => (
            <Input
              {...fieldProps}
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="My account"
            />
          )}
        </Field>

        <Field label="Type">
          {(fieldProps) => (
            <Select
              {...fieldProps}
              value={type}
              onChange={(e) => {
                const next = e.target.value as 'user' | 'bot';
                setType(next);
                if (next === 'user') {
                  setStep('method');
                  setMode('phone');
                }
              }}
            >
              <option value="user">User (phone login or session file)</option>
              <option value="bot">Bot (token)</option>
            </Select>
          )}
        </Field>

        {type === 'user' && mode === 'phone' && renderUserPhoneFlow()}

        {showUploadForm && (
          <form id="add-account-form" onSubmit={handleUploadSubmit} className="space-y-4">
            {type === 'bot' && (
              <Field label="Bot token" required>
                {(fieldProps) => (
                  <Input
                    {...fieldProps}
                    type="password"
                    autoComplete="off"
                    value={botToken}
                    onChange={(e) => setBotToken(e.target.value)}
                    placeholder="123456:ABC..."
                  />
                )}
              </Field>
            )}
            {type === 'user' && mode === 'upload' && (
              <Field
                label="Session file"
                hint="A .session file generated by Telethon outside this app."
                required
              >
                {(fieldProps) => (
                  <input
                    {...fieldProps}
                    type="file"
                    accept=".session"
                    onChange={(e) => setSessionFile(e.target.files?.[0] ?? null)}
                    className="w-full rounded-control border border-line-strong bg-surface-raised px-3 py-2 text-sm text-ink file:mr-3 file:rounded file:border-0 file:bg-surface-sunken file:px-2.5 file:py-1 file:text-sm file:font-medium file:text-ink"
                  />
                )}
              </Field>
            )}
          </form>
        )}
      </div>
    </Modal>
  );
}
