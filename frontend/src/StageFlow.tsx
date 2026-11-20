import { useRef, useState } from 'react'
import { ArrowRight, Info } from 'lucide-react'
import { fmt } from './api'
import type { Queue } from './types'
import './StageFlow.css'

const stages = [
  { name: 'Molding', short: 'Molding', help: 'Molding forms parts from feedstock.' },
  { name: 'Debinding', short: 'Debinding', help: 'Debinding removes binder from molded parts.' },
  { name: 'Sintering', short: 'Sintering', help: 'Sintering densifies parts using heat.' },
  {
    name: 'CNC Machining',
    short: 'CNC',
    help: 'CNC machining is optional; some parts skip this stage.',
  },
  { name: 'Finishing', short: 'Finishing', help: 'Finishing covers final processing of parts.' },
]

export function StageFlow({
  queues,
  onSchedule,
  disabled,
}: {
  queues: Queue[]
  onSchedule: () => void
  disabled: boolean
}) {
  const [focused, setFocused] = useState<string | null>(null)
  const [hovered, setHovered] = useState<string | null>(null)
  const [dismissed, setDismissed] = useState<string | null>(null)
  const wasFocusedOnPointerDown = useRef(false)
  const active =
    (focused !== dismissed ? focused : null) ?? (hovered !== dismissed ? hovered : null)
  const max = Math.max(1, ...queues.map((queue) => queue.queue_depth))
  const detail = stages.find((stage) => stage.name === active)
  return (
    <section className="panel flow-panel">
      <div className="panel-heading">
        <div>
          <h2>Production flow</h2>
          <p>Open work orders by current stage</p>
        </div>
        <span className="neutral-pill">
          <span className="pulse" /> API SNAPSHOT
        </span>
      </div>
      <div className="flow-track">
        {stages.map((stage, index) => {
          const queue = queues.find((item) => item.stage === stage.name)
          return (
            <div className="stage-column" key={stage.name}>
              <div className="stage-top">
                <span className="stage-index">{String(index + 1).padStart(2, '0')}</span>
                {index < stages.length - 1 && (
                  <span className="stage-connector" aria-hidden="true">
                    <ArrowRight size={13} />
                  </span>
                )}
              </div>
              <div className="stage-count">{queue ? queue.queue_depth.toLocaleString() : '—'}</div>
              <div className="stage-name">
                {stage.short}
                {stage.name === 'CNC Machining' && ' (optional)'}
              </div>
              <div className="stage-bar" aria-hidden="true">
                <span
                  style={{
                    width: `${queue ? Math.max(queue.queue_depth ? 5 : 0, (queue.queue_depth / max) * 100) : 0}%`,
                  }}
                />
              </div>
              <div className="stage-meta">
                {queue ? `${fmt(queue.avg_wip_age_hours)}h avg age` : 'No stage data'}
              </div>
              <button
                type="button"
                className="stage-help"
                aria-label={`About ${stage.name}`}
                aria-expanded={active === stage.name}
                aria-controls="stage-help-detail"
                onMouseEnter={() => {
                  setHovered(stage.name)
                  setDismissed(null)
                }}
                onMouseLeave={() => setHovered(null)}
                onFocus={() => {
                  setFocused(stage.name)
                  setDismissed(null)
                }}
                onBlur={() => setFocused(null)}
                onPointerDown={(event) => {
                  wasFocusedOnPointerDown.current = document.activeElement === event.currentTarget
                }}
                onClick={(event) => {
                  const firstPointerActivation =
                    event.detail > 0 && !wasFocusedOnPointerDown.current
                  setDismissed(!firstPointerActivation && active === stage.name ? stage.name : null)
                }}
                onKeyDown={(event) => {
                  if (event.key === 'Escape') setDismissed(stage.name)
                }}
              >
                <Info size={14} /> Help
              </button>
            </div>
          )
        })}
      </div>
      <p className="stage-route-note">Some parts skip CNC machining.</p>
      <div id="stage-help-detail" className="stage-help-detail" aria-live="polite">
        {detail ? (
          <>
            <strong>{detail.name}:</strong> {detail.help} Counts show open orders at this current
            stage, not live transfers.
          </>
        ) : (
          'Select or focus Help for stage details.'
        )}
      </div>
      <div className="flow-foot">
        <span>
          <i className="legend-dot" /> Open orders at each operation’s current stage
        </span>
        <button className="link-button" onClick={onSchedule} disabled={disabled}>
          View schedule <ArrowRight size={14} />
        </button>
      </div>
    </section>
  )
}
