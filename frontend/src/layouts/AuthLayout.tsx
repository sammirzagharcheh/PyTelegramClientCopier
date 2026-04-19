import { Outlet } from 'react-router-dom';
import { ThemeSwitcher } from '../components/ThemeSwitcher';

export function AuthLayout() {
  return (
    <div className="relative min-h-screen flex items-center justify-center bg-gray-100 dark:bg-gray-900 p-4">
      <div className="absolute right-4 top-4">
        <ThemeSwitcher />
      </div>
      <div className="w-full max-w-md">
        <Outlet />
      </div>
    </div>
  );
}
