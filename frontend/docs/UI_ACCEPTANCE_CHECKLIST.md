# IndoFlow — Frontend Acceptance, Visual QA and Founder Demo Checklist

**Owner:** Frontend/UI/UX agent  
**Reference:** `FRONTEND_MASTER_BRIEF.md`, `API_CONTRACT_AND_METRICS.md`  
**Rule:** Do not check items as complete without executing the corresponding verification. Mark blocked items clearly.

## 0. Startup / collaboration

- [x] Identified and reused/cloned `JustChaos10/grind-till-we-make-it`, not a new repo.
- [x] `git status`, current SHA, default branch, remote and uncommitted changes inspected.
- [x] Created an isolated frontend branch, not editing/pushing `main`.
- [x] Read current backend API endpoints and current frontend files.
- [x] Existing relevant `AGENTS.md` rules inspected and reconciled.
- [x] Local Windows Node/Python requirements verified.
- [x] API started on explicit local `indoflow-demo.db` DB; Vite app started successfully.
- [x] Frontend build/lint/tests and backend tests/lint run; results recorded in `FRONTEND_AUDIT.md`.
- [ ] Baseline screenshots or visual observations recorded before redesign.

## 1. Truth and safety

- [ ] Every screen identifies `Synthetic demo` clearly.
- [ ] No live telemetry/actual ERP/verified Indo-MIM production claims.
- [ ] Baseline named `Illustrative FIFO reference` or equivalent.
- [ ] Scheduling result named `Proposed model schedule`, not guaranteed globally optimal.
- [ ] Queue-depth indicator not declared proven system constraint.
- [ ] `bottleneck_resource_id` not declared proven throughput bottleneck.
- [ ] Furnace **batch fill** not confused with OEE or utilization.
- [ ] Flow average current WIP age distinguished from schedule projection.
- [ ] Throughput defined within a 168-hour modeled horizon.
- [ ] No fabricated financial impact, customer identities, materials recipes or machine capacities.
- [ ] No source-work-order mutations from scheduling or simulation UI.
- [x] `/api/seed` never called automatically; user sees explicit deletion/reset warning.
- [ ] No real data, `INDOFLOW_*_TOKEN`, password or secret in committed/browser code.

## 2. Flow Board

- [ ] API offline → informative error and retry, not a fake zero dashboard.
- [x] API online with no orders → clear onboarding/seed CTA (component test).
- [x] Seed confirmation explains reset and requires deliberate action (component test).
- [ ] Populated board shows correct totals and queues from API.
- [ ] All five stages and optional CNC context presented correctly.
- [ ] Stage labels/count/avg age readable on desktop and phone.
- [ ] Alert panel treats warnings as planning signals.
- [ ] Empty alerts doesn't imply real production is normal.
- [ ] Navigation to optimizer and scenario works by click and keyboard.
- [ ] Refresh works, updates time only on successful data fetch.

## 3. Optimizer & Gantt

- [ ] Clicking `Run comparison` calls `/api/schedule/optimize` once with supported body.
- [ ] Comparison cards handle improved/worse/unchanged/missing data correctly.
- [ ] Percent metric displays changes in percentage points.
- [ ] Operations scheduled after 96 hours are inspectable.
- [x] More than 90 operations overall are discoverable in the Gantt component (120-operation test); >24 per resource was not separately tested.
- [ ] Gantt uses consistent relative-hour axis and correct start/end bar geometry.
- [ ] Baseline and proposed selections show the corresponding real response dataset.
- [ ] Resource rows grouped by stable resource IDs, labels include plant.
- [ ] Horizontal and vertical scroll behave correctly at dense data sizes.
- [ ] Stage legend readable and status not dependent on color alone.
- [ ] Operation details show WO, SKU, stage, resource, plant, relative time, batch ID if present, late status, reason.
- [x] Operation details are keyboard-focusable and Escape restores focus (component test); full screen keyboard traversal remains unverified.
- [ ] Filters (if implemented) have clear reset and correct results count.
- [ ] Filtered timeline doesn't silently change global unfiltered KPI figures.
- [ ] Late orders beyond first eight accessible via scroll/pagination.
- [ ] No unsupported optimality or scheduling-feasibility claim.
- [ ] No fabricated wall-clock times or apparent real machine dispatch instructions.

## 4. Scenario Lab

