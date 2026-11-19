import { useEffect, useId, useMemo, useRef, useState } from 'react'
import { Wrench } from 'lucide-react'
import { fmt } from './api'
import type { ScheduledOperation as Operation } from './types'
import './Gantt.css'

const stages = ['Molding', 'Debinding', 'Sintering', 'CNC Machining', 'Finishing']

export function Gantt({
  operations,
  maxHour,
  focusWorkOrderRequest,
}: {
  operations: Operation[]
  maxHour: number
  focusWorkOrderRequest?: { order: string; sequence: number }
}) {
  const emptyFilters = { stage: '', plant: '', resource: '', order: '', status: '' }
  const [filterState, setFilterState] = useState({ filters: emptyFilters, sequence: 0 })
  const requestSequence = focusWorkOrderRequest?.sequence ?? 0
  const filters = useMemo(
    () =>
      filterState.sequence === requestSequence
        ? filterState.filters
        : {
            stage: '',
            plant: '',
            resource: '',
            order: focusWorkOrderRequest?.order ?? '',
            status: '',
          },
    [filterState, requestSequence, focusWorkOrderRequest?.order],
  )
  const [zoom, setZoom] = useState(1)
  const orderFilter = useRef<HTMLSelectElement | null>(null)
  useEffect(() => {
    if (!focusWorkOrderRequest) return
    orderFilter.current?.focus()
    orderFilter.current?.scrollIntoView?.({ block: 'nearest' })
  }, [focusWorkOrderRequest])
  const filtered = useMemo(
    () =>
      operations.filter(
        (item) =>
          (!filters.stage || item.stage === filters.stage) &&
          (!filters.plant || item.plant === filters.plant) &&
          (!filters.resource || item.resource_id === filters.resource) &&
          (!filters.order || item.wo_number === filters.order) &&
          (!filters.status || (filters.status === 'late' ? item.is_late : !item.is_late)),
      ),
    [operations, filters],
  )
  const options = (values: string[]) => [...new Set(values)].sort((a, b) => a.localeCompare(b))
  const setFilter = (name: keyof typeof filters, value: string) =>
    setFilterState({ filters: { ...filters, [name]: value }, sequence: requestSequence })
  const activeFilters = Object.values(filters).filter(Boolean).length
  const [selected, setSelected] = useState<Operation | null>(null)
  const detailId = useId()
  const selectedBar = useRef<HTMLButtonElement | null>(null)
  const detailClose = useRef<HTMLButtonElement | null>(null)
  const rows = useMemo(() => {
    const grouped = new Map<string, Operation[]>()
    filtered.forEach((operation) => {
      const key = operation.resource_id
      const items = grouped.get(key) ?? []
      items.push(operation)
      grouped.set(key, items)
    })
    return [...grouped.entries()]
  }, [filtered])
  const selectedOperation = selected && filtered.includes(selected) ? selected : null
  useEffect(() => {
    if (selectedOperation) detailClose.current?.focus()
  }, [selectedOperation])
  useEffect(() => {
    if (!selectedOperation) return
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        setSelected(null)
        requestAnimationFrame(() => selectedBar.current?.focus())
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [selectedOperation])
  return (
    <>
      <div className="gantt-controls" aria-label="Timeline filters">
        <label>
          Stage
          <select value={filters.stage} onChange={(e) => setFilter('stage', e.target.value)}>
            <option value="">All stages</option>
            {options(operations.map((item) => item.stage)).map((value) => (
              <option key={value}>{value}</option>
            ))}
          </select>
        </label>
        <label>
          Plant
          <select value={filters.plant} onChange={(e) => setFilter('plant', e.target.value)}>
            <option value="">All plants</option>
            {options(operations.map((item) => item.plant)).map((value) => (
              <option key={value}>{value}</option>
            ))}
          </select>
        </label>
        <label>
          Resource
          <select value={filters.resource} onChange={(e) => setFilter('resource', e.target.value)}>
            <option value="">All resources</option>
            {[
              ...new Map(
                operations.map((item) => [item.resource_id, item.resource_name]),
              ).entries(),
            ]
              .sort((a, b) => a[1].localeCompare(b[1]))
              .map(([id, name]) => (
                <option key={id} value={id}>
                  {name}
                </option>
              ))}
          </select>
        </label>
        <label>
          Work order
          <select
            ref={orderFilter}
            value={filters.order}
            onChange={(e) => setFilter('order', e.target.value)}
          >
            <option value="">All work orders</option>
            {options(operations.map((item) => item.wo_number)).map((value) => (
              <option key={value}>{value}</option>
            ))}
          </select>
        </label>
        <label>
          Status
          <select value={filters.status} onChange={(e) => setFilter('status', e.target.value)}>
            <option value="">All statuses</option>
            <option value="late">Late</option>
            <option value="on-time">On time</option>
          </select>
        </label>
        <button
          type="button"
          onClick={() => setFilterState({ filters: emptyFilters, sequence: requestSequence })}
          disabled={!activeFilters}
        >
          Clear filters ({activeFilters})
        </button>
        <label>
          Zoom
          <select value={zoom} onChange={(e) => setZoom(Number(e.target.value))}>
            <option value={1}>100%</option>
            <option value={2}>200%</option>
            <option value={4}>400%</option>
          </select>
        </label>
      </div>
      <div className="gantt-summary" aria-live="polite">
        {filtered.length.toLocaleString()} operations across {rows.length} resources · Timeline: 0–
        {fmt(maxHour, 0)}h
      </div>
      {filtered.length === 0 ? (
        <div className="gantt-empty">
          {operations.length
            ? 'No operations match these filters. Clear filters to see the full schedule.'
            : 'No operations are available for this schedule.'}
        </div>
      ) : (
        <div
          className="gantt"
          role="region"
          tabIndex={0}
          aria-label="Schedule timeline. Use the scroll area to review all resources and hours."
        >
          <div className="gantt-canvas" style={{ width: `${zoom * 100}%` }}>
            <div className="gantt-axis">
              <span>RESOURCE / MACHINE</span>
              <div>
                {[0, 0.25, 0.5, 0.75, 1].map((point) => (
                  <span key={point}>{fmt(maxHour * point, 0)}h</span>
                ))}
              </div>
            </div>
            {rows.map(([resourceId, items]) => {
              const ends: number[] = []
              const slots = [...items]
                .sort((a, b) => a.start_hour - b.start_hour || a.end_hour - b.end_hour)
                .map((item) => {
                  let slot = ends.findIndex((end) => end <= item.start_hour)
                  if (slot < 0) slot = ends.length
                  ends[slot] = item.end_hour
                  return { item, slot }
                })
              return (
                <div className="gantt-row" key={resourceId}>
                  <div className="gantt-resource">
                    <span className="machine-icon">
                      <Wrench size={13} />
                    </span>
                    <span>
                      {items[0].resource_name}
                      <small>{items[0].plant}</small>
                    </span>
                  </div>
                  <div
                    className="gantt-lane"
                    style={{ height: `${Math.max(25, ends.length * 25)}px` }}
                  >
                    {slots.map(({ item, slot }, index) => {
                      const left = Math.max(0, (item.start_hour / maxHour) * 100)
                      const width = (Math.max(0, item.end_hour - item.start_hour) / maxHour) * 100
                      const accessibleName = `${item.wo_number}, ${item.sku_code}, ${item.stage}, ${item.resource_name}, ${fmt(item.start_hour)} to ${fmt(item.end_hour)} hours, ${item.is_late ? 'late' : 'on time'}${item.batch_id ? `, batch ${item.batch_id}` : ''}${item.delay_reason ? `, ${item.delay_reason}` : ''}`
                      return (
                        <button
                          type="button"
                          className={`gantt-bar stage-${stages.indexOf(item.stage) + 1}${item.is_late ? ' is-late' : ''}`}
                          key={`${item.work_order_id}-${item.stage}-${index}`}
                          style={{
                            left: `${left}%`,
                            width: `${Math.min(width, 100 - left)}%`,
                            top: `${slot * 25 + 3}px`,
                          }}
                          aria-label={accessibleName}
                          aria-expanded={selectedOperation === item}
                          aria-controls={selectedOperation === item ? detailId : undefined}
                          title={accessibleName}
                          onClick={(event) => {
                            selectedBar.current = event.currentTarget
                            setSelected(item)
                          }}
                        >
                          <span aria-hidden="true">{item.wo_number}</span>
                        </button>
                      )
                    })}
                  </div>
                </div>
              )
            })}
            <div className="gantt-legend">
              {stages.map((stage, index) => (
                <span key={stage}>
                  <i className={`legend-stage stage-${index + 1}`} />
                  {stage}
                </span>
              ))}
              <span>
                <i className="legend-late" />
                Late at scheduled completion
              </span>
            </div>
          </div>
        </div>
      )}
      {selectedOperation && (
        <div
          className="gantt-detail"
          id={detailId}
          role="region"
          aria-label="Selected operation details"
        >
          <strong>{selectedOperation.wo_number}</strong>
          <span>{selectedOperation.sku_code}</span>
          <span>{selectedOperation.stage}</span>
          {selectedOperation.batch_id && <span>Batch {selectedOperation.batch_id}</span>}
          <span>
            {selectedOperation.resource_name} · {selectedOperation.plant}
          </span>
          <span>
            {fmt(selectedOperation.start_hour)}–{fmt(selectedOperation.end_hour)}h
          </span>
          {selectedOperation.is_late ? (
            <span className="delay-tag">
              Late{selectedOperation.delay_reason ? ` · ${selectedOperation.delay_reason}` : ''}
            </span>
          ) : (
            <span className="on-time-tag">On time at scheduled completion</span>
          )}
          <button
            ref={detailClose}
            type="button"
            className="link-button"
            onClick={() => {
              setSelected(null)
              requestAnimationFrame(() => selectedBar.current?.focus())
            }}
          >
            Clear selection
          </button>
        </div>
      )}
    </>
  )
}
