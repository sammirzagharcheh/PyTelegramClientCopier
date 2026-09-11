import { describe, it, expect } from 'vitest';
import {
  hasRouteErrors,
  parseChatId,
  validateMappingRoute,
} from './mappingValidation';

describe('mappingValidation', () => {
  it('parseChatId rejects invalid values', () => {
    expect(parseChatId('')).toBeNull();
    expect(parseChatId('abc')).toBeNull();
    expect(parseChatId('0')).toBeNull();
  });

  it('parseChatId accepts safe integers', () => {
    expect(parseChatId('-100123')).toBe(-100123);
    expect(parseChatId(' 42 ')).toBe(42);
  });

  it('validateMappingRoute requires account and distinct chats', () => {
    const errors = validateMappingRoute({
      telegramAccountId: null,
      sourceChatId: '-1001',
      destChatId: '-1002',
      sourceChatTitle: '',
      destChatTitle: '',
      useManualIds: false,
    });
    expect(errors.telegramAccountId).toBeTruthy();
    expect(hasRouteErrors(errors)).toBe(true);
  });

  it('validateMappingRoute rejects same source and dest', () => {
    const errors = validateMappingRoute({
      telegramAccountId: 1,
      sourceChatId: '-1001',
      destChatId: '-1001',
      sourceChatTitle: '',
      destChatTitle: '',
      useManualIds: true,
    });
    expect(errors.destChatId).toMatch(/differ/i);
  });
});
