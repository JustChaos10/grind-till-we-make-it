# Backend requests for frontend integration

These requests support clearer and safer frontend behavior. They are not implemented by the frontend branch. Please review and implement them in the backend when practical.

## Priority 1: Explicit dataset safety metadata

Expose `dataset_type`, `dataset_id`, `is_synthetic`, `has_orders`, and `seed_safe` in a health or factory metadata response. The UI currently needs to distinguish an empty factory from a disconnected API and cannot infer that seeding is safe from order counts alone. The frontend requires the user to confirm a seed action and uses a dedicated local database for this demo.

## Priority 1: Solver provenance

Return supported provenance fields such as `solver_mode` (`CP_SAT`, `HEURISTIC`, or `FEASIBLE_FALLBACK`), `solver_status`, `solve_elapsed_ms`, and `feasible`. Return objective and optimality gap only where the solver can support them accurately. The frontend must not describe a feasible result as optimal without this evidence.

## Priority 1: Scenario lock preservation

Please verify that scenario request mapping preserves `locked_resource_id` and `locked_until_hour` from source orders, and add a backend regression test. Please also verify that a scenario with no changes preserves the baseline order inputs and explain any intentional transformations in the contract.

## Priority 2: Metric definitions and comparison provenance

Document or expose the formula/version for late-order count, average WIP age, throughput, and furnace batch fill. Include baseline provenance and the time origin used by the comparison. This will let the frontend explain each comparison without implying unsupported business outcomes.

## Priority 2: Stable schedule provenance and history

Return a stable run or input snapshot identifier, solver/configuration version, creation timestamp with timezone, and deterministic seed where relevant. Add saved schedule history only with clear rules for retention and selection.

## Priority 3: Richer operational evidence

If the API supports it, add paginated work-order detail, process routes, stage queue age bands, utilization denominators, and operation wait times. This evidence is needed before the UI can make stronger bottleneck or constraint claims.

## Production access boundary

The current browser client is for local demonstration. Before any public frontend, provide user-level authentication or a trusted server-side proxy. Do not expose shared admin or API tokens to browser JavaScript.
