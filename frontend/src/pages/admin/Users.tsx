import { Lock, Pencil, Plus, Trash2, Users, X } from 'lucide-react';
import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { errorMessage } from '../../lib/apiError';
import { CreateUserDialog } from '../../components/CreateUserDialog';
import { EditUserDialog } from '../../components/EditUserDialog';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { useAuth } from '../../store/AuthContext';
import { PageHeader } from '../../components/PageHeader';
import { SortableTh } from '../../components/SortableTh';
import { StatusBadge } from '../../components/StatusBadge';
import { Pagination } from '../../components/Pagination';
import { TableSkeleton } from '../../components/Skeleton';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Field, Input, Select } from '../../components/ui/Field';
import { FormError } from '../../components/ui/FormError';
import { EmptyState, ErrorState } from '../../components/ui/States';
import { TableShell, Tbody, Td, Th, Thead, Tr } from '../../components/ui/TableShell';

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
      setActionError(errorMessage(err, 'Failed to delete user'));
    },
  });

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['admin', 'users', page, pageSize, roleFilter, statusFilter, search, sortBy, sortOrder],
    queryFn: async () => {
      const params = new URLSearchParams({
        page: String(page),
        page_size: String(pageSize),
        sort_by: sortBy,
        sort_order: sortOrder,
      });
      if (roleFilter) params.set('role', roleFilter);
      if (statusFilter) params.set('status_filter', statusFilter);
      if (search.trim()) params.set('search', search.trim());
      return (await api.get<PaginatedUsers>(`/admin/users?${params}`)).data;
    },
  });

  const users = data?.items ?? [];
  const isFiltered = search !== '' || roleFilter !== '' || statusFilter !== '';

  const handleSort = (key: string, order: 'asc' | 'desc') => {
    setSortBy(key);
    setSortOrder(order);
    setPage(1);
  };

  const sortProps = { currentSort: sortBy, currentOrder: sortOrder, onSort: handleSort };

  return (
    <div>
      <PageHeader
        title="Users"
        icon={Users}
        subtitle="Manage user accounts and permissions"
        actions={
          <Button icon={Plus} onClick={() => setShowCreate(true)}>
            Create User
          </Button>
        }
      />

      <div className="mb-4 flex flex-wrap items-end gap-4">
        <Field label="Search" className="w-56">
          {(fieldProps) => (
            <Input
              {...fieldProps}
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              placeholder="Email or name"
            />
          )}
        </Field>
        <Field label="Role" className="w-40">
          {(fieldProps) => (
            <Select
              {...fieldProps}
              value={roleFilter}
              onChange={(e) => {
                setRoleFilter(e.target.value);
                setPage(1);
              }}
            >
              <option value="">All roles</option>
              <option value="user">User</option>
              <option value="viewer">Viewer</option>
              <option value="admin">Admin</option>
            </Select>
          )}
        </Field>
        <Field label="Status" className="w-40">
          {(fieldProps) => (
            <Select
              {...fieldProps}
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
            >
              <option value="">All statuses</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </Select>
          )}
        </Field>
        {isFiltered && (
          <Button
            type="button"
            variant="secondary"
            size="sm"
            icon={X}
            onClick={() => {
              setSearch('');
              setRoleFilter('');
              setStatusFilter('');
              setPage(1);
            }}
          >
            Reset
          </Button>
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
      <FormError message={actionError} className="mb-4" />

      {isError ? (
        <ErrorState title="We couldn't load the user list" error={error} onRetry={() => refetch()} />
      ) : isLoading ? (
        <TableSkeleton columns={6} />
      ) : (
        <TableShell
          caption="User accounts"
          footer={
            users.length === 0 ? (
              <EmptyState
                icon={Users}
                title={isFiltered ? 'No users match these filters' : 'No users yet'}
                description={
                  isFiltered
                    ? 'Clear the search, role, or status filter to see the rest.'
                    : 'Create the first account to give someone access.'
                }
                action={
                  !isFiltered && (
                    <Button icon={Plus} size="sm" onClick={() => setShowCreate(true)}>
                      Create User
                    </Button>
                  )
                }
              />
            ) : (
              data && (
                <Pagination
                  page={data.page}
                  pageSize={data.page_size}
                  total={data.total}
                  totalPages={data.total_pages}
                  onPageChange={setPage}
                  onPageSizeChange={(n) => {
                    setPageSize(n);
                    setPage(1);
                  }}
                />
              )
            )
          }
        >
          <Thead>
            <tr>
              <SortableTh label="ID" sortKey="id" {...sortProps} />
              <SortableTh label="Email" sortKey="email" {...sortProps} />
              <SortableTh label="Name" sortKey="name" {...sortProps} />
              <SortableTh label="Role" sortKey="role" {...sortProps} />
              <SortableTh label="Status" sortKey="status" {...sortProps} />
              <Th className="w-40 text-right">Actions</Th>
            </tr>
          </Thead>
          <Tbody>
            {users.map((u) => (
              <Tr key={u.id}>
                <Td className="tabular-nums text-ink-subtle">{u.id}</Td>
                <Td className="font-medium">
                  <span className="inline-flex items-center gap-2">
                    {u.email}
                    {u.id === currentUser?.id && (
                      <Badge tone="neutral" icon={Lock}>
                        You
                      </Badge>
                    )}
                  </span>
                </Td>
                <Td className="text-ink-muted">{u.name || 'Not set'}</Td>
                <Td>
                  <StatusBadge status={u.role} variant="role" />
                </Td>
                <Td>
                  <StatusBadge status={u.status} variant="status" />
                </Td>
                <Td className="text-right">
                  <div className="flex items-center justify-end gap-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      icon={Pencil}
                      onClick={() => setEditingUser(u)}
                    >
                      Edit
                    </Button>
                    <Button
                      type="button"
                      variant="danger"
                      size="sm"
                      icon={Trash2}
                      disabled={u.id === currentUser?.id}
                      title={
                        u.id === currentUser?.id ? 'You cannot delete your own account' : 'Delete user'
                      }
                      onClick={() => {
                        setActionError('');
                        setDeletingUser(u);
                      }}
                    >
                      Delete
                    </Button>
                  </div>
                </Td>
              </Tr>
            ))}
          </Tbody>
        </TableShell>
      )}
    </div>
  );
}
