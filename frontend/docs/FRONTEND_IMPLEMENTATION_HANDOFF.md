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

- Frontend unit tests: `npm test -- --reporter=dot` — 9 tests passed.
- Production build: `npm run build` — passed.
- Lint and formatting: `npm run lint` — passed.
- `git diff --check` — passed.
- Backend regression suite: `.venv\Scripts\python.exe -m pytest -q` — 23 passed. `.venv\Scripts\python.exe -m ruff check .` — passed. Backend source was not changed. Global Python 3.13 lacks `aiosqlite`; use the repository `.venv` (Python 3.12).
- Local API health returned `ready`. The read-only Flow Board response and rendered UI showed 150 synthetic work orders, a 31.53h average WIP age, stage queues 56/25/26/24/19, and two API-returned alerts. The startup command used `DATABASE_URL=sqlite+aiosqlite:///./indoflow-demo.db`, `APP_ENV=development`, and refused to start if that DB file already existed. No seed request was made in this continuation.
- Previous local browser smoke review exercised optimization (524 returned operations) and a CNC-1 downtime scenario. Review notes from that session cover 1440×900, 1024×768, and 390×844; see `FRONTEND_AUDIT.md` for what was and was not verified.
- Screenshot `screenshots/flow-desktop.png` was opened and visually inspected in this continuation. It is a desktop Flow Board capture. It does not prove tablet/mobile behavior or every screen.

## Current changes in final verification

- Extracted API error handling and missing-value formatting to `src/api.ts`, which also removes Fast Refresh lint warnings.
- Added regression tests for empty-database onboarding, opt-in seed confirmation, demand bounds, disabled empty scenarios, dense/long-horizon Gantt operations, operation details and Escape focus restoration, submitted scenario snapshots, Pydantic error arrays, and unavailable metric formatting.
- Updated PowerShell startup instructions to gate the destructive seed control behind `VITE_ENABLE_DEMO_SEED=true` and explain the dedicated-database check.

## Final Git record

- Feature branch: `feat/frontend-experience`.
- Branch base: `6bd4c7e80dff7a2449a71f67fdc2ab290b239e34` (`main` at task setup).
- No changes were pushed; `main` and backend source were not edited. Record the final commit SHA and status in `FRONTEND_AUDIT.md` after the final commit.

## Local run commands (PowerShell)

From the repository root, use one terminal for the API:

```powershell
$env:DATABASE_URL = "sqlite+aiosqlite:///./indoflow-demo.db"
python -m uvicorn main:app --reload
```

Use a second terminal for the frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL, usually `http://localhost:5173`. Load synthetic data only in the dedicated demo database. See the root README for the explicit seed warning.

## Follow-up

- Backend contract requests are listed in `BACKEND_REQUESTS.md`.
- Validate the UI against representative customer data before using it for shop-floor decisions.
- Production use requires a trusted authentication/proxy design; the browser must not hold shared API credentials.
- `UI_ACCEPTANCE_CHECKLIST.md` remains the acceptance ledger. Do not treat unchecked visual, keyboard, or founder-demo items as complete based only on this handoff.
- Desktop/tablet/mobile review was performed in the local browser. Screenshots were inspected during review; persistent image files were not exported in this handoff.
