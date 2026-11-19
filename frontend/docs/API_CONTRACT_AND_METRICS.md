# IndoFlow — API Contract, Metric Dictionary and Frontend Truth Rules

**Reviewed from:** `main.py`, `domain.py`, `models.py`, `schedule_utils.py`, `baseline.py`, `solver.py`, `seed.py` and `frontend/src/App.tsx` in repository `JustChaos10/grind-till-we-make-it`, revision `6bd4c7e` on 2026-11-19. This is a **snapshot**: inspect current server code/OpenAPI on every new implementation session.

This is not a manufacturing system specification or a guarantee about actual Indo-MIM operations. It is the **current example backend contract** to help a frontend engineer avoid accidentally inventing data or promising things the solver cannot establish.

---

## A. Deployment modes and permission model

- **Local development:** Python 3.12+; `APP_ENV=development`; SQLite default `indoflow.db`. Prefer isolated `DATABASE_URL=sqlite+aiosqlite:///./indoflow-demo.db` for all synthetic demo activity.
- **Local frontend:** Vite dev server proxy forwards `/api` and `/health` to `http://127.0.0.1:8000`.
- **Production API:** requires `APP_ENV=production`, PostgreSQL, `INDOFLOW_API_TOKEN`, `INDOFLOW_ADMIN_TOKEN`; its seed endpoint is disabled by default. The current browser frontend does **not** provide safe production authentication.
- **Never** put a shared API token in browser JS, `VITE_*`, or `localStorage`. A trusted reverse proxy/BFF or user-based auth is future backend work.

### Existing endpoints

| Verb/path | Input | Output / important behavior | Frontend note |
|---|---|---|---|
| `GET /health` | none | `{ status: 'ready', service: 'IndoFlow' }` or HTTP 503 | Readiness includes DB query |
| `GET /health/live` | none | `{ status: 'alive', service: 'IndoFlow' }` | Process liveness only, not DB readiness |
| `GET /api/flow-board` | none | WIP counters, queue data, alerts | May return valid zero-filled board with empty database |
| `GET /api/catalog` | none | Resource and active-ish order labels/IDs | No separate part/plant details endpoint |
| `POST /api/schedule/optimize` | JSON `time_limit_seconds` | Comparison + two timelines + late-order explanations | Persists **schedule versions**, not mutations to work orders |
| `POST /api/schedule/simulate` | JSON scenario | Scenario metrics, due-impact list, scenario timeline | Does **not** persist scenario; uses synthetic/loaded data |
| `POST /api/seed` | no body | message + resource/part/order counts | **Deletes existing factory + saved schedule records** in current DB |
| `POST /api/import/erp-csv` | CSV as `text/csv` body | imported/rejected counts and row-level reasons | Admin auth; not safe as direct browser production upload |

## B. `GET /api/flow-board`

Representative structural shape (numeric values below are **examples**, not claims):

```json
{
  "total_wip_orders": 150,
  "avg_wip_age_hours": 28.4,
  "queues": [
    {"stage": "Molding", "queue_depth": 50, "avg_wip_age_hours": 30.3},
    {"stage": "Debinding", "queue_depth": 25, "avg_wip_age_hours": 22.8}
  ],
  "active_bottleneck_alerts": ["CNC Machining queue has 30 work orders"]
}
```

Actual stage list from `domain.py`:

1. `Molding`
2. `Debinding`
3. `Sintering`
4. `CNC Machining`
5. `Finishing`

**Important:** `flow_board()` counts all work orders not marked `COMPLETED`; the queue array uses the same exclusion. This may include `QUALITY_HOLD` orders even though the solver excludes `QUALITY_HOLD`. Hence the KPI is **open WIP orders** rather than strictly schedulable orders. If any inconsistency arises, don't silently reconcile in the frontend; request backend clarification.

Queue alerts are rules on static data; e.g. queue depths >=20, machine status `DOWN`, and a remembered schedule's `bottleneck_resource_id`. They are **not** telemetry-verified root cause analysis. A valid zero-order flow-board object is possible: don't rely only on `board === null` to show an empty factory state.

## C. `GET /api/catalog`

