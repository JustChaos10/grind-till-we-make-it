# Backend requests for frontend integration

These requests support clearer and safer frontend behavior. They are not implemented by the frontend branch. Please review and implement them in the backend when practical.

## Priority 1: Explicit dataset safety metadata

Expose `dataset_type`, `dataset_id`, `is_synthetic`, `has_orders`, and `seed_safe` in a health or factory metadata response. The UI currently needs to distinguish an empty factory from a disconnected API and cannot infer that seeding is safe from order counts alone. The frontend requires the user to confirm a seed action and uses a dedicated local database for this demo.

## Priority 1: Solver provenance

Return supported provenance fields such as `solver_mode` (`CP_SAT`, `HEURISTIC`, or `FEASIBLE_FALLBACK`), `solver_status`, `solve_elapsed_ms`, and `feasible`. Return objective and optimality gap only where the solver can support them accurately. The frontend must not describe a feasible result as optimal without this evidence.

## Priority 1: Scenario lock preservation

Source review on 2026-11-19 found that `_order_specs()` copies `locked_resource_id` and `locked_until_hour` into `OrderSpec` (`main.py`), but the scenario reconstruction in `simulate_schedule()` creates new `OrderSpec` values without either field (`main.py`, scenario mapping). Please preserve both fields when constructing scenario specs and add a backend regression test for locked orders. Also verify that a scenario with no changes preserves baseline order inputs and document intentional transformations in the contract. This finding is source-confirmed; no backend request was made to reproduce it.

## Priority 2: Metric definitions and comparison provenance

Document or expose the formula/version for late-order count, average WIP age, throughput, and furnace batch fill. Include baseline provenance and the time origin used by the comparison. This will let the frontend explain each comparison without implying unsupported business outcomes.

Please also characterize expected latency and timeout behavior for schedule optimization and scenario simulation. One local CNC-1 downtime + rush-order simulation took about 20 seconds to return; this is a single observation, not a performance benchmark. Return solve duration/progress or a documented timeout budget where the backend can support it so the UI can communicate long-running work accurately.

## Priority 2: Stable schedule provenance and history

Return a stable run or input snapshot identifier, solver/configuration version, creation timestamp with timezone, and deterministic seed where relevant. Add saved schedule history only with clear rules for retention and selection.

## Priority 3: Richer operational evidence

If the API supports it, add paginated work-order detail, process routes, stage queue age bands, utilization denominators, and operation wait times. This evidence is needed before the UI can make stronger bottleneck or constraint claims.

## Production access boundary

The current browser client is for local demonstration. Before any public frontend, provide user-level authentication or a trusted server-side proxy. Do not expose shared admin or API tokens to browser JavaScript.

## Contract details for backend review

These are proposed additions. The current frontend does not consume them. Preserve existing response fields for older clients.

| Request | Proposed contract example | Frontend behavior until available |
| --- | --- | --- |
| Identify a safe demo dataset | Add metadata to `GET /api/catalog`, for example `{"dataset_type":"synthetic","is_synthetic":true,"seed_safe":true}`. Derive safety on the server. | Restrict seed controls to an explicitly enabled local demo and ask before resetting records. |
| Identify a solve method | Add optional per-run metadata to the optimization and simulation responses, for example `{"solver_mode":"HEURISTIC","solve_elapsed_ms":320}`. Report the actual method and elapsed time. | Label schedules as model outputs. Leave optimality and solve duration unspecified. |
| Preserve scenario locks | Keep the simulation response shape. Carry each original lock through scenario reconstruction and test the no-change case with a locked fixture. | Treat scenario output as advisory and disclose the model limit. |
| Explain metric definitions | Add an optional `metric_definition_version` alongside returned metrics. Document units, horizon and included order population for each version. | Display the returned values and explain the known reference and horizon. |
| Identify the input snapshot | Return an optional opaque `input_snapshot_id` with schedule versions. Specify whether IDs change after a factory edit or a reseed. | Keep comparisons tied to their returned result in this browser session. |
| Support order drill-down | Propose a paginated route with stable order IDs, route stages, and queue timestamps with units and origin. Agree on the included statuses before implementation. | Use the available catalog and operation fields only. |
