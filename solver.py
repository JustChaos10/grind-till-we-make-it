"""Constraint-aware multi-stage scheduling with Google OR-Tools CP-SAT."""

from __future__ import annotations

import math
import re

from ortools.sat.python import cp_model

from domain import OperationResult, OrderSpec, duration_ticks, eligible_resources, route_for, ticks_to_hours
from schedule_utils import ScheduleResult, calculate_metrics

MAX_TIME_TICKS = 4000  # 1,000 hours at 15-minute resolution
MAX_SOLVER_SECONDS = 1.8  # Leave time for model construction and API serialization.


class SchedulingError(RuntimeError):
    pass


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
    last_sku: dict[str, str] = {}
    while len(completed) < len(node_orders):
        ready = [node for node in node_orders if node not in completed and predecessors[node] <= completed]
        if not ready:
            raise SchedulingError("The work-order stage graph contains a cycle")

        def urgency(node):
            associated = [order_map[oid] for oid in node_orders[node]]
            return (
                min(order.due_date_hours - order.priority * 2 for order in associated),
                -max(order.priority for order in associated),
                str(node),
            )

        node = min(ready, key=urgency)
        if node[0] == "batch":
            key = (node[1], node[2])
            candidates = list(batch_resource[key])
            duration = batch_records[key]["duration"]
        else:
            order_id, stage = node[1], node[2]
            candidates = list(task_vars[(order_id, stage)]["assign"])
            duration = task_vars[(order_id, stage)]["duration"]
        predecessor_end = max((times[pred][1] for pred in predecessors[node]), default=0)
        options = []
        for resource_id in candidates:
            resource = resource_by_id[resource_id]
            setup = 0
            if node[0] == "order" and node[2] == "CNC Machining":
                part = parts_by_id[order_map[node[1]].part_id]
                if resource_id in last_sku and last_sku[resource_id] != part.sku_code:
                    setup = math.ceil(resource.setup_changeover_mins / 15)
            start = max(predecessor_end, free_at[resource_id] + setup)
            options.append((start, resource_id))
        start, resource_id = min(options)
        end = start + duration
        times[node] = (start, end, resource_id)
        free_at[resource_id] = end
        if node[0] == "order" and node[2] == "CNC Machining":
            last_sku[resource_id] = parts_by_id[order_map[node[1]].part_id].sku_code
        completed.add(node)
    return times, order_nodes


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
    down = down_resource_ids or set()
    available = [
        resource for resource in resources
        if resource.status == "ACTIVE" and resource.id not in down
    ]
    model = cp_model.CpModel()
    task_vars: dict[tuple[str, str], dict] = {}
    routes: dict[str, tuple[str, ...]] = {}
    order_map = {order.id: order for order in orders}
    resource_map = {resource.id: resource for resource in resources}
    intervals_by_resource: dict[str, list] = {resource.id: [] for resource in available}

    # Create a start/end pair for each operation before linking precedence.
    for order in orders:
        part = parts_by_id[order.part_id]
        route = route_for(order, part.requires_machining)
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
            if not candidates:
                raise SchedulingError(f"No active compatible resource for {order.wo_number} at {stage}")
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
                choices.append(use)
            model.AddExactlyOne(choices)

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

    # Resource exclusivity. CNC uses a circuit per machine so each assigned
    # operation has one predecessor/successor and setup time is charged on
    # actual transitions, without pairwise order booleans for every task pair.
    cnc_circuits = {}
    cnc_by_resource = {
        resource.id: [order.id for order in orders
                      if (order.id, "CNC Machining") in task_vars
                      and resource.id in task_vars[(order.id, "CNC Machining")]["assign"]]
        for resource in available if resource.stage == "CNC Machining"
    }
    for resource_id, intervals in intervals_by_resource.items():
        resource = resource_map[resource_id]
        if intervals and resource.stage != "CNC Machining":
            model.AddNoOverlap(intervals)
        if resource.stage != "CNC Machining":
            continue
        cnc_orders = cnc_by_resource.get(resource_id, [])
        empty = model.NewBoolVar(f"cnc_empty_{_safe_name(resource_id)}")
        cnc_uses = [task_vars[(order_id, "CNC Machining")]["assign"][resource_id] for order_id in cnc_orders]
        model.Add(sum(cnc_uses) == 0).OnlyEnforceIf(empty)
        model.Add(sum(cnc_uses) >= 1).OnlyEnforceIf(empty.Not())
        arcs = [(0, 0, empty)]
        arc_vars = {}
        node_by_order = {order_id: index + 1 for index, order_id in enumerate(cnc_orders)}
        for order_id in cnc_orders:
            node = node_by_order[order_id]
            use = task_vars[(order_id, "CNC Machining")]["assign"][resource_id]
            arcs.append((node, node, use.Not()))
            start_arc = model.NewBoolVar(f"cnc_start_{resource_id}_{order_id}")
            end_arc = model.NewBoolVar(f"cnc_end_{resource_id}_{order_id}")
            arcs.extend([(0, node, start_arc), (node, 0, end_arc)])
            arc_vars[(0, order_id)] = start_arc
            arc_vars[(order_id, 0)] = end_arc
        for first_id in cnc_orders:
            for second_id in cnc_orders:
                if first_id == second_id:
                    continue
                arc = model.NewBoolVar(f"cnc_next_{resource_id}_{first_id}_{second_id}")
                arcs.append((node_by_order[first_id], node_by_order[second_id], arc))
                arc_vars[(first_id, second_id)] = arc
                first = task_vars[(first_id, "CNC Machining")]
                second = task_vars[(second_id, "CNC Machining")]
                first_part = parts_by_id[order_map[first_id].part_id]
                second_part = parts_by_id[order_map[second_id].part_id]
                setup_ticks = 0 if first_part.sku_code == second_part.sku_code else math.ceil(resource.setup_changeover_mins / 15)
                model.Add(second["start"] >= first["end"] + setup_ticks).OnlyEnforceIf(arc)
        model.AddCircuit(arcs)
        cnc_circuits[resource_id] = {
            "empty": empty,
            "orders": cnc_orders,
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
        late = model.NewIntVar(0, MAX_TIME_TICKS, f"late_{order.id}")
        due_ticks = math.ceil(order.due_date_hours * 4 - 1e-9)
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
    for resource_id, circuit in cnc_circuits.items():
        sequence = sorted(
            (order_id for order_id in circuit["orders"]
             if hint_times[hint_order_nodes[(order_id, "CNC Machining")]][2] == resource_id),
            key=lambda order_id: hint_times[hint_order_nodes[(order_id, "CNC Machining")]][0],
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
