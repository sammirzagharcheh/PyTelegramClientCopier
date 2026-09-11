import { Eye, Pencil, Trash2 } from 'lucide-react';
import { ActionDivider, IconAction } from './ui/IconAction';

type Props = {
  onEdit: () => void;
  onView: () => void;
  onDelete: () => void;
};

export function AccountTableActions({ onEdit, onView, onDelete }: Props) {
  return (
    <div className="flex items-center justify-end gap-0.5">
      <IconAction icon={Pencil} label="Edit account" onClick={onEdit} />
      <IconAction icon={Trash2} label="Delete account" tone="danger" onClick={onDelete} />
      <ActionDivider />
      <IconAction icon={Eye} label="View account details" onClick={onView} />
    </div>
  );
}
