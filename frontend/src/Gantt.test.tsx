import { cleanup, fireEvent, render, screen } from '@testing-library/react'
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
  it('shows dismissible hover details without moving focus or replacing an activated selection', () => {
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
    expect(screen.getByRole('button', { name: 'Clear selection' })).toHaveFocus()
    fireEvent.mouseEnter(secondBar)
    fireEvent.mouseLeave(secondBar.closest('.gantt')!.parentElement!)
    expect(detail).toHaveTextContent('WO-1')
    fireEvent.keyDown(window, { key: 'Escape' })
    expect(screen.queryByRole('region', { name: 'Selected operation details' })).toBeNull()
  })

  it('filters, reports empty matches, and clears filters without changing the timeline scale', () => {
    render(<Gantt operations={[first, second]} maxHour={24} />)
    fireEvent.change(screen.getByLabelText('Status'), { target: { value: 'late' } })
    expect(screen.getByText(/1 operations across 1 resources/)).toBeTruthy()
    expect(screen.getByRole('button', { name: /WO-2, B/ })).toBeTruthy()
    fireEvent.change(screen.getByLabelText('Work order'), { target: { value: 'WO-1' } })
    expect(screen.getByText(/No operations match/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Clear filters (2)' }))
    expect(screen.getByText(/2 operations across 1 resources · Timeline: 0–24h/)).toBeTruthy()
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
    fireEvent.click(screen.getByRole('button', { name: /^WO-1199,/ }))
    expect(screen.getByRole('region', { name: 'Selected operation details' })).toHaveTextContent(
      'WO-1199',
    )
    fireEvent.change(screen.getByLabelText('Work order'), { target: { value: 'WO-1199' } })
    expect(container.querySelectorAll('.gantt-bar')).toHaveLength(1)
  })
})
