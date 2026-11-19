"""FastAPI entry point for the read-only IndoFlow scheduling service."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import csv
import hmac
import io
import math
import os
import logging
import uuid
from datetime import datetime, timezone
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from baseline import schedule as run_baseline
from database import get_session, init_db
from domain import ALLOYS, SEGMENTS, OrderSpec, STAGES
from models import Part, Resource, ScheduleVersion, ScheduledOperation, WorkOrder
from seed import RECIPES, seed_database
from solver import SchedulingError, solve as run_solver
from validator import ScheduleValidationError, validate_schedule_rows

logger = logging.getLogger("indoflow.import")
MAX_ERP_CSV_BYTES = 5 * 1024 * 1024
MAX_ERP_CSV_ROWS = 10_000
CYCLE_TIME_COLUMNS = {
    "Molding": "molding_cycle_mins",
    "Debinding": "debinding_cycle_mins",
    "Sintering": "sintering_cycle_mins",
    "CNC Machining": "cnc_machining_cycle_mins",
    "Finishing": "finishing_cycle_mins",
}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if os.getenv("APP_ENV", "development").lower() == "production":
        if not os.getenv("INDOFLOW_API_TOKEN") or not os.getenv("INDOFLOW_ADMIN_TOKEN"):
            raise RuntimeError("INDOFLOW_API_TOKEN and INDOFLOW_ADMIN_TOKEN are required in production")
        database_url = os.getenv("DATABASE_URL", "")
        if not database_url.startswith(("postgresql+asyncpg://", "postgresql://")):
            raise RuntimeError("Production requires DATABASE_URL using PostgreSQL")
    else:
        await init_db()
    yield


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class SeedResponse(StrictModel):
    message: str
    resources: int
    parts: int
    work_orders: int


class StageQueue(StrictModel):
    stage: str
    queue_depth: int
    avg_wip_age_hours: float


class FlowBoardResponse(StrictModel):
    total_wip_orders: int
    avg_wip_age_hours: float
    queues: list[StageQueue]
    active_bottleneck_alerts: list[str]


class OptimizeRequest(StrictModel):
    time_limit_seconds: float = Field(default=5.0, ge=0.1, le=5.0)


class ScenarioRequest(StrictModel):
    down_resource_ids: list[str] = Field(default_factory=list)
    rush_order_ids: list[str] = Field(default_factory=list)
    demand_spike_pct: float = Field(default=0.0, ge=0.0, le=300.0)
    time_limit_seconds: float = Field(default=5.0, ge=0.1, le=5.0)


app = FastAPI(
    title="IndoFlow Scheduling API",
    version="1.0.0",
    lifespan=lifespan,
    description=(
        "Read-only production scheduling and WIP bottleneck optimization for "
        "the Hoskote and Doddaballapura MIM plants. Schedule runs are stored; "
        "work orders and shop-floor state are never changed by optimization."
    ),
)
bearer_scheme = HTTPBearer(auto_error=False)
origins = [item.strip() for item in os.getenv(
    "CORS_ORIGINS", "http://localhost:3000,http://localhost:5173"
).split(",") if item.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


def _matches_configured_token(token: str, variable: str) -> bool:
    expected = os.getenv(variable, "")
    return bool(expected) and hmac.compare_digest(token, expected)


async def require_api_access(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> None:
    api_token = os.getenv("INDOFLOW_API_TOKEN", "")
    if (
        os.getenv("APP_ENV", "development").lower() != "production"
        and not api_token and not os.getenv("INDOFLOW_ADMIN_TOKEN", "")
    ):
        return
    token = credentials.credentials if credentials and credentials.scheme.lower() == "bearer" else ""
    if token and _matches_configured_token(token, "INDOFLOW_API_TOKEN"):
        return
    raise HTTPException(status_code=401, detail="Valid IndoFlow bearer token required", headers={"WWW-Authenticate": "Bearer"})


async def require_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> None:
    admin_token = os.getenv("INDOFLOW_ADMIN_TOKEN", "")
    if (os.getenv("APP_ENV", "development").lower() != "production"
            and not admin_token and not os.getenv("INDOFLOW_API_TOKEN")):
        return
    if not admin_token:
        raise HTTPException(status_code=503, detail="Administrator token is not configured")
    token = credentials.credentials if credentials and credentials.scheme.lower() == "bearer" else ""
    if token and _matches_configured_token(token, "INDOFLOW_ADMIN_TOKEN"):
        return
    raise HTTPException(status_code=403, detail="Administrator bearer token required")


@app.get("/health")
async def health(session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database is not ready") from exc
    return {"status": "ready", "service": "IndoFlow"}


@app.get("/health/live")
async def liveness() -> dict[str, str]:
    return {"status": "alive", "service": "IndoFlow"}


@app.post("/api/seed", response_model=SeedResponse, dependencies=[Depends(require_admin)])
async def seed() -> SeedResponse:
    """Reset and repopulate the deterministic demo dataset."""
    if (os.getenv("APP_ENV", "development").lower() == "production"
            and os.getenv("ENABLE_PRODUCTION_SEED", "false").lower() != "true"):
        raise HTTPException(status_code=404, detail="Seed endpoint disabled in production")
    counts = await seed_database()
    return SeedResponse(message="Factory data reset and seeded", **counts)


@app.post("/api/import/erp-csv", dependencies=[Depends(require_admin)])
async def import_erp_csv(request: Request, session: AsyncSession = Depends(get_session)) -> dict:
    """Import valid ERP work orders from a UTF-8 CSV request body.

    Invalid rows are isolated and returned with row numbers and actionable
    reasons; valid rows in the same file are committed.
    """
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_ERP_CSV_BYTES:
                raise HTTPException(status_code=413, detail="CSV exceeds the 5 MiB import limit")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid Content-Length header") from None
    body_parts = []
    total_bytes = 0
    async for chunk in request.stream():
        total_bytes += len(chunk)
        if total_bytes > MAX_ERP_CSV_BYTES:
            raise HTTPException(status_code=413, detail="CSV exceeds the 5 MiB import limit")
        body_parts.append(chunk)
    body = b"".join(body_parts)
    try:
        text_body = body.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text_body))
    except (UnicodeDecodeError, csv.Error) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid UTF-8 CSV: {exc}") from exc
    if not reader.fieldnames:
        raise HTTPException(status_code=422, detail="CSV must include a header row")
    normalized_headers = [name.strip().casefold() for name in reader.fieldnames if name is not None]
    if len(normalized_headers) != len(reader.fieldnames) or len(set(normalized_headers)) != len(normalized_headers):
        raise HTTPException(status_code=422, detail="CSV headers must be non-empty and unique")
    required_headers = {"wo_number", "sku_code", "segment", "alloy_family", "quantity", "due_date_hours", "current_stage"}
    missing_headers = sorted(required_headers - set(normalized_headers))
    if missing_headers:
        raise HTTPException(status_code=422, detail=f"CSV is missing required columns: {', '.join(missing_headers)}")

    def canonical(value: str | None, values: tuple[str, ...]) -> str | None:
        key = (value or "").strip().casefold().replace("_", "-")
        return next((item for item in values if item.casefold() == key), None)

    recipe_by_alloy = {alloy: RECIPES[alloy] for alloy in ALLOYS}
    recipe_aliases = {recipe.casefold(): recipe for recipe in RECIPES.values()}
    existing_parts = {
        part.sku_code.casefold(): part
        for part in (await session.scalars(select(Part))).all()
    }
    existing_orders = {
        order.wo_number.casefold()
        for order in (await session.scalars(select(WorkOrder))).all()
    }
    seen_orders: set[str] = set()
    imported = 0
    rejected = []
    for row_number, raw in enumerate(reader, start=2):
        if row_number > MAX_ERP_CSV_ROWS + 1:
            raise HTTPException(status_code=413, detail="CSV exceeds the 10000 row import limit")
        row = {
            key.strip().casefold(): str(value or "").strip()
            for key, value in raw.items() if key is not None
        }
        errors: list[str] = []
        if None in raw:
            errors.append("row has more values than the CSV header")
        if any(value is None for value in raw.values()):
            errors.append("row has fewer values than the CSV header")
        wo_number = row.get("wo_number", "")
        sku_code = row.get("sku_code", "").upper()
        if not wo_number:
            errors.append("wo_number is required")
        elif wo_number.casefold() in seen_orders or wo_number.casefold() in existing_orders:
            errors.append(f"duplicate work-order ID '{wo_number}'")
        quantity_text = row.get("quantity", "")
        try:
            quantity = int(quantity_text)
            if quantity <= 0:
                errors.append("quantity must be greater than zero")
        except (TypeError, ValueError):
            quantity = 0
            errors.append("quantity must be a positive integer")
        alloy = canonical(row.get("alloy_family"), ALLOYS)
        if not alloy:
            errors.append(f"unknown or missing alloy_family '{row.get('alloy_family', '')}'")
        recipe_input = row.get("sintering_recipe_id", "").strip()
        recipe = recipe_aliases.get(recipe_input.casefold()) if recipe_input else None
        if not recipe and alloy:
            recipe = recipe_by_alloy[alloy]
        elif recipe_input and not recipe:
            errors.append(f"unknown sintering_recipe_id '{recipe_input}'")
        if recipe and alloy and recipe != recipe_by_alloy[alloy]:
            errors.append(f"recipe {recipe} is incompatible with alloy {alloy}")
        stage_input = row.get("current_stage", "").strip().casefold().replace("_", " ")
        stage = next((item for item in STAGES if item.casefold() == stage_input), None)
        if not stage:
            errors.append(f"current_stage must be one of: {', '.join(STAGES)}")
        route_input = row.get("process_route", "")
        process_route = None
        if route_input:
            process_route = []
            for value in route_input.split(">"):
                normalized_stage = value.strip().casefold().replace("_", " ")
                matched_stage = next(
                    (item for item in STAGES if item.casefold() == normalized_stage), None
                )
                process_route.append(matched_stage or value.strip())
            invalid_route = (
                any(item not in STAGES for item in process_route)
                or len(set(process_route)) != len(process_route)
                or process_route != sorted(
                    process_route,
                    key=lambda item: STAGES.index(item) if item in STAGES else len(STAGES),
                )
            )
            if invalid_route:
                errors.append("process_route must list unique known stages in order, separated by '>'")
            elif stage and stage not in process_route:
                errors.append(f"current_stage '{stage}' must be present in process_route")
        segment = canonical(row.get("segment"), SEGMENTS)
        if not segment:
            errors.append(f"unknown or missing segment '{row.get('segment', '')}'; choose one of: {', '.join(SEGMENTS)}")
        try:
            due = float(row.get("due_date_hours", ""))
            if not math.isfinite(due):
                raise ValueError
        except (TypeError, ValueError):
            due = 0.0
            errors.append("due_date_hours must be a finite number")
        try:
            priority = int(row.get("priority") or "3")
            if not 1 <= priority <= 5:
                raise ValueError
        except ValueError:
            priority = 3
            errors.append("priority must be an integer from 1 to 5")
        try:
            wip_age = float(row.get("wip_age_hours") or "0")
            if not math.isfinite(wip_age) or wip_age < 0:
                raise ValueError
        except ValueError:
            wip_age = 0.0
            errors.append("wip_age_hours must be a non-negative finite number")
        machining_value = row.get("requires_machining", "true").casefold()
        if machining_value not in {"1", "0", "true", "false", "yes", "no", "y", "n"}:
            errors.append("requires_machining must be true or false")
        requires_machining = machining_value in {"1", "true", "yes", "y"}
        if not sku_code:
            errors.append("sku_code is required")
        existing_part = existing_parts.get(sku_code.casefold())
        if existing_part and not recipe_input:
            recipe = existing_part.sintering_recipe_id
        if existing_part and alloy and existing_part.alloy_family != alloy:
            errors.append(
                f"SKU {sku_code} is registered as {existing_part.alloy_family}, not {alloy}"
            )
        full_route = process_route or tuple(
            item for item in STAGES if requires_machining or item != "CNC Machining"
        )
        cycle_times: dict[str, float] = {}
        for cycle_stage, column in CYCLE_TIME_COLUMNS.items():
            cycle_text = row.get(column, "")
            if not cycle_text:
                if existing_part is None and cycle_stage in full_route:
                    errors.append(f"{column} is required for new SKU {sku_code} because its route includes {cycle_stage}")
                continue
            try:
                cycle_value = float(cycle_text)
                if not math.isfinite(cycle_value) or cycle_value <= 0:
                    raise ValueError
                cycle_times[cycle_stage] = cycle_value
            except (TypeError, ValueError):
                errors.append(f"{column} must be a positive finite number of minutes")
        if existing_part:
            if segment and existing_part.segment != segment:
                errors.append(f"SKU {sku_code} is registered in segment {existing_part.segment}, not {segment}")
            if recipe and existing_part.sintering_recipe_id != recipe:
                errors.append(f"SKU {sku_code} is registered with recipe {existing_part.sintering_recipe_id}, not {recipe}")
            registered_route = tuple(existing_part.process_route or tuple(
                item for item in STAGES
                if existing_part.requires_machining or item != "CNC Machining"
            ))
            if route_input and registered_route != tuple(process_route or ()):
                errors.append(f"SKU {sku_code} has a different registered process_route")
            if "requires_machining" in row and existing_part.requires_machining != requires_machining:
                errors.append(f"SKU {sku_code} has a different registered machining requirement")
            if row.get("tool_id") and existing_part.tool_id != row["tool_id"]:
                errors.append(f"SKU {sku_code} is registered with a different physical tool_id")
            for cycle_stage, cycle_value in cycle_times.items():
                registered = (existing_part.cycle_times_mins or {}).get(cycle_stage)
                if registered is None or abs(float(registered) - cycle_value) > 1e-6:
                    errors.append(f"SKU {sku_code} has a different registered {cycle_stage} cycle time")
        if errors:
            logger.warning("ERP CSV row %d rejected for %s: %s", row_number, wo_number or "<missing ID>", "; ".join(errors))
            rejected.append({"row": row_number, "work_order_id": wo_number or None, "errors": errors})
            continue

        part = existing_part
        if part is None:
            part = Part(
                id=f"erp-part-{uuid.uuid4().hex}",
                sku_code=sku_code,
                name=row.get("part_name") or sku_code,
                segment=segment,
                alloy_family=alloy,
                sintering_recipe_id=recipe,
                cycle_times_mins=cycle_times,
                requires_machining=requires_machining,
                process_route=process_route,
                tool_id=row.get("tool_id") or None,
            )
            session.add(part)
            existing_parts[sku_code.casefold()] = part
        order = WorkOrder(
            id=f"erp-wo-{uuid.uuid4().hex}",
            wo_number=wo_number,
            part_id=part.id,
            quantity=quantity,
            due_date_hours=due,
            priority=priority,
            current_stage=stage,
            status="QUEUED",
            wip_age_hours=wip_age,
        )
        session.add(order)
        seen_orders.add(wo_number.casefold())
        imported += 1

    await session.commit()
    return {"imported": imported, "rejected": len(rejected), "rejected_rows": rejected}


@app.get("/api/flow-board", response_model=FlowBoardResponse, dependencies=[Depends(require_api_access)])
async def flow_board(session: AsyncSession = Depends(get_session)) -> FlowBoardResponse:
    orders = list((await session.scalars(select(WorkOrder))).all())
    resources = list((await session.scalars(select(Resource))).all())
    open_orders = [order for order in orders if order.status != "COMPLETED"]
    total = len(open_orders)
    avg_age = round(sum(order.wip_age_hours for order in open_orders) / max(1, total), 2)
    queues = []
    for stage in STAGES:
        stage_orders = [order for order in orders if order.current_stage == stage and order.status != "COMPLETED"]
        queues.append(StageQueue(
            stage=stage,
            queue_depth=len(stage_orders),
            avg_wip_age_hours=round(
                sum(order.wip_age_hours for order in stage_orders) / max(1, len(stage_orders)), 2
            ),
        ))
    alerts = [
        f"{resource.name} at {resource.plant} is down"
        for resource in resources if resource.status == "DOWN"
    ]
    queue_depths = sorted((queue.queue_depth for queue in queues), reverse=True)
    if queue_depths and queue_depths[0] > 0:
        highest = queue_depths[0]
        for queue in queues:
            if queue.queue_depth == highest and highest >= 20:
                alerts.append(f"{queue.stage} queue has {highest} work orders")
    latest = await session.scalar(
        select(ScheduleVersion).order_by(ScheduleVersion.created_at.desc()).limit(1)
    )
    if latest and latest.bottleneck_resource_id:
        resource = next((item for item in resources if item.id == latest.bottleneck_resource_id), None)
        if resource:
            alerts.append(f"Latest schedule identifies {resource.name} as the active bottleneck")
    return FlowBoardResponse(
        total_wip_orders=total,
        avg_wip_age_hours=avg_age,
        queues=queues,
        active_bottleneck_alerts=alerts,
    )


@app.get("/api/catalog", dependencies=[Depends(require_api_access)])
async def catalog(session: AsyncSession = Depends(get_session)) -> dict:
    """Return the public IDs and labels needed to configure what-if runs."""
    resources = list((await session.scalars(select(Resource).order_by(Resource.stage, Resource.name))).all())
    parts = {part.id: part for part in (await session.scalars(select(Part))).all()}
    orders = list((await session.scalars(select(WorkOrder).order_by(WorkOrder.due_date_hours, WorkOrder.wo_number))).all())
    return {
        "resources": [{
            "id": resource.id,
            "name": resource.name,
            "plant": resource.plant,
            "stage": resource.stage,
            "status": resource.status,
        } for resource in resources],
        "work_orders": [{
            "id": order.id,
            "wo_number": order.wo_number,
            "sku_code": parts[order.part_id].sku_code,
            "stage": order.current_stage,
            "status": order.status,
            "due_date_hours": order.due_date_hours,
            "priority": order.priority,
        } for order in orders if order.status not in ("COMPLETED", "QUALITY_HOLD")],
    }


async def _load_factory(session: AsyncSession):
    resources = list((await session.scalars(select(Resource).order_by(Resource.id))).all())
    parts = list((await session.scalars(select(Part).order_by(Part.sku_code))).all())
    work_orders = list((await session.scalars(select(WorkOrder).order_by(WorkOrder.wo_number))).all())
    if not resources or not parts or not work_orders:
        raise HTTPException(status_code=409, detail="Factory data is empty. Call POST /api/seed first.")
    return resources, parts, work_orders


def _order_specs(work_orders: list[WorkOrder]) -> list[OrderSpec]:
    return [OrderSpec(
        id=order.id,
        wo_number=order.wo_number,
        part_id=order.part_id,
        quantity=order.quantity,
        due_date_hours=order.due_date_hours,
        priority=order.priority,
        current_stage=order.current_stage,
        wip_age_hours=order.wip_age_hours,
        status=order.status,
        locked_resource_id=order.locked_resource_id,
        locked_until_hour=order.locked_until_hour,
    ) for order in work_orders]


def _timeline(result, orders: list[WorkOrder], parts: list[Part], resources: list[Resource]) -> list[dict]:
    order_map = {order.id: order for order in orders}
    part_map = {part.id: part for part in parts}
    resource_map = {resource.id: resource for resource in resources}
    return [{
        "work_order_id": operation.work_order_id,
        "wo_number": order_map[operation.work_order_id].wo_number,
        "sku_code": part_map[order_map[operation.work_order_id].part_id].sku_code,
        "resource_id": operation.resource_id,
        "resource_name": resource_map[operation.resource_id].name,
        "plant": resource_map[operation.resource_id].plant,
        "stage": operation.stage,
        "start_hour": operation.start_hour,
        "end_hour": operation.end_hour,
        "batch_id": operation.batch_id,
        "is_late": operation.is_late,
        "delay_reason": operation.delay_reason,
    } for operation in sorted(result.operations, key=lambda op: (op.start_hour, op.stage, op.work_order_id))]


def _why_late(result, orders: list[WorkOrder]) -> list[dict]:
    order_map = {order.id: order for order in orders}
    return [{
        "work_order_id": order_id,
        "wo_number": order_map[order_id].wo_number,
        "due_date_hours": order_map[order_id].due_date_hours,
        "completion_hours": result.completion_hours[order_id],
        "delay_hours": round(max(0, result.completion_hours[order_id] - order_map[order_id].due_date_hours), 2),
        "priority": order_map[order_id].priority,
        "explanation": result.explanations.get(order_id, "Production capacity and stage precedence"),
    } for order_id in result.late_order_ids]


async def _persist_schedule(session: AsyncSession, result, orders: list[WorkOrder]) -> str:
    version_id = f"sv-{uuid.uuid4().hex}"
    version = ScheduleVersion(
        id=version_id,
        created_at=datetime.now(timezone.utc),
        mode=result.mode,
        total_late_orders=result.metrics["late_orders"],
        avg_wip_age_hours=result.metrics["avg_wip_age_hours"],
        bottleneck_resource_id=result.metrics.get("bottleneck_resource_id"),
        summary_metrics=result.metrics,
    )
    session.add(version)
    session.add_all([ScheduledOperation(
        id=f"op-{uuid.uuid4().hex}",
        schedule_version_id=version_id,
        work_order_id=operation.work_order_id,
        resource_id=operation.resource_id,
        stage=operation.stage,
        start_hour=operation.start_hour,
        end_hour=operation.end_hour,
        batch_id=operation.batch_id,
        is_late=operation.is_late,
        delay_reason=operation.delay_reason,
    ) for operation in result.operations])
    return version_id


def _validate_generated_schedule(result, orders, parts, resources, *, unavailable_resource_ids=None) -> None:
    """Reject solver output before exposing it or persisting a schedule run."""
    try:
        validate_schedule_rows(
            result.operations,
            orders,
            parts,
            resources,
            unavailable_resource_ids=unavailable_resource_ids,
        )
    except (ScheduleValidationError, ValueError, TypeError, KeyError) as exc:
        raise HTTPException(
            status_code=500,
            detail="Generated schedule failed independent validation",
        ) from exc


@app.post("/api/schedule/optimize", dependencies=[Depends(require_api_access)])
async def optimize(
    request: OptimizeRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Save and compare FIFO ERP and optimized CP-SAT schedules."""
    resources, parts, work_orders = await _load_factory(session)
    specs = _order_specs(work_orders)
    part_map = {part.id: part for part in parts}
    try:
        baseline_result, optimized_result = await asyncio.gather(
            asyncio.to_thread(run_baseline, specs, resources, part_map),
            asyncio.to_thread(run_solver, specs, resources, part_map, time_limit_seconds=request.time_limit_seconds),
        )
    except (SchedulingError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    _validate_generated_schedule(baseline_result, specs, parts, resources)
    _validate_generated_schedule(optimized_result, specs, parts, resources)
    baseline_id = await _persist_schedule(session, baseline_result, work_orders)
    optimized_id = await _persist_schedule(session, optimized_result, work_orders)
    await session.commit()

    comparison = {
        "baseline": {**baseline_result.metrics, "schedule_version_id": baseline_id},
        "optimized": {**optimized_result.metrics, "schedule_version_id": optimized_id},
        "delta": {
            "late_orders": optimized_result.metrics["late_orders"] - baseline_result.metrics["late_orders"],
            "avg_wip_age_hours": round(optimized_result.metrics["avg_wip_age_hours"] - baseline_result.metrics["avg_wip_age_hours"], 2),
            "throughput": optimized_result.metrics["throughput"] - baseline_result.metrics["throughput"],
            "furnace_batch_efficiency_pct": round(
                optimized_result.metrics["furnace_batch_efficiency_pct"] - baseline_result.metrics["furnace_batch_efficiency_pct"], 1
            ),
        },
    }
    return {
        "comparison": comparison,
        "gantt": {
            "baseline": _timeline(baseline_result, work_orders, parts, resources),
            "optimized": _timeline(optimized_result, work_orders, parts, resources),
        },
        "why_late": {
            "baseline": _why_late(baseline_result, work_orders),
            "optimized": _why_late(optimized_result, work_orders),
        },
    }


@app.post("/api/schedule/simulate", dependencies=[Depends(require_api_access)])
async def simulate(
    request: ScenarioRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Run a non-persistent what-if scenario and report its impact."""
    resources, parts, work_orders = await _load_factory(session)
    resource_ids = {resource.id for resource in resources}
    order_ids = {order.id for order in work_orders}
    unknown_resources = sorted(set(request.down_resource_ids) - resource_ids)
    unknown_orders = sorted(set(request.rush_order_ids) - order_ids)
    if unknown_resources:
        raise HTTPException(status_code=422, detail=f"Unknown down_resource_ids: {unknown_resources}")
    if unknown_orders:
        raise HTTPException(status_code=422, detail=f"Unknown rush_order_ids: {unknown_orders}")

    original_specs = _order_specs(work_orders)
    rush_ids = set(request.rush_order_ids)
    factor = 1.0 + request.demand_spike_pct / 100.0
    scenario_specs = [OrderSpec(
        id=order.id,
        wo_number=order.wo_number,
        part_id=order.part_id,
        quantity=max(1, math.ceil(order.quantity * factor)),
        due_date_hours=min(order.due_date_hours, 24.0) if order.id in rush_ids else order.due_date_hours,
        priority=5 if order.id in rush_ids else order.priority,
        current_stage=order.current_stage,
        wip_age_hours=order.wip_age_hours,
        status=order.status,
        locked_resource_id=order.locked_resource_id,
        locked_until_hour=order.locked_until_hour,
    ) for order in original_specs]
    part_map = {part.id: part for part in parts}
    try:
        reference, scenario = await asyncio.gather(
            asyncio.to_thread(run_solver, original_specs, resources, part_map, time_limit_seconds=request.time_limit_seconds),
            asyncio.to_thread(
                run_solver, scenario_specs, resources, part_map,
                down_resource_ids=set(request.down_resource_ids),
                time_limit_seconds=request.time_limit_seconds,
            ),
        )
    except (SchedulingError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    _validate_generated_schedule(reference, original_specs, parts, resources)
    _validate_generated_schedule(
        scenario,
        scenario_specs,
        parts,
        resources,
        unavailable_resource_ids=set(request.down_resource_ids),
    )

    original_by_id = {order.id: order for order in original_specs}
    scenario_by_id = {order.id: order for order in scenario_specs}
    due_impact = []
    for order_id in sorted(original_by_id):
        baseline_end = reference.completion_hours.get(order_id)
        scenario_end = scenario.completion_hours.get(order_id)
        if baseline_end is None or scenario_end is None:
            continue
        before_due = original_by_id[order_id].due_date_hours
        after_due = scenario_by_id[order_id].due_date_hours
        delay_before = max(0.0, baseline_end - before_due)
        delay_after = max(0.0, scenario_end - after_due)
        if (order_id in rush_ids) or abs(delay_after - delay_before) >= 0.25 or abs(after_due - before_due) >= 0.25:
            due_impact.append({
                "work_order_id": order_id,
                "wo_number": original_by_id[order_id].wo_number,
                "due_date_before_hours": before_due,
                "due_date_scenario_hours": after_due,
                "completion_before_hours": baseline_end,
                "completion_scenario_hours": scenario_end,
                "completion_delta_hours": round(scenario_end - baseline_end, 2),
                "late_before": delay_before > 0,
                "late_scenario": delay_after > 0,
                "delay_delta_hours": round(delay_after - delay_before, 2),
            })
    return {
        "scenario_inputs": {
            "down_resource_ids": request.down_resource_ids,
            "rush_order_ids": request.rush_order_ids,
            "demand_spike_pct": request.demand_spike_pct,
        },
        "reference_metrics": reference.metrics,
        "scenario_metrics": scenario.metrics,
        "delta": {
            "late_orders": scenario.metrics["late_orders"] - reference.metrics["late_orders"],
            "avg_wip_age_hours": round(scenario.metrics["avg_wip_age_hours"] - reference.metrics["avg_wip_age_hours"], 2),
            "throughput": scenario.metrics["throughput"] - reference.metrics["throughput"],
            "bottleneck_before": reference.metrics.get("bottleneck_resource_id"),
            "bottleneck_after": scenario.metrics.get("bottleneck_resource_id"),
        },
        "due_date_impact": due_impact,
        "why_late": _why_late(scenario, [
            WorkOrder(
                id=spec.id,
                wo_number=spec.wo_number,
                part_id=spec.part_id,
                quantity=spec.quantity,
                due_date_hours=spec.due_date_hours,
                priority=spec.priority,
                current_stage=spec.current_stage,
                status="QUEUED",
                wip_age_hours=spec.wip_age_hours,
            ) for spec in scenario_specs
        ]),
        "gantt": _timeline(scenario, work_orders, parts, resources),
    }
