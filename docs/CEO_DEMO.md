# IndoFlow CEO demo runbook

## Before the meeting

- Follow [Run the CEO demo locally](../README.md#run-the-ceo-demo-locally) to start the API on `indoflow-demo.db` and the Vite app.
- Load the synthetic dataset from the welcome screen. Confirm the dashboard shows work orders and queue depths.
- Run the optimizer once. Keep the results ready on the Schedule optimizer page.
- In the Scenario lab, select a furnace or CNC resource and run a disruption scenario.
- Keep `/docs` available as a technical backup; the product walkthrough itself stays in the browser UI.

## Five-minute narrative

1. **Flow board:** “This synthetic example shows work orders across Molding, Debinding, Sintering, CNC, and Finishing. Queue depth is a planning signal, not proof of a bottleneck.”
2. **Schedule optimizer:** “This compares an illustrative FIFO reference with a proposed model schedule. The metrics and timeline are model outputs; throughput counts orders completed inside the modeled 168-hour horizon, and furnace batch fill is not utilization or OEE.”
3. **Scenario lab:** “This what-if run removes a selected resource from modeled availability and shows returned schedule and due-date changes. It does not change source work orders or control equipment.”
4. **Close:** “This demo shows visibility and modeled planning tradeoffs. The next step is to validate routings, calendars, ERP inputs, and constraints with plant experts before any operational use.”

## Be precise about what is demonstrated

- The bundled order book is deterministic synthetic demo data, not plant data.
- The large-order scheduling path uses a fast dispatch heuristic. The timeline and metrics are a planning aid, not a proof of a globally optimal schedule.
- Optimization and what-if requests do not update source work orders. A human planner remains responsible for accepting any plan.
- The browser app is local-only. Do not expose it with production API tokens or connect it to a live production database.
