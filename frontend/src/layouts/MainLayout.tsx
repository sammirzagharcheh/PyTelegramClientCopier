import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../store/AuthContext';

const navItems = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/accounts', label: 'Accounts' },
  { to: '/mappings', label: 'Mappings' },
  { to: '/workers', label: 'Workers' },
  { to: '/logs', label: 'Message Logs' },
  { to: '/message-index', label: 'Message Index' },
];

const adminNavItems = [
  { to: '/admin', label: 'Dashboard' },
  { to: '/admin/users', label: 'Users' },
  { to: '/admin/settings', label: 'Settings' },
  { to: '/admin/mappings', label: 'Mappings' },
  { to: '/admin/logs', label: 'Logs' },
  { to: '/admin/message-index', label: 'Message Index' },
  { to: '/admin/workers', label: 'Workers' },
];

export function MainLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const isAdmin = user?.role === 'admin';
  const items = isAdmin ? adminNavItems : navItems;

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen flex">
      <aside className="w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 shrink-0">
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <Link to={isAdmin ? '/admin' : '/dashboard'} className="font-semibold text-lg">
            Telegram Copier
          </Link>
        </div>
        <nav className="p-2">
          {items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `block px-4 py-2 rounded-md mb-1 ${
                  isActive
                    ? 'bg-gray-100 dark:bg-gray-700 text-blue-600 dark:text-blue-400'
                    : 'text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="flex-1 flex flex-col">
        <header className="h-14 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between px-6 bg-white dark:bg-gray-800">
          <span className="text-sm text-gray-500">
            {user?.email} ({user?.role})
          </span>
          <button
            onClick={handleLogout}
            className="px-4 py-2 text-sm rounded-md border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700"
          >
            Logout
          </button>
        </header>
        <main className="flex-1 p-6 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
