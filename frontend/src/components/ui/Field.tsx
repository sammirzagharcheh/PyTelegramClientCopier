import { forwardRef, useId } from 'react';

const controlBase =
  'w-full rounded-control border bg-surface-raised px-3 text-sm text-ink ' +
  'transition-colors placeholder:text-ink-subtle disabled:cursor-not-allowed disabled:opacity-60';

function borderFor(invalid?: boolean) {
  return invalid ? 'border-red-500 dark:border-red-400' : 'border-line-strong hover:border-ink-subtle';
}

type FieldProps = {
  label: string;
  children: (props: { id: string; 'aria-describedby'?: string; 'aria-invalid'?: true }) => React.ReactNode;
  hint?: string;
  error?: string;
  required?: boolean;
  className?: string;
};

/**
 * Label above, control, then hint and error below, per the skill's form rules.
 * The render prop exists so the label, hint, and error are wired to the control
 * by id without every caller having to invent one.
 */
export function Field({ label, children, hint, error, required, className = '' }: FieldProps) {
  const id = useId();
  const hintId = `${id}-hint`;
  const errorId = `${id}-error`;
  const describedBy = [hint ? hintId : null, error ? errorId : null].filter(Boolean).join(' ');

  return (
    <div className={`flex flex-col gap-1.5 ${className}`.trim()}>
      <label htmlFor={id} className="text-sm font-medium text-ink">
        {label}
        {required && (
          <span className="ml-1 text-red-600 dark:text-red-400" aria-hidden>
            *
          </span>
        )}
      </label>
      {children({
        id,
        'aria-describedby': describedBy || undefined,
        'aria-invalid': error ? true : undefined,
      })}
      {hint && !error && (
        <p id={hintId} className="text-xs text-ink-subtle">
          {hint}
        </p>
      )}
      {error && (
        <p id={errorId} className="text-xs font-medium text-red-600 dark:text-red-400">
          {error}
        </p>
      )}
    </div>
  );
}

export function Input({
  className = '',
  invalid,
  ...rest
}: React.InputHTMLAttributes<HTMLInputElement> & { invalid?: boolean }) {
  return <input className={`${controlBase} ${borderFor(invalid)} h-9.5 ${className}`} {...rest} />;
}

export function Select({
  className = '',
  invalid,
  children,
  ...rest
}: React.SelectHTMLAttributes<HTMLSelectElement> & { invalid?: boolean }) {
  return (
    <select className={`${controlBase} ${borderFor(invalid)} h-9.5 ${className}`} {...rest}>
      {children}
    </select>
  );
}

export const Textarea = forwardRef<
  HTMLTextAreaElement,
  React.TextareaHTMLAttributes<HTMLTextAreaElement> & { invalid?: boolean }
>(function Textarea({ className = '', invalid, ...rest }, ref) {
  return (
    <textarea
      ref={ref}
      className={`${controlBase} ${borderFor(invalid)} py-2 ${className}`}
      {...rest}
    />
  );
});
