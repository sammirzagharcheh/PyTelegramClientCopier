import { AlertTriangle } from 'lucide-react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/Button';
import { Field, Input } from '../components/ui/Field';
import { errorMessage } from '../lib/apiError';
import { useAuth } from '../store/AuthContext';

export function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);
    try {
      await login(email, password);
      navigate('/');
    } catch (err: unknown) {
      setError(errorMessage(err, 'Sign in failed. Check your email and password.'));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="rounded-surface border border-line bg-surface-raised p-6 shadow-surface">
      <h1 className="text-lg font-semibold text-ink">Sign in</h1>
      <p className="mt-1 text-sm text-ink-subtle">Use your operator account to continue.</p>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        {error && (
          <div
            role="alert"
            className="flex items-start gap-2 rounded-control border border-red-300 bg-red-50 px-3 py-2.5 text-sm text-red-900 dark:border-red-800 dark:bg-red-950/50 dark:text-red-200"
          >
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
            <span>{error}</span>
          </div>
        )}
        <Field label="Email" required>
          {(fieldProps) => (
            <Input
              {...fieldProps}
              type="email"
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              invalid={Boolean(error)}
              required
            />
          )}
        </Field>
        <Field label="Password" required>
          {(fieldProps) => (
            <Input
              {...fieldProps}
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              invalid={Boolean(error)}
              required
            />
          )}
        </Field>
        <Button type="submit" isLoading={isSubmitting} className="w-full">
          Sign in
        </Button>
      </form>
    </div>
  );
}