```ts
type Resource = {
  id: string
  name: string
  plant: string
  stage: string
  status: string
}

type CatalogWorkOrder = {
  id: string
  wo_number: string
  sku_code: string
  stage: string
  status: string
  due_date_hours: number
  priority: number
}

type CatalogResponse = {
  resources: Resource[]
  work_orders: CatalogWorkOrder[]
}
```

The catalog excludes orders with status `COMPLETED` or `QUALITY_HOLD` from `work_orders`. It does **not** currently include quantities, exact process route, full part metadata, real plant time zones, calendars, customer identity, order stage timestamps or actual ERP schedule.

Some demo `resource.id` values include `F-1`, `F-2`, `F-3`, `F-4` (sintering) and `CNC-1` through `CNC-4`; always read real ID options from the current catalog rather than hardcoding them.

## D. `POST /api/schedule/optimize`

Request currently defined by strict Pydantic model:

```json
{"time_limit_seconds": 3}
```

Valid interval: `0.1 <= time_limit_seconds <= 5.0`; default 5. The API may return HTTP 409 for an empty factory, HTTP 422 on scheduler/constraint errors. It computes baseline and proposed schedule and saves both schedule versions, but **does not update source orders' quantity, stage, due date or status**.

Response shape:

```ts
type Metrics = {
  late_orders: number
  avg_wip_age_hours: number
  throughput: number
  throughput_horizon_hours: number       // 168 in current model
  furnace_batch_efficiency_pct: number
  makespan_hours: number
  bottleneck_resource_id: string | null
  resource_busy_hours: Record<string, number>
  weighted_tardiness_hours: number
  schedule_version_id?: string           // added on optimize comparison metrics
}

type ScheduledOperation = {
  work_order_id: string
  wo_number: string
  sku_code: string
  resource_id: string
  resource_name: string
  plant: string
  stage: string
  start_hour: number
  end_hour: number
  batch_id: string | null
  is_late: boolean
  delay_reason: string | null
}

type LateOrder = {
  work_order_id: string
  wo_number: string
  due_date_hours: number
  completion_hours: number
  delay_hours: number
  priority: number
  explanation: string
}

type OptimizeResponse = {
  comparison: {
    baseline: Metrics & {schedule_version_id: string}
    optimized: Metrics & {schedule_version_id: string}
    delta: {
      late_orders: number
      avg_wip_age_hours: number
      throughput: number
      furnace_batch_efficiency_pct: number
    }
  }
  gantt: { baseline: ScheduledOperation[]; optimized: ScheduledOperation[] }
  why_late: { baseline: LateOrder[]; optimized: LateOrder[] }
}
```

**Terminology:** The baseline is a simple `NAIVE_ERP` FIFO-like model that sends orders through sintering separately; it is **not a measured Indo-MIM ERP schedule**. UI should say `Illustrative FIFO reference`, not `current plant schedule`. Current solver may use CP-SAT, a deterministic fallback, or at >=300 active orders a dispatch heuristic. Backend response does not expose a reliable globally optimal status/gap. Use `Proposed schedule` rather than claiming proven optimum.

## E. `POST /api/schedule/simulate`

Request:

```ts
type ScenarioRequest = {
  down_resource_ids: string[]
  rush_order_ids: string[]
  demand_spike_pct: number      // 0 to 300
  time_limit_seconds: number    // 0.1 to 5
}
```

Example safe no-change request:

```json
{
  "down_resource_ids": [],
  "rush_order_ids": [],
  "demand_spike_pct": 0,
  "time_limit_seconds": 3
}
```

The backend implements **scenario quantities multiplied by `1 + demand_spike_pct/100`**, rounded upward. It doesn't add new independent forecast orders. Rush IDs become priority 5 and get a due time capped at 24 relative hours. Down resources are excluded for the scenario. In this snapshot, its scenario-transformation code reconstructs `OrderSpec` objects **without copying the original `locked_resource_id` and `locked_until_hour`**. This could change results even for a nominal no-change scenario when there are locked orders. **Do not claim zero-input scenarios are guaranteed to be numerically identical to reference; document this potential modeling issue for the backend collaborator if reproduced.** Don't patch the backend without approval.

Response:

