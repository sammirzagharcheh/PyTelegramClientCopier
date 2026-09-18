type Props = {
  title?: string | null;
  chatId: number;
  messageId?: number | null;
};

export function MessageRef({ title, chatId, messageId }: Props) {
  return (
    <span className="block min-w-0">
      {title && <span className="block truncate text-ink">{title}</span>}
      <span className="block font-mono text-xs tabular-nums text-ink-subtle">
        {chatId}
        {messageId != null ? ` / ${messageId}` : ''}
      </span>
    </span>
  );
}
