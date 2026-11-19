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
- [x] Baseline capture recorded before the design pass (`docs/screenshots/baseline-board.png`).

## 1. Truth and safety

- [x] Every screen identifies `Synthetic demo` clearly (browser review and source inspection).
- [x] No live telemetry/actual ERP/verified Indo-MIM production claims (copy/source review).
- [x] Baseline named `Illustrative FIFO reference` or equivalent (source review).
- [x] Scheduling result named `Proposed model schedule`, not guaranteed globally optimal (component test and source review).
- [x] Queue-depth indicator not declared proven system constraint (component test).
- [x] `bottleneck_resource_id` not declared proven throughput bottleneck (component test and copy review).
- [x] Furnace **batch fill** not confused with OEE or utilization (component test and source review).
- [x] Flow average current WIP age distinguished from schedule projection (copy/source review).
- [x] Throughput defined within a 168-hour modeled horizon (component test and source review).
- [x] No fabricated financial impact, customer identities, materials recipes or machine capacities (frontend source review).
- [x] No source-work-order mutations from scheduling or simulation UI; only documented schedule/simulation endpoints are called (source and request tests).
- [x] `/api/seed` never called automatically; user sees explicit deletion/reset warning.
- [x] No real data, `INDOFLOW_*_TOKEN`, password or secret found in frontend source by the final targeted scan (`FRONTEND_AUDIT.md`); this is not a whole-repository security audit.

## 2. Flow Board

- [x] API offline → informative error and retry, not a fake zero dashboard (component test).
- [x] API online with no orders → clear onboarding/seed CTA (component test).
- [x] Seed confirmation explains reset and requires deliberate action (component test).
- [x] Populated board shows correct totals and queues from API (API/browser smoke and component test).
- [x] All five stages and optional CNC context presented correctly (API/browser review).
- [x] Stage labels/count/avg age readable on desktop and phone (responsive review).
- [x] Alert panel treats warnings as planning signals (component test and source review).
- [x] Empty alerts doesn't imply real production is normal (copy/source review).
- [x] Navigation to optimizer and scenario works by click and keyboard activation (component tests cover click; browser Enter activation checked for all three screens). Full keyboard-only traversal remains unverified.
- [x] Refresh works, updates time only on successful data fetch (failure recovery and stale-response component tests).

## 3. Optimizer & Gantt

- [x] Clicking `Run comparison` calls `/api/schedule/optimize` once with supported body (component test).
- [x] Comparison cards handle improved/worse/unchanged/missing data correctly (component test asserts all four states).
- [x] Percent metric displays changes in percentage points (source review).
- [x] Operations scheduled after 96 hours are inspectable (120-operation, 240-hour component test).
- [x] Dense Gantt remains inspectable. A single-resource component test renders all 1,200 operations and opens the last operation.
- [x] Gantt uses consistent relative-hour axis and correct start/end bar geometry (component test and source review).
- [x] Baseline and proposed selections show the corresponding API response dataset (component test and source review).
- [x] Resource rows grouped by stable resource IDs, labels include plant (source review and browser smoke).
- [x] Horizontal and vertical scroll behave at reviewed dense data sizes (browser review; not a stress test).
- [x] Stage legend readable and status not dependent on color alone (source review).
- [x] Operation details show WO, SKU, stage, resource, plant, relative time, batch ID if present, late status, reason (component test and source review).
- [x] Operation details are keyboard-focusable and Escape restores focus (component test); full screen keyboard traversal remains unverified.
- [x] Gantt filters use returned stage, plant, resource, work order, and late status values. Tests cover status and order filters, no matches, reset, consistent time scale, zoom, and work-order drill-down.
- [x] Late orders beyond first eight accessible via a labeled, keyboard-focusable scroll region (10-row component regression test includes WO-010).
- [x] No unsupported optimality or scheduling-feasibility claim (copy/source review).
- [x] No fabricated wall-clock times or apparent real machine dispatch instructions (copy/source review).

## 4. Scenario Lab

- [x] Default scenario has no machine outage/rush and 0% quantity increase (component test and source review).
- [x] Select options derive from `/api/catalog` IDs (component test and source review).
- [x] Range/labels agree with backend validation (0–300%) (component test).
- [x] Form clearly explains how rush orders and quantity increases are modeled (source and browser review).
- [x] Inputs are validated before submission and a synchronous guard prevents duplicate requests on repeated clicks (component regression test).
- [x] Scenario summary displays exact submitted (not merely current draft) inputs (component test).
- [x] Results tie to last submitted input and later edits mark them stale (component test).
- [x] Scenario comparison shows returned results, including no change; regression display reviewed in API-derived UI code (component test and source review).
- [x] Due-date impact list is a labeled, keyboard-focusable region; regression test covers earlier/later/unchanged values, signed hours and late-state text.
- [x] Scenario Gantt uses actual scenario response, not a reused optimization timeline (component test and source review).
- [x] Reset works and doesn't silently mutate factory data (source review; local smoke did not invoke a seed/reset).
- [x] Scenario lock-state mapping reviewed; source omission is documented for backend follow-up in `BACKEND_REQUESTS.md` (not changed or run against backend).