```ts
type DueDateImpact = {
  work_order_id: string
  wo_number: string
  due_date_before_hours: number
  due_date_scenario_hours: number
  completion_before_hours: number
  completion_scenario_hours: number
  completion_delta_hours: number
  late_before: boolean
  late_scenario: boolean
  delay_delta_hours: number
}

type ScenarioResponse = {
  scenario_inputs: {
    down_resource_ids: string[]
    rush_order_ids: string[]
    demand_spike_pct: number
  }
  reference_metrics: Metrics
  scenario_metrics: Metrics
  delta: {
    late_orders: number
    avg_wip_age_hours: number
    throughput: number
    bottleneck_before: string | null
    bottleneck_after: string | null
  }
  due_date_impact: DueDateImpact[]
  why_late: LateOrder[]
  gantt: ScheduledOperation[]
}
```

This endpoint does **not** persist a new schedule version. Its `gantt` is a scenario timeline, not the saved optimization timeline. Display its own input summary. If users edit draft inputs after running, label output as belonging to the **last submitted scenario** until rerun.

## F. `POST /api/seed` and CSV import

`POST /api/seed` response:

```ts
type SeedResponse = {
  message: string
  resources: number
  parts: number
  work_orders: number
}
```

At inspected revision, seed creates **18 resources, 50 parts, 150 work orders** with reproducible random seed. It deletes existing `ScheduledOperation`, `ScheduleVersion`, `WorkOrder`, `Part`, `Resource` rows. It is safe only for a **dedicated local demo DB** deliberately selected in the backend environment. It is NOT a harmless refresh action.

`POST /api/import/erp-csv` requires administrator access and a CSV request body. It returns `imported`, `rejected`, `rejected_rows`; validation can reject individual records. **Never implement a public browser upload that exposes an administrator bearer token.** Treat UI import as blocked pending approved secure server-side integration.

## G. Metrics: precise definitions and recommended copy

| Backend field | Actual definition in code | Recommended UI title | Common misinterpretation to prevent |
|---|---|---|---|
| Flow `total_wip_orders` | Count of orders status != `COMPLETED` | `Open work orders` | Not part count; may include quality holds |
| Flow `avg_wip_age_hours` | Mean `WorkOrder.wip_age_hours` over open orders | `Average current WIP age` | Not lead time, not days of inventory |
| Flow `queue_depth` | Number of open orders whose `current_stage` matches | `Orders at this stage` | Largest queue ≠ proven bottleneck |
| Metrics `late_orders` | Count with modeled completion hour > relative due hour | `Projected late work orders` | Not historically missed customer orders |
| Metrics `avg_wip_age_hours` | Mean over scheduled orders of `order.wip_age_hours + modeled completion_hour` | `Model-derived age through completion` | Different from flow board current WIP age; not measured physical residence |
| Metrics `throughput` | Count orders with modeled completion <= 168h | `Orders completed within 168h (model)` | Not parts/hour or annual throughput |
| Metrics `furnace_batch_efficiency_pct` | Sum quantities in sintering runs / sum rated capacity across those runs ×100 | `Modeled furnace batch fill` | Not furnace hours utilized, OEE or validated production efficiency |
| Metrics `makespan_hours` | Maximum modeled order completion hour | `Modeled schedule span` | Not customer lead time |
| Metrics `weighted_tardiness_hours` | Sum over orders of max(0, finish - due) × priority | `Priority-weighted late hours (model)` | Not simply late hours or money |
| Metrics `resource_busy_hours` | Sum of modeled active-operation duration per resource, counting sintering batch once | `Modeled busy hours by resource` | Not uptime/OEE |
| Metrics `bottleneck_resource_id` | Resource with maximum busy-hours sum | `Resource with most modeled busy hours` | Not mathematically proven throughput-limiting bottleneck |
| Timeline `start_hour`, `end_hour` | Decimal hours since planning origin | `Starts at 24.5h (model)` | Not a verified wall-clock date/time |

### Presentation requirements

- Preserve `null`, unavailable or omitted values; don't turn every absent value into `0`.
- Show percent points rather than percent growth when comparing percentage KPIs: 60% → 75% is +15 **percentage points**.
- Show correct direction for negative deltas. Define baseline/proposed subtraction clearly.
- If `before=0`, avoid nonsensical percent change denominators.
- Some metrics are not unconditionally good in one direction; e.g. batch fill can improve while lateness worsens. Make trade-offs visible.
- The ordering of 'optimized' and 'baseline' names is backend syntax; UI language should be explicit about modeled meaning.

