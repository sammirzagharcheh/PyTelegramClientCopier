import { Field, Input } from './ui/Field';

type Props = {
  name: string;
  sourceChatId: string;
  destChatId: string;
  onNameChange: (value: string) => void;
  onSourceChatIdChange: (value: string) => void;
  onDestChatIdChange: (value: string) => void;
  errors?: { name?: string; sourceChatId?: string; destChatId?: string };
};

export function MappingFormFields({
  name,
  sourceChatId,
  destChatId,
  onNameChange,
  onSourceChatIdChange,
  onDestChatIdChange,
  errors = {},
}: Props) {
  return (
    <>
      <Field label="Name" hint="Optional. Only used to label the mapping." error={errors.name}>
        {(fieldProps) => (
          <Input
            {...fieldProps}
            type="text"
            value={name}
            onChange={(e) => onNameChange(e.target.value)}
            placeholder="Announcements to mirror"
            invalid={Boolean(errors.name)}
          />
        )}
      </Field>
      <Field
        label="Source chat ID"
        hint="Copy from @userinfobot. Channels look like -1001234567890."
        error={errors.sourceChatId}
        required
      >
        {(fieldProps) => (
          <Input
            {...fieldProps}
            type="text"
            inputMode="numeric"
            value={sourceChatId}
            onChange={(e) => onSourceChatIdChange(e.target.value)}
            className="font-mono"
            placeholder="-1001234567890"
            required
            invalid={Boolean(errors.sourceChatId)}
          />
        )}
      </Field>
      <Field label="Destination chat ID" error={errors.destChatId} required>
        {(fieldProps) => (
          <Input
            {...fieldProps}
            type="text"
            inputMode="numeric"
            value={destChatId}
            onChange={(e) => onDestChatIdChange(e.target.value)}
            className="font-mono"
            placeholder="-1009876543210"
            required
            invalid={Boolean(errors.destChatId)}
          />
        )}
      </Field>
    </>
  );
}
