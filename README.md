# IndoFlow

IndoFlow is a read-only scheduling and WIP bottleneck API for a configurable Metal Injection Molding flow. Its supported stage set is:

`Molding → Debinding → Sintering → CNC Machining → Finishing`

Each part can use an ordered subset of those stages; records without a route retain the legacy route controlled by `requires_machining`. It compares a FIFO baseline with an OR-Tools CP-SAT schedule and saves schedule runs. Optimization does not change work-order state, quantities, due dates, or current stages.

## Local development

Requires Python 3.12 or newer.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m uvicorn main:app --reload
```

The API is at `http://127.0.0.1:8000`; interactive docs are at `/docs`. SQLite is created automatically for local development.

### Run the CEO demo locally

Use a dedicated demo database so loading synthetic factory records cannot replace `indoflow.db`:

1. In a PowerShell terminal at the repository root, start the API against a separate database:

   ```powershell
   $env:DATABASE_URL = "sqlite+aiosqlite:///./indoflow-demo.db"
   python -m uvicorn main:app --reload
   ```

2. In a second terminal, start the browser app:

   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

   The frontend requires Node.js 20.19+ or 22.12+.

3. Open the Vite URL shown in the terminal (usually `http://localhost:5173`) and choose **Load synthetic demo data**. The app asks before seeding; that action resets data only in the API database configured in step 1.
4. Walk through **Flow board**, **Schedule optimizer**, and **Scenario lab**. Try taking a furnace or CNC machine offline, then compare the impact.

The local app uses the API's development mode and same-origin Vite proxy. Do not point it at a production database. The frontend is a local demo client; it does not store or expose a production API token.

Load the deterministic demo data locally with:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/seed
```

**The seed endpoint deletes existing factory and schedule rows before inserting synthetic demo data. It is disabled in production by default. Never enable it on a production database containing real data.**

## API

- `GET /health` checks database readiness; `GET /health/live` checks process liveness.
- `GET /api/flow-board` returns current WIP queues.
- `POST /api/schedule/optimize` compares baseline and optimized schedules and persists both runs.
- `POST /api/schedule/simulate` evaluates a downtime, rush-order, or demand scenario without persisting it.
- `POST /api/import/erp-csv` imports valid work orders from a `text/csv` request body and reports rejected rows with row numbers and reasons.

Example local request:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/schedule/optimize `
  -H "Content-Type: application/json" `
  -d '{"time_limit_seconds":5}'
```

The simulation endpoint accepts `down_resource_ids`, `rush_order_ids`, `demand_spike_pct`, and `time_limit_seconds`. Use IDs returned by the API.

Production CSV imports use the administrator bearer token. Missing recipe IDs are inferred from the normalized alloy family; invalid rows are logged and isolated from valid rows. Files must have unique headers and explicit `plant` and `segment` values, and are limited to 5 MiB and 10,000 rows. Supported columns include `wo_number`, `sku_code`, `plant`, `part_name`, `segment`, `alloy_family`, `sintering_recipe_id`, `quantity`, `due_date_hours`, `priority`, `current_stage`, `process_route`, `molding_cycle_mins`, `debinding_cycle_mins`, `sintering_cycle_mins`, `cnc_machining_cycle_mins`, `finishing_cycle_mins`, `wip_age_hours`, `requires_machining`, and `tool_id`. New SKUs must include valid positive cycle times for every stage in their route; existing SKUs use the registered part master and reject conflicting supplied values. `process_route` is optional and uses `>` between ordered stage names, such as `Molding > Debinding > Sintering > Finishing`.

## Tests and lint

```powershell
python -m pytest -q
python -m ruff check .
```

## Production deployment (Render)

The repository includes a Render Blueprint (`render.yaml`), Dockerfile, PostgreSQL configuration, and Alembic migration. To deploy:

