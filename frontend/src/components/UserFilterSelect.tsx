import { Field, Select } from './ui/Field';

type Props = {
  users: { id: number; email: string }[];
  value: number | null;
  onChange: (userId: number | null) => void;
  label?: string;
  className?: string;
};

/** The "filter by user" control shared by the admin list views. */
export function UserFilterSelect({
  users,
  value,
  onChange,
  label = 'Filter by user',
  className = 'max-w-80',
}: Props) {
  return (
    <div className={className}>
      <Field label={label}>
        {(fieldProps) => (
          <Select
            {...fieldProps}
            value={value ?? ''}
            onChange={(e) => {
              const next = e.target.value;
              onChange(next === '' ? null : parseInt(next, 10));
            }}
          >
            <option value="">All users</option>
            {users.map((u) => (
              <option key={u.id} value={u.id}>
                {u.email} (user {u.id})
              </option>
            ))}
          </Select>
        )}
      </Field>
    </div>
  );
}
