import { useEffect, useId, useMemo, useRef, useState } from 'react'
import { Wrench } from 'lucide-react'
import { fmt } from './api'
import type { ScheduledOperation as Operation } from './types'
import './Gantt.css'

const stages = ['Molding', 'Debinding', 'Sintering', 'CNC Machining', 'Finishing']

function revealFocusedBar(bar: HTMLButtonElement) {
  const timeline = bar.closest<HTMLElement>('.gantt')
  const resource = bar.closest('.gantt-row')?.querySelector<HTMLElement>('.gantt-resource')
  if (!timeline || !resource) return

  const barBounds = bar.getBoundingClientRect()
  const timelineBounds = timeline.getBoundingClientRect()
  const left =
    Math.max(timelineBounds.left + timeline.clientLeft, resource.getBoundingClientRect().right) + 4
  const right = timelineBounds.left + timeline.clientLeft + timeline.clientWidth - 4
  if (barBounds.left < left) timeline.scrollLeft -= left - barBounds.left
  else if (barBounds.right > right) timeline.scrollLeft += barBounds.right - right
}

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
  const [listOpen, setListOpen] = useState(false)
  const [listPage, setListPage] = useState(0)
  const orderFilter = useRef<HTMLSelectElement | null>(null)
  const previousPageButton = useRef<HTMLButtonElement | null>(null)
  const nextPageButton = useRef<HTMLButtonElement | null>(null)
  const paginationFocus = useRef<'previous' | 'next' | null>(null)
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
  const setFilter = (name: keyof typeof filters, value: string) => {
    setListPage(0)
    setFilterState({ filters: { ...filters, [name]: value }, sequence: requestSequence })
  }
  const activeFilters = Object.values(filters).filter(Boolean).length
  const [selected, setSelected] = useState<Operation | null>(null)
  const [hovered, setHovered] = useState<{ item: Operation; rect: DOMRect } | null>(null)
  const detailId = useId()
  const selectedBar = useRef<HTMLButtonElement | null>(null)
  const hoveredBar = useRef<HTMLButtonElement | null>(null)
  const detailRef = useRef<HTMLDivElement | null>(null)
  const timelineEndRef = useRef<HTMLDivElement | null>(null)
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
  const hoveredOperation = hovered && filtered.includes(hovered.item) ? hovered.item : null
  const displayedOperation = selectedOperation ?? hoveredOperation
  const pageSize = 50
  const currentPage = Math.min(listPage, Math.max(0, Math.ceil(filtered.length / pageSize) - 1))
  const pageStart = currentPage * pageSize
  useEffect(() => {
    const target = paginationFocus.current
    if (!target) return
    paginationFocus.current = null
    ;(target === 'previous' ? previousPageButton : nextPageButton).current?.focus()
  }, [currentPage])
  const spaceBelow = hovered ? window.innerHeight - hovered.rect.bottom : 0
  const showBelow = hovered ? spaceBelow >= hovered.rect.top : true
  useEffect(() => {
    if (selectedOperation) detailRef.current?.focus()
  }, [selectedOperation])
  useEffect(() => {
    if (!hoveredOperation || selectedOperation) return
    const dismiss = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setHovered(null)
    }
    window.addEventListener('keydown', dismiss)
    return () => window.removeEventListener('keydown', dismiss)
  }, [hoveredOperation, selectedOperation])
  useEffect(() => {
    if (!hoveredOperation) return
    const dismiss = (event: Event) => {
      if (event.target instanceof Node && detailRef.current?.contains(event.target)) return
      setHovered(null)
    }
    window.addEventListener('scroll', dismiss, true)
    window.addEventListener('resize', dismiss)
    return () => {
      window.removeEventListener('scroll', dismiss, true)
      window.removeEventListener('resize', dismiss)
    }
  }, [hoveredOperation])
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
          onClick={() => {
            setListPage(0)
            setFilterState({ filters: emptyFilters, sequence: requestSequence })
          }}
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
        {filtered.length.toLocaleString()} {filtered.length === 1 ? 'operation' : 'operations'}{' '}
        across {rows.length} {rows.length === 1 ? 'resource' : 'resources'} · Timeline: 0–
        {fmt(maxHour, 0)}h
      </div>
      {filtered.length > 0 && (
        <details
          className="operation-list"
          onToggle={(event) => setListOpen(event.currentTarget.open)}
        >
          <summary>Browse operations as a list</summary>
          {listOpen && (
            <div>
              <p>Choose an operation to view its details. The list follows the timeline filters.</p>
              <p className="operation-list-count" aria-live="polite">
                Showing {pageStart + 1}–{Math.min(pageStart + pageSize, filtered.length)} of{' '}
                {filtered.length} operations
              </p>
              <ul>
                {filtered.slice(pageStart, pageStart + pageSize).map((item, index) => (
                  <li key={`${item.work_order_id}-${item.stage}-${pageStart + index}`}>
                    <button
                      type="button"
                      className="operation-list-item"
                      aria-expanded={selectedOperation === item}
                      aria-controls={selectedOperation === item ? detailId : undefined}
                      onClick={(event) => {
                        selectedBar.current = event.currentTarget
                        setHovered(null)
                        setSelected(item)
                        if (selectedOperation === item) detailRef.current?.focus()
                      }}
                    >
                      {item.wo_number} · {item.stage} · {item.resource_name} ·{' '}
                      {fmt(item.start_hour)}–{fmt(item.end_hour)}h ·{' '}
                      {item.is_late ? 'Late' : 'On time'}
                    </button>
                  </li>
                ))}
              </ul>
              <div className="gantt-controls">
                <button
                  type="button"
                  ref={previousPageButton}
                  disabled={currentPage === 0}
                  onClick={() => {
                    paginationFocus.current = currentPage === 1 ? 'next' : null
                    setListPage(currentPage - 1)
                  }}
                >
                  Previous operations
                </button>
                <button
                  type="button"
                  ref={nextPageButton}
                  disabled={pageStart + pageSize >= filtered.length}
                  onClick={() => {
                    paginationFocus.current =
                      pageStart + 2 * pageSize >= filtered.length ? 'previous' : null
                    setListPage(currentPage + 1)
                  }}
                >
                  Next operations
                </button>
              </div>
            </div>
          )}
        </details>
      )}
      {filtered.length > 0 && (
        <button
          className="gantt-skip"
          type="button"
          onClick={() => timelineEndRef.current?.focus()}
        >
          Skip timeline operations
        </button>
      )}
      <div onMouseLeave={() => setHovered(null)}>
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
                            onFocus={(event) => revealFocusedBar(event.currentTarget)}
                            onMouseEnter={(event) => {
                              if (!selectedOperation) {
                                hoveredBar.current = event.currentTarget
                                setHovered({
                                  item,
                                  rect: event.currentTarget.getBoundingClientRect(),
                                })
                              }
                            }}
                            onMouseLeave={(event) => {
                              if (
                                !(event.relatedTarget instanceof Node) ||
                                !detailRef.current?.contains(event.relatedTarget)
                              )
                                setHovered(null)
                            }}
                            onClick={(event) => {
                              selectedBar.current = event.currentTarget
                              setHovered(null)
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
        {filtered.length > 0 && (
          <div className="gantt-end" ref={timelineEndRef} tabIndex={-1}>
            End of timeline
          </div>
        )}
        {displayedOperation && (
          <div
            ref={detailRef}
            className="gantt-detail"
            id={selectedOperation ? detailId : undefined}
            role={selectedOperation ? 'region' : undefined}
            aria-label={selectedOperation ? 'Selected operation details' : undefined}
            aria-describedby={
              selectedOperation
                ? [
                    'order',
                    'sku',
                    'stage',
                    'batch',
                    'resource',
                    'time',
                    'duration',
                    'status',
                    'provenance',
                  ]
                    .map((part) => `${detailId}-${part}`)
                    .join(' ')
                : undefined
            }
            tabIndex={selectedOperation ? -1 : undefined}
            aria-hidden={selectedOperation ? undefined : true}
            onMouseLeave={(event) => {
              if (
                !selectedOperation &&
                (!(event.relatedTarget instanceof Node) ||
                  !hoveredBar.current?.contains(event.relatedTarget))
              )
                setHovered(null)
            }}
            style={
              !selectedOperation && hovered
                ? {
                    position: 'fixed',
                    zIndex: 20,
                    left: Math.max(8, Math.min(hovered.rect.left, window.innerWidth - 328)),
                    ...(showBelow
                      ? { top: hovered.rect.bottom }
                      : { bottom: window.innerHeight - hovered.rect.top }),
                    width: 'min(320px, calc(100vw - 16px))',
                    maxHeight: Math.max(
                      0,
                      Math.min(200, (showBelow ? spaceBelow : hovered.rect.top) - 8),
                    ),
                    overflowY: 'auto',
                    padding: '12px',
                    background: 'var(--surface)',
                    border: '1px solid var(--line)',
                    borderRadius: '6px',
                    boxShadow: '0 4px 18px #0003',
                  }
                : undefined
            }
          >
            <strong id={`${detailId}-order`}>{displayedOperation.wo_number}</strong>
            <span id={`${detailId}-sku`}>{displayedOperation.sku_code}</span>
            <span id={`${detailId}-stage`}>{displayedOperation.stage}</span>
            <span id={`${detailId}-batch`}>
              {displayedOperation.batch_id ? `Batch ${displayedOperation.batch_id}` : 'No batch'}
            </span>
            <span id={`${detailId}-resource`}>
              {displayedOperation.resource_name} · {displayedOperation.plant}
            </span>
            <span id={`${detailId}-time`}>
              {fmt(displayedOperation.start_hour)}–{fmt(displayedOperation.end_hour)}h
            </span>
            <span id={`${detailId}-duration`}>
              Duration: {fmt(displayedOperation.end_hour - displayedOperation.start_hour)} hours
            </span>
            {displayedOperation.is_late ? (
              <span id={`${detailId}-status`} className="delay-tag">
                Late{displayedOperation.delay_reason ? ` · ${displayedOperation.delay_reason}` : ''}
              </span>
            ) : (
              <span id={`${detailId}-status`} className="on-time-tag">
                On time at scheduled completion
              </span>
            )}
            <span id={`${detailId}-provenance`}>
              Modeled operation · not a committed production order
            </span>
            {selectedOperation && (
              <button
                type="button"
                className="link-button"
                onClick={() => {
                  setSelected(null)
                  requestAnimationFrame(() => selectedBar.current?.focus())
                }}
              >
                Clear selection
              </button>
            )}
          </div>
        )}
      </div>
    </>
  )
}
