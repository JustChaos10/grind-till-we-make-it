# IndoFlow CEO demo runbook

## Before the meeting

- Follow [Run the CEO demo locally](../README.md#run-the-ceo-demo-locally) to start the API on `indoflow-demo.db` and the Vite app.
- Load the synthetic dataset from the welcome screen. Confirm the dashboard shows work orders and queue depths.
- Run the optimizer once. Keep the results ready on the Schedule optimizer page.
- In the Scenario lab, select a furnace or CNC resource and run a disruption scenario.
- Keep `/docs` available as a technical backup; the product walkthrough itself stays in the browser UI.

## Five-minute narrative

1. **Flow board:** “IndoFlow makes the current flow visible across Molding, Debinding, Sintering, CNC, and Finishing. We can see where WIP is accumulating and which plant signals need attention.”
2. **Schedule optimizer:** “Here we compare the FIFO baseline with a capacity-aware plan. The view calls out late orders, average WIP age, throughput, furnace fill, and the first part of the machine timeline.”
3. **Scenario lab:** “Before reacting to a breakdown or demand change, we can model it. This run removes one machine from the available capacity and shows which due-date outcomes move.”
4. **Close:** “The current value is operational visibility and faster planning. The next step is to validate with actual plant routings, calendars, ERP data, and planner feedback before making shop-floor commitments.”

## Be precise about what is demonstrated

- The bundled order book is deterministic synthetic demo data, not plant data.
- The large-order scheduling path uses a fast dispatch heuristic. The timeline and metrics are a planning aid, not a proof of a globally optimal schedule.
- Optimization and what-if requests do not update source work orders. A human planner remains responsible for accepting any plan.
- The browser app is local-only. Do not expose it with production API tokens or connect it to a live production database.
