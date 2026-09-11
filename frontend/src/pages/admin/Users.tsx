import { Pencil, Plus, Users } from 'lucide-react';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { CreateUserDialog } from '../../components/CreateUserDialog';
import { EditUserDialog } from '../../components/EditUserDialog';
import { PageHeader } from '../../components/PageHeader';
import { SortableTh } from '../../components/SortableTh';
import { StatusBadge } from '../../components/StatusBadge';
import { Pagination } from '../../components/Pagination';
import { TableSkeleton } from '../../components/Skeleton';
import { Button } from '../../components/ui/Button';
import { Field, Select } from '../../components/ui/Field';
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
  const [showCreate, setShowCreate] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [roleFilter, setRoleFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [sortBy, setSortBy] = useState<string>('id');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['admin', 'users', page, pageSize, roleFilter, statusFilter, sortBy, sortOrder],
    queryFn: async () => {
      const params = new URLSearchParams({ page: String(page), page_size: String(pageSize), sort_by: sortBy, sort_order: sortOrder });
      if (roleFilter) params.set('role', roleFilter);
      if (statusFilter) params.set('status_filter', statusFilter);
      return (await api.get<PaginatedUsers>(`/admin/users?${params}`)).data;
    },
  });

  const users = data?.items ?? [];
  const isFiltered = roleFilter !== '' || statusFilter !== '';

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

      <div className="mb-4 flex flex-wrap gap-4">
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
      </div>

      {showCreate && <CreateUserDialog onClose={() => setShowCreate(false)} />}
      {editingUser && <EditUserDialog user={editingUser} onClose={() => setEditingUser(null)} />}

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
                    ? 'Clear the role or status filter to see the rest.'
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
              <Th className="w-28 text-right">Actions</Th>
            </tr>
          </Thead>
          <Tbody>
            {users.map((u) => (
              <Tr key={u.id}>
                <Td className="tabular-nums text-ink-subtle">{u.id}</Td>
                <Td className="font-medium">{u.email}</Td>
                <Td className="text-ink-muted">{u.name || 'Not set'}</Td>
                <Td>
                  <StatusBadge status={u.role} variant="role" />
                </Td>
                <Td>
                  <StatusBadge status={u.status} variant="status" />
                </Td>
                <Td className="text-right">
                  <Button
                    variant="secondary"
                    size="sm"
                    icon={Pencil}
                    onClick={() => setEditingUser(u)}
                  >
                    Edit
                  </Button>
                </Td>
              </Tr>
            ))}
          </Tbody>
        </TableShell>
      )}
    </div>
  );
}
