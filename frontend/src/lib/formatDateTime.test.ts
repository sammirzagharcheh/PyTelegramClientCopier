import { describe, it, expect } from 'vitest'
import { formatLocalDateTime } from './formatDateTime'

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
