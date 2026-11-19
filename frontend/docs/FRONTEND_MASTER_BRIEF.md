# IndoFlow — Frontend Master Implementation Brief

**Version:** 1.0, 2026-11-19  
**Audience:** Codex agent responsible for the entire frontend/UI/UX  
**Source of truth:** Live repository code always takes precedence over this snapshot  
**Repository:** https://github.com/JustChaos10/grind-till-we-make-it  
**Inspected reference revision:** `main` at `6bd4c7e80dff7a2449a71f67fdc2ab290b239e34` (2026-11-19)

> **Primary mission:** Take over the *already existing* React/TypeScript frontend, deliver an exceptional, trustworthy, highly functional manufacturing operations interface, integrate with the existing FastAPI scheduler, and keep every change isolated from a teammate's backend work. **Execute and test the work**; do not merely write an audit or proposal.
>
> **Important:** Read `frontend/AGENTS.md`, `frontend/docs/API_CONTRACT_AND_METRICS.md`, and `frontend/docs/UI_ACCEPTANCE_CHECKLIST.md` before implementing. These are executable project instructions and factual references, not replacement code. Reinspect the latest repo because it may change while two developers work simultaneously.

---

## 0. Executive brief: what success actually means

IndoFlow is a **read-only manufacturing production-flow and scheduling decision-support application**. A user should be able to understand a queue, compare an illustrative reference with a feasible proposed schedule, and see how a disruption affects modeled order completion. The software must explicitly distinguish **simulation**, **live monitoring**, **actual ERP schedules**, and **validated savings**. The latter three are **not provided** by this repository today.

The immediate product is a high-fidelity MIM (Metal Injection Molding) executive/operations demonstration; the long-term aspiration is a transferable scheduling product for heat-treatment, powder metallurgy, precision machining, foundry and ceramic operations. Avoid making either a brittle Indo-MIM-only mockup or an imaginary generic SaaS platform. Architect for configuration while implementing only supported workflows.

Success criteria:

1. Existing backend remains untouched and unbroken.
2. All 3 frontend screens run against **actual local API responses** from the existing repo.
3. The visual interface feels designed by an experienced enterprise product team, not generated from a template.
4. Schedules, operations and metrics are accurate, comprehensible, and inspectable. No silent truncation.
5. Every interface action has a real result or is explicitly disabled as not yet supported.
6. Errors, empty data, loading, auth and outage states are comprehensible and recoverable.
7. Full keyboard access, essential accessibility, responsive behavior, consistent design tokens.
8. Meaningful automated tests plus screenshots/actual browser inspection.
9. All work committed only on a **frontend feature branch**, with reviewable changes and a clean handoff.
10. A CEO can understand the demonstration within 5 minutes without claiming unverifiable real-world outcomes.

### Responsibilities

| You own and may implement | Collaborator owns — don't modify without approval |
|---|---|
| React/TypeScript UI, components, API client, state management | `main.py`/FastAPI routes and response shapes |
| Design system, CSS, responsive layout, accessible interactions | `solver.py`, `baseline.py`, OR-Tools scheduling |
| Gantt charts, scheduling visualizations, UX microcopy | Models, migrations, database, production connectors |
| Frontend tests, Playwright, screenshots, lint/build | Backend tests, security policy, production deployment |
| Frontend-specific docs and precise API enhancement requests | Real plant data access, recipe validation, operational approvals |

Read backend files for context, not to rewrite them.

---

## 1. Verified existing repo: don't start from scratch

At inspected revision, the repo has:

- React 19 + TypeScript + Vite 8 frontend in `frontend/`.
- `frontend/src/App.tsx`: ~1,165 lines; page state, API calls, 3 views, cards and a basic Gantt in one file.
- `frontend/src/styles.css`: ~1,819 lines of styles, design tokens and breakpoints.
- `frontend/src/main.tsx`, `frontend/index.html`, Lucide icons; npm lockfile and scripts for dev, build, lint and format.
- FastAPI `/api/flow-board`, `/api/catalog`, `/api/schedule/optimize`, `/api/schedule/simulate`, `/api/seed`, `/api/import/erp-csv`, `/health`, `/health/live`.
- SQLAlchemy models and migrations, SQLite development default, PostgreSQL deployment configuration, OR-Tools CP-SAT scheduling, heuristic path for large cases and an independent schedule validator.
- A deterministic synthetic seed of **150 orders, 50 parts, 18 resources** across **Hoskote and Doddaballapura example plant labels**. Four example sintering resources are `F-1` through `F-4`; two per plant in the demo. Resource and plant configuration is *synthetic*, not an Indo-MIM equipment inventory.
- `docs/CEO_DEMO.md` with a 5-minute walkthrough.
- GitHub Actions CI configured to run Python lint/tests, frontend install/build/lint, and Docker build. The last CI at the reference revision passed. Rerun local checks rather than assuming the present checkout is green.

### Concrete observed gaps to resolve

