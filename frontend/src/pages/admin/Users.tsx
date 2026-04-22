import { Filter, Lock, Pencil, Plus, Search, Trash2, Users, X } from 'lucide-react';
import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { CreateUserDialog } from '../../components/CreateUserDialog';
import { EditUserDialog } from '../../components/EditUserDialog';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { useAuth } from '../../store/AuthContext';
import { PageHeader } from '../../components/PageHeader';
import { SortableTh } from '../../components/SortableTh';
import { StatusBadge } from '../../components/StatusBadge';
import { Pagination } from '../../components/Pagination';

type User = {
  id: number;
  email: string;
  name: string | null;
  role: string;
  status: string;
  created_at: string | null;
};

type PaginatedUsers = { items: User[]; total: number; page: number; page_size: number; total_pages: number };

export function AdminUsers() {
  const { user: currentUser } = useAuth();
  const [showCreate, setShowCreate] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [deletingUser, setDeletingUser] = useState<User | null>(null);
  const [actionError, setActionError] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [roleFilter, setRoleFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [search, setSearch] = useState<string>('');
  const [sortBy, setSortBy] = useState<string>('id');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const queryClient = useQueryClient();

  const deleteMutation = useMutation({
    mutationFn: async (userId: number) => {
      await api.delete(`/admin/users/${userId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'users'] });
      setDeletingUser(null);
      setActionError('');
    },
    onError: (err: unknown) => {
      setActionError(
        err &&
          typeof err === 'object' &&
          'response' in err &&
          err.response &&
          typeof err.response === 'object' &&
          'data' in err.response &&
          err.response.data &&
          typeof err.response.data === 'object' &&
          'detail' in err.response.data
          ? String((err.response.data as { detail: unknown }).detail)
          : 'Failed to delete user'
      );
    },
  });

  const { data, isLoading } = useQuery({
    queryKey: ['admin', 'users', page, pageSize, roleFilter, statusFilter, search, sortBy, sortOrder],
    queryFn: async () => {
      const params = new URLSearchParams({ page: String(page), page_size: String(pageSize), sort_by: sortBy, sort_order: sortOrder });
      if (roleFilter) params.set('role', roleFilter);
      if (statusFilter) params.set('status_filter', statusFilter);
      if (search.trim()) params.set('search', search.trim());
      return (await api.get<PaginatedUsers>(`/admin/users?${params}`)).data;
    },
  });

  if (isLoading) return <div className="animate-pulse h-32 bg-gray-200 dark:bg-gray-700 rounded" />;

  const users = data?.items ?? [];

  return (
    <div>
      <PageHeader
        title="Users"
        icon={Users}
        subtitle="Manage user accounts and permissions"
        actions={
          <button onClick={() => setShowCreate(true)} className="flex items-center gap-2 px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700">
            <Plus className="h-4 w-4" />
            Create User
          </button>
        }
      />
      <div className="mb-6 flex flex-wrap items-center gap-4 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-800/50 px-4 py-3">
        <Filter className="h-4 w-4 text-gray-500 dark:text-gray-400" />
        <label htmlFor="admin-users-search" className="text-sm font-medium">Search</label>
        <div className="relative">
          <Search className="h-4 w-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            id="admin-users-search"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            placeholder="Email or name"
            className="pl-9 pr-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-sm w-56"
          />
        </div>
        <label htmlFor="admin-users-role" className="text-sm font-medium">Role</label>
        <select
          id="admin-users-role"
          value={roleFilter}
          onChange={(e) => { setRoleFilter(e.target.value); setPage(1); }}
          className="px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-sm"
        >
          <option value="">All</option>
          <option value="user">User</option>
          <option value="viewer">Viewer</option>
          <option value="admin">Admin</option>
        </select>
        <label htmlFor="admin-users-status" className="text-sm font-medium">Status</label>
        <select
          id="admin-users-status"
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          className="px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-sm"
        >
          <option value="">All</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </select>
        {(search || roleFilter || statusFilter) && (
          <button
            type="button"
            onClick={() => { setSearch(''); setRoleFilter(''); setStatusFilter(''); setPage(1); }}
            className="inline-flex items-center gap-1 px-3 py-2 rounded border border-gray-300 dark:border-gray-600 text-sm hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <X className="h-3 w-3" />
            Reset
          </button>
        )}
      </div>
      {showCreate && <CreateUserDialog onClose={() => setShowCreate(false)} />}
      {editingUser && <EditUserDialog user={editingUser} onClose={() => setEditingUser(null)} />}
      {deletingUser && (
        <ConfirmDialog
          title="Delete User"
          message={`Are you sure you want to delete ${deletingUser.email}? This action permanently removes this user and related data.`}
          confirmLabel="Delete"
          variant="danger"
          isPending={deleteMutation.isPending}
          onCancel={() => setDeletingUser(null)}
          onConfirm={() => deleteMutation.mutate(deletingUser.id)}
        />
      )}
      {actionError && (
        <div className="mb-4 p-3 rounded bg-red-50 dark:bg-red-900/20 text-red-600 text-sm">{actionError}</div>
      )}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden transition-shadow hover:shadow-lg">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-700">
            <tr>
              <SortableTh label="ID" sortKey="id" currentSort={sortBy} currentOrder={sortOrder} onSort={(k, o) => { setSortBy(k); setSortOrder(o); setPage(1); }} />
              <SortableTh label="Email" sortKey="email" currentSort={sortBy} currentOrder={sortOrder} onSort={(k, o) => { setSortBy(k); setSortOrder(o); setPage(1); }} />
              <SortableTh label="Name" sortKey="name" currentSort={sortBy} currentOrder={sortOrder} onSort={(k, o) => { setSortBy(k); setSortOrder(o); setPage(1); }} />
              <SortableTh label="Role" sortKey="role" currentSort={sortBy} currentOrder={sortOrder} onSort={(k, o) => { setSortBy(k); setSortOrder(o); setPage(1); }} />
              <SortableTh label="Status" sortKey="status" currentSort={sortBy} currentOrder={sortOrder} onSort={(k, o) => { setSortBy(k); setSortOrder(o); setPage(1); }} />
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {users.map((u) => (
              <tr key={u.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                <td className="px-6 py-4 text-sm">{u.id}</td>
                <td className="px-6 py-4 text-sm">
                  <span className="inline-flex items-center gap-2">
                    {u.email}
                    {u.id === currentUser?.id && (
                      <span
                        title="Current account"
                        className="inline-flex items-center gap-1 rounded-full border border-gray-300 dark:border-gray-600 px-2 py-0.5 text-xs text-gray-600 dark:text-gray-300"
                      >
                        <Lock className="h-3 w-3" />
                        You
                      </span>
                    )}
                  </span>
                </td>
                <td className="px-6 py-4 text-sm">{u.name || '—'}</td>
                <td className="px-6 py-4 text-sm">
                  <StatusBadge status={u.role} variant="role" />
                </td>
                <td className="px-6 py-4 text-sm">
                  <StatusBadge status={u.status} variant="status" />
                </td>
                <td className="px-6 py-4 text-sm">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setEditingUser(u)}
                      className="flex items-center gap-1 px-3 py-1 rounded bg-gray-200 dark:bg-gray-600 hover:bg-gray-300 dark:hover:bg-gray-500 text-sm"
                    >
                      <Pencil className="h-3 w-3" />
                      Edit
                    </button>
                    <button
                      type="button"
                      disabled={u.id === currentUser?.id}
                      onClick={() => { setActionError(''); setDeletingUser(u); }}
                      title={u.id === currentUser?.id ? 'You cannot delete your own account' : 'Delete user'}
                      className="flex items-center gap-1 px-3 py-1 rounded bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300 hover:bg-red-200 dark:hover:bg-red-900/50 text-sm disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-red-100 dark:disabled:hover:bg-red-900/30"
                    >
                      <Trash2 className="h-3 w-3" />
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {users.length === 0 && (
          <div className="p-8 text-center text-gray-500 flex flex-col items-center gap-2">
            <Users className="h-12 w-12 text-gray-400" />
            <p>{search || roleFilter || statusFilter ? 'No users match current filters.' : 'No users yet.'}</p>
          </div>
        )}
        {data && (
          <Pagination
            page={data.page}
            pageSize={data.page_size}
            total={data.total}
            totalPages={data.total_pages}
            onPageChange={setPage}
            onPageSizeChange={(n) => { setPageSize(n); setPage(1); }}
          />
        )}
      </div>
    </div>
  );
}
