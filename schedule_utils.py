"""Shared schedule result and KPI calculations."""

from __future__ import annotations

from dataclasses import dataclass

from domain import OperationResult, OrderSpec


@dataclass
class ScheduleResult:
    mode: str
    operations: list[OperationResult]
    metrics: dict
    late_order_ids: list[str]
    completion_hours: dict[str, float]
    explanations: dict[str, str]


def calculate_metrics(orders: list[OrderSpec], resources, operations: list[OperationResult]) -> tuple[dict, list[str], dict[str, float]]:
    order_map = {order.id: order for order in orders}
    resource_map = {resource.id: resource for resource in resources}
    completion_ticks: dict[str, float] = {}
    for op in operations:
        completion_ticks[op.work_order_id] = max(
            completion_ticks.get(op.work_order_id, 0.0), op.end_hour
        )
    late_ids = sorted(
        order_id for order_id, end in completion_ticks.items()
        if end > order_map[order_id].due_date_hours
    )
    horizon = max(completion_ticks.values(), default=0.0)
    avg_wip_age = sum(
        order_map[order_id].wip_age_hours + end
        for order_id, end in completion_ticks.items()
    ) / max(1, len(completion_ticks))

    # Count a sintering furnace run once even though each member order has an
    # operation row. Its loaded quantity is divided by the selected furnace's
    # rated tray/parts capacity.
    runs: dict[tuple[str, str], set[str]] = {}
    for op in operations:
        if op.stage == "Sintering":
            key = (op.resource_id, op.batch_id or op.work_order_id)
            runs.setdefault(key, set()).add(op.work_order_id)
    order_qty = {order.id: order.quantity for order in orders}
    furnace_slots = sum(resource_map[rid].capacity_units for rid, _ in runs if rid in resource_map)
    loaded_units = sum(
        order_qty[order_id]
        for order_ids in runs.values()
        for order_id in order_ids
        if order_id in order_qty
    )
    batch_efficiency = round(100 * loaded_units / furnace_slots, 1) if furnace_slots else 0.0

    busy_hours: dict[str, float] = {}
    seen_runs: set[tuple[str, str]] = set()
    for op in operations:
        if op.stage == "Sintering":
            key = (op.resource_id, op.batch_id or op.work_order_id)
            if key in seen_runs:
                continue
            seen_runs.add(key)
        busy_hours[op.resource_id] = busy_hours.get(op.resource_id, 0.0) + (op.end_hour - op.start_hour)
    bottleneck_id = max(busy_hours, key=lambda rid: (busy_hours[rid], rid), default=None)
    throughput_168h = sum(1 for end in completion_ticks.values() if end <= 168)
    makespan = round(horizon, 2)
    metrics = {
        "late_orders": len(late_ids),
        "avg_wip_age_hours": round(avg_wip_age, 2),
        "throughput": throughput_168h,
        "throughput_horizon_hours": 168,
        "furnace_batch_efficiency_pct": batch_efficiency,
        "makespan_hours": makespan,
        "bottleneck_resource_id": bottleneck_id,
        "resource_busy_hours": {rid: round(hours, 2) for rid, hours in busy_hours.items()},
        "weighted_tardiness_hours": round(sum(
            max(0.0, completion_ticks[order_id] - order_map[order_id].due_date_hours)
            * order_map[order_id].priority
            for order_id in completion_ticks
        ), 2),
    }
    completion_hours = {order_id: round(end, 2) for order_id, end in completion_ticks.items()}
    return metrics, late_ids, completion_hours