- [ ] Default scenario has no machine outage/rush and 0% quantity increase.
- [ ] Select options derive from `/api/catalog` IDs.
- [ ] Range/labels agree with backend validation (0–300%).
- [ ] Form clearly explains how rush orders and quantity increases are modeled.
- [ ] Only valid inputs submitted; no duplicate requests on repeated clicks.
- [ ] Scenario summary displays exact submitted (not merely current draft) inputs.
- [x] Results tie to last submitted input and later edits mark them stale (component test).
- [ ] Scenario comparison shows real results, including regressions/no change.
- [ ] Due-date impact list has accessible details and correctly displayed signs/status.
- [ ] Scenario Gantt uses actual response, not a reused optimization timeline.
- [ ] Reset works and doesn't silently mutate factory data.
- [ ] No-change scenario potential backend lock-state issue investigated/documented if reproduced.

## 5. Design and responsiveness

- [ ] Consistent tokens for color, spacing, typography, borders and status semantics.
- [ ] Body text comfortably legible; no unnecessary 7–10px labels.
- [ ] Desktop 1920×1080 reviewed.
- [ ] Desktop 1440×900 reviewed.
- [ ] Laptop 1280×800 reviewed.
- [ ] Tablet ~768×1024 reviewed.
- [ ] Mobile ~390×844 reviewed.
- [ ] No unintended horizontal page overflow, clipped cards or hidden buttons.
- [ ] Dense chart and tables have intentional scroll rather than illegible compression.
- [ ] Hover, focus, disabled, loading, empty and failure states visually consistent.
- [ ] Interaction affordances correspond to working actions; no decorative dead buttons.
- [ ] Respects prefers-reduced-motion.
- [ ] Tested keyboard-only navigation across all three screens.
- [ ] Form controls have accessible names/help/error association.
- [ ] Dialogs have appropriate focus and escape behavior.
- [ ] Color contrast and no color-only status indicators checked.

## 6. Engineering and tests

- [ ] Shared typed API client and types reflect current backend response exactly.
- [ ] `App.tsx` responsibly refactored rather than blindly replaced.
- [ ] `styles.css` improved with consistent tokens/component boundaries.
- [x] Missing/null/non-finite metric values are not displayed as fabricated zeroes (component test).
- [x] Pydantic array `detail` renders field locations and messages (unit test); object detail path is not separately covered.
- [ ] Canceled/stale async requests don't overwrite newer results incorrectly.
- [x] Frontend component/unit tests added for missing metrics, Gantt, error parsing, seed confirmation, and scenario behavior; filters/delta/dialog coverage remains incomplete.
- [ ] Browser smoke test covers full demo using real local API or explicitly documented test fixtures. (Partial manual smoke is recorded in `FRONTEND_AUDIT.md`.)
- [x] `npm run build` passes.
- [x] `npm run lint` passes.
- [x] Frontend test suite passes.
- [x] Python backend pytest/ruff regression results documented (without backend edits).
- [x] Desktop screenshot captured and **actually inspected**, not just created. (Responsive visual coverage is incomplete.)
- [ ] No production deploy, public secret or paid infrastructure action.

## 7. Git handoff and founder demo

- [ ] Source branch contains only intended frontend/documentation changes.
- [ ] Changes grouped into meaningful commits.
- [ ] No history rewrite or force push.
- [ ] No direct merge/push to main.
- [ ] Final `git status` and commit SHA recorded. (Update `FRONTEND_AUDIT.md` after final commit.)
- [ ] Frontend setup/run instructions verified in PowerShell.
- [ ] Backend requests listed separately in `frontend/docs/BACKEND_REQUESTS.md` if needed.
- [ ] Five-minute founder walkthrough rehearsed against actual UI.
- [ ] Demo communicates: *synthetic -> compare -> stress-test -> request plant expert validation*.
- [ ] All incomplete items explicitly listed with specific next steps.

## Founder presentation five-minute test

| Time | Screen | Audience question answered | Honest limit |
|---|---|---|---|
| 0:00–1:00 | Flow Board | Where are orders sitting in this example system? | Not live ERP data |
| 1:00–2:30 | Optimizer | What modeled scheduling tradeoffs appear? | FIFO is illustrative, not actual baseline |
| 2:30–4:00 | Scenario Lab | How do simulated disruptions change commitments? | Model must be calibrated/validated |
| 4:00–5:00 | Discussion | Which real constraints/data would validate the product? | Human planner and secure historical records required |

### Handoff report format

1. `Starting SHA`, `current branch`, `ending SHA`, `git status`.
2. What existed vs what was changed.
3. Which acceptance items are verified vs incomplete/blocked.
4. Exact build/lint/test commands and results.
5. Screenshot paths and visual review notes.
6. Backend contract requests for collaborator.
7. How to run demo locally in Windows PowerShell.
8. The next highest-value improvement and known limitations.
