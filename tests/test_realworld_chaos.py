from __future__ import annotations

import csv
import io
import random
import time
from types import SimpleNamespace

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from domain import ALLOYS, STAGES, OrderSpec
from factory_validation import FactoryDataError, validate_factory_data
from main import app
from seed import RECIPES, make_parts, make_resources
from solver import solve
from validator import ScheduleValidationError, validate_schedule, validate_schedule_rows


def _parts_and_resources():
    rng = random.Random(702)
    parts = make_parts(rng)
    return {part.id: part for part in parts}, make_resources()


def _order(part, index: int, *, stage="Molding", status="QUEUED", due=160, lock=None, lock_until=0, plant=None, quantity=10):
    return OrderSpec(
        id=f"chaos-{index:04d}",
        wo_number=f"CHAOS-WO-{index:04d}",
        part_id=part.id,
        quantity=quantity,
        due_date_hours=float(due),
        priority=(index % 5) + 1,
        current_stage=stage,
        wip_age_hours=float(index % 72),
        status=status,
        locked_resource_id=lock,
        locked_until_hour=float(lock_until),
        plant=plant,
    )


def _persisted_rows(result):
    return [SimpleNamespace(
        id=f"raw-{index}",
        work_order_id=op.work_order_id,
        resource_id=op.resource_id,
        stage=op.stage,
        start_hour=op.start_hour,
        end_hour=op.end_hour,
        batch_id=op.batch_id,
        is_late=op.is_late,
        delay_reason=op.delay_reason,
    ) for index, op in enumerate(result.operations)]


def _assert_independently_feasible(result, orders, parts, resources):
    validate_schedule_rows(_persisted_rows(result), orders, list(parts.values()), resources)


def test_brownfield_wip_resumes_locked_orders_and_excludes_quality_hold():
    parts, resources = _parts_and_resources()
    source = list(parts.values())
    orders = []
    for index in range(30):
        orders.append(_order(source[index], index, stage="Sintering"))
    locked_parts = [part for part in source if part.requires_machining]
    for index in range(30, 45):
        orders.append(_order(
            locked_parts[index - 30], index, stage="CNC Machining", lock="CNC-3", lock_until=4
        ))
    for index in range(45, 55):
        orders.append(_order(source[index % len(source)], index, stage="Molding", status="QUALITY_HOLD"))
    for index in range(55, 100):
        part = source[index % len(source)]
        stage = STAGES[index % len(STAGES)]
        if stage == "CNC Machining" and not part.requires_machining:
            stage = "Finishing"
        orders.append(_order(part, index, stage=stage))

    result = solve(orders, resources, parts, time_limit_seconds=1.0)
    scheduled_ids = {op.work_order_id for op in result.operations}
    held_ids = {order.id for order in orders if order.status == "QUALITY_HOLD"}
    assert not (scheduled_ids & held_ids)
    cnc_by_order = {
        op.work_order_id: op for op in result.operations if op.stage == "CNC Machining"
    }
    for order in orders:
        if order.locked_resource_id:
            assert cnc_by_order[order.id].resource_id == "CNC-3"
            assert cnc_by_order[order.id].start_hour >= 4
    _assert_independently_feasible(result, orders, parts, resources)


def test_shared_physical_mold_cannot_run_in_two_presses():
    parts, resources = _parts_and_resources()
    source = list(parts.values())[:10]
    for part in source:
        part.tool_id = "MOLD-TOOL-SHARED-17"
    orders = [_order(part, index, due=500) for index, part in enumerate(source)]

    result = solve(orders, resources, parts, time_limit_seconds=1.0)
    molding = [op for op in result.operations if op.stage == "Molding"]
    assert len(molding) == 10
    _assert_independently_feasible(result, orders, parts, resources)


