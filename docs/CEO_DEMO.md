# IndoFlow CEO demo runbook

## Before the meeting

- Start the API and frontend with the [local review commands](../frontend/docs/FRONTEND_IMPLEMENTATION_HANDOFF.md#local-run-commands-powershell). Use an isolated database and keep demo seeding disabled.
- For a populated walkthrough, have the backend owner prepare an [approved historical metal injection molding snapshot](../frontend/docs/BACKEND_REQUESTS.md#permission-cleared-historical-mim-snapshot). Confirm the dates, order count, route, and resource calendars with the plant data owner.
- Rehearse the comparison and outage in the browser before presenting. Record the displayed snapshot date, model horizon, and selected resource. Choose an active furnace or CNC machine from the catalog.
- If the approved snapshot is pending, use the empty workspace to show how the app connects, refreshes, and guides users. Show the [public data validation report](../frontend/docs/PUBLIC_DATA_VALIDATION.md) as evidence that the timeline layout handled observed intervals. Leave the optimizer and scenario idle.

## Five-minute walkthrough with approved records

| Time | Screen | What to show |
| --- | --- | --- |
| 0:00–1:00 | Flow board | State the data period. Read the current open-order count, which includes quality holds. Open a stage queue and describe what planners can inspect. |
| 1:00–2:30 | Schedule optimizer | Run the comparison. Describe the FIFO reference as illustrative. Read a returned metric with its unit and model horizon. Switch timelines, select an operation, then press Escape to return. |
| 2:30–4:00 | Scenario lab | Select an active resource and run the outage. Read the submitted resource and the returned due-date impact. If the results stay the same, report that result. Change a draft input to show which results belong to the previous submission. |
| 4:00–5:00 | Discussion | Ask the plant planner to validate a specific route, resource calendar, or order constraint. Confirm which records the planner needs before deciding whether to use the proposed schedule. |

Queue depth describes where work is waiting. Throughput counts orders completed in the displayed model horizon. Furnace batch fill measures how much batch capacity the model uses. The large-order scheduling path can use a dispatch heuristic. Optimization and scenarios leave source work orders unchanged, and a planner decides whether to accept a plan.
