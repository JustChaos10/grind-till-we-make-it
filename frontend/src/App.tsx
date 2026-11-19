import { useCallback, useEffect, useMemo, useState } from 'react'
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
  Sparkles,
  Truck,
  Wrench,
  Zap,
} from 'lucide-react'

type Queue = { stage: string; queue_depth: number; avg_wip_age_hours: number }
type Board = {
  total_wip_orders: number
  avg_wip_age_hours: number
  queues: Queue[]
  active_bottleneck_alerts: string[]
}
type Resource = { id: string; name: string; plant: string; stage: string; status: string }
type WorkOrder = {
  id: string
  wo_number: string
  sku_code: string
  stage: string
  status: string
  due_date_hours: number
  priority: number
}
type Operation = {
  work_order_id: string
  wo_number: string
  sku_code: string
  resource_id: string
  resource_name: string
  plant: string
  stage: string
  start_hour: number
  end_hour: number
  is_late: boolean
  delay_reason: string | null
}
type Metrics = {
  late_orders: number
  avg_wip_age_hours: number
  throughput: number
  furnace_batch_efficiency_pct?: number
  bottleneck_resource_id?: string | null
}
type Optimization = {
  comparison: {
    baseline: Metrics
    optimized: Metrics
    delta: {
      late_orders: number
      avg_wip_age_hours: number
      throughput: number
      furnace_batch_efficiency_pct: number
    }
  }
  gantt: { baseline: Operation[]; optimized: Operation[] }
  why_late: { baseline: LateOrder[]; optimized: LateOrder[] }
}
type LateOrder = {
  work_order_id: string
  wo_number: string
  delay_hours: number
  explanation: string
  due_date_hours?: number
}
type Simulation = {
  reference_metrics: Metrics
  scenario_metrics: Metrics
  delta: {
    late_orders: number
    avg_wip_age_hours: number
    throughput: number
    bottleneck_before: string | null
    bottleneck_after: string | null
  }
  due_date_impact: {
    work_order_id: string
    wo_number: string
    completion_delta_hours: number
    delay_delta_hours: number
    late_before: boolean
    late_scenario: boolean
  }[]
  gantt: Operation[]
  why_late: LateOrder[]
}
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
const fmt = (value: number | undefined, digits = 1) =>
  Number(value ?? 0).toLocaleString(undefined, { maximumFractionDigits: digits })

