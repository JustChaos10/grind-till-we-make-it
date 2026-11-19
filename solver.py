"""Constraint-aware multi-stage scheduling with Google OR-Tools CP-SAT."""

from __future__ import annotations

import math
import re
import time

from ortools.sat.python import cp_model

from domain import OperationResult, OrderSpec, duration_ticks, eligible_resources, hours_to_ticks, route_for, ticks_to_hours
from schedule_utils import ScheduleResult, calculate_metrics

MAX_TIME_TICKS = 4000  # 1,000 hours at 15-minute resolution
MAX_SOLVER_SECONDS = 1.8  # Leave time for model construction and API serialization.


class SchedulingError(RuntimeError):
    pass


def _next_open_tick(start: int, duration: int, resource) -> int:
    """Move an uninterruptible operation past any overlapping blackout."""
    windows = sorted(getattr(resource, "blackout_windows", None) or [])
    while True:
        moved = False
        for blackout_start, blackout_end in windows:
            start_tick = hours_to_ticks(float(blackout_start))
            end_tick = hours_to_ticks(float(blackout_end))
            if start < end_tick and start + duration > start_tick:
                start = end_tick
                moved = True
        if not moved:
            return start


def _add_blackout_constraints(model, start, end, resource, literal, prefix: str) -> None:
    for index, (blackout_start, blackout_end) in enumerate(getattr(resource, "blackout_windows", None) or []):
        before = model.NewBoolVar(f"before_blackout_{prefix}_{index}")
        model.Add(end <= hours_to_ticks(float(blackout_start))).OnlyEnforceIf([literal, before])
        model.Add(start >= hours_to_ticks(float(blackout_end))).OnlyEnforceIf([literal, before.Not()])


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", value)


def _greedy_schedule_hints(orders, parts_by_id, resources, task_vars, routes, batch_records, batch_resource):
    """Create a feasible list-schedule to seed CP-SAT's search."""
    order_map = {order.id: order for order in orders}
    order_nodes = {}
    node_orders: dict[tuple, set[str]] = {}
    predecessors: dict[tuple, set[tuple]] = {}

    for key, batch in batch_records.items():
        node = ("batch", key[0], key[1])
        node_orders[node] = set(batch["orders"])
        predecessors[node] = set()
        for order_id in batch["orders"]:
            order_nodes[(order_id, "Sintering")] = node
    for order in orders:
        for stage in routes[order.id]:
            if stage == "Sintering":
                continue
            node = ("order", order.id, stage)
            order_nodes[(order.id, stage)] = node
            node_orders[node] = {order.id}
            predecessors[node] = set()
    for order in orders:
        route = routes[order.id]
        for previous, following in zip(route, route[1:]):
            predecessors[order_nodes[(order.id, following)]].add(order_nodes[(order.id, previous)])

    # Include every resource used by any operation, then initialize CNC setup state.
    resource_ids = set()
    for task in task_vars.values():
        resource_ids.update(task["assign"])
    for choices in batch_resource.values():
        resource_ids.update(choices)
    free_at = {resource_id: 0 for resource_id in resource_ids}
    resource_by_id = {resource.id: resource for resource in resources}

    completed: set[tuple] = set()
    times: dict[tuple, tuple[int, int, str]] = {}
    last_part: dict[str, str] = {}
    tool_free_at: dict[str, int] = {}
    for order in orders:
        if order.locked_resource_id and order.locked_until_hour > 0:
            free_at[order.locked_resource_id] = max(
                free_at.get(order.locked_resource_id, 0), hours_to_ticks(order.locked_until_hour)
            )
    while len(completed) < len(node_orders):
        ready = [node for node in node_orders if node not in completed and predecessors[node] <= completed]
        if not ready:
            raise SchedulingError("The work-order stage graph contains a cycle")

        def urgency(node):
            associated = [order_map[oid] for oid in node_orders[node]]
            return (
                min(order.due_date_hours for order in associated),
                -max(order.priority for order in associated),
                min(order.wip_age_hours for order in associated),
                str(node),
            )

        feasible_choices = []
        for candidate_node in ready:
            if candidate_node[0] == "batch":
                key = (candidate_node[1], candidate_node[2])
                candidates = list(batch_resource[key])
                duration = batch_records[key]["duration"]
            else:
                order_id, stage = candidate_node[1], candidate_node[2]
                candidates = list(task_vars[(order_id, stage)]["assign"])
                duration = task_vars[(order_id, stage)]["duration"]
                order = order_map[order_id]
                if stage == order.current_stage and order.locked_resource_id:
                    candidates = [item for item in candidates if item == order.locked_resource_id]
            predecessor_end = max(
                (times[pred][1] for pred in predecessors[candidate_node]), default=0
            )
            for resource_id in candidates:
                resource = resource_by_id[resource_id]
                setup = 0
                tool = None
                if candidate_node[0] == "order":
                    part = parts_by_id[order_map[candidate_node[1]].part_id]
                    if (
                        candidate_node[2] in {"Molding", "CNC Machining", "Finishing"}
                        and resource_id in last_part
                        and last_part[resource_id] != part.id
                    ):
                        setup = math.ceil(resource.setup_changeover_mins / 15)
                    if candidate_node[2] == "Molding" and part.tool_id:
                        tool = part.tool_id
                earliest = max(predecessor_end, free_at[resource_id] + setup)
                if tool:
                    earliest = max(earliest, tool_free_at.get(tool, 0))
                if (
                    candidate_node[0] == "order"
                    and candidate_node[2] == order_map[candidate_node[1]].current_stage
                ):
                    earliest = max(earliest, hours_to_ticks(order_map[candidate_node[1]].locked_until_hour))
                earliest = _next_open_tick(earliest, duration, resource)
                feasible_choices.append((
                    earliest, urgency(candidate_node), str(candidate_node), resource_id,
                    candidate_node, duration,
                ))
        if not feasible_choices:
            raise SchedulingError("No feasible resource remains for ready manufacturing operations")
        start, _, _, resource_id, node, duration = min(feasible_choices)
        end = start + duration
        times[node] = (start, end, resource_id)
        free_at[resource_id] = end
        if node[0] == "order" and node[2] in {"Molding", "CNC Machining", "Finishing"}:
            part = parts_by_id[order_map[node[1]].part_id]
            last_part[resource_id] = part.id
        if node[0] == "order" and node[2] == "Molding":
            part = parts_by_id[order_map[node[1]].part_id]
            if part.tool_id:
                tool_free_at[part.tool_id] = end
        completed.add(node)
    return times, order_nodes


