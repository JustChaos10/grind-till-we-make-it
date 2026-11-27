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

it.each([502, 503, 504])(
  'offers recovery steps for a non-JSON HTTP %i response',
  async (status) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status })))

    await expect(api('/api/flow-board')).rejects.toThrow(
      'The IndoFlow API is unavailable. Try again. If the problem continues, ask your administrator to check the API connection.',
    )
  },
)
