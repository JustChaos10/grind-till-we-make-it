import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
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

function makeSimulation() {
  const operation = makeOperations(1)[0]
  return {
    reference_metrics: { late_orders: 1, avg_wip_age_hours: 12, throughput: 2 },
    scenario_metrics: { late_orders: 1, avg_wip_age_hours: 12, throughput: 2 },
    delta: {
      late_orders: 0,
      avg_wip_age_hours: 0,
      throughput: 0,
      bottleneck_before: null,
      bottleneck_after: null,
    },
    due_date_impact: [],
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

  it('keeps the demand control within the documented API range', async () => {
    mockApi()
    render(<App />)
    await screen.findByRole('heading', { name: 'No work orders in this database' })
    fireEvent.click(screen.getAllByRole('button', { name: /scenario lab/i })[0])

    const demand = screen.getByRole('slider', { name: 'Demand increase' }) as HTMLInputElement
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
    fireEvent.click(bar)
    expect(screen.getByText('Batch B-42')).toBeTruthy()
    expect(screen.getByText('On time at scheduled completion')).toBeTruthy()
    fireEvent.keyDown(window, { key: 'Escape' })
    await waitFor(() => expect(bar).toHaveFocus())
  })

  it('submits and labels the exact scenario inputs that produced the returned Gantt', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input)
      const body = path.endsWith('/api/flow-board')
        ? { ...emptyBoard, total_wip_orders: 1 }
        : path.endsWith('/api/catalog')
          ? makeCatalog()
          : path.endsWith('/api/schedule/simulate')
            ? makeSimulation()
            : { message: 'ok' }
      return { ok: true, status: 200, statusText: 'OK', json: async () => body } as Response
    })
    vi.stubGlobal('fetch', fetchMock)
    render(<App />)
    await screen.findByRole('heading', { name: 'Production flow overview' })
    fireEvent.click(screen.getAllByRole('button', { name: /scenario lab/i })[0])
    fireEvent.change(screen.getByLabelText('Machine unavailable'), { target: { value: 'res-1' } })
    fireEvent.change(screen.getByLabelText('Priority rush order'), { target: { value: 'wo-1' } })
    fireEvent.change(screen.getByRole('slider', { name: 'Demand increase' }), {
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
})