def test_part_specific_route_skips_unneeded_machining_and_validates():
    parts, resources = _parts_and_resources()
    part = list(parts.values())[0]
    part.process_route = ["Molding", "Debinding", "Sintering", "Finishing"]
    order = _order(part, 701, due=500)

    result = solve([order], resources, parts, time_limit_seconds=1.0)

    assert [op.stage for op in sorted(result.operations, key=lambda op: op.start_hour)] == [
        "Molding", "Debinding", "Sintering", "Finishing",
    ]
    _assert_independently_feasible(result, [order], parts, resources)


def test_order_plant_prevents_cross_plant_stage_assignments():
    parts, resources = _parts_and_resources()
    part = next(part for part in parts.values() if part.alloy_family == "MIM-17-4PH")
    order = _order(part, 702, due=500, plant="Hoskote")

    result = solve([order], resources, parts, time_limit_seconds=1.0)

    assert result.operations
    plants = {next(resource for resource in resources if resource.id == op.resource_id).plant for op in result.operations}
    assert plants == {"Hoskote"}
    _assert_independently_feasible(result, [order], parts, resources)


def test_oversized_lot_is_rejected_before_debinding_capacity_is_violated():
    parts, resources = _parts_and_resources()
    for resource in resources:
        resource.blackout_windows = []
    part = next(part for part in parts.values() if part.alloy_family == "MIM-17-4PH")
    order = _order(part, 703, due=500, plant="Hoskote", quantity=500)
    with pytest.raises(FactoryDataError, match="exceeds the largest compatible debinding vessel"):
        validate_factory_data(resources, list(parts.values()), [order])


def test_independent_validator_rejects_tampered_schedule_rows():
    parts, resources = _parts_and_resources()
    source = list(parts.values())[:4]
    for part in source:
        part.tool_id = "MOLD-TOOL-RAW-CHECK"
    orders = [_order(part, index, due=500) for index, part in enumerate(source)]
    result = solve(orders, resources, parts, time_limit_seconds=1.0)
    raw_rows = _persisted_rows(result)
    molding_rows = sorted(
        (row for row in raw_rows if row.stage == "Molding"),
        key=lambda row: row.start_hour,
    )
    assert len(molding_rows) >= 2
    # Deliberately lie in the schedule's non-authoritative solver flag fields;
    # the validator must still detect a physical tool collision from raw rows.
    shift = molding_rows[0].start_hour - molding_rows[1].start_hour
    molding_rows[1].start_hour += shift
    molding_rows[1].end_hour += shift
    molding_rows[1].is_late = False
    with pytest.raises(ScheduleValidationError, match="physical mold MOLD-TOOL-RAW-CHECK"):
        validate_schedule_rows(raw_rows, orders, list(parts.values()), resources)


def test_shifts_and_furnace_maintenance_are_respected():
    parts, resources = _parts_and_resources()
    # Planning origin is Monday 00:00. These windows encode an 8h night
    # shutdown, Sunday off, and a scheduled thermal-furnace maintenance block.
    for resource in resources:
        if resource.stage in {"CNC Machining", "Finishing"}:
            resource.blackout_windows = [[0, 8], [16, 24], [32, 40], [120, 168]]
        elif resource.stage == "Sintering":
            resource.blackout_windows = [[0, 20], [120, 144]]
    orders = [
        _order(list(parts.values())[index], index, stage="CNC Machining", due=300)
        for index in range(8)
    ]
    orders.extend(
        _order(list(parts.values())[index + 8], index + 8, stage="Sintering", due=300)
        for index in range(8)
    )

    result = solve(orders, resources, parts, time_limit_seconds=1.0)
    _assert_independently_feasible(result, orders, parts, resources)
    assert any(
        resource.stage == "Sintering" and resource.blackout_windows
        for resource in resources
    )


