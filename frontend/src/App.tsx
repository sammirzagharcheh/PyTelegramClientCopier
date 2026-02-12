import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider, useAuth } from './store/AuthContext';
import { AuthLayout } from './layouts/AuthLayout';
import { MainLayout } from './layouts/MainLayout';
import { Login } from './pages/Login';
import { UserDashboard } from './pages/user/Dashboard';
import { Accounts } from './pages/user/Accounts';
import { Mappings } from './pages/user/Mappings';
import { MappingDetail } from './pages/user/MappingDetail';
import { Logs } from './pages/user/Logs';
import { MessageIndex } from './pages/user/MessageIndex';
import { AdminDashboard } from './pages/admin/Dashboard';
import { AdminUsers } from './pages/admin/Users';
import { AdminMappings } from './pages/admin/AdminMappings';
import { AdminLogs } from './pages/admin/AdminLogs';
import { AdminMessageIndex } from './pages/admin/AdminMessageIndex';
import { Workers } from './pages/admin/Workers';
import { Settings } from './pages/admin/Settings';
import { UserWorkers } from './pages/user/Workers';
import { WorkerLogs } from './pages/user/WorkerLogs';
import { AdminWorkerLogs } from './pages/admin/AdminWorkerLogs';

const queryClient = new QueryClient();

function ProtectedRoute({ children, adminOnly }: { children: React.ReactNode; adminOnly?: boolean }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="min-h-screen flex items-center justify-center">Loading...</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (adminOnly && user.role !== 'admin') return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
}

function RootRedirect() {
  const { user, loading } = useAuth();
  if (loading) return <div className="min-h-screen flex items-center justify-center">Loading...</div>;
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={user.role === 'admin' ? '/admin' : '/dashboard'} replace />;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<AuthLayout />}>
        <Route index element={<Login />} />
      </Route>
      <Route path="/" element={<ProtectedRoute><MainLayout /></ProtectedRoute>}>
        <Route index element={<RootRedirect />} />
        <Route path="dashboard" element={<UserDashboard />} />
        <Route path="accounts" element={<Accounts />} />
        <Route path="mappings" element={<Mappings />} />
        <Route path="mappings/:id" element={<MappingDetail />} />
        <Route path="workers" element={<UserWorkers />} />
        <Route path="worker-logs" element={<WorkerLogs />} />
        <Route path="logs" element={<Logs />} />
        <Route path="message-index" element={<MessageIndex />} />
      </Route>
      <Route path="/admin" element={<ProtectedRoute adminOnly><MainLayout /></ProtectedRoute>}>
        <Route index element={<AdminDashboard />} />
        <Route path="users" element={<AdminUsers />} />
        <Route path="mappings" element={<AdminMappings />} />
        <Route path="logs" element={<AdminLogs />} />
        <Route path="message-index" element={<AdminMessageIndex />} />
        <Route path="workers" element={<Workers />} />
        <Route path="worker-logs" element={<AdminWorkerLogs />} />
        <Route path="settings" element={<Settings />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </QueryClientProvider>
    </BrowserRouter>
  );
}