## H. Modeled production assumptions to teach users

- Five current stages are fixed in backend code. Certain parts can skip CNC machining.
- `Molding`, `CNC Machining`, `Finishing` duration model multiplies per-part cycle time by work-order quantity.
- `Debinding`, `Sintering` modeled durations are per-lot/batch.
- Furnace compatibility uses alloy and recipe permissions. Same alloy doesn't universally mean same approved production recipe.
- Machine status, resource blackout windows, shared tooling and locked WIP can affect feasibility.
- Solver granularity: 15-minute ticks; API timeline rounds to decimal hours.
- Scenario calculations represent a planning counterfactual on simulated assumptions, not an industrial digital twin that has been calibrated to plant logs.
- For large active order sets (>=300 in inspected code), solver switches to a heuristic dispatch path; results need not be mathematically optimal.

## I. Example safe explanatory UI copy

**Data provenance:** `Synthetic demonstration data — no live ERP or machine connection.`

**Reference:** `Illustrative FIFO-style reference schedule, not the plant's actual production plan.`

**Proposed:** `Constraint-aware model-generated schedule. Review with planners before operational use.`

**Batch fill:** `Percent of modeled capacity occupied across scheduled sintering runs; does not measure furnace uptime.`

**Largest queue:** `Highest current work-order count among modeled stages; not conclusive evidence of the system constraint.`

**Scenario:** `A modeled what-if analysis that does not modify source work orders.`

**Confidence:** `Results depend on synthetic input durations, compatibility rules and available machine data.`

## J. Recommended backend change requests, not frontend implementation

Give the backend collaborator requests in a document, including priority and exact contract:

1. **Solver provenance:** `solver_mode` (`CP_SAT`, `HEURISTIC`, `FEASIBLE_FALLBACK`), `solver_status`, `solve_elapsed_ms`, `feasible`, objective/gap if supported and trustworthy, so the UI doesn't imply optimality.
2. **Run timestamps / planning origin:** explicit ISO timestamp and zone if future absolute-time labels are wanted.
3. **Factory-empty metadata:** explicit `dataset_type`, `dataset_id`, `is_synthetic`, `has_orders`, `seed_safe`/demo-only safety gating instead of inferring solely from board count.
4. **Metric definitions:** expose objective, comparison baseline provenance and detailed formulas/version for auditability.
5. **Scenario lock preservation:** investigate whether scenario `OrderSpec` drops `locked_resource_id`/`locked_until_hour`, including null-change scenario behavior.
6. **Full per-order detail / drilldown:** paginated work-order attributes, process route and approvals, if real planner work demands it.
7. **Per-stage constraint evidence:** queue age bands, utilization time denominators, operation waiting times, genuine bottleneck evidence (not just largest busy-hours resource).
8. **Auth and secure imports:** non-browser admin token exposure, scoped role auth, trusted BFF/proxy for production.
9. **Saved schedule history and deterministic provenance:** filters for versions/results; audit trail and stable seed/snapshot ID.
10. **Generic industry routing:** versioned workflow templates only after actual customer discovery and backend support.

These are **future requests**, not existing features. Do not assume implementation or independently edit backend to create them.

---

## Source links

- [GitHub repository](https://github.com/JustChaos10/grind-till-we-make-it)
- [API source](https://github.com/JustChaos10/grind-till-we-make-it/blob/main/main.py)
- [Metrics calculation](https://github.com/JustChaos10/grind-till-we-make-it/blob/main/schedule_utils.py)
- [Baseline](https://github.com/JustChaos10/grind-till-we-make-it/blob/main/baseline.py)
- [Synthetic seed](https://github.com/JustChaos10/grind-till-we-make-it/blob/main/seed.py)
- [Scheduling solver](https://github.com/JustChaos10/grind-till-we-make-it/blob/main/solver.py)
- [Existing frontend](https://github.com/JustChaos10/grind-till-we-make-it/blob/main/frontend/src/App.tsx)

The exact current Python source and generated OpenAPI schema take precedence if any of these implementation details change.
