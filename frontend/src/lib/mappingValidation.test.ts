import { describe, it, expect } from 'vitest';
import {
  hasRouteErrors,
  parseChatId,
  parseChatRef,
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

  it('parseChatRef accepts @username, t.me links, and numeric IDs', () => {
    expect(parseChatRef('@MyChannel')).toBe('MyChannel');
    expect(parseChatRef('https://t.me/MyChannel')).toBe('MyChannel');
    expect(parseChatRef('t.me/MyChannel/12')).toBe('MyChannel');
    expect(parseChatRef('-1001234567890')).toBe(-1001234567890);
    expect(parseChatRef('https://t.me/c/1234567890/5')).toBe(-1001234567890);
  });

  it('parseChatRef rejects invite links and empty values', () => {
    expect(parseChatRef('')).toBeNull();
    expect(parseChatRef('https://t.me/+AbCdEf')).toBeNull();
    expect(parseChatRef('https://t.me/joinchat/AAAA')).toBeNull();
    expect(parseChatRef('ab')).toBeNull();
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

  it('validateMappingRoute allows @username in manual fields', () => {
    const errors = validateMappingRoute({
      telegramAccountId: 1,
      sourceChatId: '@srcchan',
      destChatId: 'https://t.me/dstchan',
      sourceChatTitle: '',
      destChatTitle: '',
      useManualIds: true,
    });
    expect(errors).toEqual({});
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