1. **Empty database:** `GET /api/flow-board` returns a valid object even when there are zero orders; the UI shows its onboarding screen mostly when the board object is `null`, leaving the user looking at an empty dashboard with no obvious seed action.
2. **Gantt truncation:** the UI sorts and slices to 90 schedule operations; then each resource row slices to 24 operations; the chart horizon is further capped visually. Valid operations can disappear or be clipped.
3. **Horizon inconsistency:** max displayed horizon is derived from optimized operations while a different baseline may be selected; use the correct dataset or a shared comparison axis with documented rationale.
4. **Misleading labels:** the existing simulated FIFO is sometimes called 'current ERP' or 'current dispatch plan'. It is **not a verified Indo-MIM schedule**. Also 'live queue' and 'bottleneck' labels can overstate available evidence.
5. **Metric confusion:** flow-board average WIP age differs from the schedule metric, 'throughput' has a fixed 168-hour definition, and furnace fill is not utilization or OEE.
6. **Operation detail:** backend timeline contains `batch_id` and `delay_reason`; current UI typing/visualization does not fully exploit the information.
7. **Readability:** existing CSS includes microscopic text (7–10px) and cards that become less usable at small widths. Improve hierarchy rather than simply raising font sizes randomly.
8. **State management:** one monolithic `App` owns fetch, auth error, page navigation, seed, optimize and simulate. Introduce clean composition, shared typed API access and predictable async states.
9. **Data provenance:** distinguish 'synthetic', 'modelled', 'derived from API', 'not a historical actual' in UI.
10. **Testing:** existing CI runs frontend build/lint; introduce meaningful frontend component and browser tests, and extend CI only after ensuring additions are stable/within ownership boundaries.
11. **Error resilience:** distinguish a stopped API from an empty dataset, 401/403 from 409/422, and a failed solve from a negative optimization outcome.
12. **Scenarios:** the current UI's default demand change is +20%, causing an unintended disruptive scenario by default; prefer default 0% and explicit user selection.

Treat these as **investigations and implementation priorities**, not proof that all of them still exist after subsequent upstream commits.

---

## 2. First local session — Windows, no repo previously cloned

### 2.1 Environment discovery

Do not assume tools are installed. In PowerShell, inspect:

```powershell
Get-Location
git --version
node --version
npm --version
py --list-paths
```

Follow compatible versions from the current repo. The reviewed README requires Python **3.12+** and Node **20.19+ or 22.12+**. Prefer Node 22 LTS if available. Use the smallest necessary installation steps if tools are missing. Do not disable Windows security controls globally just to unblock a task.

### 2.2 Clone and branch safely

If there's no checkout, clone the *existing* repo. Inspect for duplicate folders or local changes first.

```powershell
git clone https://github.com/JustChaos10/grind-till-we-make-it.git
cd grind-till-we-make-it
git status --short
git remote -v
git branch -a
git log -10 --oneline
```

If clean and on `main`, fetch and create a separate branch based on the latest tracked `main`:

```powershell
git fetch origin
git switch main
git pull --ff-only origin main
git switch -c feat/frontend-experience
```

If the branch already exists, either use it safely after inspection or create an unambiguous new name, e.g. `feat/frontend-experience-2026-11`. Never overwrite a collaborator's branch or reset an uncommitted working tree. Never force-push or directly merge to `main`.

### 2.3 Put supplied reference files in the right place

If this task came with Markdown attachments, copy:

- `AGENTS.md` → `frontend/AGENTS.md`
- `FRONTEND_MASTER_BRIEF.md` → `frontend/docs/FRONTEND_MASTER_BRIEF.md`
- `API_CONTRACT_AND_METRICS.md` → `frontend/docs/API_CONTRACT_AND_METRICS.md`
- `UI_ACCEPTANCE_CHECKLIST.md` → `frontend/docs/UI_ACCEPTANCE_CHECKLIST.md`

If a matching file exists upstream, inspect and reconcile instead of overwriting it. These docs can live in the feature branch. Be mindful of existing `AGENTS.md` instructions elsewhere in the directory hierarchy.

### 2.4 Boot the existing API using an isolated demo database

From the project root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
$env:APP_ENV = 'development'
$env:DATABASE_URL = 'sqlite+aiosqlite:///./indoflow-demo.db'
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

On another terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Expected local addresses: API `http://127.0.0.1:8000` and frontend usually `http://localhost:5173`. Vite proxies `/api` and `/health` to the local API. Verify with the actual terminal URLs. Run `/health` and `/health/live` and inspect `/docs`.

**Seeding is destructive.** The `POST /api/seed` endpoint deletes/replaces factory and saved schedule rows in its connected DB. Never call it unless you have confirmed the API process uses `indoflow-demo.db`, has `APP_ENV=development`, and is not a shared/real database. User must deliberately confirm loading demo data. Never seed on page mount. Don't set `ENABLE_PRODUCTION_SEED=true` or bypass auth.

### 2.5 Baseline quality gate

Before editing, run:

```powershell
# Repo root, using the existing venv
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .

# frontend/
npm run build
npm run lint
```

