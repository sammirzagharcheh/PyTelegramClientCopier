import { describe, it, expect } from 'vitest';
import { isStartableWorkerAccount } from '../hooks/useActiveAccounts';
import { formatWorkerSessionLabel } from './workerLabel';

describe('worker startable accounts', () => {
  it('allows user accounts with a session file', () => {
    expect(isStartableWorkerAccount({ type: 'user', session_path: '/tmp/a.session' })).toBe(true);
    expect(isStartableWorkerAccount({ type: 'user', session_path: null })).toBe(false);
  });

  it('allows bot accounts', () => {
    expect(isStartableWorkerAccount({ type: 'bot', session_path: null })).toBe(true);
  });
});

describe('formatWorkerSessionLabel', () => {
  it('labels bot registry sentinels', () => {
    expect(formatWorkerSessionLabel('bot://9', 9)).toBe('Bot #9');
    expect(formatWorkerSessionLabel('/data/u.session', 1)).toBe('/data/u.session');
  });
});
