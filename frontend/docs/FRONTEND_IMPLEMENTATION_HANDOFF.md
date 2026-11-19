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

- Frontend unit tests: `npm test` — 4 tests passed.
- Production build: `npm run build` — passed.
- Lint and formatting: `npm run lint` — passed.
- `git diff --check` — passed.
- Existing backend baseline: 23 pytest tests and Ruff passed earlier in this task; backend files were not changed.
- Local UI review used the synthetic database and API. Flow Board loaded 150 synthetic work orders, 50 parts, and 18 resources. Optimization returned 524 operations. A CNC-1 downtime scenario returned a result.
- UI was reviewed at 1440×900, 1024×768, and 390×844. The Gantt keeps its own horizontal scroll area on narrow screens. The viewport was restored after review.

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
- Desktop/tablet/mobile review was performed in the local browser. Screenshots were inspected during review; persistent image files were not exported in this handoff.
