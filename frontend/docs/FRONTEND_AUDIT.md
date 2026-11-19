# Frontend implementation and verification record

Date: 2026-11-19  
Repository: `JustChaos10/grind-till-we-make-it`  
Branch: `feat/frontend-experience`

## Scope and Git safety

- Reused the existing checkout at `C:\IndoFlow\grind-till-we-make-it` and the existing remote `origin`.
- Work is isolated on `feat/frontend-experience`. At task setup, local `main` was `6bd4c7e`; the branch's prior head was `e12e03f`.
- `origin/main` had advanced to `d9ae616` and local `main` was six commits behind it at inspection. Those backend commits were not merged or edited here.
- No backend source, migrations, production database, public deployment, or remote branch was changed. No push was made.
- Source documents were copied to `frontend/AGENTS.md` and `frontend/docs/{FRONTEND_MASTER_BRIEF.md,API_CONTRACT_AND_METRICS.md,UI_ACCEPTANCE_CHECKLIST.md}` after checking the repository instruction file. Existing frontend rules were retained and reconciled.

## Implementation completed

- Kept the Flow Board, Schedule Optimizer, and Scenario Lab grounded in API responses. Empty data is shown as onboarding rather than a zero-value production dashboard.
- Made destructive synthetic seeding unavailable by default, opt-in through `VITE_ENABLE_DEMO_SEED=true`, and subject to an explicit confirmation dialog. README instructions require a dedicated local demo database.
- Handled missing, null, and non-finite metric values as unavailable; parsed Pydantic detail strings, objects, and arrays into readable errors.
- Preserved schedule result snapshots and labeled scenario results from the inputs that produced them; later draft edits make prior results visibly stale.
- Improved Gantt discoverability for large schedules and long horizons, returned operation details (including batch and lateness), and restored focus after Escape closes details.
- Corrected the due-date impact threshold copy and expressed furnace batch fill as percentage points.
- Extracted the shared API request/formatting helpers to `frontend/src/api.ts` and added frontend regression coverage.
- Taste/Unslop, UI UX Pro Max, Awesome Design MD, and Ant Design were used as workflow/reference sources for focused hierarchy, plain operational copy, responsive structure, and reusable patterns. Ant Design was not added as a dependency. No upstream design repository was copied wholesale.

## Verification evidence

| Check | Result |
| --- | --- |
| `cd frontend; npm test -- --reporter=dot` | Passed: 9 tests |
| `cd frontend; npm run build` | Passed |
| `cd frontend; npm run lint` | Passed (Oxlint and Prettier) |
| `.venv\Scripts\python.exe -m pytest -q` | Passed: 23 tests; one Starlette/httpx deprecation warning |
| `.venv\Scripts\python.exe -m ruff check .` | Passed |
| `git diff --check` | Passed; Git reported line-ending conversion notices only |
| `GET http://127.0.0.1:8000/health` | Passed: `ready` |
| `GET http://127.0.0.1:8000/api/flow-board` | Passed: 150 synthetic WIP orders, 31.53h average age, stage counts 56/25/26/24/19, two alerts |
| Vite at `http://127.0.0.1:5173` | Loaded Flow Board and rendered the same synthetic snapshot |
| Previous local API/browser smoke review | Optimization returned 524 operations; a CNC-1 downtime scenario returned results |
| Desktop screenshot inspection | Inspected `frontend/docs/screenshots/flow-desktop.png` in this continuation |

The API process command line showed `DATABASE_URL=sqlite+aiosqlite:///./indoflow-demo.db` and `APP_ENV=development`. Its startup guard refused to reuse an existing file. This continuation used read-only API requests and did not call `/api/seed`.

Global Python 3.13 did not have `aiosqlite`, so its initial pytest run failed during test setup. The repository `.venv` (Python 3.12) contains the dependencies and passed the complete suite. Use the `.venv` commands above for backend checks.

## Visual and acceptance limits

The prior browser review recorded 1440×900, 1024×768, and 390×844 checks. The desktop screenshot was inspected in this continuation. The required 1920×1080, 1280×800, and ~768×1024 viewports were not verified here. Keyboard-only navigation across every screen, reduced-motion behavior, contrast measurements, browser automation of every demo path, and a full five-minute founder walkthrough remain incomplete. The checklist leaves these unchecked. Do not describe this branch as fully acceptance-complete until those checks are done.

The current browser/API smoke is against local synthetic demo data only. It is not evidence of production ERP integration, validated plant constraints, solver optimality, realized savings, or production readiness.

## Backend requests

Requests for the backend owner are listed in `BACKEND_REQUESTS.md`. They include explicit dataset safety metadata, solver provenance, scenario lock preservation/regression coverage, metric formulas and time origin, and stronger schedule provenance. No backend behavior was changed to fill these gaps.

## Run locally (Windows PowerShell)

From the repository root, start the API in one terminal:

```powershell
$env:DATABASE_URL = "sqlite+aiosqlite:///./indoflow-demo.db"
$env:APP_ENV = "development"
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
cd frontend
$env:VITE_ENABLE_DEMO_SEED = "true"
npm install
npm run dev -- --host 127.0.0.1
```

Only enable the seed control after confirming the API uses the dedicated local demo database. The seed route deletes and recreates factory and saved schedule rows in its connected database. Do not use it with shared, customer, or production data.

## Next work

1. Complete the remaining viewport, keyboard, screen-reader, reduced-motion, and contrast checks, then update `UI_ACCEPTANCE_CHECKLIST.md` with evidence.
2. Run a repeatable browser smoke flow covering empty state, confirmed seed, optimization, operation details, and scenario simulation against the local demo API.
3. Review `BACKEND_REQUESTS.md` with the backend owner before stronger solver or metric claims are made.

## Final commit record

Fill after commit: starting branch head `e12e03f`; ending SHA: pending; `git status`: pending.
