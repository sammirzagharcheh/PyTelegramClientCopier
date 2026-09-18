import { describe, it, expect, vi, beforeEach } from 'vitest';
import { api } from './api';
import { resolveMappingRouteChats } from './peerResolve';

vi.mock('./api', () => ({
  api: { post: vi.fn() },
}));

describe('resolveMappingRouteChats', () => {
  beforeEach(() => {
    vi.mocked(api.post).mockReset();
  });

  it('skips Telegram lookup for numeric IDs', async () => {
    const result = await resolveMappingRouteChats(1, '-1001', '-1002', 'Src', 'Dst');
    expect(result).toEqual({
      source_chat_id: -1001,
      dest_chat_id: -1002,
      source_chat_title: 'Src',
      dest_chat_title: 'Dst',
    });
    expect(api.post).not.toHaveBeenCalled();
  });

  it('resolves @username then returns integer ids', async () => {
    vi.mocked(api.post).mockImplementation(async (_url, body) => {
      const query = (body as { query: string }).query;
      if (query === '@srcchan') {
        return {
          data: {
            chat_id: -100111,
            title: 'Src',
            username: 'srcchan',
            dialog_type: 'channel',
          },
        };
      }
      return {
        data: {
          chat_id: -100222,
          title: 'Dst',
          username: 'dstchan',
          dialog_type: 'channel',
        },
      };
    });

    const result = await resolveMappingRouteChats(7, '@srcchan', '@dstchan');
    expect(result.source_chat_id).toBe(-100111);
    expect(result.dest_chat_id).toBe(-100222);
    expect(result.source_chat_title).toBe('Src');
    expect(result.dest_chat_title).toBe('Dst');
    expect(api.post).toHaveBeenNthCalledWith(1, '/accounts/7/resolve-peer', { query: '@srcchan' });
    expect(api.post).toHaveBeenNthCalledWith(2, '/accounts/7/resolve-peer', { query: '@dstchan' });
  });

  it('rejects when resolved chats are the same', async () => {
    vi.mocked(api.post).mockResolvedValue({
      data: { chat_id: -100111, title: 'Same', username: 'x', dialog_type: 'channel' },
    });
    await expect(resolveMappingRouteChats(1, '@a', '@b')).rejects.toThrow(/differ/i);
  });
});
