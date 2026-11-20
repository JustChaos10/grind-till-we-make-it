import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App, { Gantt, type Operation } from './App'
import { api, fmt } from './api'

const emptyBoard = {
  total_wip_orders: 0,
  avg_wip_age_hours: 0,
  queues: [],
  active_bottleneck_alerts: [],
}

function mockApi() {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const path = String(input)
    const body = path.endsWith('/api/flow-board')
      ? emptyBoard
      : path.endsWith('/api/catalog')
        ? { resources: [], work_orders: [] }
        : { message: 'Synthetic demo data loaded' }
    return { ok: true, status: 200, statusText: 'OK', json: async () => body } as Response
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

function makeCatalog() {
  return {
    resources: [
      {
        id: 'res-1',
        name: 'Furnace 1',
        plant: 'Example plant',
        stage: 'Sintering',
        status: 'ACTIVE',
      },
    ],
    work_orders: [
      {
        id: 'wo-1',
        wo_number: 'WO-001',
        sku_code: 'SKU-1',
        stage: 'Sintering',
        status: 'QUEUED',
        due_date_hours: 24,
        priority: 2,
      },
    ],
  }
}

function makeSimulation(
  dueDateImpact: Array<{
    work_order_id: string
    wo_number: string
    due_date_before_hours: number
    due_date_scenario_hours: number
    completion_before_hours: number
    completion_scenario_hours: number
    completion_delta_hours: number
    late_before: boolean
    late_scenario: boolean
    delay_delta_hours: number
  }> = [],
) {
  const operation = makeOperations(1)[0]
  return {
    scenario_inputs: { down_resource_ids: [], rush_order_ids: [], demand_spike_pct: 0 },
    reference_metrics: { late_orders: 1, avg_wip_age_hours: 12, throughput: 2 },
    scenario_metrics: { late_orders: 1, avg_wip_age_hours: 12, throughput: 2 },
    delta: {
      late_orders: 0,
      avg_wip_age_hours: 0,
      throughput: 0,
      bottleneck_before: null,
      bottleneck_after: null,
    },
    due_date_impact: dueDateImpact,
    why_late: [],
    gantt: [{ ...operation, batch_id: 'BATCH-1' }],
  }
}

function makeOperations(count: number): Operation[] {
  return Array.from({ length: count }, (_, index) => ({
    work_order_id: `id-${index}`,
    wo_number: `WO-${String(index + 1).padStart(3, '0')}`,
    sku_code: `SKU-${index + 1}`,
    resource_id: 'machine-1',
    resource_name: 'Molding Cell 1',
    plant: 'Synthetic plant',
    stage: 'Molding',
    batch_id: null,
    start_hour: index * 2,
    end_hour: index * 2 + 1,
    is_late: index === count - 1,
    delay_reason: index === count - 1 ? 'Capacity constraint' : null,
  }))
}

afterEach(() => {
  cleanup()
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('frontend data states', () => {
  it('keeps destructive synthetic seeding disabled unless explicitly enabled for a local demo', async () => {
    vi.stubEnv('VITE_ENABLE_DEMO_SEED', 'false')
    const fetchMock = mockApi()
    render(<App />)

    expect(
      await screen.findByRole('heading', { name: 'No work orders in this database' }),
    ).toBeTruthy()
    expect(screen.getByRole('button', { name: /load synthetic example/i })).toBeDisabled()
    expect(screen.queryByText('Clear for now')).toBeNull()
    expect(screen.getAllByText('—')).toHaveLength(2)

    expect(fetchMock.mock.calls.some(([input]) => String(input).endsWith('/api/seed'))).toBe(false)
  })

  it('requires explicit confirmation before the opt-in synthetic seed request', async () => {
    vi.stubEnv('VITE_ENABLE_DEMO_SEED', 'true')
    const fetchMock = mockApi()
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    render(<App />)
    await screen.findByRole('heading', { name: 'No work orders in this database' })

    fireEvent.click(screen.getByRole('button', { name: 'Load synthetic example' }))
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/seed',
        expect.objectContaining({ method: 'POST' }),
      ),
    )
  })

  it('does not seed when the user cancels the confirmation', async () => {
    vi.stubEnv('VITE_ENABLE_DEMO_SEED', 'true')
    const fetchMock = mockApi()
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    render(<App />)
    await screen.findByRole('heading', { name: 'No work orders in this database' })

    fireEvent.click(screen.getByRole('button', { name: 'Load synthetic example' }))

    expect(window.confirm).toHaveBeenCalledOnce()
    expect(fetchMock.mock.calls.some(([input]) => String(input).endsWith('/api/seed'))).toBe(false)
  })

  it('keeps the demand control within the documented API range', async () => {
    mockApi()
    render(<App />)
    await screen.findByRole('heading', { name: 'No work orders in this database' })
    fireEvent.click(screen.getAllByRole('button', { name: /scenario lab/i })[0])

    const demand = screen.getByRole('slider', {
      name: 'Increase quantities in this model',
    }) as HTMLInputElement
    expect(demand.min).toBe('0')
    expect(demand.max).toBe('300')
    expect(demand.value).toBe('0')
    fireEvent.change(demand, { target: { value: '150' } })
    expect(demand.value).toBe('150')
    expect(screen.getAllByText('150%')).toHaveLength(2)
  })

  it('does not offer scenario simulation when the API has no work orders', async () => {
    const fetchMock = mockApi()
    render(<App />)
    await screen.findByRole('heading', { name: 'No work orders in this database' })
    fireEvent.click(screen.getAllByRole('button', { name: /scenario lab/i })[0])

    expect(screen.getByRole('status').textContent).toContain('No schedulable work orders')
    expect(screen.getByRole('button', { name: /run scenario/i })).toBeDisabled()
    expect(
      fetchMock.mock.calls.some(([input]) => String(input).endsWith('/api/schedule/simulate')),
    ).toBe(false)
  })

  it('shows API failures and recovers on a user refresh without inventing zeros', async () => {
    let failed = true
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input)
      if (failed && path.endsWith('/api/flow-board')) {
        return {
          ok: false,
          status: 503,
          statusText: 'Service Unavailable',
          json: async () => ({ detail: 'Planning API is unavailable' }),
        } as Response
      }
      const body = path.endsWith('/api/flow-board')
        ? emptyBoard
        : { resources: [], work_orders: [] }
      return { ok: true, status: 200, statusText: 'OK', json: async () => body } as Response
    })
    vi.stubGlobal('fetch', fetchMock)
    render(<App />)

    expect(await screen.findByRole('alert')).toHaveTextContent('Planning API is unavailable')
    expect(screen.queryByRole('heading', { name: 'Production flow overview' })).toBeNull()
    failed = false
    fireEvent.click(screen.getByRole('button', { name: 'Refresh data' }))
    expect(
      await screen.findByRole('heading', { name: 'No work orders in this database' }),
    ).toBeTruthy()
    expect(screen.queryByRole('alert')).toBeNull()
  })

  it('does not let an older refresh replace a newer API snapshot', async () => {
    let resolveFirst: ((response: Response) => void) | undefined
    let flowRequests = 0
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input)
      if (path.endsWith('/api/flow-board')) {
        flowRequests += 1
        if (flowRequests === 1) {
          return await new Promise<Response>((resolve) => {
            resolveFirst = resolve
          })
        }
        return {
          ok: true,
          status: 200,
          statusText: 'OK',
          json: async () => ({
            ...emptyBoard,
            total_wip_orders: 7,
            queues: [{ stage: 'Molding', queue_depth: 7, avg_wip_age_hours: 4 }],
          }),
        } as Response
      }
      return {
        ok: true,
        status: 200,
        statusText: 'OK',
        json: async () => ({ resources: [], work_orders: [] }),
      } as Response
    })
    vi.stubGlobal('fetch', fetchMock)
    render(<App />)

    await waitFor(() => expect(resolveFirst).toBeTypeOf('function'))
    fireEvent.click(screen.getByRole('button', { name: 'Refresh data' }))
    expect(await screen.findByText('7 open work orders in this API snapshot')).toBeTruthy()

    await act(async () => {
      resolveFirst?.({
        ok: true,
        status: 200,
        statusText: 'OK',
        json: async () => emptyBoard,
      } as Response)
    })

    expect(screen.getByText('7 open work orders in this API snapshot')).toBeTruthy()
    expect(screen.queryByRole('heading', { name: 'No work orders in this database' })).toBeNull()
  })

  it('shows populated queue signals as snapshot counts, not proven bottlenecks', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input)
      const body = path.endsWith('/api/flow-board')
        ? {
            total_wip_orders: 4,
            avg_wip_age_hours: 9.5,
            queues: [
              { stage: 'Molding', queue_depth: 2, avg_wip_age_hours: 7 },
              { stage: 'Sintering', queue_depth: 4, avg_wip_age_hours: 9.5 },
            ],
            active_bottleneck_alerts: [
              'Molding queue has 56 work orders',
              'Latest schedule identifies D-3 as the active bottleneck',
            ],
          }
        : { resources: [], work_orders: [] }
      return { ok: true, status: 200, statusText: 'OK', json: async () => body } as Response
    })
    vi.stubGlobal('fetch', fetchMock)
    render(<App />)

    await screen.findByRole('heading', { name: 'Production flow overview' })
    expect(screen.getByText('Largest stage queue')).toBeTruthy()
    expect(screen.getByText('4 open work orders in this API snapshot')).toBeTruthy()
    expect(
      screen.getByText('Latest schedule identifies D-3 as the modeled busy-hours signal'),
    ).toBeTruthy()
    expect(screen.getByText('Stage queue')).toBeTruthy()
    expect(screen.getByText('Modeled busy-hours signal')).toBeTruthy()
    expect(screen.getByText(/validate constraints with a planner/i)).toBeTruthy()
    expect(screen.getByText('Synthetic demo · no live ERP')).toBeTruthy()
  })

  it('renders and exposes every operation, including a long horizon', () => {
    const operations = makeOperations(120)
    const { container } = render(<Gantt operations={operations} maxHour={240} />)

    expect(screen.getByText(/120 operations across 1 resources · Timeline: 0–240h/)).toBeTruthy()
    const bars = container.querySelectorAll('.gantt-bar')
    expect(bars).toHaveLength(120)
    const last = screen.getByRole('button', { name: /WO-120, SKU-120.*late.*Capacity constraint/ })
    expect(Number.parseFloat((last as HTMLButtonElement).style.width)).toBeCloseTo(0.4167, 3)
    expect(last.querySelector('span')).toHaveAttribute('aria-hidden', 'true')
    fireEvent.click(last)
    expect(document.querySelector('.gantt-detail')?.textContent).toContain('Capacity constraint')
  })

  it('shows batch and on-time details and returns focus after Escape', async () => {
    const operation = { ...makeOperations(1)[0], batch_id: 'B-42', is_late: false }
    render(<Gantt operations={[operation]} maxHour={24} />)
    const bar = screen.getByRole('button', { name: /on time.*batch B-42/i })
    expect(screen.getByRole('region', { name: /schedule timeline/i })).toHaveAttribute(
      'tabindex',
      '0',
    )
    expect(bar).toHaveAttribute('aria-expanded', 'false')
    fireEvent.click(bar)
    const details = screen.getByRole('region', { name: /selected operation details/i })
    expect(bar).toHaveAttribute('aria-expanded', 'true')
    expect(bar).toHaveAttribute('aria-controls', details.id)
    expect(screen.getByRole('button', { name: 'Clear selection' })).toHaveFocus()
    expect(screen.getByText('Batch B-42')).toBeTruthy()
    expect(screen.getByText('On time at scheduled completion')).toBeTruthy()
    fireEvent.keyDown(window, { key: 'Escape' })
    await waitFor(() => expect(bar).toHaveFocus())
  })

  it('associates scenario validation errors with controls and retains other errors', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const path = String(input)
        if (path.endsWith('/api/schedule/simulate')) {
          return Response.json(
            {
              detail: [
                { loc: ['body', 'demand_spike_pct'], msg: 'Invalid demand' },
                { loc: ['body', 'other'], msg: 'Other problem' },
              ],
            },
            { status: 422 },
          )
        }
        return Response.json(
          path.endsWith('/api/catalog') ? makeCatalog() : { ...emptyBoard, total_wip_orders: 1 },
        )
      }),
    )
    render(<App />)
    await screen.findByRole('heading', { name: 'Production flow overview' })
    fireEvent.click(screen.getAllByRole('button', { name: /scenario lab/i })[0])
    fireEvent.click(screen.getByRole('button', { name: /run scenario/i }))
    const slider = screen.getByRole('slider', { name: 'Increase quantities in this model' })
    await waitFor(() => expect(slider).toHaveAttribute('aria-invalid', 'true'))
    expect(slider).toHaveAccessibleDescription(/Invalid demand/)
    expect(screen.getByRole('alert')).toHaveTextContent('Other problem')
  })

  it('submits and labels the exact scenario inputs that produced the returned Gantt', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input)
      const body = path.endsWith('/api/flow-board')
        ? { ...emptyBoard, total_wip_orders: 1 }
        : path.endsWith('/api/catalog')
          ? makeCatalog()
          : path.endsWith('/api/schedule/simulate')
            ? {
                ...makeSimulation(),
                scenario_inputs: {
                  down_resource_ids: ['res-1'],
                  rush_order_ids: ['wo-1'],
                  demand_spike_pct: 25,
                },
              }
            : { message: 'ok' }
      return { ok: true, status: 200, statusText: 'OK', json: async () => body } as Response
    })
    vi.stubGlobal('fetch', fetchMock)
    render(<App />)
    await screen.findByRole('heading', { name: 'Production flow overview' })
    fireEvent.click(screen.getAllByRole('button', { name: /scenario lab/i })[0])
    fireEvent.change(screen.getByLabelText('Machine unavailable'), { target: { value: 'res-1' } })
    fireEvent.change(screen.getByLabelText('Priority rush order'), { target: { value: 'wo-1' } })
    fireEvent.change(screen.getByRole('slider', { name: 'Increase quantities in this model' }), {
      target: { value: '25' },
    })
    fireEvent.click(screen.getByRole('button', { name: /run scenario/i }))

    expect(
      await screen.findByText(
        /Resource outage: res-1 · Priority order: wo-1 · Demand increase: 25%/,
      ),
    ).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Scenario schedule' })).toBeTruthy()
    expect(screen.getByRole('button', { name: /WO-001.*late.*BATCH-1/i })).toBeTruthy()
    const request = fetchMock.mock.calls.find(([input]) =>
      String(input).endsWith('/api/schedule/simulate'),
    )
    expect(JSON.parse(String(request?.[1]?.body))).toEqual({
      down_resource_ids: ['res-1'],
      rush_order_ids: ['wo-1'],
      demand_spike_pct: 25,
      time_limit_seconds: 3,
    })
    fireEvent.click(screen.getByRole('button', { name: 'Reset inputs' }))
    expect(screen.getByLabelText('Machine unavailable')).toHaveValue('')
    expect(screen.getByLabelText('Priority rush order')).toHaveValue('')
    expect(screen.getByRole('slider', { name: 'Increase quantities in this model' })).toHaveValue(
      '0',
    )
    expect(screen.getByRole('status')).toHaveTextContent('Inputs changed since this run')
    expect(
      fetchMock.mock.calls.filter(([input]) => String(input).endsWith('/api/schedule/simulate')),
    ).toHaveLength(1)
  })

  it('posts one optimizer request and labels the API result as a proposed schedule', async () => {
    let finishOptimize: ((response: Response) => void) | undefined
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input)
      if (path.endsWith('/api/schedule/optimize')) {
        return await new Promise<Response>((resolve) => {
          finishOptimize = resolve
        })
      }
      const body = path.endsWith('/api/flow-board')
        ? { ...emptyBoard, total_wip_orders: 1 }
        : path.endsWith('/api/catalog')
          ? makeCatalog()
          : { message: 'ok' }
      return { ok: true, status: 200, statusText: 'OK', json: async () => body } as Response
    })
    vi.stubGlobal('fetch', fetchMock)
    render(<App />)
    await screen.findByRole('heading', { name: 'Production flow overview' })
    fireEvent.click(screen.getByRole('button', { name: 'Run comparison' }))
    await waitFor(() =>
      expect(
        fetchMock.mock.calls.filter(([input]) => String(input).endsWith('/api/schedule/optimize')),
      ).toHaveLength(1),
    )
    const optimizeButton = screen.getByRole('button', { name: /working/i })
    expect(optimizeButton).toBeDisabled()

    const metrics = {
      late_orders: 1,
      avg_wip_age_hours: 12,
      throughput: 2,
      throughput_horizon_hours: 168,
      furnace_batch_efficiency_pct: 72,
      makespan_hours: 42,
      bottleneck_resource_id: 'res-1',
      resource_busy_hours: { 'res-1': 18 },
      weighted_tardiness_hours: 4,
    }
    const operations = makeOperations(1)
    finishOptimize?.({
      ok: true,
      status: 200,
      statusText: 'OK',
      json: async () => ({
        comparison: {
          baseline: {
            ...metrics,
            late_orders: 2,
            avg_wip_age_hours: 12,
            schedule_version_id: 'baseline-1',
          },
          optimized: {
            ...metrics,
            late_orders: 1,
            avg_wip_age_hours: 13,
            throughput: 2,
            furnace_batch_efficiency_pct: null,
            schedule_version_id: 'proposed-1',
          },
          delta: {
            late_orders: -1,
            avg_wip_age_hours: 1,
            throughput: 0,
            furnace_batch_efficiency_pct: null,
          },
        },
        gantt: { baseline: operations, optimized: operations },
        why_late: {
          baseline: [],
          optimized: Array.from({ length: 10 }, (_, index) => ({
            work_order_id: `wo-${index + 1}`,
            wo_number: `WO-${String(index + 1).padStart(3, '0')}`,
            due_date_hours: 24,
            completion_hours: 30,
            delay_hours: 6,
            priority: 2,
            explanation: 'Capacity constraint',
          })),
        },
      }),
    } as Response)

    expect(await screen.findByText('Proposed model schedule ready')).toBeTruthy()
    expect(screen.getByText(/completed within 168 hours/)).toBeTruthy()
    expect(screen.getByText(/not utilization or OEE/)).toBeTruthy()
    const deltaLabels = Array.from(document.querySelectorAll('.delta-chip')).map((chip) =>
      chip.textContent?.replace(/\s+/g, ' ').trim(),
    )
    expect(deltaLabels).toEqual([
      'Improved · -1 orders',
      'Worsened · +1 hours',
      'Unchanged · 0 orders',
      'Unavailable',
    ])
    const lateOrders = screen.getByRole('region', { name: 'Late order explanations' })
    expect(lateOrders).toHaveAttribute('tabindex', '0')
    expect(within(lateOrders).getByRole('table')).toBeTruthy()
    expect(within(lateOrders).getByRole('columnheader', { name: 'Due' })).toBeTruthy()
    expect(within(lateOrders).getByRole('columnheader', { name: 'Completion' })).toBeTruthy()
    const lastOrder = within(lateOrders).getByRole('row', { name: /WO-010/ })
    expect(within(lastOrder).getByText('24h')).toBeTruthy()
    expect(within(lastOrder).getByText('30h')).toBeTruthy()
    expect(within(lastOrder).getByText('2')).toBeTruthy()
    fireEvent.click(within(lateOrders).getByRole('button', { name: 'WO-001' }))
    expect(screen.getByLabelText('Work order')).toHaveValue('WO-001')
    expect(screen.getByText(/baseline-1/)).toBeTruthy()
    expect(screen.getByText(/proposed-1/)).toBeTruthy()
    const request = fetchMock.mock.calls.find(([input]) =>
      String(input).endsWith('/api/schedule/optimize'),
    )
    expect(request?.[1]?.method).toBe('POST')
    expect(JSON.parse(String(request?.[1]?.body))).toEqual({ time_limit_seconds: 3 })
  })

  it('sends only one scenario request when Run is clicked repeatedly while pending', async () => {
    let finishSimulation: ((response: Response) => void) | undefined
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input)
      if (path.endsWith('/api/schedule/simulate')) {
        return await new Promise<Response>((resolve) => {
          finishSimulation = resolve
        })
      }
      const body = path.endsWith('/api/flow-board')
        ? { ...emptyBoard, total_wip_orders: 1 }
        : path.endsWith('/api/catalog')
          ? makeCatalog()
          : { message: 'ok' }
      return { ok: true, status: 200, statusText: 'OK', json: async () => body } as Response
    })
    vi.stubGlobal('fetch', fetchMock)
    render(<App />)
    await screen.findByRole('heading', { name: 'Production flow overview' })
    fireEvent.click(screen.getAllByRole('button', { name: /scenario lab/i })[0])
    const run = screen.getByRole('button', { name: /run scenario/i })

    fireEvent.click(run)
    fireEvent.click(run)

    expect(
      fetchMock.mock.calls.filter(([input]) => String(input).endsWith('/api/schedule/simulate')),
    ).toHaveLength(1)
    finishSimulation?.({
      ok: true,
      status: 200,
      statusText: 'OK',
      json: async () =>
        makeSimulation([
          {
            work_order_id: 'impact-1',
            wo_number: 'WO-EARLIER',
            due_date_before_hours: 24,
            due_date_scenario_hours: 24,
            completion_before_hours: 30,
            completion_scenario_hours: 28,
            completion_delta_hours: -2,
            late_before: true,
            late_scenario: true,
            delay_delta_hours: -2,
          },
          {
            work_order_id: 'impact-2',
            wo_number: 'WO-LATER',
            due_date_before_hours: 24,
            due_date_scenario_hours: 24,
            completion_before_hours: 22,
            completion_scenario_hours: 25,
            completion_delta_hours: 3,
            late_before: false,
            late_scenario: true,
            delay_delta_hours: 1,
          },
          {
            work_order_id: 'impact-3',
            wo_number: 'WO-UNCHANGED',
            due_date_before_hours: 24,
            due_date_scenario_hours: 24,
            completion_before_hours: 22,
            completion_scenario_hours: 22,
            completion_delta_hours: 0,
            late_before: false,
            late_scenario: false,
            delay_delta_hours: 0,
          },
        ]),
    } as Response)
    expect(await screen.findByRole('heading', { name: 'Scenario schedule' })).toBeTruthy()
    const impact = screen.getByRole('region', { name: 'Due-date impact by work order' })
    expect(impact).toHaveAttribute('tabindex', '0')
    expect(impact.querySelector('table')).toBeTruthy()
    const rows = Array.from(impact.querySelectorAll('tbody tr')).map((row) =>
      Array.from(row.querySelectorAll('th, td')).map((cell) => cell.textContent),
    )
    expect(rows).toEqual([
      ['WO-EARLIER', '24h', '24h', '30h', '28h', 'Late', 'Late', '-2h'],
      ['WO-LATER', '24h', '24h', '22h', '25h', 'On track', 'Late', '+3h'],
      ['WO-UNCHANGED', '24h', '24h', '22h', '22h', 'On track', 'On track', '0h'],
    ])
  })
})

describe('API and metric formatting', () => {
  it('renders missing and non-finite metrics as unavailable, not zero', () => {
    expect(fmt(null)).toBe('—')
    expect(fmt(undefined)).toBe('—')
    expect(fmt(Number.NaN)).toBe('—')
  })

  it('renders Pydantic array detail with field locations', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          ({
            ok: false,
            status: 422,
            statusText: 'Unprocessable Entity',
            json: async () => ({
              detail: [
                {
                  loc: ['body', 'demand_spike_pct'],
                  msg: 'Input should be less than or equal to 300',
                },
              ],
            }),
          }) as Response,
      ),
    )
    await expect(api('/api/schedule/simulate')).rejects.toThrow(
      'body → demand_spike_pct: Input should be less than or equal to 300',
    )
  })

  it('renders object-shaped API error details', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          ({
            ok: false,
            status: 409,
            statusText: 'Conflict',
            json: async () => ({ detail: { message: 'No schedulable work orders' } }),
          }) as Response,
      ),
    )
    await expect(api('/api/schedule/optimize')).rejects.toThrow('No schedulable work orders')
  })
})
