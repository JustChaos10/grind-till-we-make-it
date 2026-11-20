import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { StageFlow } from './StageFlow'

afterEach(cleanup)

describe('production stage flow', () => {
  it('distinguishes a zero queue from a missing reading and explains optional CNC', () => {
    render(
      <StageFlow
        queues={[{ stage: 'Molding', queue_depth: 0, avg_wip_age_hours: 0 }]}
        onSchedule={vi.fn()}
        disabled={false}
      />,
    )
    const molding = screen.getByRole('button', { name: 'About Molding' }).closest('.stage-column')!
    const cnc = screen
      .getByRole('button', { name: 'About CNC Machining' })
      .closest('.stage-column')!
    expect(within(molding as HTMLElement).getByText('0')).toBeInTheDocument()
    expect(within(cnc as HTMLElement).getByText('—')).toBeInTheDocument()
    expect(within(cnc as HTMLElement).getByText('No stage data')).toBeInTheDocument()
    const help = screen.getByRole('button', { name: 'About CNC Machining' })
    fireEvent.focus(help)
    expect(help).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByText(/CNC machining is optional/)).toBeInTheDocument()
    fireEvent.blur(help)
    fireEvent.mouseEnter(help)
    expect(screen.getByText(/CNC machining is optional/)).toBeInTheDocument()
  })

  it('disables the schedule action when unavailable', () => {
    render(<StageFlow queues={[]} onSchedule={vi.fn()} disabled />)
    expect(screen.getByRole('button', { name: /View schedule/ })).toBeDisabled()
  })

  it('lets a focused user close and reopen stage help', () => {
    render(<StageFlow queues={[]} onSchedule={vi.fn()} disabled={false} />)
    const help = screen.getByRole('button', { name: 'About Molding' })
    fireEvent.focus(help)
    fireEvent.click(help)
    expect(help).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByText(/Molding forms parts from feedstock/)).not.toBeInTheDocument()
    fireEvent.click(help)
    expect(help).toHaveAttribute('aria-expanded', 'true')
    fireEvent.keyDown(help, { key: 'Escape' })
    expect(help).toHaveAttribute('aria-expanded', 'false')
  })

  it('keeps help open while either focus or hover remains', () => {
    render(<StageFlow queues={[]} onSchedule={vi.fn()} disabled={false} />)
    const help = screen.getByRole('button', { name: 'About Molding' })
    fireEvent.mouseEnter(help)
    fireEvent.focus(help)
    fireEvent.mouseLeave(help)
    expect(help).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByText(/Molding forms parts from feedstock/)).toBeInTheDocument()

    fireEvent.mouseEnter(help)
    fireEvent.blur(help)
    expect(help).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByText(/Molding forms parts from feedstock/)).toBeInTheDocument()
    fireEvent.mouseLeave(help)
    expect(help).toHaveAttribute('aria-expanded', 'false')
  })
})
