type Props = {
  title?: string | null;
  id: number;
};

/**
 * Channel titles are optional, so the numeric id is always shown: it is what
 * users paste back into Telegram tooling when something needs checking.
 */
export function ChannelCell({ title, id }: Props) {
  if (!title) {
    return <span className="font-mono text-xs tabular-nums text-ink">{id}</span>;
  }
  return (
    <span className="block min-w-0">
      <span className="block truncate text-ink">{title}</span>
      <span className="block font-mono text-xs tabular-nums text-ink-subtle">{id}</span>
    </span>
  );
}
