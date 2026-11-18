"""FIFO-style ERP baseline: no grouped furnace runs and no CNC sequencing."""

from __future__ import annotations

import math

from domain import OperationResult, OrderSpec, duration_ticks, eligible_resources, route_for, ticks_to_hours
from schedule_utils import ScheduleResult, calculate_metrics


def schedule(orders: list[OrderSpec], resources, parts_by_id: dict, *, down_resource_ids: set[str] | None = None) -> ScheduleResult:
    down = down_resource_ids or set()
    usable_resources = [
        resource for resource in resources
        if resource.status == "ACTIVE" and resource.id not in down
    ]
    free_at: dict[str, int] = {resource.id: 0 for resource in usable_resources}
    last_sku: dict[str, str] = {}
    operations: list[OperationResult] = []
    order_stage_ops: dict[str, list[OperationResult]] = {}
    batch_counter = 0

    # FIFO retains WO creation order. The baseline sends each work order
    # through sintering alone, so compatible furnace capacity stays unused.
    for order in sorted(orders, key=lambda item: item.wo_number):
        part = parts_by_id[order.part_id]
        ready = 0
        order_stage_ops[order.id] = []
        for stage in route_for(order, part.requires_machining):
            candidates = eligible_resources(usable_resources, part, stage)
            if not candidates:
                raise ValueError(f"No active compatible resource for {order.wo_number} at {stage}")
            duration = duration_ticks(order, part, stage)
            choices: list[tuple[int, str, int]] = []
            for resource in candidates:
                setup = 0
                if stage == "CNC Machining" and resource.id in last_sku and last_sku[resource.id] != part.sku_code:
                    setup = math.ceil(resource.setup_changeover_mins / 15)
                start = max(ready, free_at[resource.id] + setup)
                choices.append((start, resource.id, setup))
            start, resource_id, setup = min(choices)
            end = start + duration
            free_at[resource_id] = end
            if stage == "CNC Machining":
                last_sku[resource_id] = part.sku_code
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
