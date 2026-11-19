"""Preflight checks for factory master and work-in-process data."""

from __future__ import annotations

import math

from domain import STAGES, eligible_resources, route_for


class FactoryDataError(ValueError):
    """Factory data is incomplete or inconsistent with the scheduling model."""


def validate_factory_data(resources, parts, work_orders) -> None:
    resource_by_id = {resource.id: resource for resource in resources}
    part_by_id = {part.id: part for part in parts}
    if len(resource_by_id) != len(resources):
        raise FactoryDataError("Resource IDs must be unique")
    if len(part_by_id) != len(parts):
        raise FactoryDataError("Part IDs must be unique")

    for resource in resources:
        if resource.stage not in STAGES:
            raise FactoryDataError(f"Resource {resource.id} has unsupported stage {resource.stage!r}")
        if resource.status not in {"ACTIVE", "DOWN", "INACTIVE"}:
            raise FactoryDataError(f"Resource {resource.id} has unsupported status {resource.status!r}")
        if not isinstance(resource.capacity_units, int) or resource.capacity_units < 1:
            raise FactoryDataError(f"Resource {resource.id} capacity_units must be a positive integer")
        setup = _finite(resource.setup_changeover_mins, f"Resource {resource.id} setup_changeover_mins")
        if setup < 0:
            raise FactoryDataError(f"Resource {resource.id} setup_changeover_mins cannot be negative")
        for field in ("alloy_compatibility", "recipe_compatibility"):
            values = getattr(resource, field, None)
            if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
                raise FactoryDataError(f"Resource {resource.id} {field} must be a list of strings")
        windows = getattr(resource, "blackout_windows", None)
        if not isinstance(windows, list):
            raise FactoryDataError(f"Resource {resource.id} blackout_windows must be a list of [start, end] hours")
        parsed = []
        for window in windows:
            if not isinstance(window, (list, tuple)) or len(window) != 2:
                raise FactoryDataError(f"Resource {resource.id} has a malformed blackout window")
            start = _finite(window[0], f"Resource {resource.id} blackout start")
            end = _finite(window[1], f"Resource {resource.id} blackout end")
            if start < 0 or end <= start:
                raise FactoryDataError(f"Resource {resource.id} blackout windows must have 0 <= start < end")
            parsed.append((start, end))
        parsed.sort()
        if any(previous[1] > following[0] for previous, following in zip(parsed, parsed[1:])):
            raise FactoryDataError(f"Resource {resource.id} blackout windows cannot overlap")

    seen_work_order_numbers = set()
    for order in work_orders:
        if order.part_id not in part_by_id:
            raise FactoryDataError(f"Work order {order.id} references unknown part {order.part_id}")
        if order.wo_number.casefold() in seen_work_order_numbers:
            raise FactoryDataError(f"Work-order number {order.wo_number!r} is duplicated")
        seen_work_order_numbers.add(order.wo_number.casefold())
        if not isinstance(order.quantity, int) or order.quantity < 1:
            raise FactoryDataError(f"Work order {order.wo_number} quantity must be a positive integer")
        if not 1 <= order.priority <= 5:
            raise FactoryDataError(f"Work order {order.wo_number} priority must be between 1 and 5")
        _finite(order.due_date_hours, f"Work order {order.wo_number} due_date_hours")
        age = _finite(order.wip_age_hours, f"Work order {order.wo_number} wip_age_hours")
        lock_until = _finite(order.locked_until_hour, f"Work order {order.wo_number} locked_until_hour")
        if age < 0 or lock_until < 0:
            raise FactoryDataError(f"Work order {order.wo_number} age and lock time cannot be negative")
        if order.locked_resource_id:
            locked = resource_by_id.get(order.locked_resource_id)
            if locked is None:
                raise FactoryDataError(
                    f"Work order {order.wo_number} is locked to unknown resource {order.locked_resource_id}"
                )
            if locked.stage != order.current_stage:
                raise FactoryDataError(
                    f"Work order {order.wo_number} lock resource {locked.id} does not match stage {order.current_stage}"
                )
        if order.status.upper() in {"COMPLETED", "QUALITY_HOLD"}:
            continue
        if not order.plant or order.plant not in {resource.plant for resource in resources}:
            raise FactoryDataError(f"Work order {order.wo_number} needs a valid plant assignment")
        part = part_by_id[order.part_id]
        try:
            remaining_route = route_for(
                order, part.requires_machining, getattr(part, "process_route", None)
            )
        except (TypeError, ValueError) as exc:
            raise FactoryDataError(f"Work order {order.wo_number} has an invalid route: {exc}") from exc
        for stage in remaining_route:
            cycle = (part.cycle_times_mins or {}).get(stage)
            cycle_value = _finite(cycle, f"Part {part.sku_code} {stage} cycle time")
            if cycle_value <= 0:
                raise FactoryDataError(f"Part {part.sku_code} {stage} cycle time must be positive")
            if not eligible_resources(resources, part, stage, plant=order.plant):
                raise FactoryDataError(
                    f"No active compatible {stage} resource at {order.plant} for {order.wo_number}"
                )


def _finite(value, label: str) -> float:
    try:
        converted = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise FactoryDataError(f"{label} must be a finite number") from exc
    if not math.isfinite(converted):
        raise FactoryDataError(f"{label} must be a finite number")
    return converted
