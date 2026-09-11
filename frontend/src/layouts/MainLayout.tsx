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
  Menu,
  MessageSquare,
  Monitor,
  Moon,
  ScrollText,
  Settings,
  Smartphone,
  Sun,
  Users,
  X,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom';
import { ChangePasswordDialog } from '../components/ChangePasswordDialog';
import { TimezonePreferencesDialog } from '../components/TimezonePreferencesDialog';
import { useAuth } from '../store/AuthContext';
import { useTheme } from '../store/ThemeContext';
import type { ThemePreference } from '../store/ThemeContext';

type NavItem = { to: string; label: string; icon: LucideIcon };
type NavGroup = { heading: string; items: NavItem[] };

const userNav: NavGroup[] = [
  {
    heading: 'Overview',
    items: [{ to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard }],
  },
  {
    heading: 'Copying',
    items: [
      { to: '/accounts', label: 'Accounts', icon: Smartphone },
      { to: '/mappings', label: 'Mappings', icon: GitBranch },
      { to: '/schedule', label: 'Schedule', icon: Clock },
      { to: '/media-assets', label: 'Media Assets', icon: Image },
    ],
  },
  {
    heading: 'Operations',
    items: [
      { to: '/workers', label: 'Workers', icon: Activity },
      { to: '/worker-logs', label: 'Worker Logs', icon: ScrollText },
      { to: '/logs', label: 'Message Logs', icon: MessageSquare },
      { to: '/message-index', label: 'Message Index', icon: Database },
    ],
  },
];

const adminNav: NavGroup[] = [
  {
    heading: 'Overview',
    items: [{ to: '/admin', label: 'Dashboard', icon: LayoutDashboard }],
  },
  {
    heading: 'Administration',
    items: [
      { to: '/admin/users', label: 'Users', icon: Users },
      { to: '/admin/settings', label: 'Settings', icon: Settings },
    ],
  },
  {
    heading: 'Copying',
    items: [
      { to: '/admin/mappings', label: 'Mappings', icon: GitBranch },
      { to: '/admin/media-assets', label: 'Media Assets', icon: Image },
    ],
  },
  {
    heading: 'Operations',
    items: [
      { to: '/admin/workers', label: 'Workers', icon: Activity },
      { to: '/admin/worker-logs', label: 'Worker Logs', icon: ScrollText },
      { to: '/admin/logs', label: 'Logs', icon: MessageSquare },
      { to: '/admin/message-index', label: 'Message Index', icon: Database },
    ],
  },
];

const themeOptions: { value: ThemePreference; label: string; icon: LucideIcon }[] = [
  { value: 'light', label: 'Light', icon: Sun },
  { value: 'dark', label: 'Dark', icon: Moon },
  { value: 'system', label: 'System', icon: Monitor },
];

