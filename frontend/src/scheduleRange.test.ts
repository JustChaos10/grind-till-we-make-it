import { describe, expect, it } from 'vitest'
import { scheduleEndHour } from './scheduleRange'

describe('scheduleEndHour', () => {
  it('keeps a minimum 24-hour view and includes the end of a large schedule', () => {
    expect(scheduleEndHour([])).toBe(24)
    const operations = Array.from({ length: 200_000 }, (_, index) => ({ end_hour: index }))
    expect(scheduleEndHour(operations)).toBe(199_999)
  })
})