## 5. Design and responsiveness

- [ ] Consistent tokens for color, spacing, typography, borders and status semantics (source review is partial; a full token/contrast audit is open).
- [ ] Body text comfortably legible; no unnecessary 7–10px labels (small table and impact labels were raised to 10–11px; a whole-screen typography review is still open).
- [x] Desktop 1920×1080 reviewed (`docs/screenshots/flow-desktop-1920.png`).
- [x] Desktop 1440×900 reviewed.
- [x] Laptop 1280×800 reviewed (`docs/screenshots/flow-laptop-1280.png`).
- [x] Tablet ~768×1024 reviewed.
- [x] Mobile ~390×844 reviewed after the CSS width adjustment (`docs/screenshots/flow-mobile-390.png`); KPI and stage cards use two columns and navigation moves to the bottom bar.
- [x] No unintended horizontal page overflow at reviewed viewport sizes. Browser measurements showed `scrollWidth === clientWidth` at desktop 1920, laptop 1280, tablet 768 (753 px client area after vertical scrollbar), and mobile 390 (375 px client area after vertical scrollbar).
- [x] Dense chart and tables use intentional scroll in reviewed browser views.
- [ ] Hover, focus, disabled, loading, empty and failure states visually consistent.
- [ ] Interaction affordances correspond to working actions; no decorative dead buttons.
- [x] A `prefers-reduced-motion` stylesheet rule disables smooth scrolling and reduces animation/transition duration (`src/styles.css`); behavior under an OS reduced-motion setting still needs browser verification.
- [ ] Tested keyboard-only navigation across all three screens. Browser Tab and Enter checks reached all three screens. The fixture smoke also covers Gantt details, focus restoration, and scenario inputs. Full Tab traversal and focus order remain to be reviewed.
- [ ] Form controls have accessible names/help/error association.
- [ ] Dialogs have appropriate focus and escape behavior. Seed confirmation and Gantt Escape/focus restoration have targeted coverage. A full focus review is open.
- [ ] Color contrast and no color-only status indicators checked (at 1440 px, sampled fixture board, optimizer, and scenario result text met 4.5:1; coverage of all states remains open).

## 6. Engineering and tests

- [x] Shared typed API client and types reflect current backend response contract (contract and source review).
- [x] `App.tsx` responsibly refactored rather than blindly replaced (diff review).
- [x] `styles.css` improved with consistent tokens/component boundaries (source review).
- [x] Missing/null/non-finite metric values are not displayed as fabricated zeroes (component test).
- [x] Pydantic array and object-shaped `detail` values render field locations/messages (unit tests).
- [x] Canceled/stale async requests don't overwrite newer results incorrectly (out-of-order refresh regression test).
- [x] Frontend component/unit tests cover missing metrics, Gantt, error parsing, seed confirmation/cancel, refresh races, comparison states, scenario behavior, and timeline filters.
- [x] Repeatable browser smoke passed with synthetic fixtures and an isolated real API and temporary SQLite DB. `scripts/browser_real_api.py` covers outage/retry, empty onboarding, explicit seed, optimization, timeline interactions, and two scenario runs.
- [x] `npm run build` passes.
- [x] `npm run lint` passes.
- [x] Frontend test suite passes.
- [x] Python backend pytest/ruff regression results documented (without backend edits).
- [x] Flow Board screenshots captured and **actually inspected**, not just created, at desktop 1920×1080, laptop 1280×800, tablet 768×1024, and phone 390×844 (`docs/screenshots/flow-*.png`). The optimizer and Scenario Lab were also visually reviewed in the browser; additional desktop, tablet and mobile captures for all three screens are in `docs/screenshots/{board,optimizer,scenario}-{desktop,tablet,mobile}.png`.
- [x] No production deploy, public secret or paid infrastructure action was taken.

## 7. Git handoff and founder demo

- [x] Source branch contains only intended frontend/documentation changes (final status review).
- [x] Changes grouped into meaningful commits.
- [x] No history rewrite or force push.
- [x] No direct merge/push to main.
- [x] Final `git status` and commit SHA recorded in the task handoff; implementation SHA is in `FRONTEND_AUDIT.md`.
- [x] Frontend setup/run instructions verified in PowerShell; exact commands are in `FRONTEND_AUDIT.md`.
- [x] Backend requests listed separately in `frontend/docs/BACKEND_REQUESTS.md`.
- [ ] Five-minute spoken founder walkthrough rehearsed against actual UI. Use `docs/CEO_DEMO.md` and time the prepared presentation.
- [x] `CEO_DEMO.md` and the reviewed UI communicate: *synthetic → compare → stress-test → request plant expert validation*.
- [x] All incomplete items explicitly listed with specific next steps below and in `FRONTEND_AUDIT.md`.

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