function SidebarNav({
  groups,
  isAdmin,
  onNavigate,
}: {
  groups: NavGroup[];
  isAdmin: boolean;
  onNavigate?: () => void;
}) {
  return (
    <div className="flex h-full flex-col">
      <div className="flex h-14 shrink-0 items-center border-b border-line px-4">
        <Link
          to={isAdmin ? '/admin' : '/dashboard'}
          onClick={onNavigate}
          className="flex items-center gap-2 rounded-control text-sm font-semibold text-ink"
        >
          <span className="rounded-control bg-accent p-1.5 text-accent-fg">
            <Smartphone className="h-4 w-4" strokeWidth={2} aria-hidden />
          </span>
          Telegram Copier
        </Link>
      </div>
      <nav aria-label="Main" className="flex-1 overflow-y-auto px-3 py-4">
        {groups.map((group) => (
          <div key={group.heading} className="mb-5 last:mb-0">
            <h2 className="px-2.5 pb-1.5 text-[11px] font-semibold tracking-wider text-ink-subtle uppercase">
              {group.heading}
            </h2>
            <ul className="space-y-0.5">
              {group.items.map((item) => {
                const Icon = item.icon;
                return (
                  <li key={item.to}>
                    <NavLink
                      to={item.to}
                      end={item.to === '/admin'}
                      onClick={onNavigate}
                      className={({ isActive }) =>
                        `flex items-center gap-2.5 rounded-control px-2.5 py-2 text-sm transition-colors ${
                          isActive
                            ? 'bg-accent-soft font-medium text-accent-ink'
                            : 'text-ink-muted hover:bg-surface-hover hover:text-ink'
                        }`
                      }
                    >
                      {({ isActive }) => (
                        <>
                          <Icon
                            className="h-4 w-4 shrink-0"
                            strokeWidth={2}
                            aria-hidden
                          />
                          {item.label}
                          {isActive && <span className="sr-only">(current page)</span>}
                        </>
                      )}
                    </NavLink>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>
    </div>
  );
}

export function MainLayout() {
  const { user, logout } = useAuth();
  const { preference, setPreference } = useTheme();
  const navigate = useNavigate();
  const isAdmin = user?.role === 'admin';
  const groups = isAdmin ? adminNav : userNav;
  const [menuOpen, setMenuOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [changePasswordOpen, setChangePasswordOpen] = useState(false);
  const [timezoneOpen, setTimezoneOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const menuButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!menuOpen) return;
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    }
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setMenuOpen(false);
        menuButtonRef.current?.focus();
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
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
    <div className="flex min-h-[100dvh] bg-surface">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-toast focus:rounded-control focus:bg-accent focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-accent-fg"
      >
        Skip to content
      </a>

      <aside className="hidden w-60 shrink-0 border-r border-line bg-surface-raised lg:block">
        <div className="sticky top-0 h-[100dvh]">
          <SidebarNav groups={groups} isAdmin={isAdmin} />
        </div>
      </aside>

      {sidebarOpen && (
        <div className="fixed inset-0 z-overlay lg:hidden">
          <div
            className="absolute inset-0 bg-black/50"
            onClick={() => setSidebarOpen(false)}
            aria-hidden
          />
          <div className="absolute inset-y-0 left-0 flex w-64 flex-col border-r border-line bg-surface-raised shadow-overlay">
            <SidebarNav
              groups={groups}
              isAdmin={isAdmin}
              onNavigate={() => setSidebarOpen(false)}
            />
            <button
              type="button"
              onClick={() => setSidebarOpen(false)}
              aria-label="Close navigation"
              className="absolute top-3.5 right-3 rounded-control p-1.5 text-ink-subtle transition-colors hover:bg-surface-hover hover:text-ink"
            >
              <X className="h-4 w-4" aria-hidden />
            </button>
          </div>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-sticky flex h-14 shrink-0 items-center gap-2 border-b border-line bg-surface-raised/90 px-4 backdrop-blur">
          <button
            type="button"
            onClick={() => setSidebarOpen(true)}
            aria-label="Open navigation"
            aria-expanded={sidebarOpen}
            className="-ml-1 rounded-control p-2 text-ink-muted transition-colors hover:bg-surface-hover hover:text-ink lg:hidden"
          >
            <Menu className="h-5 w-5" aria-hidden />
          </button>

          <div className="flex-1" />

          <div className="relative" ref={menuRef}>
            <button
              ref={menuButtonRef}
              type="button"
              onClick={() => setMenuOpen(!menuOpen)}
              aria-expanded={menuOpen}
              aria-haspopup="menu"
              className="flex max-w-[14rem] items-center gap-2 rounded-control px-2.5 py-1.5 text-sm text-ink-muted transition-colors hover:bg-surface-hover hover:text-ink sm:max-w-xs"
            >
              <span className="truncate">{user?.email}</span>
              {isAdmin && (
                <span className="hidden shrink-0 rounded-full bg-violet-100 px-1.5 py-0.5 text-[11px] font-medium text-violet-800 sm:inline dark:bg-violet-500/15 dark:text-violet-300">
                  admin
                </span>
              )}
              <ChevronDown
                className={`h-4 w-4 shrink-0 transition-transform ${menuOpen ? 'rotate-180' : ''}`}
                aria-hidden
              />
            </button>
            {menuOpen && (
              <div
                role="menu"
                className="absolute right-0 mt-1.5 w-60 rounded-surface border border-line bg-surface-raised py-1.5 shadow-raised z-dropdown"
              >
                <div className="border-b border-line px-3 pt-1 pb-2.5">
                  <p className="mb-1.5 text-[11px] font-semibold tracking-wider text-ink-subtle uppercase">
                    Appearance
                  </p>
                  <div
                    role="radiogroup"
                    aria-label="Colour theme"
                    className="flex gap-1 rounded-control bg-surface-sunken p-0.5"
                  >
                    {themeOptions.map((option) => {
                      const OptionIcon = option.icon;
                      const selected = preference === option.value;
                      return (
                        <button
                          key={option.value}
                          type="button"
                          role="radio"
                          aria-checked={selected}
                          onClick={() => setPreference(option.value)}
                          className={`flex flex-1 items-center justify-center gap-1.5 rounded-[0.3rem] px-2 py-1.5 text-xs font-medium transition-colors ${
                            selected
                              ? 'bg-surface-raised text-ink shadow-surface'
                              : 'text-ink-subtle hover:text-ink'
                          }`}
                        >
                          <OptionIcon className="h-3.5 w-3.5" aria-hidden />
                          {option.label}
                        </button>
                      );
                    })}
                  </div>
                </div>
                <button
                  type="button"
                  role="menuitem"
                  onClick={handleTimezoneClick}
                  className="flex w-full items-center gap-2.5 px-3 py-2 text-left text-sm text-ink-muted transition-colors hover:bg-surface-hover hover:text-ink"
                >
                  <Globe className="h-4 w-4 shrink-0" aria-hidden />
                  Timezone
                </button>
                <button
                  type="button"
                  role="menuitem"
                  onClick={handleChangePasswordClick}
                  className="flex w-full items-center gap-2.5 px-3 py-2 text-left text-sm text-ink-muted transition-colors hover:bg-surface-hover hover:text-ink"
                >
                  <KeyRound className="h-4 w-4 shrink-0" aria-hidden />
                  Change password
                </button>
                <button
                  type="button"
                  role="menuitem"
                  onClick={handleLogout}
                  className="flex w-full items-center gap-2.5 px-3 py-2 text-left text-sm text-ink-muted transition-colors hover:bg-surface-hover hover:text-ink"
                >
                  <LogOut className="h-4 w-4 shrink-0" aria-hidden />
                  Log out
                </button>
              </div>
            )}
          </div>
        </header>

        {changePasswordOpen && (
          <ChangePasswordDialog onClose={() => setChangePasswordOpen(false)} />
        )}
        {timezoneOpen && <TimezonePreferencesDialog onClose={() => setTimezoneOpen(false)} />}

        <main id="main-content" tabIndex={-1} className="flex-1 px-4 py-6 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-[100rem]">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
