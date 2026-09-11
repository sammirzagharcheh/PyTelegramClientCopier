export type MappingRouteValues = {
  telegramAccountId: number | null;
  sourceChatId: string;
  destChatId: string;
  sourceChatTitle: string;
  destChatTitle: string;
  useManualIds: boolean;
};

export type MappingRouteFieldErrors = {
  telegramAccountId?: string;
  sourceChatId?: string;
  destChatId?: string;
};

export function parseChatId(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const n = Number(trimmed);
  if (!Number.isSafeInteger(n) || n === 0) return null;
  return n;
}

export function validateMappingRoute(values: MappingRouteValues): MappingRouteFieldErrors {
  const errors: MappingRouteFieldErrors = {};
  if (values.telegramAccountId == null) {
    errors.telegramAccountId = 'Select a Telegram account';
  }
  const src = parseChatId(values.sourceChatId);
  const dst = parseChatId(values.destChatId);
  if (src == null) {
    errors.sourceChatId = 'Select or enter a valid source chat ID';
  }
  if (dst == null) {
    errors.destChatId = 'Select or enter a valid destination chat ID';
  }
  if (src != null && dst != null && src === dst) {
    errors.destChatId = 'Destination must differ from source';
  }
  return errors;
}

export function hasRouteErrors(errors: MappingRouteFieldErrors): boolean {
  return Object.keys(errors).length > 0;
}
