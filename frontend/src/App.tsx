import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Activity,
  AlertTriangle,
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  Boxes,
  Check,
  ChevronDown,
  CircleHelp,
  Clock3,
  Factory,
  Gauge,
  GitCompareArrows,
  Layers3,
  Play,
  RefreshCw,
  ShieldCheck,
  GitBranch,
  Truck,
  Wrench,
  Zap,
} from 'lucide-react'
import { api, fmt } from './api'
import type {
  Board,
  CatalogResponse,
  OptimizeResponse,
  Queue,
  Resource,
  ScenarioResponse,
  ScheduledOperation,
  WorkOrder,
} from './types'

export type Operation = ScheduledOperation
type Optimization = OptimizeResponse
type Simulation = ScenarioResponse
type ScenarioInputs = { downId: string; rushId: string; demand: number }
type ScenarioRun = { inputs: ScenarioInputs; result: Simulation }
type Page = 'board' | 'optimizer' | 'scenario'

const stages = ['Molding', 'Debinding', 'Sintering', 'CNC Machining', 'Finishing']
const stageShort: Record<string, string> = {
  Molding: 'Molding',
  Debinding: 'Debinding',
  Sintering: 'Sintering',
  'CNC Machining': 'CNC',
  Finishing: 'Finishing',
}
const stageGlyph: Record<string, string> = {
  Molding: '01',
  Debinding: '02',
  Sintering: '03',
  'CNC Machining': '04',
  Finishing: '05',
}
const canSeedDemo = () => import.meta.env.VITE_ENABLE_DEMO_SEED === 'true'
const formatPlanningAlert = (alert: string) =>
  alert.replace(/active bottleneck/gi, 'modeled busy-hours signal')

