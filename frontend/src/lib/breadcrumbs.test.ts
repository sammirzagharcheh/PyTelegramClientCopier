import { describe, expect, it } from 'vitest';
import { getBreadcrumbs } from './breadcrumbs';

describe('getBreadcrumbs', () => {
  it('returns empty for root', () => {
    expect(getBreadcrumbs('/')).toEqual([]);
    expect(getBreadcrumbs('')).toEqual([]);
  });

  it('handles admin dashboard', () => {
    expect(getBreadcrumbs('/admin')).toEqual([{ to: '/admin', label: 'Dashboard' }]);
  });

  it('handles admin child routes', () => {
    expect(getBreadcrumbs('/admin/users')).toEqual([
      { to: '/admin', label: 'Admin' },
      { to: '/admin/users', label: 'Users' },
    ]);
    expect(getBreadcrumbs('/admin/settings')).toEqual([
      { to: '/admin', label: 'Admin' },
      { to: '/admin/settings', label: 'Settings' },
    ]);
  });

  it('handles admin mapping detail', () => {
    expect(getBreadcrumbs('/admin/mappings/42')).toEqual([
      { to: '/admin', label: 'Admin' },
      { to: '/admin/mappings', label: 'Mappings' },
      { to: '/admin/mappings/42', label: 'Mapping #42' },
    ]);
  });

  it('handles user top-level routes', () => {
    expect(getBreadcrumbs('/dashboard')).toEqual([{ to: '/dashboard', label: 'Dashboard' }]);
    expect(getBreadcrumbs('/worker-logs')).toEqual([{ to: '/worker-logs', label: 'Worker logs' }]);
  });

  it('handles user mapping detail', () => {
    expect(getBreadcrumbs('/mappings/7')).toEqual([
      { to: '/mappings', label: 'Mappings' },
      { to: '/mappings/7', label: 'Mapping #7' },
    ]);
  });

  it('strips trailing slashes', () => {
    expect(getBreadcrumbs('/accounts/')).toEqual([{ to: '/accounts', label: 'Accounts' }]);
  });

  it('falls back for unknown paths', () => {
    expect(getBreadcrumbs('/unknown/route')).toEqual([
      { to: '/unknown', label: 'Unknown' },
      { to: '/unknown/route', label: 'Route' },
    ]);
  });
});
