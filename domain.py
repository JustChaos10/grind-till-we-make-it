"""Shared scheduling constants and small domain helpers."""

from __future__ import annotations

import math
from dataclasses import dataclass

STAGES = ("Molding", "Debinding", "Sintering", "CNC Machining", "Finishing")
SEGMENTS = ("Aerospace", "Medical", "Automotive", "ECM")
ALLOYS = ("MIM-17-4PH", "MIM-316L", "MIM-4605", "Ti-6Al-4V")
TICKS_PER_HOUR = 4  # 15-minute solver resolution


@dataclass(frozen=True)
class OrderSpec:
    id: str
    wo_number: str
    part_id: str
    quantity: int
    due_date_hours: float
    priority: int
    current_stage: str
    wip_age_hours: float
    status: str = "QUEUED"
    locked_resource_id: str | None = None
    locked_until_hour: float = 0.0
    plant: str | None = None


@dataclass
class OperationResult:
    work_order_id: str
    resource_id: str
    stage: str
    start_hour: float
    end_hour: float
    batch_id: str | None = None
    is_late: bool = False
    delay_reason: str | None = None


def stage_index(stage: str) -> int:
    try:
        return STAGES.index(stage)
    except ValueError as exc:
        raise ValueError(f"Unknown manufacturing stage: {stage}") from exc


def route_for(order: OrderSpec, requires_machining: bool, process_route=None) -> tuple[str, ...]:
    """Resolve a part's ordered route and return the remaining stages.

    An explicit route supports application-specific operations. Existing
    records retain the legacy route implied by ``requires_machining``.
    """
    if process_route is None:
        route = tuple(stage for stage in STAGES if requires_machining or stage != "CNC Machining")
    else:
        route = tuple(process_route)
        if not route or any(stage not in STAGES for stage in route):
            raise ValueError("process_route must contain known manufacturing stages")
        if tuple(sorted(route, key=STAGES.index)) != route or len(set(route)) != len(route):
            raise ValueError("process_route stages must be unique and in manufacturing order")
    if order.current_stage not in route:
        raise ValueError(
            f"Current stage {order.current_stage} is not present in the part's process route"
        )
    return route[route.index(order.current_stage):]


def hours_to_ticks(hours: float) -> int:
    return max(0, math.ceil(hours * TICKS_PER_HOUR - 1e-9))


def ticks_to_hours(ticks: int) -> float:
    return round(ticks / TICKS_PER_HOUR, 2)


def duration_ticks(order: OrderSpec, part, stage: str) -> int:
    """Return run duration in 15-minute ticks.

    Molding, CNC, and finishing cycle values are per-part minutes. Debinding
    and sintering values describe a fixed batch/lot cycle.
    """
    cycle_mins = float(part.cycle_times_mins[stage])
    if stage in ("Molding", "CNC Machining", "Finishing"):
        cycle_mins *= order.quantity
    return max(1, math.ceil(cycle_mins / 15.0 - 1e-9))


def eligible_resources(
    resources,
    part,
    stage: str,
    *,
    plant: str | None = None,
    quantity: int | None = None,
    active_only: bool = True,
):
    compatible = []
    for resource in resources:
        if resource.stage != stage:
            continue
        if plant is not None and resource.plant != plant:
            continue
        if active_only and resource.status != "ACTIVE":
            continue
        if part.alloy_family not in (resource.alloy_compatibility or []):
            continue
        if stage == "Sintering":
            recipes = resource.recipe_compatibility or []
            if recipes and part.sintering_recipe_id not in recipes:
                continue
        if stage == "Debinding" and quantity is not None and resource.capacity_units < quantity:
            continue
        compatible.append(resource)
    return compatible
