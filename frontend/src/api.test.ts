import { afterEach, expect, it, vi } from 'vitest'
import { api } from './api'

afterEach(() => vi.unstubAllGlobals())

it.each([
  [401, 'Authentication required'],
  [403, 'Access denied'],
])('explains HTTP %i even when the API returns detail text', async (status, reason) => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue(Response.json({ detail: 'Valid bearer token required' }, { status })),
  )
  await expect(api('/api/catalog')).rejects.toThrow(
    `${reason}. Ask the administrator to check access through the API proxy.`,
  )
})
