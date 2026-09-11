export const DEVICE_TZ_VALUE = '__device__';

export function getTimezoneUtcOffset(tz: string): string {
  try {
    const formatter = new Intl.DateTimeFormat('en', {
      timeZone: tz,
      timeZoneName: 'longOffset',
    });
    const str = formatter.format(new Date());
    const match = str.match(/GMT([+-]\d{1,2}:\d{2})/);
    return match ? `UTC${match[1]}` : '';
  } catch {
    return '';
  }
}