Record pass/fail and errors. If a dependency version/platform mismatch appears, investigate lockfile and supported Node versions; don't assume source code failure. Take or inspect baseline screenshots if browser automation is available. Make notes in `frontend/docs/FRONTEND_AUDIT.md` (a new implementation artifact), then **continue coding**, not just reporting.

---

## 3. Research and product judgment built into the UI

### User mental models

A plant planner asks: "Which jobs are waiting? Which machine is available? What happens to downstream operations if I move this batch? Can I trust the result?"

A plant manager asks: "Which commitments are at risk? Why? What alternatives do we have?"

A CEO asks: "Where would this help my existing team make better decisions? Is it incremental or another system? Can I see credible evidence rather than a slide?"

Answer these with **correct data labels** and progressively disclosed detail. Don't assume the user knows MIM terminology, but don't patronize professional planners.

### Scientific and commercial humility

Do not claim the public 30.58% MIM capacity utilization figure proves empty furnaces, nor that 441 inventory days can be fixed by the proposed scheduling UI. These are different business metrics. There is not sufficient evidence of actual ERP gaps, actual furnace occupancy, actual site routing/qualification, or verified financial savings. The interface is a simulated decision aid, not plant telemetry or a pricing promise.

### The demonstration's four-part narrative

1. **See:** Five-stage snapshot of synthetic WIP and queue distribution.
2. **Compare:** Demonstrate how an illustrative reference schedule differs from a constraint-aware proposed schedule.
3. **Stress-test:** Simulate an outage/rush/demand change and inspect the modeled effects.
4. **Validate:** Invite plant engineers to identify missing constraints and explain the next evidence required. Do not position the software as smarter than the plant team.

---

## 4. Product visual identity and information architecture

### Desired aesthetic

Create a calm, precise, high-end **industrial operations workbench**, comparable in care to a mature financial workstation or engineering planning console. It should not look like a marketing landing page, an AI generated template, or a consumer fintech app.

Preferred direction:

- Mostly neutral warm white/light gray surfaces; deep ink typography.
- One restrained industrial-green/teal accent; amber for warnings, red for genuine negative outcomes, controlled semantic palette in charts.
- Subtle rule/divider lines rather than thick cards everywhere.
- Consistent 4/8px spacing rhythm, approximately 8–12px border radii on panels; rounded enough to feel contemporary, not bubbly.
- Large page titles but restrained KPI hierarchy. Ensure critical task buttons are visible.
- Use 14–16px normal text. Many current 7–10px labels are too small; optimize readability.
- Monospaced or tabular numbers in timeline, KPIs and tables. Keep dates/hours aligned.
- Explicit status labels and icons; never color alone.
- Richness from *data visualizations*, not random gradients, glowing chips, fake imagery or animated gimmicks.
- Keep existing identity where effective; design improvements should be intentional, not replacement for its own sake.

Do not use gradients, excessive glassmorphism, stock photos, fake robot icons, marketing counters, useless animations, emoji status pins, or tiny microtext. Avoid shifting layouts while requests load.

### Design tokens

Implement CSS custom properties or existing suitable token system for:

- neutral foreground/background/secondary/tertiary text;
- primary/hover/focus;
- success, caution, danger and muted statuses;
- stage series colors with a legend, sufficient contrast and non-color encodings;
- spacing, radii, border, elevation, typography, controls and chart-specific tokens;
- desktop/tablet/mobile breakpoints and reduced motion.

Prefer maintainable CSS or CSS Modules if it fits the repo. Do not install an entire component system because it's fashionable. Normalize control sizes, focus indicators, headings and field descriptions.

### Core navigation

Keep three primary destinations:

1. **Flow Board** (orientation, WIP, alerts)
2. **Schedule Optimizer** (comparison and Gantt)
3. **Scenario Lab** (assumptions and simulated change)

Use accessible navigation landmarks, clear active state, stable page structure, optional URL-backed navigation if it can be added safely without server routing problems. Consider a persistent topbar indicating `Synthetic demo` and `Read-only planning`. Avoid false `Live` labels. Provide meaningful `Last refreshed` only when a fetch actually completes.

### Responsive strategy

Design the desktop-first layout at 1440×900; review 1920×1080, 1280×800, 768px tablet, 390×844 mobile. On small screens, show summaries as stacks, let dense tables/Gantt scroll intentionally and avoid compressing bars to unreadable strips. Mobile support should preserve tasks, not mimic the entire desktop grid.

---

## 5. Frontend architecture and implementation conventions

Current `App.tsx` is monolithic; refactor incrementally, making sure every commit builds. A possible structure (adjust if code suggests a better one):

