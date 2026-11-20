import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { Gantt } from './Gantt'
import type { ScheduledOperation } from './types'

const first: ScheduledOperation = {
  work_order_id: '1',
  wo_number: 'WO-1',
  sku_code: 'A',
  resource_id: 'r1',
  resource_name: 'Furnace',
  plant: 'Plant A',
  stage: 'Sintering',
  start_hour: 0,
  end_hour: 10,
  batch_id: 'B1',
  is_late: false,
  delay_reason: null,
}
const second: ScheduledOperation = {
  ...first,
  work_order_id: '2',
  wo_number: 'WO-2',
  sku_code: 'B',
  start_hour: 2,
  end_hour: 8,
  is_late: true,
}

afterEach(cleanup)

describe('Gantt controls', () => {
  it('shows dismissible hover details without moving focus or replacing an activated selection', async () => {
    render(<Gantt operations={[first, second]} maxHour={24} />)
    const firstBar = screen.getByRole('button', { name: /^WO-1, A/ })
    const secondBar = screen.getByRole('button', { name: /^WO-2, B/ })
    const status = screen.getByLabelText('Status')
    status.focus()
    fireEvent.mouseEnter(firstBar)
    expect(status).toHaveFocus()
    expect(screen.getByText('Batch B1')).toBeInTheDocument()
    expect(screen.getByText('Batch B1').closest('.gantt-detail')).toHaveStyle({ position: 'fixed' })
    fireEvent.keyDown(window, { key: 'Escape' })
    expect(screen.queryByText('Batch B1')).not.toBeInTheDocument()
    expect(status).toHaveFocus()

    fireEvent.click(firstBar)
    const detail = screen.getByRole('region', { name: 'Selected operation details' })
    expect(detail).toHaveTextContent('WO-1')
    expect(detail).toHaveFocus()
    expect(detail).toHaveAccessibleDescription(
      'WO-1 A Sintering Batch B1 Furnace · Plant A 0–10h Duration: 10 hours On time at scheduled completion Modeled operation · not a committed production order',
    )
    fireEvent.mouseEnter(secondBar)
    fireEvent.mouseLeave(secondBar.closest('.gantt')!.parentElement!)
    expect(detail).toHaveTextContent('WO-1')
    fireEvent.keyDown(window, { key: 'Escape' })
    expect(screen.queryByRole('region', { name: 'Selected operation details' })).toBeNull()
    await waitFor(() => expect(firstBar).toHaveFocus())

    fireEvent.click(secondBar)
    expect(screen.getByRole('region', { name: 'Selected operation details' })).toHaveFocus()
    fireEvent.click(screen.getByRole('button', { name: 'Clear selection' }))
    await waitFor(() => expect(secondBar).toHaveFocus())
  })

  it('describes an operation without a batch and its duration', () => {
    render(<Gantt operations={[{ ...second, batch_id: null }]} maxHour={24} />)
    fireEvent.click(screen.getByRole('button', { name: /^WO-2, B/ }))
    const detail = screen.getByRole('region', { name: 'Selected operation details' })
    expect(detail).toHaveTextContent('No batch')
    expect(detail).toHaveTextContent('Duration: 6 hours')
    expect(detail).toHaveAccessibleDescription(
      'WO-2 B Sintering No batch Furnace · Plant A 2–8h Duration: 6 hours Late Modeled operation · not a committed production order',
    )
  })

  it('filters, reports empty matches, and clears filters without changing the timeline scale', () => {
    render(<Gantt operations={[first, second]} maxHour={24} />)
    fireEvent.change(screen.getByLabelText('Status'), { target: { value: 'late' } })
    expect(screen.getByText(/1 operation across 1 resource/)).toBeTruthy()
    expect(screen.getByRole('button', { name: /WO-2, B/ })).toBeTruthy()
    fireEvent.change(screen.getByLabelText('Work order'), { target: { value: 'WO-1' } })
    expect(screen.getByText(/No operations match/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Clear filters (2)' }))
    expect(screen.getByText(/2 operations across 1 resource · Timeline: 0–24h/)).toBeTruthy()
  })

  it('does not restore a hidden selection or lose focus when filters are cleared', () => {
    render(<Gantt operations={[first, second]} maxHour={24} />)
    fireEvent.click(screen.getByRole('button', { name: /^WO-1, A/ }))
    const status = screen.getByLabelText('Status')
    status.focus()
    fireEvent.change(status, { target: { value: 'late' } })
    expect(screen.queryByRole('region', { name: 'Selected operation details' })).toBeNull()
    const clear = screen.getByRole('button', { name: 'Clear filters (1)' })
    clear.focus()
    fireEvent.click(clear)
    expect(screen.queryByRole('region', { name: 'Selected operation details' })).toBeNull()
    expect(screen.getByLabelText('Stage')).toHaveFocus()
  })

  it('retains selected details and focus when refreshed with equivalent operation objects', async () => {
    const { rerender } = render(<Gantt operations={[first]} maxHour={24} />)
    fireEvent.click(screen.getByRole('button', { name: /^WO-1, A/ }))
    expect(screen.getByRole('region', { name: 'Selected operation details' })).toHaveFocus()

    rerender(<Gantt operations={[{ ...first }]} maxHour={24} />)

    await waitFor(() =>
      expect(screen.getByRole('region', { name: 'Selected operation details' })).toHaveFocus(),
    )
    expect(screen.getByRole('region', { name: 'Selected operation details' })).toHaveTextContent(
      'WO-1',
    )
    const status = screen.getByLabelText('Status')
    status.focus()
    rerender(<Gantt operations={[{ ...first }]} maxHour={24} />)
    expect(status).toHaveFocus()
  })

  it('keeps overlapping operations discoverable and supports zoom and table selection', () => {
    const { container, rerender } = render(<Gantt operations={[first, second]} maxHour={24} />)
    const bars = container.querySelectorAll<HTMLButtonElement>('.gantt-bar')
    expect(bars[0].style.top).not.toBe(bars[1].style.top)
    fireEvent.change(screen.getByLabelText('Zoom'), { target: { value: '2' } })
    expect((container.querySelector('.gantt-canvas') as HTMLElement).style.width).toBe('200%')
    rerender(
      <Gantt
        operations={[first, second]}
        maxHour={24}
        focusWorkOrderRequest={{ order: 'WO-2', sequence: 1 }}
      />,
    )
    expect(screen.getByLabelText('Work order')).toHaveValue('WO-2')
    expect(screen.getByLabelText('Work order')).toHaveFocus()
    expect(screen.queryByRole('button', { name: /WO-1, A/ })).toBeNull()
  })
  it('renders and inspects a schedule of 1,200 operations', () => {
    const operations = Array.from({ length: 1200 }, (_, index) => ({
      ...first,
      work_order_id: String(index),
      wo_number: `WO-${index}`,
      start_hour: index,
      end_hour: index + 1,
    }))
    const { container } = render(<Gantt operations={operations} maxHour={1200} />)
    expect(container.querySelectorAll('.gantt-bar')).toHaveLength(1200)
    fireEvent.click(screen.getByRole('button', { name: 'Skip timeline operations' }))
    expect(screen.getByText('End of timeline')).toHaveFocus()
    fireEvent.click(screen.getByRole('button', { name: /^WO-1199,/ }))
    expect(screen.getByRole('region', { name: 'Selected operation details' })).toHaveTextContent(
      'WO-1199',
    )
    fireEvent.change(screen.getByLabelText('Work order'), { target: { value: 'WO-1199' } })
    expect(container.querySelectorAll('.gantt-bar')).toHaveLength(1)
  })

  it('offers paged, text-labelled controls for short operations and respects timeline filters', async () => {
    const operations = Array.from({ length: 51 }, (_, index) => ({
      ...first,
      work_order_id: String(index),
      wo_number: `WO-${index}`,
      start_hour: index,
      end_hour: index + 0.01,
      is_late: index === 50,
    }))
    render(<Gantt operations={operations} maxHour={1200} />)
    const disclosure = screen.getByText('Browse operations as a list').closest('details')!
    disclosure.open = true
    fireEvent(disclosure, new Event('toggle'))
    expect(screen.getByText('Showing 1–50 of 51 operations')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Next operations' }))
    expect(screen.getByText('Showing 51–51 of 51 operations')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Previous operations' })).toHaveFocus()
    const listButton = screen.getByRole('button', { name: /WO-50 · Sintering · Furnace.*Late/ })
    expect(listButton).toHaveAttribute('aria-expanded', 'false')
    fireEvent.click(listButton)
    const detail = screen.getByRole('region', { name: 'Selected operation details' })
    expect(detail).toHaveFocus()
    expect(listButton).toHaveAttribute('aria-expanded', 'true')
    expect(listButton).toHaveAttribute('aria-controls', detail.id)
    fireEvent.keyDown(window, { key: 'Escape' })
    await waitFor(() => expect(listButton).toHaveFocus())
    expect(listButton).toHaveAttribute('aria-expanded', 'false')
    expect(listButton).not.toHaveAttribute('aria-controls')
    fireEvent.click(listButton)
    fireEvent.click(screen.getByRole('button', { name: 'Clear selection' }))
    await waitFor(() => expect(listButton).toHaveFocus())
    fireEvent.click(screen.getByRole('button', { name: 'Previous operations' }))
    expect(screen.getByText('Showing 1–50 of 51 operations')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Next operations' })).toHaveFocus()
    fireEvent.change(screen.getByLabelText('Status'), { target: { value: 'late' } })
    expect(screen.getByText('Showing 1–1 of 1 operations')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /WO-50 · Sintering/ })).toBeInTheDocument()
  })
})
