const USER_PAGE_LABELS: Record<string, string> = {
  dashboard: 'Dashboard',
  accounts: 'Accounts',
  mappings: 'Mappings',
  workers: 'Workers',
  'worker-logs': 'Worker logs',
  'webhook-logs': 'Webhook logs',
  logs: 'Message logs',
  'message-index': 'Message index',
  schedule: 'Schedule',
  'media-assets': 'Media assets',
};

const ADMIN_CHILD_LABELS: Record<string, string> = {
  users: 'Users',
  mappings: 'Mappings',
  logs: 'Logs',
  'message-index': 'Message index',
  workers: 'Workers',
  'worker-logs': 'Worker logs',
  'webhook-logs': 'Webhook logs',
  'media-assets': 'Media assets',
  settings: 'Settings',
};

export type BreadcrumbItem = { to: string; label: string };

function normalizePathname(pathname: string): string {
  if (pathname.length > 1 && pathname.endsWith('/')) {
    return pathname.replace(/\/+$/, '');
  }
  return pathname || '/';
}

/**
 * Builds desk-friendly breadcrumbs for known app routes. Unknown paths fall back to title-cased segments.
 */
export function getBreadcrumbs(pathname: string): BreadcrumbItem[] {
  const p = normalizePathname(pathname);

  if (p === '/' || p === '') {
    return [];
  }

  if (p === '/admin') {
    return [{ to: '/admin', label: 'Dashboard' }];
  }

  const userMapping = p.match(/^\/mappings\/(\d+)$/);
  if (userMapping) {
    return [
      { to: '/mappings', label: 'Mappings' },
      { to: p, label: `Mapping #${userMapping[1]}` },
    ];
  }

  const adminMapping = p.match(/^\/admin\/mappings\/(\d+)$/);
  if (adminMapping) {
    return [
      { to: '/admin', label: 'Admin' },
      { to: '/admin/mappings', label: 'Mappings' },
      { to: p, label: `Mapping #${adminMapping[1]}` },
    ];
  }

  const adminChild = p.match(/^\/admin\/([^/]+)$/);
  if (adminChild) {
    const key = adminChild[1];
    const label = ADMIN_CHILD_LABELS[key];
    if (label) {
      return [{ to: '/admin', label: 'Admin' }, { to: p, label }];
    }
  }

  const userTop = p.match(/^\/([^/]+)$/);
  if (userTop) {
    const key = userTop[1];
    const label = USER_PAGE_LABELS[key];
    if (label) {
      return [{ to: p, label }];
    }
  }

  const segments = p.split('/').filter(Boolean);
  let prefix = '';
  return segments.map((seg) => {
    prefix += `/${seg}`;
    const raw = decodeURIComponent(seg.replace(/-/g, ' '));
    const label = raw.length ? raw.charAt(0).toUpperCase() + raw.slice(1) : seg;
    return { to: prefix, label };
  });
}