```text
frontend/
  AGENTS.md
  docs/
    FRONTEND_MASTER_BRIEF.md
    API_CONTRACT_AND_METRICS.md
    UI_ACCEPTANCE_CHECKLIST.md
    FRONTEND_AUDIT.md              # agent-created
    BACKEND_REQUESTS.md            # agent-created when necessary
  src/
    app/App.tsx
    app/navigation.ts
    api/client.ts
    api/types.ts
    api/errors.ts
    components/layout/{AppShell,Sidebar,Topbar,PageHeader}.tsx
    components/ui/{Button,StatusPill,MetricCard,EmptyState,ErrorState,Dialog,Tooltip}.tsx
    features/flow-board/{FlowBoardPage,StageFlow,QueueSummary,Alerts}.tsx
    features/schedule/{SchedulePage,ComparisonPanel,ScheduleTimeline,OperationDetails,LateOrders}.tsx
    features/scenario/{ScenarioPage,ScenarioForm,ScenarioComparison,DueDateImpact}.tsx
    hooks/
    lib/{format,dates,metrics,stages}.ts
    styles/{tokens,global,layout}.css
    test/
```

Do not create every component by default. Extract clear reusable concerns with a good reason. Avoid splitting trivial JSX into dozens of files. Keep IDs stable, keyboard interactions explicit and async state transitions well modeled.

### Typed API integration

Implement one typed API client for browser communication with `/api/` and `/health` under Vite proxy. Use `fetch` with clear response parsing, method/body handling and error types. Respect application/json for existing request endpoints. Handle HTTP statuses individually:

- Network/connection refused → backend unavailable; retry help.
- 401 → authentication required; no browser token workaround.
- 403 → insufficient permissions.
- 404 → unsupported endpoint or production seed disabled.
- 409 → empty factory data / action cannot proceed.
- 422 → solver infeasibility, validation or bad scenario input; show `detail` safely.
- 5xx → server issue; recoverable UI with details.

Pydantic validation sometimes returns a structured array as `detail`; render a safe, comprehensible summary, never concatenate an object into `[object Object]`. Validate optional/nullable fields. Do not silently coerce missing metrics to zero; distinguish 'not available' from numeric 0.

Use abort/cancellation or stale-result guarding for relevant requests. Disable conflicting submissions while running. Avoid duplicate optimization calls, infinite retries and side effects on render.

### State architecture

Keep API data, input draft state and a completed saved result distinct. A change to a scenario input should mark the currently displayed result as belonging to the *previous* inputs or require rerun. Do not show old scenario results under new selections without a visible warning. Preserve meaningful navigation state without undue caching complexity.

Decide whether React context, a small hook, or TanStack Query actually helps. Prefer the simplest correct approach; avoid unnecessary global state libraries and API mocks in the actual app.

### No invented backend functionality

Do not implement a fake plant selector that claims to filter backend data if the backend has no corresponding filtered endpoint. Client filtering of already fetched records is fine if clearly labeled. Backend change requests go in `frontend/docs/BACKEND_REQUESTS.md` with endpoint/field, semantics, backward compatibility, example response, urgency and frontend fallback.

---

## 6. Screen 1 — Flow Board

### Primary task

At a glance, answer **"How is modeled work distributed across the process today, and what appears to deserve investigation?"**

### Page layout

- Heading: `Production flow overview`, subtitle `Synthetic work orders across the example MIM process`.
- A small, visible `SYNTHETIC DATA · READ-ONLY` provenance indicator, with tooltip explaining no ERP or machine connection.
- Summary KPI strip: `Open work orders`, `Average current WIP age`, `Largest queue`, `Resources available`. Use exact API definitions from the metric dictionary.
- Primary five-stage production map with arrows and readable quantitative stage indicators.
- Secondary alerts panel with backend-provided signals, not fabricated telemetry.
- Task-oriented CTA: `Compare schedules` and `Run a scenario`.
- Links to metric help and demo assumptions, without displacing the core data.

### Empty and disconnected states — first priority

Explicit UI states:

1. **Loading**: request is in progress; structured skeleton or non-jarring indicator.
2. **API unavailable**: show connection failure and `Retry connection`; do not present empty data as real zero production.
3. **API healthy but no factory rows**: show an intentional onboarding call to action `Load synthetic demo dataset` with explicit destructive reset confirmation. Do not automatically seed. Warn that this affects whichever API database is configured; inspect local dev environment before enabling.
4. **API returned zero due to valid configuration/filter**: display `No matching orders` and reset filters, not a server error.
5. **Populated demo**: render accurate queue and KPI views.
6. **Unauthorized**: clearly state server-side auth is needed; don't ask user to paste production secret into JS.

### Process visualization details

Represent the backend's 5 stages in correct order. Each stage must show label, count, modelled average age (hours), bar/marker scaled to the largest queue, and status text. Convey flow via alignment/links; arrows do not imply actual live material transfers. Stage 4 optionality: some parts skip CNC, so avoid implying every item always visits CNC. Responsive layout must preserve that nuance where possible.

Enable accessible hover/focus help for each stage. If work-order breakdown is not available from the flow-board endpoint, you may use `/api/catalog` to show stage-level order lists, but note catalog excludes `COMPLETED` and `QUALITY_HOLD` while flow-board count logic differs; do not silently assert that the two numbers must match. Where definitions differ, explain and avoid misleading combined totals.

