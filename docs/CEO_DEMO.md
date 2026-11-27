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

## Unseeded narration

Use the same screen timings when approved records are pending. Pause on each screen after the narration so the audience can read the interface. Keep the run actions idle.

### 0:00 Flow board

This workspace connects to an isolated IndoFlow API. The flow board says there are no open work orders. I can refresh the API and see that the workspace is still empty. To start a factory review, a data administrator needs to load and check the work orders and the resources that can process them. Once those records are in place, this board shows where work is waiting across molding, debinding, sintering, optional CNC machining, and finishing.

### 1:00 Schedule optimizer

The schedule optimizer asks for work orders before it can run. With approved records, the optimizer can compare a proposed schedule with an illustrative first-in, first-out reference. Before discussing a change, we check the model horizon and the unit on the metric. The timeline then lets us inspect each operation and its assigned resource. We checked the chart layout against published production intervals from bottling and CNC machining. Those records did not include the inputs needed to run this factory's schedule.

### 2:30 Scenario lab

The scenario lab has inputs for a resource outage, a rush work order, and extra demand. The run button stays disabled until schedulable work orders are available. With approved records, we can select an active resource and see the modeled effect of the outage on order completion and due dates. We would read the selected resource and the returned changes on this screen. The plant planner would check whether the resource, outage, and affected orders match the situation they need to plan for.

### 4:00 Discussion

Let's pick one historical planning period that your team knows well. We need approved work orders, their due dates and routes, and the resource and shift calendars that applied at the time. Which furnace batch rule or CNC constraint would you check first? That gives us a concrete test for a populated review. We can compare schedule assumptions with that planning period once the approved records are loaded in an isolated workspace.
