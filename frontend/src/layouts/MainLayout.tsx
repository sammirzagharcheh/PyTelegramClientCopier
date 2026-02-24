import { useEffect, useRef, useState } from 'react';
import {
  Activity,
  ChevronDown,
  Clock,
  Database,
  GitBranch,
  Globe,
  Image,
  KeyRound,
  LayoutDashboard,
  LogOut,
  MessageSquare,
  ScrollText,
  Settings,
  Smartphone,
  Users,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom';
import { ChangePasswordDialog } from '../components/ChangePasswordDialog';
import { TimezonePreferencesDialog } from '../components/TimezonePreferencesDialog';
import { useAuth } from '../store/AuthContext';

type NavItem = { to: string; label: string; icon: LucideIcon };

const navItems: NavItem[] = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/accounts', label: 'Accounts', icon: Smartphone },
  { to: '/mappings', label: 'Mappings', icon: GitBranch },
  { to: '/workers', label: 'Workers', icon: Activity },
  { to: '/worker-logs', label: 'Worker Logs', icon: ScrollText },
  { to: '/logs', label: 'Message Logs', icon: MessageSquare },
  { to: '/message-index', label: 'Message Index', icon: Database },
  { to: '/schedule', label: 'Schedule', icon: Clock },
  { to: '/media-assets', label: 'Media Assets', icon: Image },
];

const adminNavItems: NavItem[] = [
  { to: '/admin', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/admin/users', label: 'Users', icon: Users },
  { to: '/admin/settings', label: 'Settings', icon: Settings },
  { to: '/admin/mappings', label: 'Mappings', icon: GitBranch },
  { to: '/admin/logs', label: 'Logs', icon: MessageSquare },
  { to: '/admin/message-index', label: 'Message Index', icon: Database },
  { to: '/admin/workers', label: 'Workers', icon: Activity },
  { to: '/admin/worker-logs', label: 'Worker Logs', icon: ScrollText },
  { to: '/admin/media-assets', label: 'Media Assets', icon: Image },
];

export function MainLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const isAdmin = user?.role === 'admin';
  const items = isAdmin ? adminNavItems : navItems;
  const [menuOpen, setMenuOpen] = useState(false);
  const [changePasswordOpen, setChangePasswordOpen] = useState(false);
  const [timezoneOpen, setTimezoneOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    }
    if (menuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [menuOpen]);

  const handleLogout = async () => {
    setMenuOpen(false);
    await logout();
    navigate('/login');
  };

  const handleChangePasswordClick = () => {
    setMenuOpen(false);
    setChangePasswordOpen(true);
  };

  const handleTimezoneClick = () => {
    setMenuOpen(false);
    setTimezoneOpen(true);
  };

  return (
    <div className="min-h-screen flex">
      <aside className="w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 shrink-0">
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <Link to={isAdmin ? '/admin' : '/dashboard'} className="font-semibold text-lg flex items-center gap-2">
            <Smartphone className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            Telegram Copier
          </Link>
        </div>
        <nav className="p-2">
          {items.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-4 py-2 rounded-md mb-1 ${
                    isActive
                      ? 'bg-gray-100 dark:bg-gray-700 text-blue-600 dark:text-blue-400'
                      : 'text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
                  }`
                }
              >
                <Icon className="h-4 w-4 shrink-0" />
                {item.label}
              </NavLink>
            );
          })}
        </nav>
      </aside>
      <div className="flex-1 flex flex-col">
        <header className="h-14 border-b border-gray-200 dark:border-gray-700 flex items-center justify-end px-6 bg-white dark:bg-gray-800">
          <div className="relative" ref={menuRef}>
            <button
              type="button"
              onClick={() => setMenuOpen(!menuOpen)}
              className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer transition-colors"
            >
              <span>{user?.email}</span>
              <span className="text-gray-400 dark:text-gray-500">({user?.role})</span>
              <ChevronDown className="h-4 w-4" />
            </button>
            {menuOpen && (
              <div className="absolute right-0 mt-1 w-48 py-2 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-600 z-50">
                <button
                  type="button"
                  onClick={handleTimezoneClick}
                  className="flex items-center gap-2 w-full px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                >
                  <Globe className="h-4 w-4" />
                  Timezone
                </button>
                <button
                  type="button"
                  onClick={handleChangePasswordClick}
                  className="flex items-center gap-2 w-full px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                >
                  <KeyRound className="h-4 w-4" />
                  Change password
                </button>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="flex items-center gap-2 w-full px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                >
                  <LogOut className="h-4 w-4" />
                  Logout
                </button>
              </div>
            )}
          </div>
        </header>
        {changePasswordOpen && (
          <ChangePasswordDialog onClose={() => setChangePasswordOpen(false)} />
        )}
        {timezoneOpen && (
          <TimezonePreferencesDialog onClose={() => setTimezoneOpen(false)} />
        )}
        <main className="flex-1 p-6 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
