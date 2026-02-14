import { describe, it, expect } from 'vitest'
import {
  formatLocalDateTime,
  utcTimeToLocal,
  localTimeToUtc,
  formatScheduleSummary,
} from './formatDateTime'

describe('formatLocalDateTime', () => {
  it('returns em dash for null', () => {
    expect(formatLocalDateTime(null)).toBe('—')
  })

  it('returns em dash for undefined', () => {
    expect(formatLocalDateTime(undefined)).toBe('—')
  })

  it('returns em dash for empty string', () => {
    expect(formatLocalDateTime('')).toBe('—')
  })

  it('formats valid ISO 8601 string to locale string', () => {
    const iso = '2025-02-13T12:34:56.789Z'
    const result = formatLocalDateTime(iso)
    const parsed = new Date(iso)
    expect(result).toBe(parsed.toLocaleString())
    expect(result).not.toBe(iso)
    expect(result).toMatch(/\d/) // contains digits
  })

  it('formats ISO date without time component', () => {
    const iso = '2025-02-13'
    const result = formatLocalDateTime(iso)
    const parsed = new Date(iso)
    expect(result).toBe(parsed.toLocaleString())
  })

  it('returns raw value for invalid date string', () => {
    const invalid = 'not-a-date'
    expect(formatLocalDateTime(invalid)).toBe(invalid)
  })

  it('returns raw value when Date parsing yields NaN', () => {
    const invalid = 'invalid'
    expect(formatLocalDateTime(invalid)).toBe(invalid)
  })
})

describe('utcTimeToLocal', () => {
  it('converts UTC HH:MM to local time string', () => {
    const result = utcTimeToLocal('14:00', 'America/New_York')
    expect(result).toMatch(/\d{1,2}:\d{2}/)
    expect(result).not.toBe('14:00')
  })

  it('handles HH:MM format', () => {
    const result = utcTimeToLocal('09:00')
    expect(result).toMatch(/\d{1,2}:\d{2}/)
  })
})

describe('localTimeToUtc', () => {
  it('converts local HH:MM to UTC string', () => {
    const result = localTimeToUtc('09:00', 'America/New_York')
    expect(result).toMatch(/^\d{2}:\d{2}$/)
  })

  it('returns HH:MM format', () => {
    const result = localTimeToUtc('12:00')
    expect(result).toMatch(/^\d{2}:\d{2}$/)
  })
})

describe('formatScheduleSummary', () => {
  it('returns Default for null', () => {
    expect(formatScheduleSummary(null)).toBe('Default')
  })

  it('returns Default for empty schedule', () => {
    expect(formatScheduleSummary({})).toBe('Default')
  })

  it('returns Mon–Fri 9:00–17:00 for business hours', () => {
    const sched: Record<string, string | null> = {}
    ;['mon', 'tue', 'wed', 'thu', 'fri'].forEach((d) => {
      sched[`${d}_start_utc`] = '09:00'
      sched[`${d}_end_utc`] = '17:00'
    })
    ;['sat', 'sun'].forEach((d) => {
      sched[`${d}_start_utc`] = null
      sched[`${d}_end_utc`] = null
    })
    expect(formatScheduleSummary(sched)).toBe('Mon–Fri 9:00–17:00')
  })

  it('returns Custom for other schedules', () => {
    expect(formatScheduleSummary({ mon_start_utc: '10:00', mon_end_utc: '18:00' })).toBe('Custom')
  })
})
