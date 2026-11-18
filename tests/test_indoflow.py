from __future__ import annotations

from collections import defaultdict

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from database import SessionLocal, init_db
from main import app
from models import Part, Resource, WorkOrder


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def seeded_optimized_run():
    """Run the requested API flow once against the isolated test database."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        seeded = await client.post("/api/seed")
        assert seeded.status_code == 200, seeded.text
        board = await client.get("/api/flow-board")
        assert board.status_code == 200, board.text
        optimized = await client.post(
            "/api/schedule/optimize",
            json={"time_limit_seconds": 5.0},
        )
        assert optimized.status_code == 200, optimized.text
        simulation = await client.post(
            "/api/schedule/simulate",
            json={"down_resource_ids": ["CNC-3"], "time_limit_seconds": 5.0},
        )
        assert simulation.status_code == 200, simulation.text

        async with SessionLocal() as session:
            resources = list((await session.scalars(select(Resource))).all())
            parts = list((await session.scalars(select(Part))).all())
            orders = list((await session.scalars(select(WorkOrder))).all())

        yield {
            "seed": seeded.json(),
            "board": board.json(),
            "optimized": optimized.json(),
            "simulation": simulation.json(),
            "resources": {resource.id: resource for resource in resources},
            "parts": {part.id: part for part in parts},
            "orders": {order.id: order for order in orders},
        }


async def test_end_to_end_api_flow_returns_valid_json(seeded_optimized_run):
    run = seeded_optimized_run
    assert run["seed"]["work_orders"] == 150
    assert run["board"]["total_wip_orders"] == 150
    assert run["optimized"]["comparison"]["baseline"]["schedule_version_id"]
    assert run["optimized"]["comparison"]["optimized"]["schedule_version_id"]
    assert run["simulation"]["scenario_inputs"]["down_resource_ids"] == ["CNC-3"]
    assert run["simulation"]["gantt"]


async def test_optimized_schedule_obeys_stage_precedence(seeded_optimized_run):
    operations = seeded_optimized_run["optimized"]["gantt"]["optimized"]
    stage_order = ["Molding", "Debinding", "Sintering", "CNC Machining", "Finishing"]
    by_order: dict[str, list[dict]] = defaultdict(list)
    for operation in operations:
        by_order[operation["work_order_id"]].append(operation)

    for work_order_id, order_operations in by_order.items():
        by_stage = {operation["stage"]: operation for operation in order_operations}
        present_stages = [stage for stage in stage_order if stage in by_stage]
        assert present_stages == [
            operation["stage"] for operation in sorted(
                order_operations, key=lambda operation: stage_order.index(operation["stage"])
            )
        ], f"Stages are out of route order for {work_order_id}"
        for previous, following in zip(present_stages, present_stages[1:]):
            assert by_stage[previous]["end_hour"] <= by_stage[following]["start_hour"], (
                f"{work_order_id}: {previous} must finish before {following} starts"
            )


async def test_sintering_batches_respect_recipe_furnace_and_capacity(seeded_optimized_run):
    run = seeded_optimized_run
    sintering = [
        operation for operation in run["optimized"]["gantt"]["optimized"]
        if operation["stage"] == "Sintering"
    ]
    batches: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for operation in sintering:
        batches[(operation["resource_id"], operation["batch_id"])].append(operation)

    for (resource_id, batch_id), batch in batches.items():
        furnace = run["resources"][resource_id]
        recipe_ids = {
            run["parts"][run["orders"][op["work_order_id"]].part_id].sintering_recipe_id
            for op in batch
        }
        assert len(recipe_ids) == 1, f"Batch {batch_id} mixes sintering recipes"
        recipe_id = next(iter(recipe_ids))
        assert recipe_id in furnace.recipe_compatibility
        total_units = sum(run["orders"][op["work_order_id"]].quantity for op in batch)
        assert total_units <= furnace.capacity_units, f"Batch {batch_id} exceeds furnace capacity"
        assert len({(op["start_hour"], op["end_hour"]) for op in batch}) == 1

    by_furnace: dict[str, list[tuple[float, float, int, str]]] = defaultdict(list)
    for (resource_id, batch_id), batch in batches.items():
        load = sum(run["orders"][op["work_order_id"]].quantity for op in batch)
        by_furnace[resource_id].append((batch[0]["start_hour"], batch[0]["end_hour"], load, batch_id))
    for resource_id, furnace_batches in by_furnace.items():
        capacity = run["resources"][resource_id].capacity_units
        events = []
        for start, end, load, batch_id in furnace_batches:
            events.extend(((start, 1, load, batch_id), (end, -1, load, batch_id)))
        active_load = 0
        active_batches: set[str] = set()
        for _, event_type, load, batch_id in sorted(events, key=lambda event: (event[0], event[1])):
            if event_type == -1:
                active_load -= load
                active_batches.remove(batch_id)
            else:
                active_load += load
                active_batches.add(batch_id)
            assert active_load <= capacity, f"Furnace {resource_id} exceeds capacity while active"


async def test_discrete_machines_never_overlap(seeded_optimized_run):
    operations = seeded_optimized_run["optimized"]["gantt"]["optimized"]
    discrete_stages = {"CNC Machining", "Molding", "Finishing"}
    by_resource: dict[str, list[dict]] = defaultdict(list)
    for operation in operations:
        if operation["stage"] in discrete_stages:
            by_resource[operation["resource_id"]].append(operation)

    for resource_id, assigned in by_resource.items():
        ordered = sorted(assigned, key=lambda operation: operation["start_hour"])
        for previous, following in zip(ordered, ordered[1:]):
            assert previous["end_hour"] <= following["start_hour"], (
                f"Resource {resource_id} overlaps {previous['work_order_id']} and {following['work_order_id']}"
            )


async def test_optimized_schedule_strictly_improves_a_seeded_kpi(seeded_optimized_run):
    comparison = seeded_optimized_run["optimized"]["comparison"]
    baseline = comparison["baseline"]
    optimized = comparison["optimized"]
    assert optimized["cp_sat_status"] != "INFEASIBLE"
    assert optimized["solver_status"] != "INFEASIBLE"
    assert (
        optimized["late_orders"] < baseline["late_orders"]
        or optimized["avg_wip_age_hours"] < baseline["avg_wip_age_hours"]
    ), f"No strict KPI improvement: baseline={baseline}, optimized={optimized}"


async def test_machine_downtime_reroutes_jobs_away_from_cnc3(seeded_optimized_run):
    run = seeded_optimized_run
    before = run["optimized"]["gantt"]["optimized"]
    after = run["simulation"]["gantt"]
    before_resource_by_order = {
        operation["work_order_id"]: operation["resource_id"] for operation in before
        if operation["stage"] == "CNC Machining"
    }
    before_cnc3 = {
        order_id for order_id, resource_id in before_resource_by_order.items() if resource_id == "CNC-3"
    }
    after_resource_by_order = {
        operation["work_order_id"]: operation["resource_id"] for operation in after
        if operation["stage"] == "CNC Machining"
    }
    assert before_cnc3, "The seeded nominal schedule should exercise CNC-3"
    assert before_cnc3 <= after_resource_by_order.keys(), "Affected CNC jobs must remain scheduled"
    assert all(resource_id != "CNC-3" for resource_id in after_resource_by_order.values())
    assert all(
        after_resource_by_order[order_id] != before_resource_by_order[order_id]
        for order_id in before_cnc3
    ), "Jobs assigned to CNC-3 before downtime must be moved to an available CNC"
