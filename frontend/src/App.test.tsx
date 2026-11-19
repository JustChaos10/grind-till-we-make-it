import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App, { Gantt, type Operation } from './App'

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
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('frontend data states', () => {
  it('offers a safe-to-understand synthetic demo path for an empty database', async () => {
    const fetchMock = mockApi()
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    render(<App />)

    expect(
      await screen.findByRole('heading', { name: 'No work orders in this database' }),
    ).toBeTruthy()
    expect(screen.getByRole('button', { name: /load synthetic example/i })).toBeTruthy()
    expect(screen.queryByText('Clear for now')).toBeNull()
    expect(screen.getAllByText('—')).toHaveLength(2)

    fireEvent.click(screen.getByRole('button', { name: /load synthetic example/i }))
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
})