### Alerts behavior

Render backend-provided `active_bottleneck_alerts`, but label as `Planning signals` or `Needs review`. Latest persisted schedule may contribute a modeled high-busy-hour indication; don't call it confirmed. Empty alerts means `No current model-generated alerts`, not `all production clear`. Avoid treating a warning as an actionable instruction to stop a machine.

### Interactions and acceptance

- Refresh reliably updates timestamp and reports failures.
- Navigation works via keyboard.
- Load-data action is intentional, confirmed and disabled when unsafe/unknown.
- All content renders on zero/slow/malformed API responses.
- No fake KPI values, live statuses or synthetic names hidden behind company branding.

---

## 7. Screen 2 — Schedule Optimizer (flagship)

### Primary task

Help users compare an **illustrative FIFO reference** with a **constraint-aware proposed schedule**, understand modelled consequences and inspect exact operations.

### Before a schedule exists

Show a coherent empty state, with concise explanation of the modeling assumptions and a `Run comparison` CTA. If no factory data exists, direct users back to safe onboarding. Do not show fake bars or invented improvements.

### Run behavior

POST to `/api/schedule/optimize` with `time_limit_seconds` within backend constraints (0.1–5.0). Provide progress/loading indicators without promising a precise completion time. Handle timeout/error/422. An API response returns saved schedule version IDs in the comparison metrics; surface as technical metadata when useful, not misleading production approval.

### Compare meaningful metrics

Display reference, proposed, absolute change, optional relative change with safe zero denominator rules, units, favorable direction and definition for:

