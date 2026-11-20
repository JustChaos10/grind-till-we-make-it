import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it, vi } from 'vitest'
import App from './App'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

it('shows a loading state while the first snapshot is pending', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(() => new Promise(() => {})),
  )
  render(<App />)
  expect(
    screen.getByRole('heading', { name: 'Loading factory data' }).closest('[role="status"]'),
  ).toBeTruthy()
  expect(screen.queryByText('Connect to the factory demo')).not.toBeInTheDocument()
})

it('keeps focus on a stable refresh control when retry replaces the connection screen', async () => {
  let calls = 0
  vi.stubGlobal(
    'fetch',
    vi.fn(() => {
      calls += 1
      return calls <= 2 ? Promise.reject(new Error('Offline')) : new Promise(() => {})
    }),
  )
  render(<App />)
  const retry = await screen.findByRole('button', { name: 'Retry API connection' })
  retry.focus()
  await userEvent.keyboard('{Enter}')
  expect(screen.getByRole('heading', { name: 'Loading factory data' })).toBeVisible()
  expect(screen.getByRole('button', { name: 'Refresh data' })).toHaveFocus()
})

it('disables schedule actions when there are no schedulable catalog orders', async () => {
  const fetchMock = vi.fn(
    async (input: RequestInfo | URL) =>
      ({
        ok: true,
        status: 200,
        statusText: 'OK',
        json: async () =>
          String(input).endsWith('/api/flow-board')
            ? {
                total_wip_orders: 0,
                avg_wip_age_hours: 0,
                queues: [],
                active_bottleneck_alerts: [],
              }
            : { resources: [], work_orders: [] },
      }) as Response,
  )
  vi.stubGlobal('fetch', fetchMock)
  render(<App />)
  await screen.findByText('No work orders in this database')
  expect(screen.getByRole('button', { name: /Optimize schedule/i })).toBeDisabled()
  expect(screen.getByRole('button', { name: /Run comparison/i })).toBeDisabled()
  await userEvent.click(screen.getByRole('button', { name: /Schedule optimizer/i }))
  expect(screen.getByRole('button', { name: /Run optimization/i })).toBeDisabled()
  expect(screen.getByRole('heading', { name: 'No work orders to schedule' })).toBeVisible()
  expect(screen.getByRole('button', { name: 'Go to Flow board' })).toBeEnabled()
  await waitFor(() =>
    expect(
      fetchMock.mock.calls.some(([input]) => String(input).includes('/api/schedule/optimize')),
    ).toBe(false),
  )
})
