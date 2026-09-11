import { Smartphone } from 'lucide-react';
import { Outlet } from 'react-router-dom';
import { ThemeSwitcher } from '../components/ThemeSwitcher';

export function AuthLayout() {
  return (
    <div className="relative flex min-h-[100dvh] flex-col items-center justify-center bg-surface px-4 py-10">
      <div className="absolute right-4 top-4">
        <ThemeSwitcher />
      </div>
      <main className="mx-auto w-full max-w-sm">
        <div className="mb-7 flex items-center justify-center gap-2.5">
          <span className="rounded-control bg-accent p-2 text-accent-fg">
            <Smartphone className="h-5 w-5" strokeWidth={2} aria-hidden />
          </span>
          <span className="text-lg font-semibold text-ink">Telegram Copier</span>
        </div>
        <Outlet />
      </main>
      <p className="mt-8 text-xs text-ink-subtle">
        Self-hosted Telegram channel copier
      </p>
    </div>
  );
}
