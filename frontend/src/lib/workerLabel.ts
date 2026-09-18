export function formatWorkerSessionLabel(sessionPath: string, accountId?: number): string {
  if (sessionPath.startsWith('bot://')) {
    return accountId != null ? `Bot #${accountId}` : 'Bot worker';
  }
  return sessionPath;
}