1. Push this repository to GitHub.
2. In Render, create a new Blueprint instance and connect `JustChaos10/grind-till-we-make-it` (or your fork).
3. Review the service and managed PostgreSQL plans and region in the Blueprint before applying it. Render may charge for these resources.
4. Render generates separate `INDOFLOW_API_TOKEN` and `INDOFLOW_ADMIN_TOKEN` secrets. Keep them private; do not place either token in frontend JavaScript, source control, or logs.
5. The container runs database migrations before starting the API. Render uses `/health` as the readiness check.
6. The API starts with an empty database. Connect a trusted production data import before using it for scheduling; `/api/seed` is disabled in production. The included seed records are synthetic and are only for local development.

The Render Blueprint starts with only local development CORS origins. Set `CORS_ORIGINS` to the exact trusted frontend or proxy origin when you deploy that layer. A browser app cannot safely hold the shared API bearer token: put a trusted server-side proxy or proper user authentication in front of browser requests before exposing the API to a public frontend.

The current project supplies the API, deployment infrastructure, and a local React demo client. The frontend is not deployed, has no user-level authentication, and is not configured to safely call a token-protected public API. Production requires a trusted server-side frontend/API proxy or user authentication, a factory data connector, and validation against representative plant data and operational constraints before schedules are used to make shop-floor decisions.

## Configuration

See [.env.example](.env.example) for local settings. Production requires:

- `APP_ENV=production`
- PostgreSQL `DATABASE_URL`
- `INDOFLOW_API_TOKEN` for read/scheduling API access
- `INDOFLOW_ADMIN_TOKEN` for administrative seed access (seed remains disabled unless separately enabled)
- `CORS_ORIGINS` set to known frontend origins only

Do not commit `.env` files, database credentials, or API tokens.

## Scheduling model notes

- Solver time uses 15-minute ticks; Gantt values are decimal hours from simulation hour zero.
- Molding, CNC, and finishing cycle times are per-part. Debinding and sintering times are per-lot.
- Furnace loads are packed by compatible recipe and capacity. The model enforces part-specific stage precedence, resource non-overlap, and sequence-dependent setup times on discrete machines. Explicit routes can omit unsupported/unneeded stages from the current supported stage set.
- Debinding vessel capacity and sintering furnace capacity are treated as lot limits. Work orders larger than the largest compatible vessel or furnace are rejected during preflight and must be split into smaller ERP work orders; the scheduler does not split a work order internally.
- `Part.tool_id` represents a shared physical mold. `Resource.blackout_windows` contains absolute offline intervals in hours from the planning origin; expand recurring shifts and maintenance calendars into these windows before scheduling. Locked WIP uses `WorkOrder.locked_resource_id` and `locked_until_hour`. `COMPLETED` and `QUALITY_HOLD` orders are excluded from scheduling.
- Each active work order is assigned to one plant; the solver will not teleport it between facilities. There is no inter-plant transfer-time model. The plant column added in migration `0004_work_order_plant` is nullable for upgrade safety, but existing active orders must be backfilled before scheduling or preflight returns a data error.
- A deterministic feasible schedule is used as a fallback if CP-SAT reaches its time limit without finding an incumbent. Check the returned solver status and validate results on plant data; a fallback schedule is not a guarantee of globally optimal production performance.
- At 300 or more active orders, IndoFlow skips the quadratic CP-SAT sequencing model and uses a deterministic due-date, priority, and remaining-work dispatch heuristic. This path is designed to return a feasible schedule quickly; it does not claim mathematical optimality.
- Optimization persists `ScheduleVersion` and `ScheduledOperation` records only. It leaves source work orders unchanged.
- What-if runs retain each work order's status and locked-resource commitment. Every generated baseline, optimized, and scenario schedule is checked against raw operations and master data before it is returned or persisted; a failed check blocks the response.

`validator.py` independently checks raw persisted operation rows against orders, parts, and resources. It validates remaining route order, cycle-time duration, non-overlap, shared mold contention, setup gaps, furnace recipe/capacity, active-resource use, and blackout windows without reading solver status flags or summary metrics.

This backend is a scheduling prototype, not a validated Indo-MIM production execution system. Public Indo-MIM materials describe additional operations and both batch and continuous furnace technologies; this version models only the stages/resources present in its master data. Validate actual routing, process parameters, calendars, quality release rules, and resource qualifications with plant engineering before using a schedule operationally.
