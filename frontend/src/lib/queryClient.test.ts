import { describe, it, expect } from 'vitest';
import { createQueryClient, queryClientDefaultOptions } from './queryClient';

describe('queryClient', () => {
  it('default options have 60s staleTime', () => {
    expect(queryClientDefaultOptions.defaultOptions.queries.staleTime).toBe(60 * 1000);
  });

  it('default options have 5min gcTime', () => {
    expect(queryClientDefaultOptions.defaultOptions.queries.gcTime).toBe(5 * 60 * 1000);
  });

  it('default options disable refetchOnWindowFocus', () => {
    expect(queryClientDefaultOptions.defaultOptions.queries.refetchOnWindowFocus).toBe(false);
  });

  it('default options have retry 1', () => {
    expect(queryClientDefaultOptions.defaultOptions.queries.retry).toBe(1);
  });

  it('createQueryClient returns a QueryClient with these defaults', () => {
    const client = createQueryClient();
    const defaultOpts = client.getDefaultOptions().queries;
    expect(defaultOpts?.staleTime).toBe(60 * 1000);
    expect(defaultOpts?.gcTime).toBe(5 * 60 * 1000);
    expect(defaultOpts?.refetchOnWindowFocus).toBe(false);
  });
});
