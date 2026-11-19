# IndoFlow Frontend Agent Instructions

> Scope: `frontend/` and its descendants. These instructions complement the repository's existing guidance. Read `frontend/docs/FRONTEND_MASTER_BRIEF.md` and `frontend/docs/API_CONTRACT_AND_METRICS.md` before substantive changes. If these files have not been copied into the checkout, request their location.

## Mission and ownership

You are the frontend/UI/UX engineer for IndoFlow, a **read-only** manufacturing scheduling and WIP simulation demo. The other collaborator owns the Python/FastAPI API, SQLAlchemy database, OR-Tools solver, backend tests, migrations, and deployment. Preserve that boundary: the frontend implements presentation, state, API integration, accessible interactions, test coverage, and design documentation. Do not change backend files to make the UI work. If a backend change is needed, document an explicit contract request for the collaborator.

## First action, every session

1. Inspect `git status`, branch, remote, and recent commits; never discard work. Confirm you are **not on `main`** before editing.
2. Read `README.md`, `docs/CEO_DEMO.md`, this file, the master brief, and the API reference; inspect actual current code rather than trusting snapshots.
3. Verify environment, changes from upstream, build/lint status, and immediate scope before implementing.
4. Work through coherent milestones with tests, visual inspection, and small commits. Do not push, merge, deploy, modify paid infrastructure, or create public services without explicit authorization.

## Non-negotiable domain truth

- All bundled factory records are **synthetic**. The example plants and equipment are fictionalized demo data, not proof of actual Indo-MIM operations.
- The reference is an **illustrative FIFO-style baseline**, not a measured ERP or current plant schedule.
- Proposed schedules and what-if effects are modeled results, not verified cost savings, production predictions, or guaranteed improvements.
- Do not equate highest queue depth with a proven production bottleneck.
- Do not equate furnace **batch fill** with furnace uptime, OEE, or capacity utilization.
- The `bottleneck_resource_id` metric reflects **largest modeled resource busy-hours**, not a proven throughput constraint; label it accordingly.
- `avg_wip_age_hours` on the flow board is different from the schedule-comparison projection; do not present them as an identical KPI.
- `throughput` counts modeled work orders completed within a backend-defined 168-hour horizon, not parts per hour.
- The scheduling UI is decision support. It never instructs machinery or approves a plan. Human planners validate every operational action.

## API and security

- Use the real `/api/flow-board`, `/api/catalog`, `/api/schedule/optimize`, `/api/schedule/simulate`, `/health`, and `/health/live` endpoints. Use typed, centralized requests; model fields only from actual responses.
- `POST /api/seed` **destructively replaces records in the configured API database**. Never invoke automatically; require explicit confirmation and verify that the backend points to a dedicated local demo DB. Never use it against real or shared data.
- Do not expose `INDOFLOW_API_TOKEN`, `INDOFLOW_ADMIN_TOKEN`, or any credential in browser JavaScript, `VITE_*` variables, logs, commits, or screenshots. A production frontend requires a trusted proxy or appropriate user auth; don't fabricate one.
- Avoid inventing API responses, monitoring telemetry, real savings, customer names, or manufacturing process parameters. If the API cannot supply a field, show a truthful missing state or log a backend enhancement request.
- Use mocked data only within isolated tests/storybook-like development fixtures. Production app screens must use real API responses.

## Implementation standards

- Prefer clear, idiomatic React + strict TypeScript, reusable components where appropriate, accessible semantic HTML, well-contained CSS and design tokens. Don't add dependencies casually.
- Never silently truncate schedule operations. The Gantt must support long time horizons and large sets through explicit filtering/pagination/windowing where needed.
- Provide meaningful empty/loading/error/unauthorized/offline states, keyboard access, contrast, reduced-motion, and responsive layouts. Never use color as the sole status cue.
- Keep process stages configurable on the frontend, while accurately reflecting the backend's current five-stage MIM contract. Avoid speculative universal-manufacturing UI.
- Preserve successful flows as you refactor. Avoid wholesale rewrites that regress working screens.

## Test and handoff

- Run `npm ci`, `npm run build`, `npm run lint`; run frontend tests once added. Inspect actual rendered pages at 1440×900, 1280×800 and 390×844 where browser tooling permits.
- If backend dependencies are available, run `python -m pytest -q` and `python -m ruff check .` as non-modifying regression checks. Record command results precisely.
- Commit only frontend files and frontend documentation unless expressly authorized. Give a clear changelog, screenshot/visual review, test results, known limitations, branch name, and requested API changes in the final handoff.

## Existing snapshot, not a permanent truth

At review on 2026-11-19 (`main` commit `6bd4c7e`): React 19 + TypeScript + Vite; a large `src/App.tsx` and `src/styles.css`; three screens (Flow Board, Schedule Optimizer, Scenario Lab); 150 synthetic orders, 50 parts, 18 resources (including 4 sintering furnaces); latest CI succeeded. The repo may have evolved. Re-read current code and use it over this snapshot.
