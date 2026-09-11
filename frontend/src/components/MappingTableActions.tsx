import { Eye, Pencil, Trash2 } from 'lucide-react';
import { ActionDivider, IconAction, IconActionLink } from './ui/IconAction';

type Props = {
  mappingId: number;
  onEdit: () => void;
  onDelete: () => void;
  viewBasePath?: string;
};

export function MappingTableActions({ mappingId, onEdit, onDelete, viewBasePath }: Props) {
  const viewTo = viewBasePath ? `${viewBasePath}/${mappingId}` : `/mappings/${mappingId}`;
  return (
    <div className="flex items-center justify-end gap-0.5">
      <IconAction icon={Pencil} label="Edit mapping" onClick={onEdit} />
      <IconAction icon={Trash2} label="Delete mapping" tone="danger" onClick={onDelete} />
      <ActionDivider />
      <IconActionLink icon={Eye} label="View mapping details" to={viewTo} />
    </div>
  );
}
