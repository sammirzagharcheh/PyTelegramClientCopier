import { useEffect, useRef, useState } from 'react';
import {
  Activity,
  ChevronRight,
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
  Webhook,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { ChangePasswordDialog } from '../components/ChangePasswordDialog';
import { ThemeSwitcher } from '../components/ThemeSwitcher';
import { TimezonePreferencesDialog } from '../components/TimezonePreferencesDialog';
import { getBreadcrumbs } from '../lib/breadcrumbs';
import { useAuth } from '../store/AuthContext';

type NavItem = { to: string; label: string; icon: LucideIcon };
type NavSection = { title: string; items: NavItem[] };

const navSections: NavSection[] = [
  {
    title: 'Overview',
    items: [{ to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard }],
  },
  {
    title: 'Operations',
    items: [
      { to: '/accounts', label: 'Accounts', icon: Smartphone },
      { to: '/mappings', label: 'Mappings', icon: GitBranch },
      { to: '/workers', label: 'Workers', icon: Activity },
      { to: '/schedule', label: 'Schedule', icon: Clock },
      { to: '/media-assets', label: 'Media Assets', icon: Image },
    ],
  },
  {
    title: 'Logs & Monitoring',
    items: [
      { to: '/worker-logs', label: 'Worker Logs', icon: ScrollText },
      { to: '/webhook-logs', label: 'Webhook Logs', icon: Webhook },
      { to: '/logs', label: 'Message Logs', icon: MessageSquare },
      { to: '/message-index', label: 'Message Index', icon: Database },
    ],
  },
];

const adminNavSections: NavSection[] = [
  {
    title: 'Overview',
    items: [{ to: '/admin', label: 'Dashboard', icon: LayoutDashboard }],
  },
  {
    title: 'Administration',
    items: [
      { to: '/admin/users', label: 'Users', icon: Users },
      { to: '/admin/settings', label: 'Settings', icon: Settings },
      { to: '/admin/mappings', label: 'Mappings', icon: GitBranch },
      { to: '/admin/workers', label: 'Workers', icon: Activity },
      { to: '/admin/media-assets', label: 'Media Assets', icon: Image },
    ],
  },
  {
    title: 'Logs & Monitoring',
    items: [
      { to: '/admin/logs', label: 'Logs', icon: MessageSquare },
      { to: '/admin/worker-logs', label: 'Worker Logs', icon: ScrollText },
      { to: '/admin/webhook-logs', label: 'Webhook Logs', icon: Webhook },
      { to: '/admin/message-index', label: 'Message Index', icon: Database },
    ],
  },
];

export function MainLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const breadcrumbs = getBreadcrumbs(location.pathname);
  const isAdmin = user?.role === 'admin';
  const sections = isAdmin ? adminNavSections : navSections;
  const [menuOpen, setMenuOpen] = useState(false);
  const [collapsedSections, setCollapsedSections] = useState<Record<string, boolean>>({});
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

  const toggleSection = (title: string) => {
    setCollapsedSections((prev) => ({ ...prev, [title]: !prev[title] }));
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
        <nav className="p-2 space-y-4">
          {sections.map((section) => (
            <div key={section.title}>
              <button
                type="button"
                onClick={() => toggleSection(section.title)}
                className="w-full px-4 pb-1 flex items-center justify-between text-[11px] font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
              >
                <span>{section.title}</span>
                {collapsedSections[section.title] ? (
                  <ChevronRight className="h-3 w-3" />
                ) : (
                  <ChevronDown className="h-3 w-3" />
                )}
              </button>
              <div className={collapsedSections[section.title] ? 'hidden' : ''}>
                {section.items.map((item) => {
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
              </div>
            </div>
          ))}
        </nav>
      </aside>
      <div className="flex-1 flex flex-col">
        <header className="h-14 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between gap-4 px-6 bg-white dark:bg-gray-800">
          <div className="min-w-0 flex-1">
            {breadcrumbs.length > 0 && (
              <nav aria-label="Breadcrumb" className="min-w-0">
                <ol className="flex flex-wrap items-center gap-x-1 gap-y-0.5 text-sm">
                  {breadcrumbs.map((crumb, index) => {
                    const isLast = index === breadcrumbs.length - 1;
                    return (
                      <li key={`${crumb.to}-${index}`} className="flex items-center gap-1 min-w-0">
                        {index > 0 && (
                          <ChevronRight
                            className="h-3.5 w-3.5 shrink-0 text-gray-400 dark:text-gray-500"
                            aria-hidden
                          />
                        )}
                        {isLast ? (
                          <span
                            className="font-medium text-gray-900 dark:text-gray-100 truncate"
                            aria-current="page"
                          >
                            {crumb.label}
                          </span>
                        ) : (
                          <Link
                            to={crumb.to}
                            className="truncate text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400"
                          >
                            {crumb.label}
                          </Link>
                        )}
                      </li>
                    );
                  })}
                </ol>
              </nav>
            )}
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <ThemeSwitcher />
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
