type Props = {
  name: string;
  sourceChatId: string;
  destChatId: string;
  onNameChange: (value: string) => void;
  onSourceChatIdChange: (value: string) => void;
  onDestChatIdChange: (value: string) => void;
  errors?: { name?: string; sourceChatId?: string; destChatId?: string };
};

const inputClass =
  'w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700';

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
      <div>
        <label className="block text-sm font-medium mb-1">Name (optional)</label>
        <input
          type="text"
          value={name}
          onChange={(e) => onNameChange(e.target.value)}
          className={inputClass}
          placeholder="Source to Dest"
          aria-invalid={!!errors.name}
          aria-describedby={errors.name ? 'name-error' : undefined}
        />
        {errors.name && (
          <p id="name-error" className="text-xs text-red-600 mt-1">
            {errors.name}
          </p>
        )}
      </div>
      <div>
        <label className="block text-sm font-medium mb-1">Source Chat ID</label>
        <input
          type="text"
          value={sourceChatId}
          onChange={(e) => onSourceChatIdChange(e.target.value)}
          className={inputClass}
          placeholder="-1001234567890"
          required
          aria-invalid={!!errors.sourceChatId}
          aria-describedby={errors.sourceChatId ? 'source-error' : undefined}
        />
        <p className="text-xs text-gray-500 mt-1">Use @userinfobot to get chat IDs</p>
        {errors.sourceChatId && (
          <p id="source-error" className="text-xs text-red-600 mt-1">
            {errors.sourceChatId}
          </p>
        )}
      </div>
      <div>
        <label className="block text-sm font-medium mb-1">Destination Chat ID</label>
        <input
          type="text"
          value={destChatId}
          onChange={(e) => onDestChatIdChange(e.target.value)}
          className={inputClass}
          placeholder="-1009876543210"
          required
          aria-invalid={!!errors.destChatId}
          aria-describedby={errors.destChatId ? 'dest-error' : undefined}
        />
        {errors.destChatId && (
          <p id="dest-error" className="text-xs text-red-600 mt-1">
            {errors.destChatId}
          </p>
        )}
      </div>
    </>
  );
}