async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  })
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`
    try {
      const body = await response.json()
      message = body.detail || message
    } catch {
      /* keep status */
    }
    throw new Error(message)
  }
  return response.json() as Promise<T>
}

function App() {
  const [page, setPage] = useState<Page>('board')
  const [board, setBoard] = useState<Board | null>(null)
  const [resources, setResources] = useState<Resource[]>([])
  const [orders, setOrders] = useState<WorkOrder[]>([])
  const [optimization, setOptimization] = useState<Optimization | null>(null)
  const [simulation, setSimulation] = useState<Simulation | null>(null)
  const [busy, setBusy] = useState<'seed' | 'optimize' | 'simulate' | null>(null)
  const [error, setError] = useState('')
  const [downId, setDownId] = useState('')
  const [rushId, setRushId] = useState('')
  const [demand, setDemand] = useState(20)
  const [scheduleTab, setScheduleTab] = useState<'optimized' | 'baseline'>('optimized')
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

  const refresh = useCallback(async () => {
    try {
      const [b, catalog] = await Promise.all([
        api<Board>('/api/flow-board'),
        api<{ resources: Resource[]; work_orders: WorkOrder[] }>('/api/catalog'),
      ])
      setBoard(b)
      setResources(catalog.resources)
      setOrders(catalog.work_orders)
      setLastUpdated(new Date())
      setError('')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not connect to the IndoFlow API.')
    }
  }, [])

  useEffect(() => {
    queueMicrotask(() => void refresh())
  }, [refresh])

  const activeResources = resources.filter((resource) => resource.status === 'ACTIVE')
  const stageMax = Math.max(1, ...(board?.queues.map((queue) => queue.queue_depth) ?? [1]))
  const bottleneckQueue = board?.queues.reduce<Queue | null>(
    (top, queue) => (!top || queue.queue_depth > top.queue_depth ? queue : top),
    null,
  )
  const downResource = resources.find((resource) => resource.id === downId)
  const optimizedOperations = optimization?.gantt.optimized ?? []
  const maxHour = Math.max(24, ...optimizedOperations.map((item) => item.end_hour))
  const shownOperations = useMemo(
    () =>
      [...(optimization?.gantt[scheduleTab] ?? [])]
        .sort((a, b) => a.start_hour - b.start_hour)
        .slice(0, 90),
    [optimization, scheduleTab],
  )

  async function seedDemo() {
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
      setSimulation(null)
      await refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load demo data.')
    } finally {
      setBusy(null)
    }
  }

  async function optimize() {
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
      setBusy(null)
    }
  }

  async function runScenario() {
    setBusy('simulate')
    setError('')
    try {
      setSimulation(
        await api<Simulation>('/api/schedule/simulate', {
          method: 'POST',
          body: JSON.stringify({
            down_resource_ids: downId ? [downId] : [],
            rush_order_ids: rushId ? [rushId] : [],
            demand_spike_pct: demand,
            time_limit_seconds: 3,
          }),
        }),
      )
      setPage('scenario')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Scenario simulation failed.')
    } finally {
      setBusy(null)
    }
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
            onClick={() => setPage('board')}
          >
            <Layers3 size={17} />
            <span>Flow board</span>
            <span className="nav-dot" />
          </button>
          <button
            className={page === 'optimizer' ? 'nav-item selected' : 'nav-item'}
            onClick={() => setPage('optimizer')}
          >
            <GitCompareArrows size={17} />
            <span>Schedule optimizer</span>
          </button>
          <button
            className={page === 'scenario' ? 'nav-item selected' : 'nav-item'}
            onClick={() => setPage('scenario')}
          >
            <Sparkles size={17} />
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
              <b>India operations</b>
              <small>2 plants · MIM network</small>
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
              <i /> Demo environment
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
            <div className="error-banner">
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
              <p className="eyebrow">INDOFLOW CONTROL ROOM</p>
              <h1>
                Factory intelligence,
                <br />
                <em>at a glance.</em>
              </h1>
              <p className="welcome-copy">
                Connect to the IndoFlow API and load a synthetic factory dataset to explore live
                WIP, optimized schedules, and operational what-if scenarios.
              </p>
              <div className="welcome-actions">
                <button className="primary-button" onClick={seedDemo} disabled={busy !== null}>
                  <Play size={16} fill="currentColor" />
                  {busy === 'seed' ? 'Loading demo data…' : 'Load synthetic demo data'}
                </button>
                <button className="text-button" onClick={() => void refresh()}>
                  <RefreshCw size={15} /> Retry API connection
                </button>
              </div>
              <div className="welcome-note">
                <ShieldCheck size={15} /> Demo records are synthetic. Loading data resets the
                configured demo database.
              </div>
            </section>
          )}

          {board && page === 'board' && (
            <>
              <div className="page-heading">
                <div>
                  <p className="eyebrow">
                    OPERATIONS OVERVIEW <span>·</span> HOSKOTE + DODDABALLAPURA
                  </p>
                  <h1>
                    Your factory, in flow <span>✳</span>
                  </h1>
                  <p className="heading-sub">
                    Here’s what’s happening across your production flow today.
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
                  value={`${fmt(board.avg_wip_age_hours)}h`}
                  icon={<Clock3 size={18} />}
                  foot="Time in the production system"
                  tone="amber"
                />
                <StatCard
                  label="Largest queue"
                  value={bottleneckQueue?.stage ?? '—'}
                  icon={<Gauge size={18} />}
                  foot={`${bottleneckQueue?.queue_depth ?? 0} orders waiting`}
                  tone="violet"
                  compact
                />
                <StatCard
                  label="Machines available"
                  value={`${activeResources.length} / ${resources.length}`}
                  icon={<Activity size={18} />}
                  foot="Across 5 process stages"
                  tone="green"
                />
              </div>
              <div className="content-grid board-grid">
                <section className="panel flow-panel">
                  <div className="panel-heading">
                    <div>
                      <h2>Production flow</h2>
                      <p>Work in progress by current stage</p>
                    </div>
                    <span className="neutral-pill">
                      <span className="pulse" /> LIVE QUEUE
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
                          <div className="stage-meta">{fmt(queue?.avg_wip_age_hours)}h avg age</div>
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
                      <p>Signals from your production floor</p>
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
                            <b>{index === 0 ? 'Bottleneck signal' : 'Capacity alert'}</b>
                            <span>{alert}</span>
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
                        <small>No active bottlenecks or downtime alerts.</small>
                      </div>
                    </div>
                  )}
                  <button className="scenario-shortcut" onClick={() => setPage('scenario')}>
                    <span className="shortcut-icon">
                      <Sparkles size={16} />
                    </span>
                    <span>
                      <b>Plan for a disruption</b>
                      <small>Try a machine outage or rush order</small>
                    </span>
                    <ArrowRight size={15} />
                  </button>
                </section>
              </div>
              <div className="bottom-grid">
                <section className="panel capability-panel">
                  <div className="capability-icon">
                    <GitCompareArrows size={19} />
                  </div>
                  <div>
                    <p className="eyebrow">BETTER DECISIONS, FASTER</p>
                    <h2>See what an optimized plan can change.</h2>
                    <p>
                      Compare the current dispatch baseline with a constraint-aware schedule built
                      around your plant’s real resources.
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
                  <p className="eyebrow">
                    DECISION SUPPORT <span>·</span> CAPACITY-AWARE PLANNING
                  </p>
                  <h1>Schedule optimizer</h1>
                  <p className="heading-sub">
                    Compare the current dispatch plan with a constraint-aware production schedule.
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
                  <h2>Put the plan to work</h2>
                  <p>
                    Run the optimizer to compare late orders, WIP age, and flow time against the
                    current baseline.
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
                      <Sparkles size={18} />
                    </span>
                    <div>
                      <b>Optimized schedule ready</b>
                      <small>
                        Based on current WIP, machine capacity, tooling, and furnace constraints.
                      </small>
                    </div>
                    <span className="result-time">JUST NOW</span>
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
                      before={optimization.comparison.baseline.furnace_batch_efficiency_pct ?? 0}
                      after={optimization.comparison.optimized.furnace_batch_efficiency_pct ?? 0}
                      delta={optimization.comparison.delta.furnace_batch_efficiency_pct}
                      unit="%"
                      goodDown={false}
                    />
                  </div>
                  <section className="panel schedule-panel">
                    <div className="panel-heading schedule-heading">
                      <div>
                        <h2>Production timeline</h2>
                        <p>First 90 operations · planned hours from now</p>
                      </div>
                      <div className="segmented">
                        <button
                          className={scheduleTab === 'optimized' ? 'active' : ''}
                          onClick={() => setScheduleTab('optimized')}
                        >
                          Optimized
                        </button>
                        <button
                          className={scheduleTab === 'baseline' ? 'active' : ''}
                          onClick={() => setScheduleTab('baseline')}
                        >
                          Baseline
                        </button>
                      </div>
                    </div>
                    <Gantt operations={shownOperations} maxHour={Math.min(maxHour, 96)} />
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
                      <div className="late-table">
                        <div className="table-head">
                          <span>WORK ORDER</span>
                          <span>DELAY</span>
                          <span>CAPACITY EXPLANATION</span>
                        </div>
                        {optimization.why_late.optimized.slice(0, 8).map((order) => (
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
                  <p className="eyebrow">
                    DECISION SUPPORT <span>·</span> SAFE WHAT-IF ANALYSIS
                  </p>
                  <h1>Scenario lab</h1>
                  <p className="heading-sub">
                    Pressure-test the plan before the unexpected hits the shop floor.
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
                      <h2>Shape your scenario</h2>
                      <p>Choose one or more events to simulate</p>
                    </div>
                    <span className="control-tag">CONTROLS</span>
                  </div>
                  <label className="field-label" htmlFor="machine-down">
                    Machine unavailable
                  </label>
                  <div className="select-wrap">
                    <Wrench size={16} />
                    <select
                      id="machine-down"
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
                  <p className="field-help">
                    The selected resource is removed from the scenario schedule.
                  </p>
                  <label className="field-label" htmlFor="rush-order">
                    Priority rush order
                  </label>
                  <div className="select-wrap">
                    <Truck size={16} />
                    <select
                      id="rush-order"
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
                  <p className="field-help">
                    The selected order gets priority and an accelerated due target.
                  </p>
                  <div className="slider-head">
                    <label className="field-label" htmlFor="demand-spike">
                      Demand increase
                    </label>
                    <b>{demand}%</b>
                  </div>
                  <input
                    id="demand-spike"
                    className="range-input"
                    type="range"
                    min="0"
                    max="100"
                    step="10"
                    value={demand}
                    onChange={(e) => setDemand(Number(e.target.value))}
                  />
                  <div className="range-scale">
                    <span>0%</span>
                    <span>50%</span>
                    <span>100%</span>
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
                  <button
                    className="primary-button run-scenario"
                    onClick={runScenario}
                    disabled={busy !== null}
                  >
                    <Zap size={15} fill="currentColor" />
                    {busy === 'simulate' ? 'Simulating scenario…' : 'Run scenario'}
                    <ArrowRight size={15} />
                  </button>
                </section>
                <section className="scenario-results">
                  {simulation ? (
                    <>
                      <div className="scenario-result-top">
                        <div>
                          <p className="eyebrow">SCENARIO RESULTS</p>
                          <h2>Here’s the impact.</h2>
                        </div>
                        <span className="result-time">JUST NOW</span>
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
                      <section className="panel impact-panel">
                        <div className="panel-heading">
                          <div>
                            <h2>What changes</h2>
                            <p>Projected effect across the current order book</p>
                          </div>
                        </div>
                        {simulation.due_date_impact.length ? (
                          <div className="impact-list">
                            {simulation.due_date_impact.slice(0, 9).map((row) => (
                              <div className="impact-row" key={row.work_order_id}>
                                <span
                                  className={
                                    row.late_scenario ? 'impact-dot late' : 'impact-dot ok'
                                  }
                                />{' '}
                                <b>{row.wo_number}</b>
                                <span>
                                  {row.late_before ? 'Late' : 'On track'} <ArrowRight size={12} />{' '}
                                  {row.late_scenario ? 'Late' : 'On track'}
                                </span>
                                <small>
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
                              <b>No material due-date changes</b>
                              <small>
                                This scenario leaves projected due-date outcomes unchanged.
                              </small>
                            </div>
                          </div>
                        )}
                      </section>
                      <section className="scenario-insight">
                        <span>
                          <Sparkles size={16} />
                        </span>
                        <div>
                          <b>How to read this</b>
                          <small>
                            The simulation re-routes around the unavailable machine when capacity
                            allows. Source work orders and the saved plan remain unchanged.
                          </small>
                        </div>
                      </section>
                    </>
                  ) : (
                    <div className="scenario-placeholder panel">
                      <span className="placeholder-orbit">
                        <Sparkles size={23} />
                      </span>
                      <p className="eyebrow">YOUR DECISION SANDBOX</p>
                      <h2>Explore the ripple effect.</h2>
                      <p>
                        Choose an outage, a rush order, or a demand spike. IndoFlow will show the
                        resulting changes in late orders, WIP, and throughput.
                      </p>
                      <div className="placeholder-steps">
                        <span>
                          <b>01</b> Model a disruption
                        </span>
                        <span>
                          <b>02</b> Compare the impact
                        </span>
                        <span>
                          <b>03</b> Decide with context
                        </span>
                      </div>
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
  before: number
  after: number
  delta: number
  unit: string
  goodDown: boolean
}) {
  const improved = goodDown ? delta < 0 : delta > 0
  return (
    <article className="compare-card">
      <div className="compare-title">
        {title}
        <span className={improved ? 'delta-chip good' : delta ? 'delta-chip bad' : 'delta-chip'}>
          {improved ? <ArrowDownRight size={13} /> : <ArrowUpRight size={13} />}
          {delta > 0 ? '+' : ''}
          {fmt(delta)} {unit}
        </span>
      </div>
      <div className="compare-numbers">
        <div>
          <small>BASELINE</small>
          <b>
            {fmt(before)}
            <i>{unit}</i>
          </b>
        </div>
        <ArrowRight size={15} />
        <div>
          <small>OPTIMIZED</small>
          <b className={improved ? 'better-number' : ''}>
            {fmt(after)}
            <i>{unit}</i>
          </b>
        </div>
      </div>
      <div className="compare-bar">
        <span style={{ width: `${Math.min(100, before <= 0 ? 0 : (after / before) * 100)}%` }} />
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
  baseline: number
  scenario: number
  delta: number
  unit: string
  goodDown: boolean
}) {
  const improved = goodDown ? delta < 0 : delta > 0
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
            improved ? 'impact-change good' : delta === 0 ? 'impact-change' : 'impact-change bad'
          }
        >
          {delta > 0 ? '+' : ''}
          {fmt(delta)} {unit}
        </span>
      </div>
      <span className="impact-baseline">
        Reference: {fmt(baseline)} {unit}
      </span>
    </article>
  )
}

function Gantt({ operations, maxHour }: { operations: Operation[]; maxHour: number }) {
  const rows = useMemo(() => {
    const grouped = new Map<string, Operation[]>()
    operations.forEach((operation) => {
      const key = operation.resource_name
      grouped.set(key, [...(grouped.get(key) ?? []), operation])
    })
    return [...grouped.entries()]
  }, [operations])
  if (!operations.length)
    return <div className="gantt-empty">No operations are available for this schedule.</div>
  return (
    <div className="gantt">
      <div className="gantt-axis">
        <span>RESOURCE / MACHINE</span>
        <div>
          {[0, 0.25, 0.5, 0.75, 1].map((point) => (
            <span key={point}>{fmt(maxHour * point, 0)}h</span>
          ))}
        </div>
      </div>
      {rows.map(([resource, items]) => (
        <div className="gantt-row" key={resource}>
          <div className="gantt-resource">
            <span className="machine-icon">
              <Wrench size={13} />
            </span>
            <span>
              {resource}
              <small>{items[0].plant}</small>
            </span>
          </div>
          <div className="gantt-lane">
            {items.slice(0, 24).map((item, index) => {
              const left = Math.max(0, (item.start_hour / maxHour) * 100)
              const width = Math.max(1.4, ((item.end_hour - item.start_hour) / maxHour) * 100)
              return (
                <div
                  className={`gantt-bar stage-${stages.indexOf(item.stage) + 1}`}
                  key={`${item.work_order_id}-${item.stage}-${index}`}
                  style={{ left: `${left}%`, width: `${Math.min(width, 100 - left)}%` }}
                  title={`${item.wo_number} · ${item.stage} · ${fmt(item.start_hour)}–${fmt(item.end_hour)}h`}
                >
                  <span>{item.wo_number}</span>
                </div>
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
      </div>
    </div>
  )
}

export default App