function App() {
  const [page, setPage] = useState<Page>('board')
  const [board, setBoard] = useState<Board | null>(null)
  const [resources, setResources] = useState<Resource[]>([])
  const [orders, setOrders] = useState<WorkOrder[]>([])
  const [optimization, setOptimization] = useState<Optimization | null>(null)
  const [scenarioRun, setScenarioRun] = useState<ScenarioRun | null>(null)
  const [busy, setBusy] = useState<'seed' | 'optimize' | 'simulate' | null>(null)
  const [error, setError] = useState('')
  const [downId, setDownId] = useState('')
  const [rushId, setRushId] = useState('')
  const [demand, setDemand] = useState(0)
  const [scheduleTab, setScheduleTab] = useState<'optimized' | 'baseline'>('optimized')
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const refreshSequence = useRef(0)
  const refreshController = useRef<AbortController | null>(null)
  const scheduleRequestInFlight = useRef(false)
  const simulation = scenarioRun?.result ?? null
  const scenarioInputs = { downId, rushId, demand }
  const scenarioIsStale = Boolean(
    scenarioRun &&
    (scenarioRun.inputs.downId !== downId ||
      scenarioRun.inputs.rushId !== rushId ||
      scenarioRun.inputs.demand !== demand),
  )

  const refresh = useCallback(async () => {
    const sequence = ++refreshSequence.current
    refreshController.current?.abort()
    const controller = new AbortController()
    refreshController.current = controller
    try {
      const [b, catalog] = await Promise.all([
        api<Board>('/api/flow-board', { signal: controller.signal }),
        api<CatalogResponse>('/api/catalog', { signal: controller.signal }),
      ])
      if (sequence !== refreshSequence.current) return
      setBoard(b)
      setResources(catalog.resources)
      setOrders(catalog.work_orders)
      setLastUpdated(new Date())
      setError('')
    } catch (e) {
      if (sequence !== refreshSequence.current || (e instanceof Error && e.name === 'AbortError'))
        return
      setError(e instanceof Error ? e.message : 'Could not connect to the IndoFlow API.')
    }
  }, [])

  useEffect(() => {
    queueMicrotask(() => void refresh())
    return () => {
      refreshSequence.current += 1
      refreshController.current?.abort()
    }
  }, [refresh])

  const activeResources = resources.filter((resource) => resource.status === 'ACTIVE')
  const stageMax = Math.max(1, ...(board?.queues.map((queue) => queue.queue_depth) ?? [1]))
  const bottleneckQueue = board?.queues.reduce<Queue | null>(
    (top, queue) => (!top || queue.queue_depth > top.queue_depth ? queue : top),
    null,
  )
  const downResource = resources.find((resource) => resource.id === downId)
  const shownOperations = useMemo(
    () => [...(optimization?.gantt[scheduleTab] ?? [])].sort((a, b) => a.start_hour - b.start_hour),
    [optimization, scheduleTab],
  )
  const maxHour = Math.max(24, ...shownOperations.map((item) => item.end_hour))

  async function seedDemo() {
    if (!canSeedDemo()) {
      setError(
        'Demo seeding is disabled. Enable VITE_ENABLE_DEMO_SEED=true only for a dedicated local demo database.',
      )
      return
    }
    if (
      !window.confirm(
        'Load the synthetic demo dataset? This resets factory rows in the database currently configured for the API.',
      )
    )
      return
    setBusy('seed')
    setError('')
    try {
      await api('/api/seed', { method: 'POST' })
      setOptimization(null)
      setScenarioRun(null)
      await refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load demo data.')
    } finally {
      setBusy(null)
    }
  }

  async function optimize() {
    if (scheduleRequestInFlight.current) return
    scheduleRequestInFlight.current = true
    setBusy('optimize')
    setError('')
    try {
      setOptimization(
        await api<Optimization>('/api/schedule/optimize', {
          method: 'POST',
          body: JSON.stringify({ time_limit_seconds: 3 }),
        }),
      )
      setPage('optimizer')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Schedule optimization failed.')
    } finally {
      scheduleRequestInFlight.current = false
      setBusy(null)
    }
  }

  async function runScenario() {
    if (scheduleRequestInFlight.current) return
    scheduleRequestInFlight.current = true
    const submittedInputs = { ...scenarioInputs }
    setBusy('simulate')
    setError('')
    try {
      const result = await api<Simulation>('/api/schedule/simulate', {
        method: 'POST',
        body: JSON.stringify({
          down_resource_ids: submittedInputs.downId ? [submittedInputs.downId] : [],
          rush_order_ids: submittedInputs.rushId ? [submittedInputs.rushId] : [],
          demand_spike_pct: submittedInputs.demand,
          time_limit_seconds: 3,
        }),
      })
      setScenarioRun({ inputs: submittedInputs, result })
      setPage('scenario')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Scenario simulation failed.')
    } finally {
      scheduleRequestInFlight.current = false
      setBusy(null)
    }
  }

  function resetScenarioInputs() {
    setDownId('')
    setRushId('')
    setDemand(0)
  }

  const activePageLabel =
    page === 'board' ? 'Flow board' : page === 'optimizer' ? 'Schedule optimizer' : 'Scenario lab'
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a
          className="brand"
          href="#board"
          onClick={(e) => {
            e.preventDefault()
            setPage('board')
          }}
        >
          <span className="brand-mark">
            <Factory size={19} strokeWidth={2.4} />
          </span>
          <span className="brand-name">
            indo<span>flow</span>
            <small>PLANT INTELLIGENCE</small>
          </span>
        </a>
        <div className="side-label">WORKSPACE</div>
        <nav className="nav-list">
          <button
            className={page === 'board' ? 'nav-item selected' : 'nav-item'}
            aria-current={page === 'board' ? 'page' : undefined}
            onClick={() => setPage('board')}
          >
            <Layers3 size={17} />
            <span>Flow board</span>
            <span className="nav-dot" />
          </button>
          <button
            className={page === 'optimizer' ? 'nav-item selected' : 'nav-item'}
            aria-current={page === 'optimizer' ? 'page' : undefined}
            onClick={() => setPage('optimizer')}
          >
            <GitCompareArrows size={17} />
            <span>Schedule optimizer</span>
          </button>
          <button
            className={page === 'scenario' ? 'nav-item selected' : 'nav-item'}
            aria-current={page === 'scenario' ? 'page' : undefined}
            onClick={() => setPage('scenario')}
          >
            <GitBranch size={17} />
            <span>Scenario lab</span>
            <span className="beta">WHAT IF</span>
          </button>
        </nav>
        <div className="sidebar-bottom">
          <div className="plant-card">
            <span className="plant-icon">
              <Factory size={16} />
            </span>
            <div>
              <b>Synthetic factory</b>
              <small>Example resources</small>
            </div>
            <ChevronDown size={14} />
          </div>
          <div className="side-user">
            <div className="avatar">IF</div>
            <div>
              <b>IndoFlow demo</b>
              <small>Operations workspace</small>
            </div>
            <CircleHelp size={17} />
          </div>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="crumb">
            Workspace <span>/</span> <b>{activePageLabel}</b>
          </div>
          <div className="top-actions">
            <span className="live-indicator">
              <i /> Synthetic demo · no live ERP
            </span>
            <span className="top-divider" />
            <span className="updated">
              {lastUpdated
                ? `Updated ${lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
                : 'Waiting for API'}
            </span>
            <button
              className="icon-button"
              onClick={() => void refresh()}
              aria-label="Refresh data"
              title="Refresh data"
            >
              <RefreshCw size={16} />
            </button>
            <div className="avatar top-avatar">IF</div>
          </div>
        </header>
        <div className="page-content">
          {error && (
            <div className="error-banner" role="alert">
              <AlertTriangle size={17} />
              <div>
                <b>Something needs attention</b>
                <span>
                  {error}
                  {error.includes('401') || error.includes('403')
                    ? ' Configure the API bearer token in the frontend environment before using a protected deployment.'
                    : ''}
                </span>
              </div>
              <button onClick={() => setError('')} aria-label="Dismiss">
                ×
              </button>
            </div>
          )}
          {!board && (
            <section className="welcome-panel">
              <div className="welcome-icon">
                <Activity size={24} />
              </div>
              <h1>Connect to the factory demo</h1>
              <p className="welcome-copy">
                Connect to the IndoFlow API and load a synthetic factory dataset to explore live
                WIP, optimized schedules, and operational what-if scenarios.
              </p>
              <div className="welcome-actions">
                <button
                  className="primary-button"
                  onClick={seedDemo}
                  disabled={busy !== null || !lastUpdated || !canSeedDemo()}
                  title={
                    !canSeedDemo()
                      ? 'Seeding is off. Enable it only for a dedicated local demo database.'
                      : !lastUpdated
                        ? 'Connect to the API before loading demo records.'
                        : undefined
                  }
                >
                  <Play size={16} fill="currentColor" />
                  {busy === 'seed' ? 'Loading demo data…' : 'Load synthetic demo data'}
                </button>
                <button className="text-button" onClick={() => void refresh()}>
                  <RefreshCw size={15} /> Retry API connection
                </button>
              </div>
              <div className="welcome-note">
                <ShieldCheck size={15} /> Demo records are synthetic. Seeding is off unless
                explicitly enabled for a dedicated local demo database.
              </div>
            </section>
          )}

          {board && page === 'board' && (
            <>
              <div className="page-heading">
                <div>
                  <p className="eyebrow">Synthetic demo data</p>
                  <h1>Production flow overview</h1>
                  <p className="heading-sub">
                    Work orders and resource queues from the latest API snapshot.
                  </p>
                </div>
                <button className="primary-button" onClick={optimize} disabled={busy !== null}>
                  <Zap size={16} fill="currentColor" />
                  {busy === 'optimize' ? 'Optimizing…' : 'Optimize schedule'}
                  <ArrowRight size={15} />
                </button>
              </div>
              <div className="stat-grid">
                <StatCard
                  label="Active work orders"
                  value={fmt(board.total_wip_orders, 0)}
                  icon={<Boxes size={18} />}
                  foot="Open across all stages"
                  tone="blue"
                />
                <StatCard
                  label="Average WIP age"
                  value={board.total_wip_orders ? `${fmt(board.avg_wip_age_hours)}h` : '—'}
                  icon={<Clock3 size={18} />}
                  foot="Average age of open orders in this snapshot"
                  tone="amber"
                />
                <StatCard
                  label="Largest stage queue"
                  value={board.total_wip_orders ? (bottleneckQueue?.stage ?? '—') : '—'}
                  icon={<Gauge size={18} />}
                  foot={
                    board.total_wip_orders
                      ? `${bottleneckQueue?.queue_depth ?? 0} open work orders in this API snapshot`
                      : 'No queued work orders'
                  }
                  tone="violet"
                  compact
                />
                <StatCard
                  label="Configured resources"
                  value={`${activeResources.length} / ${resources.length}`}
                  icon={<Activity size={18} />}
                  foot="Marked active in the resource catalog"
                  tone="green"
                />
              </div>
              {board.total_wip_orders === 0 ? (
                <section className="panel empty-board">
                  <span className="placeholder-orbit">
                    <Boxes size={22} />
                  </span>
                  <h2>No work orders in this database</h2>
                  <p>
                    Load the documented synthetic dataset to explore the flow board, schedule, and
                    scenario controls.
                  </p>
                  <button
                    className="primary-button"
                    onClick={seedDemo}
                    disabled={busy !== null || !lastUpdated || !canSeedDemo()}
                    title={
                      !canSeedDemo()
                        ? 'Enable seeding only for a dedicated local demo database.'
                        : undefined
                    }
                  >
                    <GitBranch size={16} />{' '}
                    {busy === 'seed' ? 'Loading example…' : 'Load synthetic example'}
                  </button>
                </section>
              ) : (
                <div className="content-grid board-grid">
                  <section className="panel flow-panel">
                    <div className="panel-heading">
                      <div>
                        <h2>Production flow</h2>
                        <p>Work in progress by current stage</p>
                      </div>
                      <span className="neutral-pill">
                        <span className="pulse" /> API SNAPSHOT
                      </span>
                    </div>
                    <div className="flow-track">
                      {stages.map((stage, index) => {
                        const queue = board.queues.find((item) => item.stage === stage)
                        const count = queue?.queue_depth ?? 0
                        return (
                          <div className="stage-column" key={stage}>
                            <div className="stage-top">
                              <span className="stage-index">{stageGlyph[stage]}</span>
                              {index < stages.length - 1 && (
                                <span className="stage-connector">
                                  <ArrowRight size={13} />
                                </span>
                              )}
                            </div>
                            <div className="stage-count">{count.toLocaleString()}</div>
                            <div className="stage-name">{stageShort[stage]}</div>
                            <div className="stage-bar">
                              <span
                                style={{
                                  width: `${Math.max(count ? 5 : 0, (count / stageMax) * 100)}%`,
                                }}
                              />
                            </div>
                            <div className="stage-meta">
                              {fmt(queue?.avg_wip_age_hours)}h avg age
                            </div>
                          </div>
                        )
                      })}
                    </div>
                    <div className="flow-foot">
                      <span>
                        <i className="legend-dot" /> Open orders at each operation’s current stage
                      </span>
                      <button className="link-button" onClick={optimize}>
                        View schedule <ArrowRight size={14} />
                      </button>
                    </div>
                  </section>
                  <section className="panel alerts-panel">
                    <div className="panel-heading">
                      <div>
                        <h2>Needs attention</h2>
                        <p>
                          Model signals from this data snapshot; validate constraints with a planner
                        </p>
                      </div>
                      <span className="alert-count">{board.active_bottleneck_alerts.length}</span>
                    </div>
                    {board.active_bottleneck_alerts.length ? (
                      <div className="alert-list">
                        {board.active_bottleneck_alerts.map((alert, index) => (
                          <div className="alert-row" key={alert}>
                            <span className="alert-symbol">
                              <AlertTriangle size={15} />
                            </span>
                            <div>
                              <b>{index === 0 ? 'Modeled busy-hours signal' : 'Capacity signal'}</b>
                              <span>{formatPlanningAlert(alert)}</span>
                            </div>
                            <ArrowRight size={15} />
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="empty-alert">
                        <span>
                          <Check size={18} />
                        </span>
                        <div>
                          <b>Clear for now</b>
                          <small>No planning alerts in this API snapshot.</small>
                        </div>
                      </div>
                    )}
                    <button className="scenario-shortcut" onClick={() => setPage('scenario')}>
                      <span className="shortcut-icon">
                        <GitBranch size={16} />
                      </span>
                      <span>
                        <b>Plan for a disruption</b>
                        <small>Try a machine outage or rush order</small>
                      </span>
                      <ArrowRight size={15} />
                    </button>
                  </section>
                </div>
              )}
              <div className="bottom-grid">
                <section className="panel capability-panel">
                  <div className="capability-icon">
                    <GitCompareArrows size={19} />
                  </div>
                  <div>
                    <h2>Compare production schedules</h2>
                    <p>
                      Compare an illustrative FIFO baseline with a proposed schedule based on the
                      resource constraints supplied by this demo API.
                    </p>
                  </div>
                  <button className="secondary-button" onClick={optimize} disabled={busy !== null}>
                    {busy === 'optimize' ? 'Working…' : 'Run comparison'} <ArrowRight size={14} />
                  </button>
                </section>
                <div className="trust-note">
                  <ShieldCheck size={16} />
                  <span>
                    <b>Read-only by design</b>
                    <br />
                    Scheduling does not change source work orders.
                  </span>
                </div>
              </div>
            </>
          )}

          {board && page === 'optimizer' && (
            <>
              <div className="page-heading">
                <div>
                  <h1>Schedule optimizer</h1>
                  <p className="heading-sub">
                    Compare an illustrative FIFO reference with a proposed model schedule.
                  </p>
                </div>
                <button className="primary-button" onClick={optimize} disabled={busy !== null}>
                  <RefreshCw size={15} className={busy === 'optimize' ? 'spin' : ''} />
                  {busy === 'optimize' ? 'Running model…' : 'Run optimization'}
                </button>
              </div>
              {!optimization ? (
                <div className="empty-run panel">
                  <div className="empty-run-icon">
                    <GitCompareArrows size={21} />
                  </div>
                  <h2>Generate a proposed schedule</h2>
                  <p>
                    Run the model to compare late orders, WIP age, and flow time against an
                    illustrative FIFO reference.
                  </p>
                  <button className="primary-button" onClick={optimize} disabled={busy !== null}>
                    <Play size={15} fill="currentColor" />
                    {busy === 'optimize' ? 'Running…' : 'Optimize now'}
                  </button>
                </div>
              ) : (
                <>
                  <div className="result-banner">
                    <span className="result-icon">
                      <GitBranch size={18} />
                    </span>
                    <div>
                      <b>Proposed model schedule ready</b>
                      <small>
                        Based on the work orders and resource constraints returned by this API.
                      </small>
                    </div>
                    <span className="result-time">API RESULT</span>
                  </div>
                  <div className="comparison-grid">
                    <CompareCard
                      title="Late work orders"
                      before={optimization.comparison.baseline.late_orders}
                      after={optimization.comparison.optimized.late_orders}
                      delta={optimization.comparison.delta.late_orders}
                      unit="orders"
                      goodDown
                    />
                    <CompareCard
                      title="Average WIP age"
                      before={optimization.comparison.baseline.avg_wip_age_hours}
                      after={optimization.comparison.optimized.avg_wip_age_hours}
                      delta={optimization.comparison.delta.avg_wip_age_hours}
                      unit="hours"
                      goodDown
                    />
                    <CompareCard
                      title="Throughput"
                      before={optimization.comparison.baseline.throughput}
                      after={optimization.comparison.optimized.throughput}
                      delta={optimization.comparison.delta.throughput}
                      unit="orders"
                      goodDown={false}
                    />
                    <CompareCard
                      title="Furnace batch fill"
                      before={optimization.comparison.baseline.furnace_batch_efficiency_pct}
                      after={optimization.comparison.optimized.furnace_batch_efficiency_pct}
                      delta={optimization.comparison.delta.furnace_batch_efficiency_pct}
                      unit="pp"
                      goodDown={false}
                    />
                  </div>
                  <p className="metric-caption">
                    Throughput counts modeled work orders completed within 168 hours. Furnace batch
                    fill is a modeled load ratio; it is not utilization or OEE. Deltas show proposed
                    minus reference, in percentage points for batch fill.
                  </p>
                  <section className="panel schedule-panel">
                    <div className="panel-heading schedule-heading">
                      <div>
                        <h2>Production timeline</h2>
                        <p>All returned operations · planned hours from now</p>
                      </div>
                      <div className="segmented" role="group" aria-label="Schedule view">
                        <button
                          className={scheduleTab === 'optimized' ? 'active' : ''}
                          aria-pressed={scheduleTab === 'optimized'}
                          onClick={() => setScheduleTab('optimized')}
                        >
                          Optimized
                        </button>
                        <button
                          className={scheduleTab === 'baseline' ? 'active' : ''}
                          aria-pressed={scheduleTab === 'baseline'}
                          onClick={() => setScheduleTab('baseline')}
                        >
                          Baseline
                        </button>
                      </div>
                    </div>
                    <Gantt operations={shownOperations} maxHour={maxHour} />
                  </section>
                  <section className="panel late-panel">
                    <div className="panel-heading">
                      <div>
                        <h2>Late order explanations</h2>
                        <p>
                          Orders still projected to miss their due date under the optimized plan
                        </p>
                      </div>
                      <span className="neutral-pill">
                        {optimization.why_late.optimized.length} ORDERS
                      </span>
                    </div>
                    {optimization.why_late.optimized.length ? (
                      <div
                        className="late-table"
                        role="region"
                        aria-label="Late order explanations"
                        tabIndex={0}
                      >
                        <div className="table-head">
                          <span>WORK ORDER</span>
                          <span>DELAY</span>
                          <span>CAPACITY EXPLANATION</span>
                        </div>
                        {optimization.why_late.optimized.map((order) => (
                          <div className="late-row" key={order.work_order_id}>
                            <b>{order.wo_number}</b>
                            <span className="delay-tag">+{fmt(order.delay_hours)}h</span>
                            <span>{order.explanation}</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="empty-alert">
                        <span>
                          <Check size={18} />
                        </span>
                        <div>
                          <b>No late orders projected</b>
                          <small>
                            The optimized schedule places all currently schedulable orders before
                            their due dates.
                          </small>
                        </div>
                      </div>
                    )}
                  </section>
                </>
              )}
            </>
          )}

          {board && page === 'scenario' && (
            <>
              <div className="page-heading">
                <div>
                  <h1>Scenario lab</h1>
                  <p className="heading-sub">
                    Model how a change in capacity or demand affects scheduled work.
                  </p>
                </div>
                <span className="read-only-tag">
                  <ShieldCheck size={14} /> Does not change factory data
                </span>
              </div>
              <div className="scenario-layout">
                <section className="panel scenario-controls">
                  <div className="panel-heading">
                    <div>
                      <h2>Scenario inputs</h2>
                      <p>Choose one or more events to simulate</p>
                    </div>
                  </div>
                  <label className="field-label" htmlFor="machine-down">
                    Machine unavailable
                  </label>
                  <div className="select-wrap">
                    <Wrench size={16} />
                    <select
                      id="machine-down"
                      aria-describedby="machine-down-help"
                      value={downId}
                      onChange={(e) => setDownId(e.target.value)}
                    >
                      <option value="">No machine outage</option>
                      {activeResources.map((resource) => (
                        <option key={resource.id} value={resource.id}>
                          {resource.name} · {stageShort[resource.stage] ?? resource.stage} ·{' '}
                          {resource.plant}
                        </option>
                      ))}
                    </select>
                    <ChevronDown size={15} />
                  </div>
                  <p className="field-help" id="machine-down-help">
                    If selected, this resource is removed from the scenario schedule.
                  </p>
                  <label className="field-label" htmlFor="rush-order">
                    Priority rush order
                  </label>
                  <div className="select-wrap">
                    <Truck size={16} />
                    <select
                      id="rush-order"
                      aria-describedby="rush-order-help"
                      value={rushId}
                      onChange={(e) => setRushId(e.target.value)}
                    >
                      <option value="">No rush order</option>
                      {orders.map((order) => (
                        <option key={order.id} value={order.id}>
                          {order.wo_number} · {order.sku_code} · due {fmt(order.due_date_hours)}h
                        </option>
                      ))}
                    </select>
                    <ChevronDown size={15} />
                  </div>
                  <p className="field-help" id="rush-order-help">
                    Selected orders use priority 5 and a due time capped at 24 hours in the
                    simulation.
                  </p>
                  <div className="slider-head">
                    <label className="field-label" htmlFor="demand-spike">
                      Demand increase
                    </label>
                    <b>{demand}%</b>
                  </div>
                  <input
                    id="demand-spike"
                    aria-describedby="demand-spike-help"
                    aria-valuetext={`${demand}% demand increase`}
                    className="range-input"
                    type="range"
                    min="0"
                    max="300"
                    step="1"
                    value={demand}
                    onChange={(e) => setDemand(Number(e.target.value))}
                  />
                  <div className="range-scale">
                    <span>0%</span>
                    <span>150%</span>
                    <span>300%</span>
                  </div>
                  <div className="scenario-preview">
                    <span>
                      <Activity size={16} />
                    </span>
                    <div>
                      <b>Scenario preview</b>
                      <small>
                        {[
                          downId ? '1 machine outage' : '',
                          rushId ? '1 priority order' : '',
                          demand ? `${demand}% higher volume` : 'baseline demand',
                        ]
                          .filter(Boolean)
                          .join(' · ')}
                      </small>
                    </div>
                  </div>
                  <p className="field-help" id="demand-spike-help">
                    Demand scales scenario quantities by 1 + the selected percentage. It does not
                    add forecast orders.
                  </p>
                  {orders.length === 0 && (
                    <div className="scenario-no-data" role="status">
                      <b>No schedulable work orders are available.</b>
                      <span>Load the synthetic example from the Flow board before simulating.</span>
                    </div>
                  )}
                  <div className="scenario-actions">
                    <button
                      className="secondary-button"
                      onClick={resetScenarioInputs}
                      disabled={busy !== null || (!downId && !rushId && demand === 0)}
                    >
                      Reset inputs
                    </button>
                    <button
                      className="primary-button run-scenario"
                      onClick={runScenario}
                      disabled={busy !== null || orders.length === 0}
                    >
                      <Zap size={15} fill="currentColor" />
                      {busy === 'simulate' ? 'Simulating scenario…' : 'Run scenario'}
                      <ArrowRight size={15} />
                    </button>
                  </div>
                </section>
                <section className="scenario-results">
                  {simulation ? (
                    <>
                      {scenarioIsStale && (
                        <div className="result-banner" role="status">
                          <span className="result-icon">
                            <AlertTriangle size={18} />
                          </span>
                          <div>
                            <b>Inputs changed since this run</b>
                            <small>
                              The result still reflects the submitted inputs below. Run again to
                              update it.
                            </small>
                          </div>
                          <span className="result-time">STALE INPUTS</span>
                        </div>
                      )}
                      <div className="scenario-result-top">
                        <div>
                          <h2>Simulation results</h2>
                        </div>
                      </div>
                      <div className="scenario-insight">
                        <span>
                          <Activity size={16} />
                        </span>
                        <div>
                          <b>Submitted scenario inputs</b>
                          <small>
                            Resource outage: {scenarioRun?.inputs.downId || 'none'} · Priority
                            order: {scenarioRun?.inputs.rushId || 'none'} · Demand increase:{' '}
                            {scenarioRun?.inputs.demand ?? 0}%
                          </small>
                        </div>
                      </div>
                      <div className="scenario-kpis">
                        <ImpactCard
                          label="Late orders"
                          baseline={simulation.reference_metrics.late_orders}
                          scenario={simulation.scenario_metrics.late_orders}
                          delta={simulation.delta.late_orders}
                          unit="orders"
                          goodDown
                        />
                        <ImpactCard
                          label="Average WIP age"
                          baseline={simulation.reference_metrics.avg_wip_age_hours}
                          scenario={simulation.scenario_metrics.avg_wip_age_hours}
                          delta={simulation.delta.avg_wip_age_hours}
                          unit="h"
                          goodDown
                        />
                        <ImpactCard
                          label="Throughput"
                          baseline={simulation.reference_metrics.throughput}
                          scenario={simulation.scenario_metrics.throughput}
                          delta={simulation.delta.throughput}
                          unit="orders"
                          goodDown={false}
                        />
                      </div>
                      <p className="metric-caption">
                        Throughput is modeled work orders completed within 168 hours. WIP age here
                        is model-derived through completion, not the current age shown on the Flow
                        Board.
                      </p>
                      <section className="panel impact-panel">
                        <div className="panel-heading">
                          <div>
                            <h2>What changes</h2>
                            <p>Projected effect across the current order book</p>
                          </div>
                        </div>
                        {simulation.due_date_impact.length ? (
                          <div
                            className="impact-list"
                            role="region"
                            aria-label="Due-date impact by work order"
                            tabIndex={0}
                          >
                            {simulation.due_date_impact.map((row) => (
                              <div className="impact-row" key={row.work_order_id}>
                                <span
                                  className={
                                    row.late_scenario ? 'impact-dot late' : 'impact-dot ok'
                                  }
                                  aria-hidden="true"
                                />{' '}
                                <b>{row.wo_number}</b>
                                <span>
                                  {row.late_before ? 'Late' : 'On track'} <ArrowRight size={12} />{' '}
                                  {row.late_scenario ? 'Late' : 'On track'}
                                </span>
                                <small
                                  className={
                                    row.completion_delta_hours > 0
                                      ? 'impact-time later'
                                      : row.completion_delta_hours < 0
                                        ? 'impact-time earlier'
                                        : 'impact-time unchanged'
                                  }
                                >
                                  {row.completion_delta_hours > 0
                                    ? 'Later · '
                                    : row.completion_delta_hours < 0
                                      ? 'Earlier · '
                                      : 'Unchanged · '}
                                  {row.completion_delta_hours > 0 ? '+' : ''}
                                  {fmt(row.completion_delta_hours)}h completion
                                </small>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="empty-alert">
                            <span>
                              <Check size={18} />
                            </span>
                            <div>
                              <b>No due-date changes met the API reporting threshold</b>
                              <small>
                                The API reports work orders when modeled completion or delay changes
                                by at least 0.25 hours. Smaller changes may not appear here.
                              </small>
                            </div>
                          </div>
                        )}
                      </section>
                      <section className="scenario-insight">
                        <span>
                          <GitBranch size={16} />
                        </span>
                        <div>
                          <b>How to read this</b>
                          <small>
                            {scenarioRun?.inputs.downId
                              ? 'The selected resource is excluded from the scenario schedule. '
                              : 'No resource outage is applied. '}
                            The simulation does not update source work orders.
                          </small>
                        </div>
                      </section>
                      <section className="panel scenario-gantt-panel">
                        <div className="panel-heading">
                          <div>
                            <h2>Scenario schedule</h2>
                            <p>Operations returned for the submitted scenario</p>
                          </div>
                        </div>
                        <Gantt
                          operations={simulation.gantt}
                          maxHour={Math.max(24, ...simulation.gantt.map((item) => item.end_hour))}
                        />
                      </section>
                    </>
                  ) : (
                    <div className="scenario-placeholder panel">
                      <span className="placeholder-orbit">
                        <GitBranch size={23} />
                      </span>
                      <h2>Choose a disruption to model</h2>
                      <p>
                        Select an outage, rush order, or demand change, then run the API simulation
                        to review its modeled effect on late orders, WIP, and throughput.
                      </p>
                    </div>
                  )}
                </section>
              </div>
              {downId && downResource && (
                <div className="scenario-footer-note">
                  <AlertTriangle size={15} /> Simulating downtime for <b>{downResource.name}</b>.
                  Select a different resource or clear the field to compare another disruption.
                </div>
              )}
            </>
          )}
          <footer className="page-footer">
            <span>
              INDOFLOW <i>·</i> FACTORY FLOW INTELLIGENCE
            </span>
            <span>
              DEMO DATA ONLY <i>·</i> READ-ONLY SCHEDULING
            </span>
          </footer>
        </div>
      </main>
    </div>
  )
}

function StatCard({
  label,
  value,
  icon,
  foot,
  tone,
  compact = false,
}: {
  label: string
  value: string
  icon: React.ReactNode
  foot: string
  tone: string
  compact?: boolean
}) {
  return (
    <article className="stat-card">
      <div className="stat-label">
        {label}
        <span className={`stat-icon ${tone}`}>{icon}</span>
      </div>
      <div className={compact ? 'stat-value compact' : 'stat-value'}>{value}</div>
      <div className="stat-foot">
        <span className="tiny-status" />
        {foot}
      </div>
    </article>
  )
}

function CompareCard({
  title,
  before,
  after,
  delta,
  unit,
  goodDown,
}: {
  title: string
  before: number | null | undefined
  after: number | null | undefined
  delta: number | null | undefined
  unit: string
  goodDown: boolean
}) {
  const improved = delta != null && (goodDown ? delta < 0 : delta > 0)
  const hasDelta = delta != null && Number.isFinite(delta)
  const worsened = hasDelta && delta !== 0 && !improved
  const status = !hasDelta
    ? 'Unavailable'
    : delta === 0
      ? 'Unchanged'
      : improved
        ? 'Improved'
        : 'Worsened'
  return (
    <article className="compare-card">
      <div className="compare-title">
        {title}
        <span className={improved ? 'delta-chip good' : worsened ? 'delta-chip bad' : 'delta-chip'}>
          {hasDelta &&
            delta !== 0 &&
            (delta < 0 ? <ArrowDownRight size={13} /> : <ArrowUpRight size={13} />)}
          <span>{status}</span>
          {hasDelta && <> · </>}
          {hasDelta && delta > 0 ? '+' : ''}
          {hasDelta ? `${fmt(delta)} ${unit}` : ''}
        </span>
      </div>
      <div className="compare-numbers">
        <div>
          <small>REFERENCE</small>
          <b>
            {fmt(before)}
            <i>{before == null ? '' : unit}</i>
          </b>
        </div>
        <ArrowRight size={15} />
        <div>
          <small>PROPOSED</small>
          <b className={improved ? 'better-number' : ''}>
            {fmt(after)}
            <i>{after == null ? '' : unit}</i>
          </b>
        </div>
      </div>
      <div className="compare-bar">
        <span
          style={{
            width: `${before == null || after == null || before <= 0 ? 0 : Math.min(100, (after / before) * 100)}%`,
          }}
        />
      </div>
    </article>
  )
}

function ImpactCard({
  label,
  baseline,
  scenario,
  delta,
  unit,
  goodDown,
}: {
  label: string
  baseline: number | null
  scenario: number | null
  delta: number | null
  unit: string
  goodDown: boolean
}) {
  const improved = delta != null && (goodDown ? delta < 0 : delta > 0)
  const hasDelta = delta != null && Number.isFinite(delta)
  const status = !hasDelta
    ? 'Unavailable'
    : delta === 0
      ? 'Unchanged'
      : improved
        ? 'Improved'
        : 'Worsened'
  return (
    <article className="impact-kpi">
      <small>{label}</small>
      <div>
        <b>
          {fmt(scenario)}
          <i>{unit}</i>
        </b>
        <span
          className={
            improved
              ? 'impact-change good'
              : delta == null || delta === 0
                ? 'impact-change'
                : 'impact-change bad'
          }
        >
          <span className="sr-only">{status}: </span>
          {delta != null && delta > 0 ? '+' : ''}
          {hasDelta ? `${fmt(delta)} ${unit}` : '—'}
        </span>
      </div>
      <span className="impact-baseline">
        Reference: {fmt(baseline)} {unit}
      </span>
    </article>
  )
}

export function Gantt({ operations, maxHour }: { operations: Operation[]; maxHour: number }) {
  const [selected, setSelected] = useState<Operation | null>(null)
  const selectedBar = useRef<HTMLButtonElement | null>(null)
  const detailClose = useRef<HTMLButtonElement | null>(null)
  const rows = useMemo(() => {
    const grouped = new Map<string, Operation[]>()
    operations.forEach((operation) => {
      const key = operation.resource_id
      const items = grouped.get(key) ?? []
      items.push(operation)
      grouped.set(key, items)
    })
    return [...grouped.entries()]
  }, [operations])
  const selectedOperation = selected && operations.includes(selected) ? selected : null
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
  if (!operations.length)
    return <div className="gantt-empty">No operations are available for this schedule.</div>
  return (
    <>
      <div className="gantt-summary" aria-live="polite">
        {operations.length.toLocaleString()} operations across {rows.length} resources · Timeline:
        0–{fmt(maxHour, 0)}h
      </div>
      <div
        className="gantt"
        role="region"
        aria-label="Schedule timeline. Use the scroll area to review all resources and hours."
      >
        <div className="gantt-canvas">
          <div className="gantt-axis">
            <span>RESOURCE / MACHINE</span>
            <div>
              {[0, 0.25, 0.5, 0.75, 1].map((point) => (
                <span key={point}>{fmt(maxHour * point, 0)}h</span>
              ))}
            </div>
          </div>
          {rows.map(([resourceId, items]) => (
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
              <div className="gantt-lane">
                {items.map((item, index) => {
                  const left = Math.max(0, (item.start_hour / maxHour) * 100)
                  const width = (Math.max(0, item.end_hour - item.start_hour) / maxHour) * 100
                  const accessibleName = `${item.wo_number}, ${item.sku_code}, ${item.stage}, ${item.resource_name}, ${fmt(item.start_hour)} to ${fmt(item.end_hour)} hours, ${item.is_late ? 'late' : 'on time'}${item.batch_id ? `, batch ${item.batch_id}` : ''}${item.delay_reason ? `, ${item.delay_reason}` : ''}`
                  return (
                    <button
                      type="button"
                      className={`gantt-bar stage-${stages.indexOf(item.stage) + 1}${item.is_late ? ' is-late' : ''}`}
                      key={`${item.work_order_id}-${item.stage}-${index}`}
                      style={{ left: `${left}%`, width: `${Math.min(width, 100 - left)}%` }}
                      aria-label={accessibleName}
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
          ))}
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
      {selectedOperation && (
        <div className="gantt-detail" role="status">
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

export default App
