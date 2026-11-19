# Frontend implementation handoff

## Current state

- Branch: `feat/frontend-experience`.
- Scope: React frontend and frontend documentation only. No backend logic was changed and nothing was pushed.
- The frontend has a clear Flow Board, Schedule Optimizer, and Scenario Lab, with synthetic/demo and read-only messaging.
- Scenario controls submit only supported API inputs. The result view reports API values and compares them with the current optimizer result; it does not present modeled deltas as realized savings.
- The Gantt view shows returned operations with proportional durations, resource labels, baseline/optimized selection, and operation details.
- Seed controls require API readiness and user confirmation. The README uses a dedicated `indoflow-demo.db` SQLite database.
- `DESIGN.md` records the design workflow and the use of focused patterns from Taste, Unslop, UI UX Pro Max, Awesome Design MD, and Ant Design references. Ant Design itself was not added as a dependency.

## Verification completed

- Frontend unit tests: `npm test -- --reporter=dot` — 25 tests passed across five files.
- Production build: `npm run build` — passed.
- Lint and formatting: `npm run lint` — passed.
- `git diff --check` — passed.
- Backend regression suite: `.venv\Scripts\python.exe -m pytest -q` — 23 passed. `.venv\Scripts\python.exe -m ruff check .` — passed. Backend source was not changed. Global Python 3.13 lacks `aiosqlite`; use the repository `.venv` (Python 3.12).
- Local API health returned `ready`. The read-only Flow Board response and rendered UI showed 150 synthetic work orders, a 31.53h average WIP age, stage queues 56/25/26/24/19, and two API-returned alerts. The startup command used `DATABASE_URL=sqlite+aiosqlite:///./indoflow-demo.db`, `APP_ENV=development`, and refused to start if that DB file already existed. No seed request was made in this continuation.
- Local browser review exercised the Flow Board with 150 synthetic work orders, the optimizer with 524 returned operations, and a CNC-1 downtime scenario. The Flow Board was visually reviewed at 1920×1080, 1280×800, 768×1024, and 390×844; screenshots are `screenshots/flow-desktop-1920.png`, `flow-laptop-1280.png`, `flow-tablet-768.png`, and `flow-mobile-390.png`. At all four CSS viewport widths the document had no horizontal overflow; tablet and phone client widths are 753 px and 375 px after the vertical scrollbar. Dense Gantt content stays in its own scroll region. Browser review also covered the optimizer and Scenario Lab; the scenario request completed after about 20 seconds in this local run, which should be reviewed with the backend owner.
- Browser Tab and Enter checks reached all three planning screens. A 1440 px browser check found no sampled text below 4.5:1 on the fixture board or optimizer and scenario results. Full state contrast and assistive-technology review remain open.

## Final implementation update

- Reworked the stage flow, planning hierarchy, and responsive schedule layout. The Gantt keeps the timeline and resource labels together, with keyboard selection, focus restoration, filters, zoom, and a text view of returned operation details. Queue and late-order actions connect the board, timeline, and Scenario Lab. A component test inspects the last operation in a schedule of 1,200 operations on one resource.
- Added shared typed API response definitions in `src/types.ts` and hardened the Flow Board, optimizer, and scenario interactions around supported response data.
- Expanded regression tests for empty-database onboarding, seed confirmation, demand bounds, disabled empty scenarios, dense/long-horizon Gantt operations, operation details and Escape focus restoration, submitted scenario snapshots, Pydantic error arrays, and unavailable metric formatting.
- Updated the UI acceptance ledger, implementation audit, backend request list, and founder demo copy to match observed behavior and remaining verification limits.

## Final Git record

- Feature branch: `feat/frontend-experience`.
- Branch base: `6bd4c7e80dff7a2449a71f67fdc2ab290b239e34` (`main` at task setup); the design and browser verification continuation started from `6cce593`.
- Frontend implementation commit: `d2a9ace74bbd3f942a3a66a940069c371d6ef429`.
- No changes were pushed; `main` and backend source were not edited. The final documentation commit SHA and working-tree status are reported in the handoff message.

## Local run commands (PowerShell)

From the repository root, use one terminal for the API:

```powershell
$env:DATABASE_URL = "sqlite+aiosqlite:///./indoflow-demo.db"
$env:APP_ENV = "development"
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Use a second terminal for the frontend:

```powershell
cd frontend
$env:VITE_ENABLE_DEMO_SEED = "true"
npm ci
npm run dev -- --host 127.0.0.1
```

Open the Vite URL, usually `http://localhost:5173`. Load synthetic data only in the dedicated demo database. See the root README for the explicit seed warning.

## Repeatable browser verification

From `frontend`, with Vite running at `127.0.0.1:5173`, run `python scripts/browser_flow.py`. The script uses Microsoft Edge, Python Playwright, and synthetic API fixtures. It passed optimization, opening Gantt details by keyboard, Escape focus restoration, and scenario inputs. The automated fixture walkthrough took 2.38 seconds with reduced motion emulated.

Run `python scripts/browser_real_api.py` from `frontend` for the isolated API smoke. It starts its own local API and Vite processes, uses a temporary synthetic SQLite database, and exercises retry, explicit seed confirmation, optimization, timeline selection and two simulation requests. The root `.venv` must have the backend dependencies installed. Python Playwright and Microsoft Edge are also required.

## Screenshots

- `screenshots/baseline-board.png` records the board before the current design pass.
- `screenshots/{board,optimizer,scenario}-{desktop,tablet,mobile}.png` record all three screens at desktop, tablet and mobile sizes.
- `screenshots/real-api-{board,optimizer,scenario}.png` document the isolated API flow.
- `screenshots/flow-*.png` preserve the earlier Flow Board viewport review.

## Follow-up

- See `BACKEND_REQUESTS.md` for requests and `UI_ACCEPTANCE_CHECKLIST.md` for the open acceptance items.
- Have a plant planner validate routings, order data, calendars, and model assumptions before using the results for shop-floor decisions.
- Production use requires a trusted authentication/proxy design. Keep shared API credentials on the server.
- Full screen-reader, contrast, and keyboard coverage remain open. The focused browser checks cover the major planning actions. The five-minute founder presentation requires a spoken rehearsal using `docs/CEO_DEMO.md`.
