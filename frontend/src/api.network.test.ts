import { afterEach, expect, it, vi } from 'vitest'
import { api } from './api'

afterEach(() => vi.unstubAllGlobals())

it('explains a network failure and preserves cancellation', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
  await expect(api('/api/flow-board')).rejects.toThrow(
    'Could not connect to the IndoFlow API. Check the connection and try again.',
  )

  const abort = new DOMException('Cancelled', 'AbortError')
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(abort))
  await expect(api('/api/flow-board')).rejects.toBe(abort)
})