- Late work orders (lower generally preferable)
- Model-derived average WIP age including projected completion (lower often preferable)
- Throughput within **168 modeled hours** (higher generally preferable)
- Furnace **batch fill** percentage (higher isn't unconditionally better; avoid optimizing it in isolation)

Allow regressions and no-change states; don't always color proposed green. Never pretend every optimized metric is better. Show actual backend values with correct precision and readable tabular numerals. A negative delta means proposed minus reference is negative; format sign and direction correctly. Consider showing a clear overall caution: `Reference is a simplified FIFO model, not the plant's actual ERP schedule`.

### Gantt: functional specification

The Gantt must be useful for planning conversations and not a screenshot prop.

**Data fields (from existing response):** `work_order_id`, `wo_number`, `sku_code`, `resource_id`, `resource_name`, `plant`, `stage`, `start_hour`, `end_hour`, `batch_id`, `is_late`, `delay_reason`.

Required capabilities:

1. Every returned operation must be represented or discoverable. **No silent first-90 or first-24-per-row slicing.** Pagination, virtualization or explicit filters are fine.
2. Correct `start_hour`/`end_hour` alignment on a shared axis. Correct for operations starting outside visible range, sub-hour durations and long intervals.
3. Group rows by stable **resource ID**, not only name (names may collide across plants in a future product).
4. Label resource and plant; optionally group by stage/plant and let users expand groups.
5. Accessible legend: stage colors + text/shape/pattern where useful.
6. Horizontal timeline scroll/zoom (e.g. 24h/72h/168h/full), fixed resource-name column if feasible.
7. Vertical scroll/windowing when many resources; retain headers and scale where feasible.
8. Clear mode switch `Illustrative FIFO` / `Proposed schedule`, with no mixing of timelines. Shared comparison scale should be optional and clearly explained.
9. Hover **and keyboard activation** open an operation-detail popover/drawer. Must work without hover.
10. Show batch grouping for sintering where `batch_id` exists; multiple operations in one batch can overlap on the same furnace by design. Do not falsely flag this as a scheduling collision.
11. Show proper units: decimal `hours from planning origin`, not a fictional wall-clock date. Do not label `Now` unless actual origin is confirmed by backend.
12. No clipped labels/tooltips outside containers, no illegible bars. Short bars may show details only on inspection.
13. Filter by stage, plant, resource, work order, late status; all from returned data. Expose filter reset and result count.
14. If no operations match, show a clear resettable empty state.
15. Maintain acceptable performance with hundreds/thousands of operations using measured render performance and reasonable windowing.
16. Distinguish a visual-only client filter from a scheduling recomputation; filtering does not change API metrics.
17. Show enough temporal context to compare schedule alternatives; allow user to inspect later operations beyond any default viewport.

### Operation details panel

When a bar is selected, show a readable, dismissible component:

- WO number, SKU, stage, plant, resource
- Start/end and duration in hours
- Batch ID (or `No batch`, if absent)
- Late status
- Model-generated delay explanation (if supplied)
- Data provenance: modeled operation, not a committed production order

If certain data is unavailable, use a neutral `Not provided` instead of inventing it.

### Late-order investigation

Render `why_late.optimized` and optionally baseline with mode switch. Show all entries via pagination/virtualization, never only 8 without disclosure. Display WO, due/completion relative hours when available, delay, priority and reason. Link/select an item to highlight the relevant operations if present in displayed timeline. Distinguish projected lateness from confirmed customer misses.

### Comparisons that require backend enhancement

If precise solver status, optimality gap, run duration, objective tradeoff, schedule feasibility explanation, or verified baseline metadata isn't returned, do not fake it. Document proposed contract additions for your collaborator. This app currently may use heuristic/fallback logic and cannot promise globally optimal plans.

---

## 8. Screen 3 — Scenario Lab

### Primary task

Explore **what would happen in the model** if an example resource failed, a rush order appeared or quantities increased. The user should understand configured inputs, effects and limitations.

### Inputs (use current backend)

- `down_resource_ids`: list of selected example resource IDs; if frontend initially supports only one, make that limitation clear. Show resource name/stage/plant and `ACTIVE` state.
- `rush_order_ids`: list of work order IDs; present WO, SKU, stage and relative due hours. Current backend changes priority to 5 and accelerates due target to no later than relative hour 24 for selected orders; explain the simplified rule when relevant.
- `demand_spike_pct`: numeric percent in 0–300 allowed by API. The current backend **multiplies quantities for existing orders**. It doesn't add new forecasted customer orders. UI should say `Increase quantities in this model` rather than implying verified market demand.
- `time_limit_seconds`: valid 0.1–5.0, use a sensible default from the existing project.

Default **0%** demand change; no machine down; no rush order. Don't run a surprising +20% scenario by default. Present clear labels, min/max, validation messages, an intuitive scenario summary and a reset action.

### Run and results

POST `/api/schedule/simulate`; this is a non-persistent scenario operation, unlike `/optimize` which persists *schedule versions* but does not alter work orders. Show a clear busy state and suppress double-submits.

Display:

- Scenario input summary from `scenario_inputs`
- Reference and scenario late-order counts, comparison
- WIP-age projection change
- Throughput (168-hour modeled horizon) change
- Modeled highest-busy-hours resource before/after, if present
- Due-date-impact list with explicit before/after completion and lateness status
- Model-generated `why_late` explanations
- Scenario Gantt using the same timeline components

Don't treat a negative metric delta as universally good. A demand spike usually changes total work requested; make comparison semantics transparent. Show whether result reflects the last *executed* input selection, not necessarily current unsent form state. For zero-impact scenario, explain unchanged metrics without implying API failure.

### Scenario honesty

This is not a digital twin of a validated Indo-MIM production line. It is a simplified optimization model with assumed process parameters and synthetic orders. Don't call scenario output a prediction of a future real machine fault. Don't auto-apply or dispatch schedules.

---

## 9. User experience details common to all three screens

### Empty, loading, error and permissions states

Create coherent reusable components and copy. Differentiate:

- Booting API/connection test
- Empty factory dataset
- No data after filters
- In-progress optimization/simulation
- Completed response with no changed metrics
- Server-side auth required
- Validation/solver infeasibility
- Temporary network failure
- Unexpected malformed payload
- Confirmed synthetic demo data available

State transitions must be predictable. Avoid hiding all UI on a transient refresh error. Keep previously rendered results visible with an appropriate stale/error status when safe.

### Navigation and state persistence

Use conventional keyboard controls. Back/forward navigation is useful but only add URL routing if it remains robust with Vite and refreshes. Avoid losing a completed comparison when switching tabs unless deliberately reset. Place form help near inputs. Dismissed error banners must not permanently conceal recurring problems.

### Tables

Keep table headers aligned, preserve visible units, support long identifiers, use semantic table markup where appropriate and responsive horizontal scrolling for dense data. Ensure screen readers can correlate headers and cells. Support sorting only if accurately implemented and meaningful.

### Date/time semantics

The backend schedules in **relative decimal hours from a planning origin**; there is no evidenced calendar timestamp in response. Do not invent exact calendar dates or claim timezone precision. Format `72.5h`, `Start 48.0h`, `End 59.0h`, perhaps tooltip `hours from model origin`. Support future absolute-time fields via isolated utilities, not speculative UI.

### Filters, search and inspection

All filter controls should be keyboard accessible and keyboard-driven search should avoid empty or absurd results. Distinguish global KPIs from subset views. Add a `Clear filters` button. For any selection, make it obvious whether data is fully represented or currently filtered.

### Responsive constraints

A mobile planning interface can simplify visuals but must not lose the user's ability to inspect an operation, read metrics, or configure a scenario. Don't rely on 6px Gantt labels. Cards may stack; timeline should scroll. Ensure no horizontal page overflow except explicitly scrollable data surfaces.

---

## 10. Testing strategy, QA and visual review

Prefer a lean frontend testing stack compatible with installed package versions. Suggested additions: Vitest + React Testing Library for components, Playwright for smoke tests; implement only if installation is practical and licensing/network policies allow. Add `npm run test` and optionally `npm run test:e2e` without breaking existing `build` or `lint` scripts.

### Component and unit tests

- Correct number/percent/hour formatting, including missing/zero/negative values.
- Delta favorability across metrics with different directions and no-change cases.
- API error translation for 401, 403, 409, 422, 5xx, invalid JSON and disconnected API.
- Flow board on empty dataset, loading, bad response and populated response.
- Explicit seed confirmation and no automatic seed on mount.
- Stage visualization populated with correct counts and average ages.
- Gantt coordinate math: zero-duration guard, overlapping sintering batches, operations after 96h, 200+ operations, long labels, different baseline/proposed horizons.
- Resource grouping by ID and filters by plant/stage/resource/order.
- Operation drawer keyboard behavior and focus restoration.
- Late-order list longer than eight entries.
- Scenario default 0%; outgoing request uses correct IDs/ranges; stale results vs updated inputs.
- Accessibility: primary controls have labels, dialogs trap focus where appropriate, usable from keyboard and reduced-motion respects user preference.

### Integration tests

Use realistic static fixture responses only **inside tests**. Verify actual request paths and payloads. If using MSW or a similar mocking mechanism, keep it out of the shipped runtime. Check no secret tokens are used. Ensure errors from the backend `detail` shape are converted into helpful messages.

### Browser test path

With local API on isolated demo DB and frontend running:

1. Healthy API, empty DB → startup/seed onboarding.
2. Confirm seed and verify 150 synthetic orders, 50 parts and 18 resources (as of reference dataset; adjust if upstream seed changed).
3. Flow Board → KPI and queues.
4. Run optimization → compare all four model metrics, inspect both timelines and late orders.
5. Inspect operations beyond hour 96, validate long-horizon scroll.
6. Select a sintering operation and read batch ID and model metadata.
7. Scenario Lab → `F-1` or another actual catalog resource down, then run scenario and inspect due impacts.
8. Reset scenario, run no-change, verify correct state.
9. Simulate API offline while page is open; check recoverability.
10. Visit at 1440×900, 1280×800, 768×1024 and 390×844.
11. Test with keyboard only; check tab order, focus, dialogs, tooltips and major controls.
12. Confirm no critical console errors or broken network requests.

If available, use automated screenshots and visually inspect each for clipped containers, unreadable legend, chart overflows, off-screen tooltips, excessive whitespace, misaligned metrics, missing status labels and contrast problems. Run any accessible automated audit available and report tool/limitations. **A screenshot generated is not a screenshot reviewed**: inspect it and fix problems.

### CI and regression checks

At every milestone, run `npm run build`, `npm run lint`, and new frontend tests. At final handoff, run backend `pytest` and `ruff` as read-only regression checks if environment works. If CI configuration must be changed to incorporate new frontend tests, make a small isolated change with rationale, coordinate ownership as needed, and avoid accidentally changing backend jobs.

### Performance and correctness

Measure whether initial screens and Gantt interactions remain responsive with a few hundred or thousands of operations (generated test fixture). Use memoization and virtualization only for a demonstrated need. Avoid canvas/SVG accessibility pitfalls, unnecessary DOM explosion and stale async updates. Make sure chart sorting and timing computations are consistent with source data.

---

## 11. Security, privacy, deployment and future productization

The repository was public when reviewed. **Never** put any confidential Indo-MIM or third-party manufacturing data into it or into an external AI service without explicit permission. Treat real customer names, plant recipes, drawings, telemetry, quotes, schedules and log exports as sensitive.

Current local development runs without a production bearer token. Backend production mode enforces token authentication. Browser code must not embed those tokens or provide a user-paste-to-localStorage authentication workaround. Don't add public user login, payments, SSO or Render deployment in this assignment. Document security requirements for a later, reviewed architecture.

Productization should eventually consider multi-tenancy, normalized manufacturing schemas, role-based access, scheduling auditability, site configuration, customer-specific constraints and secure ERP integration—but these are **roadmap items**, not December demo prerequisites. Avoid fake implementations that imply they're complete.

For any future data import, note `/api/import/erp-csv` is an admin endpoint accepting a `text/csv` body; exposing its administrator bearer token to the browser is not acceptable. Provide a future server-side import workflow proposal if asked, not a leaky browser upload feature.

---

## 12. Development phases and autonomy

Work sequentially, but continue beyond planning to implementation. Commit meaningful milestones. Keep scope on `frontend/` unless authorized. Don't repeatedly ask for ordinary layout judgments.

### Phase 0 — Baseline, audit, and team boundary

- Clone/reuse existing repo; create branch; inspect status/remotes/upstream.
- Read full frontend and relevant backend contracts.
- Run existing app and checks; document baseline.
- Record current screenshots and top issues.
- Create `frontend/docs/FRONTEND_AUDIT.md` with concrete file/line references and a prioritized risk list.

**Gate:** Know current baseline and don't rewrite teammate code.

### Phase 1 — Reliability, semantics and design foundation

- Fix empty-data onboarding and failure states.
- Add centralized typed API/client/errors and token-safe behavior.
- Replace misleading metric copy; introduce info affordances and data provenance.
- Establish design tokens and accessible component primitives.
- Start extraction from `App.tsx` incrementally, preserving functionality.

**Gate:** Existing Flow Board remains functional; build/lint/tests pass.

### Phase 2 — Flagship timeline and schedule view

- Fix silent Gantt slicing and horizon clipping.
- Correct grouping, axis scale, view switching and filters.
- Build rich operation detail panel and link it to late-order investigation.
- Improve metric comparisons and explanatory text.
- Test realistic long schedules; inspect screenshots and accessibility.

**Gate:** Every operation returned can be located; no fabricated metrics; charts work on different horizons.

### Phase 3 — Scenario UX

- Clear inputs, 0% default, reset, validation, honest assumptions.
- Result tied to executed inputs; meaningful before/after and due impact.
- Shared Gantt component for the scenario timeline.
- Error handling, empty states, keyboard support and tests.

**Gate:** A founder can run a disruption and understand modeled consequences without guidance.

### Phase 4 — Visual polish, QA and executive demo

- Improve desktop density and hierarchy; verify tablet/mobile.
- Run automated tests, visual QA and keyboard/a11y checks.
- Update frontend runbook, screenshots and demo narrative.
- Document backend requests without implementation and complete PR-ready handoff.

**Gate:** All `UI_ACCEPTANCE_CHECKLIST.md` items complete or explicitly marked blocked with reasons.

### Prioritization under limited time

Prioritize correctness before novelty: (1) safe onboarding; (2) semantic accuracy; (3) usable complete Gantt; (4) scenario correctness; (5) maintainability and tests; (6) polish. Never spend a sprint adding visual effects while essential workflows are broken.

---

## 13. Definition of done

All must hold, or final report must explicitly mark which failed and why:

- [ ] Actual repo used; no duplicate new app or backend fork.
- [ ] Appropriate frontend feature branch, clean reviewable changes.
- [ ] Baseline status/test findings recorded.
- [ ] Existing API works locally against isolated demo DB.
- [ ] Onboarding distinguishes healthy-empty from offline and requires confirmation before seed.
- [ ] Three screens function end-to-end with real API responses.
- [ ] Metrics have correct units, meaning and provenance labels.
- [ ] Model comparison states simplified FIFO, not actual ERP baseline.
- [ ] Complete Gantt navigation beyond existing truncated limits, with correct operations and accessible details.
- [ ] Late orders inspectable beyond first 8.
- [ ] Scenario inputs accurately describe backend transformations; results reflect submitted inputs.
- [ ] No misleading live telemetry, optimality guarantee or validated savings claims.
- [ ] Strict TypeScript; design tokens/components maintainable.
- [ ] No frontend secrets, unsafe public auth or real plant data.
- [ ] Desktop/tablet/mobile layouts inspected and legible.
- [ ] Major keyboard/screen reader/reduced-motion needs addressed.
- [ ] `npm run build`, `npm run lint`, new tests passing; regression checks reported.
- [ ] Backend enhancement requests documented and separated.
- [ ] At least one founder-friendly demo script updated and checked against the actual interface.
- [ ] Work remains off `main`, no unapproved push, merge, deployment or production data modification.

---

## 14. Expected final Codex response

Provide a precise engineering handoff with:

1. **Starting revision, branch, ending revision and git status.**
2. **Baseline findings**: existing features, bugs and tests before edits.
3. **Files changed** and major behavior improvements by screen.
4. **Architecture**: component tree, API client, state, design tokens, major dependencies and rationale.
5. **Data correctness**: how synthetic/FIFO/solver caveats are surfaced.
6. **Verification**: commands and exact pass/fail; browser screenshots actually inspected; responsive and accessibility checks.
7. **Backend requests**: exact fields or endpoint changes needed; no undocumented backend edits.
8. **Run instructions**: exact PowerShell commands from repo root.
9. **Known limitations and prioritized next tasks**.
10. **Demo readiness**: 5-minute walkthrough and what a founder/plant engineer can challenge.

Don't claim implementation or validation you didn't perform. If blocked by missing attachments, credentials, unavailable dependency installation or permission, report the precise blocker and provide the safest partial deliverable achievable.

---

## 15. Essential source materials to keep at hand

- [Current repo](https://github.com/JustChaos10/grind-till-we-make-it)
- [Frontend](https://github.com/JustChaos10/grind-till-we-make-it/tree/main/frontend)
- [Backend endpoints](https://github.com/JustChaos10/grind-till-we-make-it/blob/main/main.py)
- [Current CEO runbook](https://github.com/JustChaos10/grind-till-we-make-it/blob/main/docs/CEO_DEMO.md)
- [Existing CI workflow](https://github.com/JustChaos10/grind-till-we-make-it/blob/main/.github/workflows/ci.yml)
- [OR-Tools scheduling documentation](https://developers.google.com/optimization/scheduling)
- [WCAG 2.2 accessibility guidelines](https://www.w3.org/TR/WCAG22/)

**Final instruction:** Do the actual frontend engineering and product-design work, verify it with real local execution, preserve backend ownership, and hand back reviewable code—not just a plan or a mockup.