def _solve_scale_fallback(orders, available, parts_by_id, *, time_limit_seconds: float) -> ScheduleResult:
    """Construct a deterministic feasible schedule without quadratic CP-SAT arcs.

    For large instances, sequence circuits grow quadratically in the number of
    operations per machine. A due-date/priority/remaining-work dispatch path
    keeps runtime bounded while respecting routes, tools, calendars, locks,
    resource capacities, and setup transitions.
    """
    started = time.perf_counter()
    free_at = {resource.id: 0 for resource in available}
    resource_names = {resource.id: resource.name for resource in available}
    last_part: dict[str, str] = {}
    tool_free_at: dict[str, int] = {}
    for order in orders:
        if order.locked_resource_id:
            free_at[order.locked_resource_id] = max(
                free_at.get(order.locked_resource_id, 0), hours_to_ticks(order.locked_until_hour)
            )

    def route_and_work(order):
        part = parts_by_id[order.part_id]
        route = route_for(order, part.requires_machining, getattr(part, "process_route", None))
        work = sum(duration_ticks(order, part, stage) for stage in route)
        return route, work

    routes = {order.id: route_and_work(order)[0] for order in orders}
    # Earliest due date and priority drive tardiness; remaining processing
    # burden breaks ties to keep short orders flowing and reduce average WIP.
    ordered_orders = sorted(orders, key=lambda order: (
        order.due_date_hours,
        -order.priority,
        route_and_work(order)[1],
        order.wo_number,
    ))
    operations: list[OperationResult] = []
    for order in ordered_orders:
        part = parts_by_id[order.part_id]
        ready = 0
        for stage in routes[order.id]:
            candidates = eligible_resources(available, part, stage)
            if stage == order.current_stage and order.locked_resource_id:
                candidates = [resource for resource in candidates if resource.id == order.locked_resource_id]
            if not candidates:
                raise SchedulingError(f"No active compatible resource for {order.wo_number} at {stage}")
            duration = duration_ticks(order, part, stage)
            choices = []
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
                choices.append((start, resource.id))
            start, resource_id = min(choices)
            end = start + duration
            free_at[resource_id] = end
            if stage in {"Molding", "CNC Machining", "Finishing"}:
                last_part[resource_id] = part.id
            if stage == "Molding" and part.tool_id:
                tool_free_at[part.tool_id] = end
            operations.append(OperationResult(
                work_order_id=order.id,
                resource_id=resource_id,
                stage=stage,
                start_hour=ticks_to_hours(start),
                end_hour=ticks_to_hours(end),
                batch_id=f"SCALE-{order.id}" if stage == "Sintering" else None,
            ))
            ready = end

    metrics, late_ids, completions = calculate_metrics(orders, available, operations)
    late_set = set(late_ids)
    explanations = {}
    for order in orders:
        order_ops = [op for op in operations if op.work_order_id == order.id]
        previous_end = 0.0
        for op in order_ops:
            if op.start_hour - previous_end > 0.24:
                op.delay_reason = f"Queue on {op.stage} resource {resource_names[op.resource_id]}"
            op.is_late = order.id in late_set
            previous_end = op.end_hour
        if order.id in late_set:
            explanations[order.id] = next(
                (op.delay_reason for op in order_ops if op.delay_reason),
                "Capacity-constrained weighted-tardiness schedule",
            )
    metrics["solver_status"] = "HEURISTIC_SCALE_FALLBACK"
    metrics["cp_sat_status"] = "NOT_RUN_SCALE_FALLBACK"
    metrics["solver_time_limit_seconds"] = max(0.0, time_limit_seconds)
    metrics["solver_wall_time_seconds"] = round(time.perf_counter() - started, 3)
    metrics["objective_value"] = None
    return ScheduleResult("INDOFLOW_OPTIMIZED", operations, metrics, late_ids, completions, explanations)


