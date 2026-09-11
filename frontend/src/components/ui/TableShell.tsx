type Props = {
  children: React.ReactNode;
  /** Rendered under the table: usually an empty state, error, or pagination. */
  footer?: React.ReactNode;
  caption?: string;
  className?: string;
};

/**
 * Consistent chrome for every data table: one border, one radius, and a
 * horizontal scroll container so narrow viewports scroll the table instead of
 * clipping columns.
 */
export function TableShell({ children, footer, caption, className = '' }: Props) {
  return (
    <div className={`overflow-hidden rounded-surface border border-line bg-surface-raised ${className}`.trim()}>
      <div className="overflow-x-auto">
        <table className="min-w-full text-left">
          {caption && <caption className="sr-only">{caption}</caption>}
          {children}
        </table>
      </div>
      {footer}
    </div>
  );
}

export function Th({
  children,
  className = '',
  ...rest
}: React.ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      scope="col"
      className={`px-4 py-2.5 text-xs font-semibold tracking-wide text-ink-subtle uppercase ${className}`.trim()}
      {...rest}
    >
      {children}
    </th>
  );
}

export function Thead({ children }: { children: React.ReactNode }) {
  return <thead className="border-b border-line bg-surface-sunken">{children}</thead>;
}

export function Tbody({ children }: { children: React.ReactNode }) {
  return <tbody className="divide-y divide-line">{children}</tbody>;
}

export function Tr({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <tr className={`transition-colors hover:bg-surface-hover ${className}`.trim()}>{children}</tr>
  );
}

export function Td({
  children,
  className = '',
  ...rest
}: React.TdHTMLAttributes<HTMLTableCellElement>) {
  return (
    <td className={`px-4 py-3 text-sm text-ink ${className}`.trim()} {...rest}>
      {children}
    </td>
  );
}
