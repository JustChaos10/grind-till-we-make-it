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

const board = {
  total_wip_orders: 0,
  avg_wip_age_hours: null,
  queues: [],
  active_bottleneck_alerts: [],
}
const catalog = { resources: [], work_orders: [] }
const optimize = {
  comparison: { baseline: { throughput: null }, optimized: {}, delta: { late_orders: null } },
  gantt: { baseline: [], optimized: [] },
  why_late: { baseline: [], optimized: [] },
}
const simulate = {
  scenario_inputs: { down_resource_ids: [], rush_order_ids: [], demand_spike_pct: 0 },
  reference_metrics: {},
  scenario_metrics: { throughput: null },
  delta: {},
  due_date_impact: [],
  why_late: [],
  gantt: [],
}

it.each([
  ['/api/flow-board', board],
  ['/api/catalog', catalog],
  ['/api/schedule/optimize', optimize],
  ['/api/schedule/simulate', simulate],
])('accepts valid %s data including unavailable metrics', async (path, body) => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(Response.json(body)))
  await expect(api(path)).resolves.toEqual(body)
})

it.each([
  ['/api/flow-board', { ...board, queues: [{ stage: 'Molding', queue_depth: '3' }] }],
  ['/api/catalog', { ...catalog, resources: [{ id: 'r1' }] }],
  ['/api/schedule/optimize', { ...optimize, gantt: { baseline: [{}], optimized: [] } }],
  ['/api/schedule/simulate', { ...simulate, scenario_metrics: { throughput: 'many' } }],
])('rejects malformed successful %s responses with an actionable error', async (path, body) => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(Response.json(body)))
  await expect(api(path)).rejects.toThrow(
    `The API response contains invalid data for ${path}. Retry`,
  )
})

it('reports a successful response containing invalid JSON', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('<html>', { status: 200 })))
  await expect(api('/api/catalog')).rejects.toThrow(
    'The API response contains invalid data for /api/catalog',
  )
})
