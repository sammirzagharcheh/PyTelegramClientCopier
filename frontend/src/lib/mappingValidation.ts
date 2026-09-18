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

const USERNAME_RE = /^[A-Za-z][A-Za-z0-9_]{4,31}$/;
const TME_RE = /^(?:https?:\/\/)?(?:www\.)?(?:t\.me|telegram\.me|telegram\.dog)\/(.+)$/i;

const CHAT_REF_HINT = 'Enter a chat ID, @username, or t.me link';

export function parseChatId(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const n = Number(trimmed);
  if (!Number.isSafeInteger(n) || n === 0) return null;
  return n;
}

/** Parse a pasted chat ref into a numeric ID or a username string for resolve-peer. */
export function parseChatRef(value: string): number | string | null {
  let q = value.trim();
  if (!q) return null;

  if (q.startsWith('@')) {
    q = q.slice(1).trim();
  }

  const tme = q.match(TME_RE);
  if (tme) {
    const rest = tme[1].split('?')[0].replace(/^\/+|\/+$/g, '');
    const lower = rest.toLowerCase();
    if (lower.startsWith('joinchat/') || rest.startsWith('+')) {
      return null;
    }
    if (lower.startsWith('c/')) {
      const parts = rest.split('/');
      if (parts.length >= 2 && /^\d+$/.test(parts[1])) {
        const n = Number(`-100${parts[1]}`);
        return Number.isSafeInteger(n) ? n : null;
      }
      return null;
    }
    q = rest.split('/')[0];
  }

  if (/^-?\d+$/.test(q)) {
    return parseChatId(q);
  }

  if (!USERNAME_RE.test(q)) return null;
  return q;
}

export function validateMappingRoute(values: MappingRouteValues): MappingRouteFieldErrors {
  const errors: MappingRouteFieldErrors = {};
  if (values.telegramAccountId == null) {
    errors.telegramAccountId = 'Select a Telegram account';
  }
  const src = parseChatRef(values.sourceChatId);
  const dst = parseChatRef(values.destChatId);
  if (src == null) {
    errors.sourceChatId = CHAT_REF_HINT;
  }
  if (dst == null) {
    errors.destChatId = CHAT_REF_HINT;
  }
  if (typeof src === 'number' && typeof dst === 'number' && src === dst) {
    errors.destChatId = 'Destination must differ from source';
  }
  return errors;
}

export function hasRouteErrors(errors: MappingRouteFieldErrors): boolean {
  return Object.keys(errors).length > 0;
}
