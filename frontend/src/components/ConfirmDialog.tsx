import { Button } from './ui/Button';
import { Modal } from './ui/Modal';

type Props = {
  title: string;
  message: React.ReactNode;
  confirmLabel: string;
  variant?: 'danger' | 'neutral';
  onConfirm: () => void;
  onCancel: () => void;
  isPending?: boolean;
  icon?: React.ReactNode;
};

export function ConfirmDialog({
  title,
  message,
  confirmLabel,
  variant = 'neutral',
  onConfirm,
  onCancel,
  isPending = false,
  icon,
}: Props) {
  return (
    <Modal
      title={title}
      icon={icon}
      size="sm"
      onClose={onCancel}
      footer={
        <>
          <Button variant="secondary" onClick={onCancel} disabled={isPending}>
            Cancel
          </Button>
          <Button
            variant={variant === 'danger' ? 'danger' : 'primary'}
            onClick={onConfirm}
            isLoading={isPending}
          >
            {confirmLabel}
          </Button>
        </>
      }
    >
      <p className="text-sm text-ink-muted">{message}</p>
    </Modal>
  );
}
