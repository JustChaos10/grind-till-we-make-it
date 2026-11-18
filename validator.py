"""Independent physical feasibility checks for persisted schedule rows.

This module intentionally ignores solver status flags and summary metrics. It
reconstructs material and resource constraints from operations and master data.
All schedule hours are measured from the planning origin (hour zero).
"""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain import STAGES, route_for
from models import Part, Resource, ScheduledOperation, ScheduleVersion, WorkOrder


class ScheduleValidationError(AssertionError):
    """A persisted schedule violates a physical production constraint."""


def _overlaps(start_a: float, end_a: float, start_b: float, end_b: float) -> bool:
    return start_a < end_b - 1e-9 and start_b < end_a - 1e-9


def validate_schedule_rows(
    operations,
    work_orders,
    parts,
    resources,
    *,
    current_time: float = 0.0,
) -> None:
    """Raise ``ScheduleValidationError`` if any operation is physically invalid.

    ``operations`` should be raw ``ScheduledOperation`` rows for one schedule
    version. Related work orders, parts, and resources are supplied separately
    so callers can use any database/session without coupling this validator to
    solver internals.
    """
    if current_time < 0:
        raise ValueError("current_time must use non-negative hours from the planning origin")
    order_by_id = {order.id: order for order in work_orders}
    part_by_id = {part.id: part for part in parts}
    resource_by_id = {resource.id: resource for resource in resources}
    ops_by_order: dict[str, list] = defaultdict(list)
    ops_by_resource: dict[str, list] = defaultdict(list)
    tool_ops: dict[str, list] = defaultdict(list)
    furnace_batches: dict[tuple[str, str], list] = defaultdict(list)

    for op in operations:
        if op.work_order_id not in order_by_id:
            raise ScheduleValidationError(f"Operation {op.id} references unknown work order {op.work_order_id}")
        if op.resource_id not in resource_by_id:
            raise ScheduleValidationError(f"Operation {op.id} references unknown resource {op.resource_id}")
        if op.stage not in STAGES:
            raise ScheduleValidationError(f"Operation {op.id} has unknown stage {op.stage}")
        if op.start_hour < current_time - 1e-9:
            raise ScheduleValidationError(
                f"Operation {op.id} starts at {op.start_hour}, before current_time {current_time}"
            )
        if op.end_hour <= op.start_hour:
            raise ScheduleValidationError(f"Operation {op.id} has a non-positive duration")
        resource = resource_by_id[op.resource_id]
        order = order_by_id[op.work_order_id]
        part = part_by_id[order.part_id]
        if resource.stage != op.stage:
            raise ScheduleValidationError(
                f"Operation {op.id} uses {resource.id} ({resource.stage}) for {op.stage}"
            )
        if resource.status != "ACTIVE":
            raise ScheduleValidationError(f"Operation {op.id} uses inactive resource {resource.id}")
        if op.stage not in route_for(order, part.requires_machining):
            raise ScheduleValidationError(
                f"Operation {op.id} schedules {op.stage} before/currently outside {order.current_stage} route"
            )
        if part.alloy_family not in (resource.alloy_compatibility or []):
            raise ScheduleValidationError(f"{resource.id} cannot process alloy {part.alloy_family}")

        for blackout_start, blackout_end in getattr(resource, "blackout_windows", None) or []:
            if _overlaps(op.start_hour, op.end_hour, float(blackout_start), float(blackout_end)):
                raise ScheduleValidationError(
                    f"{op.stage} operation {op.id} overlaps {resource.id} blackout "
                    f"[{blackout_start}, {blackout_end}]"
                )

        ops_by_order[op.work_order_id].append(op)
        ops_by_resource[op.resource_id].append(op)
        if op.stage == "Molding" and part.tool_id:
            tool_ops[part.tool_id].append(op)
        if op.stage == "Sintering":
            batch_id = op.batch_id or op.work_order_id
            furnace_batches[(op.resource_id, batch_id)].append(op)

    for order in work_orders:
        scheduled = ops_by_order.get(order.id, [])
        if order.status.upper() in {"COMPLETED", "QUALITY_HOLD"}:
            if scheduled:
                raise ScheduleValidationError(f"Excluded work order {order.id} has scheduled operations")
            continue
        part = part_by_id[order.part_id]
        expected_route = list(route_for(order, part.requires_machining))
        ordered = sorted(scheduled, key=lambda op: STAGES.index(op.stage))
        actual_route = [op.stage for op in ordered]
        if actual_route != expected_route:
            raise ScheduleValidationError(
                f"Work order {order.id} route mismatch: expected {expected_route}, got {actual_route}"
            )
        for previous, following in zip(ordered, ordered[1:]):
            if previous.end_hour > following.start_hour + 1e-9:
                raise ScheduleValidationError(
                    f"Work order {order.id} stage order violation: "
                    f"{previous.stage} ends at {previous.end_hour}, {following.stage} starts at {following.start_hour}"
                )
        if order.locked_resource_id:
            current_operations = [op for op in scheduled if op.stage == order.current_stage]
            for op in current_operations:
                if op.resource_id != order.locked_resource_id:
                    raise ScheduleValidationError(
                        f"Locked work order {order.id} must remain on {order.locked_resource_id}"
                    )
                if op.start_hour + 1e-9 < order.locked_until_hour:
                    raise ScheduleValidationError(
                        f"Locked work order {order.id} starts before lock expires at {order.locked_until_hour}"
                    )

    for tool_id, assigned in tool_ops.items():
        _validate_non_overlap(assigned, f"physical mold {tool_id}")

    discrete_stages = {"Molding", "CNC Machining", "Finishing"}
    for resource_id, assigned in ops_by_resource.items():
        resource = resource_by_id[resource_id]
        assigned.sort(key=lambda op: (op.start_hour, op.end_hour, op.id))
        if resource.stage in discrete_stages:
            for previous, following in zip(assigned, assigned[1:]):
                if previous.end_hour > following.start_hour + 1e-9:
                    raise ScheduleValidationError(
                        f"Resource {resource_id} overlaps operations {previous.id} and {following.id}"
                    )
                previous_part = part_by_id[order_by_id[previous.work_order_id].part_id]
                next_part = part_by_id[order_by_id[following.work_order_id].part_id]
                if (
                    previous_part.id != next_part.id
                    and following.start_hour + 1e-9
                    < previous.end_hour + resource.setup_changeover_mins / 60.0
                ):
                    raise ScheduleValidationError(
                        f"Resource {resource_id} lacks setup gap after {previous.id} before {following.id}"
                    )

    for (resource_id, batch_id), batch in furnace_batches.items():
        furnace = resource_by_id[resource_id]
        members = [order_by_id[op.work_order_id] for op in batch]
        member_parts = [part_by_id[order.part_id] for order in members]
        recipes = {part.sintering_recipe_id for part in member_parts}
        if len(recipes) != 1:
            raise ScheduleValidationError(f"Furnace batch {batch_id} mixes recipes {sorted(recipes)}")
        recipe = next(iter(recipes))
        if furnace.recipe_compatibility and recipe not in furnace.recipe_compatibility:
            raise ScheduleValidationError(f"Furnace {resource_id} is incompatible with recipe {recipe}")
        load = sum(order.quantity for order in members)
        if load > furnace.capacity_units:
            raise ScheduleValidationError(
                f"Furnace batch {batch_id} load {load} exceeds capacity {furnace.capacity_units}"
            )
        windows = {(op.start_hour, op.end_hour) for op in batch}
        if len(windows) != 1:
            raise ScheduleValidationError(f"Furnace batch {batch_id} is split across different run intervals")

    by_furnace_runs: dict[str, list] = defaultdict(list)
    for (resource_id, _batch_id), batch in furnace_batches.items():
        # Every member row in one batch describes the same physical run. Count
        # that interval once; comparing member rows to each other would treat
        # a valid multi-order furnace load as a collision.
        by_furnace_runs[resource_id].append(batch[0])
    for resource_id, runs in by_furnace_runs.items():
        _validate_non_overlap(runs, f"furnace {resource_id}")


def _validate_non_overlap(operations, label: str) -> None:
    ordered = sorted(operations, key=lambda op: (op.start_hour, op.end_hour, op.id))
    for previous, following in zip(ordered, ordered[1:]):
        if previous.end_hour > following.start_hour + 1e-9:
            raise ScheduleValidationError(
                f"{label} overlaps operations {previous.id} and {following.id}"
            )


async def validate_schedule(
    session: AsyncSession,
    schedule_version_id: str,
    *,
    current_time: float = 0.0,
) -> None:
    """Load raw persisted rows for one version and validate without solver flags."""
    version = await session.get(ScheduleVersion, schedule_version_id)
    if version is None:
        raise ScheduleValidationError(f"Unknown schedule version {schedule_version_id}")
    operations = list((await session.scalars(
        select(ScheduledOperation).where(ScheduledOperation.schedule_version_id == schedule_version_id)
    )).all())
    orders = list((await session.scalars(select(WorkOrder))).all())
    parts = list((await session.scalars(select(Part))).all())
    resources = list((await session.scalars(select(Resource))).all())
    validate_schedule_rows(operations, orders, parts, resources, current_time=current_time)
