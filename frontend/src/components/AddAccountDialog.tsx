import { Smartphone } from 'lucide-react';
import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';

type Props = {
  onClose: () => void;
};

type Mode = 'phone' | 'upload';

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

  // Existing upload/bot flow
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
      setError(
        err && typeof err === 'object' && 'response' in err && (err as any).response && typeof (err as any).response === 'object' && 'data' in (err as any).response && (err as any).response.data && typeof (err as any).response.data === 'object' && 'detail' in (err as any).response.data
          ? String(((err as any).response.data as { detail: unknown }).detail)
          : 'Failed to add account',
      );
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
      setError(
        err && typeof err === 'object' && 'response' in err && (err as any).response && typeof (err as any).response === 'object' && 'data' in (err as any).response && (err as any).response.data && typeof (err as any).response.data === 'object' && 'detail' in (err as any).response.data
          ? String(((err as any).response.data as { detail: unknown }).detail)
          : 'Failed to send code',
      );
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
      const anyErr = err as any;
      const detail = anyErr?.response?.data?.detail;

      if (detail && typeof detail === 'object' && (detail as any).code === '2FA_REQUIRED') {
        setNeedsPassword(true);
        setError((detail as any).message || '2FA password required');
        return;
      }

      setError(
        detail && typeof detail === 'object' && 'message' in detail
          ? String((detail as { message: unknown }).message)
          : anyErr?.response?.data?.detail ?? 'Login failed',
      );
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
      setError('Please upload a session file');
      return;
    }
    if (type === 'bot' && !botToken) {
      setError('Please enter bot token');
      return;
    }
    uploadMutation.mutate();
  };

  const renderUserPhoneFlow = () => {
    if (step === 'method') {
      return (
        <div className="space-y-4">
          <p className="text-sm text-gray-600 dark:text-gray-300">
            How would you like to add a user account?
          </p>
          <button
            type="button"
            onClick={() => {
              setMode('phone');
              setStep('phone');
            }}
            className="w-full px-4 py-2 rounded border border-gray-300 dark:border-gray-600 text-left hover:bg-gray-50 dark:hover:bg-gray-700"
          >
            Login with phone &amp; code (recommended)
          </button>
          <button
            type="button"
            onClick={() => {
              setMode('upload');
              setStep('method'); // keep method but switch mode; upload is handled by main form
            }}
            className="w-full px-4 py-2 rounded border border-gray-300 dark:border-gray-600 text-left hover:bg-gray-50 dark:hover:bg-gray-700 text-sm"
          >
            Upload existing .session file (advanced)
          </button>
        </div>
      );
    }

    if (step === 'phone') {
      return (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Phone number</label>
            <input
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+14155551234"
              className="w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700"
              required
            />
            <p className="text-xs text-gray-500 mt-1">
              We will send a Telegram login code to this number.
            </p>
          </div>
          <div className="flex gap-2 justify-end">
            <button
              type="button"
              onClick={() => setStep('method')}
              className="px-4 py-2 rounded border border-gray-300"
            >
              Back
            </button>
            {loginSessionId && (
              <button
                type="button"
                onClick={() => cancelLoginMutation.mutate()}
                className="px-4 py-2 rounded border border-gray-300 text-sm"
              >
                Cancel login
              </button>
            )}
            <button
              type="button"
              onClick={() => {
                setError('');
                beginLoginMutation.mutate();
              }}
              disabled={beginLoginMutation.isPending}
              className="px-4 py-2 rounded bg-blue-600 text-white disabled:opacity-50"
            >
              Send code
            </button>
          </div>
        </div>
      );
    }

    if (step === 'code') {
      return (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Login code</label>
            <input
              type="text"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="12345"
              className="w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700"
              required
            />
            <p className="text-xs text-gray-500 mt-1">
              Enter the code you received in Telegram. If you have 2FA password enabled, we&apos;ll
              add support for it in a later step.
            </p>
          </div>
          {needsPassword && (
            <div>
              <label className="block text-sm font-medium mb-1">2FA password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700"
              />
              <p className="text-xs text-gray-500 mt-1">
                Enter your Telegram 2FA password.
              </p>
            </div>
          )}
          <div className="flex gap-2 justify-end">
            <button
              type="button"
              onClick={() => setStep('phone')}
              className="px-4 py-2 rounded border border-gray-300"
            >
              Back
            </button>
            {loginSessionId && (
              <button
                type="button"
                onClick={() => cancelLoginMutation.mutate()}
                className="px-4 py-2 rounded border border-gray-300 text-sm"
              >
                Cancel login
              </button>
            )}
            <button
              type="button"
              onClick={() => {
                setError('');
                completeLoginMutation.mutate();
              }}
              disabled={completeLoginMutation.isPending}
              className="px-4 py-2 rounded bg-blue-600 text-white disabled:opacity-50"
            >
              Complete login
            </button>
          </div>
        </div>
      );
    }

    return null;
  };

  const showUploadForm = type === 'bot' || (type === 'user' && (mode === 'upload' || step !== 'phone' && step !== 'code'));

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <div
        className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 max-w-md w-full"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-2 mb-4">
          <Smartphone className="h-5 w-5 text-blue-600 dark:text-blue-400" />
          <h2 className="text-xl font-bold">Add Telegram Account</h2>
        </div>
        {error && (
          <div className="p-3 mb-4 rounded bg-red-50 dark:bg-red-900/20 text-red-600 text-sm">{error}</div>
        )}

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700"
              placeholder="My account"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Type</label>
            <select
              value={type}
              onChange={(e) => {
                const next = e.target.value as 'user' | 'bot';
                setType(next);
                if (next === 'user') {
                  setStep('method');
                  setMode('phone');
                }
              }}
              className="w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700"
            >
              <option value="user">User (phone login or session file)</option>
              <option value="bot">Bot (token)</option>
            </select>
          </div>

          {type === 'user' && mode === 'phone' && renderUserPhoneFlow()}

          {showUploadForm && (
            <form onSubmit={handleUploadSubmit} className="space-y-4 mt-2">
              {type === 'bot' && (
                <div>
                  <label className="block text-sm font-medium mb-1">Bot Token</label>
                  <input
                    type="password"
                    value={botToken}
                    onChange={(e) => setBotToken(e.target.value)}
                    className="w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700"
                    placeholder="123456:ABC..."
                  />
                </div>
              )}
              {type === 'user' && mode === 'upload' && (
                <div>
                  <label className="block text-sm font-medium mb-1">Session File (.session)</label>
                  <input
                    type="file"
                    accept=".session"
                    onChange={(e) => setSessionFile(e.target.files?.[0] ?? null)}
                    className="w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-600"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Advanced: generate .session with a separate script and upload it here.
                  </p>
                </div>
              )}
              <div className="flex gap-2 justify-end">
                <button type="button" onClick={onClose} className="px-4 py-2 rounded border border-gray-300">
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={uploadMutation.isPending}
                  className="px-4 py-2 rounded bg-blue-600 text-white disabled:opacity-50"
                >
                  Add
                </button>
              </div>
            </form>
          )}

          {!showUploadForm && (
            <div className="flex gap-2 justify-end mt-4">
              <button type="button" onClick={onClose} className="px-4 py-2 rounded border border-gray-300">
                Close
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