def test_past_due_storm_with_two_furnaces_down_still_returns_feasible_schedule():
    parts, resources = _parts_and_resources()
    recipes = list(RECIPES.values())
    furnace_ids = [resource.id for resource in resources if resource.stage == "Sintering"]
    for resource_id in furnace_ids[:2]:
        next(resource for resource in resources if resource.id == resource_id).status = "DOWN"
    # The two surviving furnaces are qualified for all four recipe families.
    for resource_id in furnace_ids[2:]:
        furnace = next(resource for resource in resources if resource.id == resource_id)
        furnace.recipe_compatibility = recipes
        furnace.alloy_compatibility = list(ALLOYS)
        furnace.capacity_units = 1000
    storm_parts = [list(parts.values())[index] for index in range(30)]
    orders = [_order(part, index, due=-24) for index, part in enumerate(storm_parts)]

    result = solve(
        orders,
        resources,
        parts,
        down_resource_ids=set(furnace_ids[:2]),
        time_limit_seconds=1.0,
    )
    assert result.metrics["cp_sat_status"] != "INFEASIBLE"
    _assert_independently_feasible(result, orders, parts, resources)


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def csv_import_client():
    from database import init_db

    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        assert (await client.post("/api/seed")).status_code == 200
        yield client


async def test_dirty_erp_csv_import_sanitizes_rows_and_optimization_continues(csv_import_client, caplog):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "wo_number", "sku_code", "plant", "part_name", "segment", "alloy_family",
        "sintering_recipe_id", "quantity", "due_date_hours", "priority", "current_stage", "process_route",
        "molding_cycle_mins", "debinding_cycle_mins", "sintering_cycle_mins",
        "cnc_machining_cycle_mins", "finishing_cycle_mins",
    ])
    writer.writerow([
        "ERP-CHAOS-001", " dirty-sku-01 ", " HOSKOTE ", "Imported part", "aerospace",
        " mim-17-4ph ", "", "5", "-24", "5", "Molding",
        "Molding > Debinding > Sintering > Finishing", "2", "390", "600", "", "1.2",
    ])
    writer.writerow([
        "ERP-CHAOS-001", "DIRTY-SKU-02", "Hoskote", "Duplicate", "Aerospace",
        "MIM-17-4PH", "", "4", "24", "3", "Molding", "", "", "", "", "", "",
    ])
    writer.writerow([
        "ERP-CHAOS-002", "DIRTY-SKU-03", "Hoskote", "Zero quantity", "Medical",
        "MIM-316L", "", "0", "24", "3", "Molding", "", "", "", "", "", "",
    ])
    writer.writerow([
        "ERP-CHAOS-003", "DIRTY-SKU-04", "Hoskote", "Missing alloy", "Medical",
        "", "", "2", "24", "3", "Molding", "", "", "", "", "", "",
    ])

    response = await csv_import_client.post(
        "/api/import/erp-csv",
        content=output.getvalue(),
        headers={"Content-Type": "text/csv"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["imported"] == 1
    assert payload["rejected"] == 3
    assert any("duplicate work-order ID" in error for item in payload["rejected_rows"] for error in item["errors"])
    assert any("quantity must be greater than zero" in error for item in payload["rejected_rows"] for error in item["errors"])
    assert "ERP CSV row" in caplog.text

    optimized = await csv_import_client.post(
        "/api/schedule/optimize",
        json={"time_limit_seconds": 1.0},
    )
    assert optimized.status_code == 200, optimized.text
    schedule_version_id = optimized.json()["comparison"]["optimized"]["schedule_version_id"]
    assert optimized.json()["gantt"]["optimized"]
    from database import SessionLocal

    async with SessionLocal() as session:
        await validate_schedule(session, schedule_version_id)


async def test_erp_csv_requires_explicit_classification_and_unique_headers(csv_import_client):
    missing_segment = (
        "wo_number,sku_code,plant,segment,alloy_family,quantity,due_date_hours,current_stage\n"
        "ERP-CHAOS-004,NO-SEGMENT,Hoskote,,MIM-17-4PH,1,24,Molding\n"
    )
    response = await csv_import_client.post(
        "/api/import/erp-csv", content=missing_segment,
        headers={"Content-Type": "text/csv"},
    )
    assert response.status_code == 200
    assert response.json()["imported"] == 0
    assert any("segment" in error for error in response.json()["rejected_rows"][0]["errors"])

    duplicate_header = (
        "wo_number,sku_code,plant,segment,alloy_family,quantity,due_date_hours,current_stage,SKU_CODE\n"
        "ERP-CHAOS-005,DUP-HEADER,Hoskote,Aerospace,MIM-17-4PH,1,24,Molding,DUP-HEADER\n"
    )
    response = await csv_import_client.post(
        "/api/import/erp-csv", content=duplicate_header,
        headers={"Content-Type": "text/csv"},
    )
    assert response.status_code == 422
    assert "unique" in response.json()["detail"]

    no_cycle_times = (
        "wo_number,sku_code,plant,segment,alloy_family,quantity,due_date_hours,current_stage\n"
        "ERP-CHAOS-006,NO-CYCLE-TIMES,Hoskote,Aerospace,MIM-17-4PH,1,24,Molding\n"
    )
    response = await csv_import_client.post(
        "/api/import/erp-csv", content=no_cycle_times,
        headers={"Content-Type": "text/csv"},
    )
    assert response.status_code == 200
    assert response.json()["imported"] == 0
    errors = response.json()["rejected_rows"][0]["errors"]
    assert any("molding_cycle_mins is required" in error for error in errors)


def test_thousand_order_45_machine_scale_is_feasible_and_improves_both_kpis():
    rng = random.Random(1000)
    parts_list = make_parts(rng)
    parts = {part.id: part for part in parts_list}
    resources = make_resources()
    # Expand to 45 heterogeneous stations while retaining qualified furnaces.
    templates = [resource for resource in resources if resource.stage in {"Molding", "CNC Machining", "Finishing"}]
    for index in range(27):
        source = templates[index % len(templates)]
        resources.append(type(source)(
            id=f"SCALE-{index:02d}",
            name=f"SCALE-{index:02d}",
            plant=source.plant,
            stage=source.stage,
            capacity_units=source.capacity_units,
            alloy_compatibility=list(source.alloy_compatibility),
            recipe_compatibility=list(source.recipe_compatibility),
            setup_changeover_mins=source.setup_changeover_mins,
            blackout_windows=[],
            status="ACTIVE",
        ))
    assert len(resources) == 45
    common_part = parts_list[0]
    for furnace in resources:
        if furnace.stage == "Sintering":
            furnace.recipe_compatibility = [common_part.sintering_recipe_id]
            furnace.alloy_compatibility = [common_part.alloy_family]
    for part in parts_list:
        part.tool_id = None
    orders = [
        OrderSpec(
            id=f"scale-{index:04d}",
            wo_number=f"SCALE-WO-{index:04d}",
            part_id=common_part.id,
            quantity=100 if index < 500 else 1,
            due_date_hours=-24.0,
            priority=1 if index < 500 else 5,
            current_stage="Molding",
            wip_age_hours=float(index % 40),
        )
        for index in range(1000)
    ]

    started = time.perf_counter()
    optimized = solve(orders, resources, parts, time_limit_seconds=5.0)
    elapsed = time.perf_counter() - started
    baseline = __import__("baseline").schedule(orders, resources, parts)
    assert elapsed < 8.0, f"Large-scale solve took {elapsed:.2f}s"
    assert optimized.metrics["cp_sat_status"] != "INFEASIBLE"
    _assert_independently_feasible(optimized, orders, parts, resources)
    _assert_independently_feasible(baseline, orders, parts, resources)
    assert optimized.metrics["weighted_tardiness_hours"] < baseline.metrics["weighted_tardiness_hours"]
    assert optimized.metrics["avg_wip_age_hours"] < baseline.metrics["avg_wip_age_hours"]