def solve(
    orders: list[OrderSpec],
    resources,
    parts_by_id: dict,
    *,
    down_resource_ids: set[str] | None = None,
    time_limit_seconds: float = 5.0,
) -> ScheduleResult:
    """Solve one schedule. Sintering lots and their furnace assignments are
    decisions in CP-SAT; lots share a recipe and cannot exceed chosen furnace
    capacity. All other stage operations are optional machine intervals.
    """
    orders = [order for order in orders if order.status.upper() not in {"COMPLETED", "QUALITY_HOLD"}]
    down = down_resource_ids or set()
    available = [
        resource for resource in resources
        if resource.status == "ACTIVE" and resource.id not in down
    ]
    if len(orders) >= 300:
        return _solve_scale_fallback(
            orders, available, parts_by_id, time_limit_seconds=time_limit_seconds
        )
    model = cp_model.CpModel()
    task_vars: dict[tuple[str, str], dict] = {}
    routes: dict[str, tuple[str, ...]] = {}
    order_map = {order.id: order for order in orders}
    resource_map = {resource.id: resource for resource in resources}
    intervals_by_resource: dict[str, list] = {resource.id: [] for resource in available}
    intervals_by_tool: dict[str, list] = {}
    resource_lock_hours: dict[str, float] = {}
    for order in orders:
        if order.locked_resource_id and order.locked_until_hour > 0:
            resource_lock_hours[order.locked_resource_id] = max(
                resource_lock_hours.get(order.locked_resource_id, 0.0), order.locked_until_hour
            )
    for resource_id, locked_until in resource_lock_hours.items():
        if resource_id in intervals_by_resource:
            lock_end = hours_to_ticks(locked_until)
            intervals_by_resource[resource_id].append(
                model.NewIntervalVar(0, lock_end, lock_end, f"lock_{_safe_name(resource_id)}")
            )

    # Create a start/end pair for each operation before linking precedence.
    for order in orders:
        part = parts_by_id[order.part_id]
        route = route_for(order, part.requires_machining, getattr(part, "process_route", None))
        routes[order.id] = route
        for stage in route:
            start = model.NewIntVar(0, MAX_TIME_TICKS, f"s_{order.id}_{_safe_name(stage)}")
            end = model.NewIntVar(0, MAX_TIME_TICKS, f"e_{order.id}_{_safe_name(stage)}")
            duration = duration_ticks(order, part, stage)
            # Furnace orders share one batch end. Its common run time is
            # applied after recipe-compatible members are packed below.
            if stage != "Sintering":
                model.Add(end == start + duration)
            task_vars[(order.id, stage)] = {
                "start": start,
                "end": end,
                "duration": duration,
                "assign": {},
                "intervals": {},
            }

    # Non-furnace stages use a compatible active discrete resource. Optional
    # intervals enforce exclusive use of each press, oven, CNC, or station.
    for order in orders:
        part = parts_by_id[order.part_id]
        for stage in routes[order.id]:
            if stage == "Sintering":
                continue
            task = task_vars[(order.id, stage)]
            candidates = eligible_resources(available, part, stage)
            if stage == order.current_stage and order.locked_resource_id:
                candidates = [resource for resource in candidates if resource.id == order.locked_resource_id]
                task["locked_until_tick"] = hours_to_ticks(order.locked_until_hour)
                model.Add(task["start"] >= task["locked_until_tick"])
            if not candidates:
                reason = (
                    f"locked resource {order.locked_resource_id} is unavailable"
                    if stage == order.current_stage and order.locked_resource_id
                    else "No active compatible resource"
                )
                raise SchedulingError(f"{reason} for {order.wo_number} at {stage}")
            choices = []
            for resource in candidates:
                use = model.NewBoolVar(f"use_{order.id}_{_safe_name(resource.id)}")
                interval = model.NewOptionalIntervalVar(
                    task["start"], task["duration"], task["end"], use,
                    f"iv_{order.id}_{_safe_name(resource.id)}",
                )
                task["assign"][resource.id] = use
                task["intervals"][resource.id] = interval
                intervals_by_resource[resource.id].append(interval)
                _add_blackout_constraints(model, task["start"], task["end"], resource, use, order.id)
                if stage == "Molding" and part.tool_id:
                    intervals_by_tool.setdefault(part.tool_id, []).append(interval)
                choices.append(use)
            model.AddExactlyOne(choices)

    for tool_id, tool_intervals in intervals_by_tool.items():
        model.AddNoOverlap(tool_intervals)

    # Consolidate recipe-compatible orders into capacity-safe batch groups.
    # The model still chooses the furnace and start time for every group; the
    # deterministic first-fit packing keeps orders with early due dates in the
    # earliest compatible lots while avoiding interchangeable empty slots.
    sinter_ids_by_recipe: dict[str, list[str]] = {}
    for order in orders:
        if "Sintering" in routes[order.id]:
            part = parts_by_id[order.part_id]
            sinter_ids_by_recipe.setdefault(part.sintering_recipe_id, []).append(order.id)

    batch_resource: dict[tuple[str, int], dict[str, object]] = {}
    order_batch_slots: dict[str, tuple[str, int]] = {}
    batch_records: dict[tuple[str, int], dict] = {}

    for recipe_id, order_ids in sinter_ids_by_recipe.items():
        order_ids.sort(key=lambda oid: (order_map[oid].due_date_hours, -order_map[oid].priority, order_map[oid].wo_number))
        first_part = parts_by_id[order_map[order_ids[0]].part_id]
        candidates = [r for r in eligible_resources(available, first_part, "Sintering")
                      if not (r.recipe_compatibility or []) or recipe_id in r.recipe_compatibility]
        if not candidates:
            raise SchedulingError(f"No active compatible furnace for recipe {recipe_id}")
        max_capacity = max(resource.capacity_units for resource in candidates)
        packed: list[dict] = []
        for order_id in order_ids:
            quantity = order_map[order_id].quantity
            batch = next((item for item in packed if item["load"] + quantity <= max_capacity), None)
            if batch is None:
                batch = {"orders": [], "load": 0}
                packed.append(batch)
            batch["orders"].append(order_id)
            batch["load"] += quantity

        for slot, batch in enumerate(packed):
            key = (recipe_id, slot)
            safe_recipe = _safe_name(recipe_id)
            batch_candidates = [resource for resource in candidates if resource.capacity_units >= batch["load"]]
            if not batch_candidates:
                raise SchedulingError(
                    f"No compatible furnace has capacity for {batch['load']} parts of recipe {recipe_id}"
                )
            duration = max(task_vars[(oid, "Sintering")]["duration"] for oid in batch["orders"])
            start = model.NewIntVar(0, MAX_TIME_TICKS, f"batch_s_{safe_recipe}_{slot}")
            end = model.NewIntVar(0, MAX_TIME_TICKS, f"batch_e_{safe_recipe}_{slot}")
            model.Add(end == start + duration)
            for order_id in batch["orders"]:
                order_batch_slots[order_id] = key
                task = task_vars[(order_id, "Sintering")]
                model.Add(task["start"] == start)
                model.Add(task["end"] == end)
            choices = []
            resource_choices = {}
            for resource in batch_candidates:
                use = model.NewBoolVar(f"batch_furnace_{safe_recipe}_{slot}_{_safe_name(resource.id)}")
                resource_choices[resource.id] = use
                choices.append(use)
                interval = model.NewOptionalIntervalVar(
                    start, duration, end, use,
                    f"batch_iv_{safe_recipe}_{slot}_{_safe_name(resource.id)}",
                )
                intervals_by_resource[resource.id].append(interval)
                _add_blackout_constraints(
                    model, start, end, resource, use,
                    f"batch_{safe_recipe}_{slot}_{_safe_name(resource.id)}",
                )
            model.AddExactlyOne(choices)
            batch_resource[key] = resource_choices
            batch_records[key] = {
                "orders": batch["orders"],
                "load": batch["load"],
                "start": start,
                "end": end,
                "duration": duration,
            }

    # Stage precedence applies to each work order, including its selected
    # sintering batch interval.
    for order in orders:
        route = routes[order.id]
        for previous, following in zip(route, route[1:]):
            model.Add(task_vars[(order.id, following)]["start"] >= task_vars[(order.id, previous)]["end"])

    # Resource exclusivity and transition setup. Circuits encode immediate
    # predecessor/successor setup gaps on each discrete press, CNC, or finisher.
    setup_circuits = {}
    sequence_stages = {"Molding", "CNC Machining", "Finishing"}
    for resource_id, intervals in intervals_by_resource.items():
        resource = resource_map[resource_id]
        if intervals:
            model.AddNoOverlap(intervals)
        if resource.stage not in sequence_stages:
            continue
        stage = resource.stage
        sequence_orders = [
            order.id for order in orders
            if (order.id, stage) in task_vars
            and resource_id in task_vars[(order.id, stage)]["assign"]
        ]
        if not sequence_orders:
            continue
        empty = model.NewBoolVar(f"seq_empty_{_safe_name(resource_id)}")
        sequence_uses = [task_vars[(order_id, stage)]["assign"][resource_id] for order_id in sequence_orders]
        model.Add(sum(sequence_uses) == 0).OnlyEnforceIf(empty)
        model.Add(sum(sequence_uses) >= 1).OnlyEnforceIf(empty.Not())
        arcs = [(0, 0, empty)]
        arc_vars = {}
        node_by_order = {order_id: index + 1 for index, order_id in enumerate(sequence_orders)}
        for order_id in sequence_orders:
            node = node_by_order[order_id]
            use = task_vars[(order_id, stage)]["assign"][resource_id]
            arcs.append((node, node, use.Not()))
            start_arc = model.NewBoolVar(f"seq_start_{resource_id}_{order_id}")
            end_arc = model.NewBoolVar(f"seq_end_{resource_id}_{order_id}")
            arcs.extend([(0, node, start_arc), (node, 0, end_arc)])
            arc_vars[(0, order_id)] = start_arc
            arc_vars[(order_id, 0)] = end_arc
        for first_id in sequence_orders:
            for second_id in sequence_orders:
                if first_id == second_id:
                    continue
                arc = model.NewBoolVar(f"seq_next_{resource_id}_{first_id}_{second_id}")
                arcs.append((node_by_order[first_id], node_by_order[second_id], arc))
                arc_vars[(first_id, second_id)] = arc
                first = task_vars[(first_id, stage)]
                second = task_vars[(second_id, stage)]
                first_part = parts_by_id[order_map[first_id].part_id]
                second_part = parts_by_id[order_map[second_id].part_id]
                setup_ticks = (
                    0 if first_part.id == second_part.id
                    else math.ceil(resource.setup_changeover_mins / 15)
                )
                model.Add(second["start"] >= first["end"] + setup_ticks).OnlyEnforceIf(arc)
        model.AddCircuit(arcs)
        setup_circuits[resource_id] = {
            "empty": empty,
            "orders": sequence_orders,
            "stage": stage,
            "arc_vars": arc_vars,
        }

    # Weighted tardiness dominates completion-time cost. A smaller batch-slot
    # penalty rewards consolidating recipe-compatible demand.
    late_vars = []
    end_vars = []
    objective_terms = []
    for order in orders:
        route = routes[order.id]
        if not route:
            continue
        completion = task_vars[(order.id, route[-1])]["end"]
        due_ticks = math.ceil(order.due_date_hours * 4 - 1e-9)
        late = model.NewIntVar(0, MAX_TIME_TICKS + max(0, -due_ticks), f"late_{order.id}")
        model.AddMaxEquality(late, [completion - due_ticks, model.NewConstant(0)])
        late_vars.append(late)
        end_vars.append(completion)
        objective_terms.append(late * order.priority * 1000)
        objective_terms.append(completion * 6)
    makespan = model.NewIntVar(0, MAX_TIME_TICKS, "makespan")
    if end_vars:
        model.AddMaxEquality(makespan, end_vars)
    objective_terms.append(makespan * 80)
    model.Minimize(sum(objective_terms))

    hint_times, hint_order_nodes = _greedy_schedule_hints(
        orders, parts_by_id, available, task_vars, routes, batch_records, batch_resource
    )
    for order in orders:
        for stage in routes[order.id]:
            task = task_vars[(order.id, stage)]
            start, end, chosen_resource = hint_times[hint_order_nodes[(order.id, stage)]]
            model.AddHint(task["start"], start)
            model.AddHint(task["end"], end)
            if stage != "Sintering":
                for resource_id, use in task["assign"].items():
                    model.AddHint(use, int(resource_id == chosen_resource))
    for key, batch in batch_records.items():
        start, end, chosen_resource = hint_times[("batch", key[0], key[1])]
        model.AddHint(batch["start"], start)
        model.AddHint(batch["end"], end)
        for resource_id, use in batch_resource[key].items():
            model.AddHint(use, int(resource_id == chosen_resource))
    for resource_id, circuit in setup_circuits.items():
        stage = circuit["stage"]
        sequence = sorted(
            (order_id for order_id in circuit["orders"]
             if hint_times[hint_order_nodes[(order_id, stage)]][2] == resource_id),
            key=lambda order_id: hint_times[hint_order_nodes[(order_id, stage)]][0],
        )
        selected_arcs = set()
        if sequence:
            selected_arcs.add((0, sequence[0]))
            selected_arcs.update(zip(sequence, sequence[1:]))
            selected_arcs.add((sequence[-1], 0))
        model.AddHint(circuit["empty"], int(not sequence))
        for arc_key, arc in circuit["arc_vars"].items():
            model.AddHint(arc, int(arc_key in selected_arcs))
    hinted_makespan = 0
    for order in orders:
        route = routes[order.id]
        if not route:
            continue
        completion = hint_times[hint_order_nodes[(order.id, route[-1])]][1]
        hinted_makespan = max(hinted_makespan, completion)
        due_ticks = math.ceil(order.due_date_hours * 4 - 1e-9)
        model.AddHint(late_vars[orders.index(order)], max(0, completion - due_ticks))
    model.AddHint(makespan, hinted_makespan)

    cp_solver = cp_model.CpSolver()
    effective_time_limit = max(0.1, min(time_limit_seconds, MAX_SOLVER_SECONDS))
    cp_solver.parameters.max_time_in_seconds = effective_time_limit
    cp_solver.parameters.num_search_workers = 4
    cp_solver.parameters.random_seed = 29
    status = cp_solver.Solve(model)
    if status == cp_model.INFEASIBLE or status == cp_model.MODEL_INVALID:
        raise SchedulingError(f"CP-SAT could not find a schedule (status={cp_solver.StatusName(status)})")
    use_greedy = status not in (cp_model.OPTIMAL, cp_model.FEASIBLE)

    chosen_batch: dict[str, tuple[str, int, str]] = {}
    for order_id, (recipe_id, slot) in order_batch_slots.items():
        if use_greedy:
            chosen_resource = hint_times[("batch", recipe_id, slot)][2]
        else:
            chosen_resource = next(
                resource_id for resource_id, use in batch_resource[(recipe_id, slot)].items()
                if cp_solver.Value(use)
            )
        chosen_batch[order_id] = (recipe_id, slot, chosen_resource)

    ops_by_order: dict[str, list[OperationResult]] = {order.id: [] for order in orders}
    for order in orders:
        for stage in routes[order.id]:
            task = task_vars[(order.id, stage)]
            if use_greedy:
                start_tick, end_tick, hinted_resource = hint_times[hint_order_nodes[(order.id, stage)]]
            else:
                start_tick = cp_solver.Value(task["start"])
                end_tick = cp_solver.Value(task["end"])
            if stage == "Sintering":
                recipe_id, slot, resource_id = chosen_batch[order.id]
                batch_id = f"{_safe_name(recipe_id)}-{slot + 1:03d}"
            else:
                resource_id = hinted_resource if use_greedy else next(
                    rid for rid, use in task["assign"].items() if cp_solver.Value(use)
                )
                batch_id = None
            ops_by_order[order.id].append(OperationResult(
                work_order_id=order.id,
                resource_id=resource_id,
                stage=stage,
                start_hour=ticks_to_hours(start_tick),
                end_hour=ticks_to_hours(end_tick),
                batch_id=batch_id,
            ))

    all_ops = [op for order in orders for op in ops_by_order[order.id]]
    metrics, late_ids, completions = calculate_metrics(orders, resources, all_ops)
    late_set = set(late_ids)
    resource_name = {resource.id: resource.name for resource in resources}
    explanations = {}
    for order in orders:
        ops = ops_by_order[order.id]
        previous_end = 0.0
        for op in ops:
            wait = op.start_hour - previous_end
            if wait > 0.24:
                if op.stage == "Sintering":
                    op.delay_reason = f"Sintering recipe batch wait on Furnace {resource_name[op.resource_id]}"
                elif op.stage == "CNC Machining":
                    op.delay_reason = f"Downstream {resource_name[op.resource_id]} setup queue"
                else:
                    op.delay_reason = f"Queue on {op.stage} resource {resource_name[op.resource_id]}"
            op.is_late = order.id in late_set
            previous_end = op.end_hour
        if order.id in late_set:
            reason = next((op.delay_reason for op in ops if op.delay_reason), None)
            if reason is None:
                # If no explicit idle gap exists, explain the route's active
                # capacity constraint deterministically from the assigned ops.
                cnc = next((op for op in ops if op.stage == "CNC Machining"), None)
                sinter = next((op for op in ops if op.stage == "Sintering"), None)
                if cnc:
                    reason = f"Downstream {resource_name[cnc.resource_id]} capacity and setup sequence"
                elif sinter:
                    reason = f"Sintering recipe capacity on Furnace {resource_name[sinter.resource_id]}"
                else:
                    reason = "Upstream production capacity and stage precedence"
            explanations[order.id] = reason

    # Explicitly mark a resource outage when it is the only compatible option
    # for an impacted stage; solve() raises instead of returning false claims.
    metrics["solver_status"] = "HEURISTIC_FALLBACK" if use_greedy else cp_solver.StatusName(status)
    metrics["cp_sat_status"] = cp_solver.StatusName(status)
    metrics["solver_time_limit_seconds"] = effective_time_limit
    metrics["solver_wall_time_seconds"] = round(cp_solver.WallTime(), 3)
    metrics["objective_value"] = None if use_greedy else round(cp_solver.ObjectiveValue(), 2)
    return ScheduleResult("INDOFLOW_OPTIMIZED", all_ops, metrics, late_ids, completions, explanations)
