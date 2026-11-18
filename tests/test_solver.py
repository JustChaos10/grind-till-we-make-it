from __future__ import annotations

import random

import pytest

from domain import OrderSpec
from seed import make_parts, make_resources, make_work_orders
from solver import SchedulingError, solve


def _small_factory():
    rng = random.Random(20261118)
    resources = make_resources()
    parts = make_parts(rng)
    work_orders = make_work_orders(parts, rng)
    part_map = {part.id: part for part in parts}
    specs = [OrderSpec(
        id=order.id,
        wo_number=order.wo_number,
        part_id=order.part_id,
        quantity=order.quantity,
        due_date_hours=order.due_date_hours,
        priority=order.priority,
        current_stage=order.current_stage,
        wip_age_hours=order.wip_age_hours,
    ) for order in work_orders]
    full_route_index = next(
        index for index, order in enumerate(specs)
        if order.current_stage == "Molding" and part_map[order.part_id].requires_machining
    )
    return resources, part_map, specs, full_route_index


def test_cp_sat_schedules_a_full_route_order():
    resources, part_map, specs, index = _small_factory()
    order = specs[index]
    result = solve([order], resources, part_map, time_limit_seconds=1.0)
    operations = sorted(result.operations, key=lambda item: item.start_hour)
    assert [operation.stage for operation in operations] == [
        "Molding", "Debinding", "Sintering", "CNC Machining", "Finishing"
    ]
    assert all(right.start_hour >= left.end_hour for left, right in zip(operations, operations[1:]))
    assert result.metrics["cp_sat_status"] in {"OPTIMAL", "FEASIBLE"}


def test_cnc_downtime_is_reported_when_no_compatible_machine_remains():
    resources, part_map, specs, _ = _small_factory()
    order = next(
        item for item in specs
        if item.current_stage == "CNC Machining" and part_map[item.part_id].requires_machining
    )
    with pytest.raises(SchedulingError, match="No active compatible resource"):
        solve(
            [order],
            resources,
            part_map,
            down_resource_ids={"CNC-1", "CNC-2", "CNC-3", "CNC-4"},
            time_limit_seconds=0.5,
        )
