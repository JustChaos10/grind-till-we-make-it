# IndoFlow

IndoFlow is a read-only scheduling and WIP bottleneck API for a five-stage Metal Injection Molding flow:

`Molding → Debinding → Sintering → CNC Machining → Finishing`

It compares a FIFO baseline with an OR-Tools CP-SAT schedule and saves schedule runs. Optimization does not change work-order state, quantities, due dates, or current stages.

## Local development

Requires Python 3.12 or newer.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m uvicorn main:app --reload
```

The API is at `http://127.0.0.1:8000`; interactive docs are at `/docs`. SQLite is created automatically for local development.

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

Example local request:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/schedule/optimize `
  -H "Content-Type: application/json" `
  -d '{"time_limit_seconds":5}'
```

The simulation endpoint accepts `down_resource_ids`, `rush_order_ids`, `demand_spike_pct`, and `time_limit_seconds`. Use IDs returned by the API.

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

Set `CORS_ORIGINS` to the exact deployed frontend origin after the frontend exists. Until then it allows only local development origins. A browser app cannot safely hold the shared API bearer token: put a trusted server-side proxy or proper user authentication in front of browser requests before exposing the API to a public frontend.

The current project supplies the API and deployment infrastructure. It does not yet include a production factory data connector/import pipeline, a deployed frontend, or user-level authentication. Production optimization quality must be validated against representative plant data and operational constraints before the schedules are used to make shop-floor decisions.

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
- Furnace loads are packed by compatible recipe and capacity. The model enforces stage precedence, resource non-overlap, and sequence-dependent CNC setup times.
- A deterministic feasible schedule is used as a fallback if CP-SAT reaches its time limit without finding an incumbent. Check the returned solver status and validate results on plant data; a fallback schedule is not a guarantee of globally optimal production performance.
- Optimization persists `ScheduleVersion` and `ScheduledOperation` records only. It leaves source work orders unchanged.
