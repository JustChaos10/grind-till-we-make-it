"""FIFO-style ERP baseline: no grouped furnace runs and no CNC sequencing."""

from __future__ import annotations

import math

from domain import OperationResult, OrderSpec, duration_ticks, eligible_resources, hours_to_ticks, route_for, ticks_to_hours
from schedule_utils import ScheduleResult, calculate_metrics


def schedule(orders: list[OrderSpec], resources, parts_by_id: dict, *, down_resource_ids: set[str] | None = None) -> ScheduleResult:
    down = down_resource_ids or set()
    orders = [order for order in orders if order.status.upper() not in {"COMPLETED", "QUALITY_HOLD"}]
    usable_resources = [
        resource for resource in resources
        if resource.status == "ACTIVE" and resource.id not in down
    ]
    free_at: dict[str, int] = {resource.id: 0 for resource in usable_resources}
    last_part: dict[str, str] = {}
    tool_free_at: dict[str, int] = {}
    for order in orders:
        if order.locked_resource_id:
            free_at[order.locked_resource_id] = max(
                free_at.get(order.locked_resource_id, 0), hours_to_ticks(order.locked_until_hour)
            )
    operations: list[OperationResult] = []
    order_stage_ops: dict[str, list[OperationResult]] = {}
    batch_counter = 0

    # FIFO retains WO creation order. The baseline sends each work order
    # through sintering alone, so compatible furnace capacity stays unused.
    for order in sorted(orders, key=lambda item: item.wo_number):
        part = parts_by_id[order.part_id]
        ready = 0
        order_stage_ops[order.id] = []
        for stage in route_for(order, part.requires_machining, getattr(part, "process_route", None)):
            candidates = eligible_resources(usable_resources, part, stage)
            if stage == order.current_stage and order.locked_resource_id:
                candidates = [resource for resource in candidates if resource.id == order.locked_resource_id]
            if not candidates:
                reason = (
                    f"locked resource {order.locked_resource_id} is unavailable"
                    if stage == order.current_stage and order.locked_resource_id
                    else "No active compatible resource"
                )
                raise ValueError(f"{reason} for {order.wo_number} at {stage}")
            duration = duration_ticks(order, part, stage)
            choices: list[tuple[int, str, int]] = []
            for resource in candidates:
                setup = 0
                if (
                    stage in {"Molding", "CNC Machining", "Finishing"}
                    and resource.id in last_part
                    and last_part[resource.id] != part.id
                ):
                    setup = math.ceil(resource.setup_changeover_mins / 15)
                start = max(ready, free_at[resource.id] + setup)
                if stage == order.current_stage:
                    start = max(start, hours_to_ticks(order.locked_until_hour))
                if stage == "Molding" and part.tool_id:
                    start = max(start, tool_free_at.get(part.tool_id, 0))
                start = _next_open_tick(start, duration, resource)
                choices.append((start, resource.id, setup))
            start, resource_id, setup = min(choices)
            end = start + duration
            free_at[resource_id] = end
            if stage in {"Molding", "CNC Machining", "Finishing"}:
                last_part[resource_id] = part.id
            if stage == "Molding" and part.tool_id:
                tool_free_at[part.tool_id] = end
            if stage == "Sintering":
                batch_counter += 1
                batch_id = f"ERP-SINGLE-{batch_counter:04d}"
            else:
                batch_id = None
            reason = None
            if start > ready:
                resource = next(item for item in candidates if item.id == resource_id)
                if stage == "CNC Machining":
                    reason = f"Downstream {resource.name} setup queue"
                elif stage == "Sintering":
                    reason = f"Single-order furnace queue on {resource.name}"
                else:
                    reason = f"Queue on {stage} resource {resource.name}"
            op = OperationResult(
                work_order_id=order.id,
                resource_id=resource_id,
                stage=stage,
                start_hour=ticks_to_hours(start),
                end_hour=ticks_to_hours(end),
                batch_id=batch_id,
                delay_reason=reason,
            )
            operations.append(op)
            order_stage_ops[order.id].append(op)
            ready = end

    metrics, late_ids, completions = calculate_metrics(orders, resources, operations)
    late_set = set(late_ids)
    explanations = {}
    for order in orders:
        is_late = order.id in late_set
        for op in order_stage_ops.get(order.id, []):
            op.is_late = is_late
        if is_late:
            causes = [op.delay_reason for op in order_stage_ops[order.id] if op.delay_reason]
            explanations[order.id] = causes[-1] if causes else "FIFO queue and sequential stage processing"
    return ScheduleResult("NAIVE_ERP", operations, metrics, late_ids, completions, explanations)


def _next_open_tick(start: int, duration: int, resource) -> int:
    """Move an uninterruptible operation past resource blackout windows."""
    windows = sorted(getattr(resource, "blackout_windows", None) or [])
    while True:
        moved = False
        for blackout_start, blackout_end in windows:
            blackout_start_tick = hours_to_ticks(float(blackout_start))
            blackout_end_tick = hours_to_ticks(float(blackout_end))
            if start < blackout_end_tick and start + duration > blackout_start_tick:
                start = blackout_end_tick
                moved = True
        if not moved:
            return start
