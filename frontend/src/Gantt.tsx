import { useCallback, useEffect, useId, useMemo, useRef, useState } from 'react'
import { Wrench } from 'lucide-react'
import { fmt } from './api'
import { layoutScheduleRow } from './scheduleRange'
import type { ScheduledOperation as Operation } from './types'
import { stages } from './stages'
import './Gantt.css'

function sameOperation(left: Operation, right: Operation) {
  return (
    (Object.keys(left) as (keyof Operation)[]).every((key) => left[key] === right[key]) &&
    (Object.keys(right) as (keyof Operation)[]).every((key) => left[key] === right[key])
  )
}

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
  const [chartState, setChartState] = useState({
    page: 0,
    length: operations.length,
    sequence: requestSequence,
  })
  const chartPrevious = useRef<HTMLButtonElement | null>(null)
  const chartNext = useRef<HTMLButtonElement | null>(null)
  const chartFocus = useRef<'previous' | 'next' | null>(null)
  const stageFilter = useRef<HTMLSelectElement | null>(null)
  const orderFilter = useRef<HTMLSelectElement | null>(null)
  const listSummary = useRef<HTMLElement | null>(null)
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
  const chartPageSize = 100
  const currentChartPage =
    chartState.sequence !== requestSequence
      ? 0
      : Math.min(chartState.page, Math.max(0, Math.ceil(filtered.length / chartPageSize) - 1))
  if (chartState.length !== filtered.length || chartState.sequence !== requestSequence) {
    setChartState({ page: currentChartPage, length: filtered.length, sequence: requestSequence })
  }
  const setChartPage = (page: number) =>
    setChartState({ page, length: filtered.length, sequence: requestSequence })
  const options = (values: string[]) => [...new Set(values)].sort((a, b) => a.localeCompare(b))
  const setFilter = (name: keyof typeof filters, value: string) => {
    setListPage(0)
    setChartPage(0)
    setSelected(null)
    setHovered(null)
    setFilterState({ filters: { ...filters, [name]: value }, sequence: requestSequence })
  }
  const activeFilters = Object.values(filters).filter(Boolean).length
  const [selected, setSelected] = useState<Operation | null>(null)
  const [selectionUnavailable, setSelectionUnavailable] = useState(false)
  const [hovered, setHovered] = useState<{ item: Operation; rect: DOMRect } | null>(null)
  const detailId = useId()
  const focusedSelection = useRef<Operation | null>(null)
  const selectedBar = useRef<HTMLButtonElement | null>(null)
  const hoveredBar = useRef<HTMLButtonElement | null>(null)
  const detailRef = useRef<HTMLDivElement | null>(null)
  const detailHasFocus = useRef(false)
  const timelineEndRef = useRef<HTMLDivElement | null>(null)
  const restoreSelectionFocus = useCallback(() => {
    requestAnimationFrame(() => {
      const button = selectedBar.current
      const target =
        button?.isConnected && !button.closest('details:not([open])') ? button : listSummary.current
      ;(target ?? stageFilter.current)?.focus()
    })
  }, [])
  const chartStart = currentChartPage * chartPageSize
  const chartOperations = useMemo(
    () => filtered.slice(chartStart, chartStart + chartPageSize),
    [filtered, chartStart],
  )
  const resourceCount = useMemo(
    () => new Set(filtered.map((item) => item.resource_id)).size,
    [filtered],
  )
  const rows = useMemo(() => {
    const grouped = new Map<string, Operation[]>()
    chartOperations.forEach((operation) => {
      const key = operation.resource_id
      const items = grouped.get(key) ?? []
      items.push(operation)
      grouped.set(key, items)
    })
    return [...grouped.entries()]
  }, [chartOperations])
  useEffect(() => {
    const target = chartFocus.current
    if (!target) return
    chartFocus.current = null
    ;(target === 'previous' ? chartPrevious : chartNext).current?.focus()
  }, [currentChartPage])
  const changeChartPage = (page: number) => {
    detailHasFocus.current = false
    chartFocus.current =
      page === 0 ? 'next' : (page + 1) * chartPageSize >= filtered.length ? 'previous' : null
    setSelected(null)
    setHovered(null)
    setSelectionUnavailable(false)
    setChartPage(page)
  }
  const previousChartPage = useRef(currentChartPage)
  useEffect(() => {
    if (previousChartPage.current === currentChartPage) return
    previousChartPage.current = currentChartPage
    if (detailHasFocus.current) stageFilter.current?.focus()
    setSelected(null)
    setHovered(null)
  }, [currentChartPage])
  const selectedOperation = selected
    ? (filtered.find((item) => item === selected) ??
      filtered.find((item) => sameOperation(item, selected)) ??
      null)
    : null
  if (selected && !selectedOperation) {
    setSelected(null)
    setSelectionUnavailable(true)
  }
  const hoveredOperation = hovered
    ? (filtered.find((item) => item === hovered.item) ??
      filtered.find((item) => sameOperation(item, hovered.item)) ??
      null)
    : null
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
    if (selectedOperation && selected !== focusedSelection.current) detailRef.current?.focus()
    focusedSelection.current = selected
  }, [selected, selectedOperation])
  useEffect(() => {
    if (!selectionUnavailable) return
    if (detailHasFocus.current) stageFilter.current?.focus()
    detailHasFocus.current = false
  }, [selectionUnavailable])
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
        restoreSelectionFocus()
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [selectedOperation, restoreSelectionFocus])
  return (
    <>
      <div className="sr-only" role="status">
        {selectionUnavailable && 'The selected operation is no longer available in this schedule.'}
      </div>
      <div className="gantt-controls" aria-label="Timeline filters">
        <label>
          Stage
          <select
            ref={stageFilter}
            value={filters.stage}
            onChange={(e) => setFilter('stage', e.target.value)}
          >
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
            setChartPage(0)
            setSelected(null)
            setHovered(null)
            setFilterState({ filters: emptyFilters, sequence: requestSequence })
            stageFilter.current?.focus()
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
        across {resourceCount} {resourceCount === 1 ? 'resource' : 'resources'} · Timeline: 0–
        {fmt(maxHour, 0)}h
      </div>
      {filtered.length > 0 && (
        <details
          className="operation-list"
          onToggle={(event) => setListOpen(event.currentTarget.open)}
        >
          <summary ref={listSummary}>Browse operations as a list</summary>
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
                        setSelectionUnavailable(false)
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
      {filtered.length > chartPageSize && (
        <nav className="gantt-chart-pages gantt-controls" aria-label="Timeline operation pages">
          <span aria-live="polite">
            Timeline showing {chartStart + 1} to{' '}
            {Math.min(chartStart + chartPageSize, filtered.length)} of {filtered.length} operations
          </span>
          <span>
            Other pages may contain operations on the same resource, including overlapping
            operations.
          </span>
          <button
            type="button"
            ref={chartPrevious}
            disabled={currentChartPage === 0}
            onClick={() => changeChartPage(currentChartPage - 1)}
          >
            Previous timeline operations
          </button>
          <button
            type="button"
            ref={chartNext}
            disabled={chartStart + chartPageSize >= filtered.length}
            onClick={() => changeChartPage(currentChartPage + 1)}
          >
            Next timeline operations
          </button>
        </nav>
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
                const { bars, laneCount } = layoutScheduleRow(items, maxHour)
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
                      style={{ height: `${Math.max(25, laneCount * 25)}px` }}
                    >
                      {bars.map(({ item, slot, left, width }, index) => {
                        const accessibleName = `${item.wo_number}, ${item.sku_code}, ${item.stage}, ${item.resource_name}, ${fmt(item.start_hour)} to ${fmt(item.end_hour)} hours, ${item.is_late ? 'late' : 'on time'}${item.batch_id ? `, batch ${item.batch_id}` : ''}${item.delay_reason ? `, ${item.delay_reason}` : ''}`
                        return (
                          <button
                            type="button"
                            className={`gantt-bar stage-${stages.findIndex((stage) => stage.name === item.stage) + 1}${item.is_late ? ' is-late' : ''}`}
                            key={`${item.work_order_id}-${item.stage}-${index}`}
                            style={{
                              left: `${left}%`,
                              width: `${width}%`,
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
                              setSelectionUnavailable(false)
                              setSelected(item)
                            }}
                          >
                            <span aria-hidden="true">
                              {item.stage} · {item.wo_number}
                            </span>
                          </button>
                        )
                      })}
                    </div>
                  </div>
                )
              })}
              <div className="gantt-legend">
                {stages.map((stage, index) => (
                  <span key={stage.name}>
                    <i className={`legend-stage stage-${index + 1}`} />
                    {stage.name}
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
            onFocusCapture={() => {
              detailHasFocus.current = true
            }}
            onBlurCapture={(event) => {
              if (
                !(event.relatedTarget instanceof Node) ||
                !event.currentTarget.contains(event.relatedTarget)
              )
                detailHasFocus.current = false
            }}
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
                  restoreSelectionFocus()
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
