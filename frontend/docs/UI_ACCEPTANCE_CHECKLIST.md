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

- [x] Every screen identifies its data mode (prior browser review in optional synthetic mode, and current Edge review of the default unseeded API mode).
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
- [x] Alert panel identifies stage queues and modeled busy-hours signals by message content. Unrecognized messages use a general planning label (component test and source review).
- [x] Empty alerts doesn't imply real production is normal (copy/source review).
- [x] Navigation to optimizer and scenario works by click and keyboard activation (component tests and the Edge keyboard-only walkthrough).
- [x] Refresh works, updates time only on successful data fetch (failure recovery and stale-response component tests).

## 3. Optimizer & Gantt

- [x] Clicking `Run comparison` calls `/api/schedule/optimize` once with supported body (component test).
- [x] Comparison cards handle improved/worse/unchanged/missing data correctly (component test asserts all four states).
- [x] Percent metric displays changes in percentage points (source review).
- [x] Operations scheduled after 96 hours are inspectable (120-operation, 240-hour component test).
- [x] Dense Gantt remains inspectable. A single-resource component test pages through 1,200 operations, renders 100 bars per page, and opens the last operation.
- [x] Gantt uses consistent relative-hour axis and correct start/end bar geometry (component test and source review).
- [x] Baseline and proposed selections show the corresponding API response dataset (component test and source review).
- [x] Resource rows grouped by stable resource IDs, labels include plant (source review and browser smoke).
- [x] Horizontal and vertical scroll behave at reviewed dense data sizes (browser review; not a stress test).
- [x] Stage legend readable and status not dependent on color alone (source review).
- [x] Operation details show WO, SKU, stage, resource, plant, relative time, batch ID if present, late status, reason (component test and source review).
- [x] Operation details are keyboard-focusable and Escape restores focus (component test and Edge keyboard-only walkthrough).
- [x] Hover opens operation details without moving focus; Escape and horizontal scrolling dismiss the hover card (synthetic Edge browser check; `docs/screenshots/gantt-hover-desktop.png`).
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
- [x] Results show API-returned inputs alongside the submitted snapshot; later edits mark them stale (component test covers differing inputs and unknown IDs).
- [x] Scenario comparison shows returned results, including no change; regression display reviewed in API-derived UI code (component test and source review).
- [x] Due-date impact list is a labeled, keyboard-focusable region; regression test covers earlier/later/unchanged values, signed hours and late-state text.
- [x] Scenario Gantt uses actual scenario response, not a reused optimization timeline (component test and source review).
- [x] Reset works and doesn't silently mutate factory data (source review and isolated real-API smoke, which reset the scenario inputs before a zero-input run).
- [x] Scenario lock-state mapping reviewed; source omission is documented for backend follow-up in `BACKEND_REQUESTS.md` (not changed or run against backend).

## 5. Design and responsiveness

- [ ] Consistent tokens for color, spacing, typography, borders and status semantics (source review is partial; a full token/contrast audit is open).
- [ ] Body text comfortably legible; no unnecessary 7–10px labels (source scan found no 7–10 px font-size declarations; review all screens and states for legibility).
- [x] Desktop 1920×1080 reviewed (`docs/screenshots/flow-desktop-1920.png`).
- [x] Desktop 1440×900 reviewed.
- [x] Laptop 1280×800 reviewed (`docs/screenshots/flow-laptop-1280.png`).
- [x] Tablet ~768×1024 reviewed.
- [x] Mobile ~390×844 reviewed after the CSS width adjustment (`docs/screenshots/flow-mobile-390.png`); KPI and stage cards use two columns and navigation moves to the bottom bar.
- [x] No unintended horizontal page overflow at reviewed viewport sizes. Browser measurements showed `scrollWidth === clientWidth` at desktop 1920, laptop 1280, tablet 768 (753 px client area after vertical scrollbar), and mobile 390 (375 px client area after vertical scrollbar). Populated optimizer and scenario results also passed at 320, 390, 768 and 1440 px in the synthetic browser flow.
- [x] Dense chart and tables use intentional scroll in reviewed browser views. Scenario late-order explanations also use a named keyboard-scrollable region; a 30-order synthetic fixture reached the last entry at 390 px (`docs/screenshots/scenario-late-list-mobile.png`).
- [ ] Hover, focus, disabled, loading, empty and failure states visually consistent. A failed refresh retains a notice after error dismissal; synthetic Edge checks covered failure and recovery at 390 and 1280 px. The dismiss target measures at least 44 px (`docs/screenshots/refresh-error-mobile.png`). Scenario selector and late timeline operation focus were checked in Edge forced-colors emulation (`docs/screenshots/scenario-forced-colors-focus.png`, `docs/screenshots/gantt-forced-colors-focus.png`). At 390 px, keyboard focus on optimizer and scenario timeline controls clears the fixed navigation in normal and forced colors (`scripts/mobile_focus_visibility.py`); other states remain open.
- [ ] Interaction affordances correspond to working actions; no decorative dead buttons.
- [x] A `prefers-reduced-motion` stylesheet rule disables smooth scrolling and reduces animation/transition duration (`src/styles.css`); the synthetic Edge walkthrough also passed with reduced motion emulated; an OS setting has not been checked.
- [x] Keyboard-only walkthrough passed across all three screens in Edge at 1280×800 with synthetic fixtures. It covered seed confirmation dismissal and acceptance, optimization, timeline scroll focus, operation selection and Escape focus restoration, and changing and submitting scenario inputs.
- [x] Form controls have accessible names, help, and error associations. Source review covered all nine native controls; browser checks confirmed scenario labels and help, and component tests cover errors and clearing for all three scenario fields. Screen-reader review remains open.
- [x] Keyboard checks verified focus retention when the native seed confirmation is dismissed and Escape focus restoration in the inline Gantt details. Retrying an unavailable API moves focus to the persistent refresh control before the retry screen is removed; the isolated real-API Edge smoke verifies this. At 390 × 844, a focused operation clears the sticky resource label after horizontal scrolling (`scripts/gantt_focus_check.py`).
- [ ] Color contrast and no color-only status indicators checked (synthetic Edge runs of `scripts/contrast_states.py` measured solid text/background pairs across the initial API failure, empty board, empty optimizer, empty scenario lab, populated board, optimizer, scenario results, stage help, scenario failure, scenario field validation and selected error/detail states at 1280 px and 390 px, with no measured failures; control borders previously measured 3.91:1 against white; the board warning icon measures 6.09:1 against its background and has adjacent text; the Gantt also has a text-labelled operation list; coverage of all states remains open).

## 6. Engineering and tests

- [x] Shared typed API client and types reflect current backend response contract (contract and source review).
- [x] `App.tsx` responsibly refactored rather than blindly replaced (diff review).
- [x] `styles.css` improved with consistent tokens/component boundaries (source review).
- [x] Missing/null/non-finite metric values are not displayed as fabricated zeroes (component test). Malformed successful board, catalog, optimizer, and scenario responses are rejected; a refresh retains the last valid snapshot (API and component tests).
- [x] Pydantic array and object-shaped `detail` values render field locations/messages (unit tests).
- [x] Canceled/stale async requests don't overwrite newer results incorrectly (out-of-order refresh regression test).
- [x] Frontend component/unit tests cover missing metrics, Gantt, error parsing, seed confirmation/cancel, refresh races, comparison states, scenario behavior, and timeline filters.
- [x] Repeatable browser smoke passed with synthetic fixtures and an isolated real API and temporary SQLite DB. `scripts/browser_real_api.py` covers outage/retry, empty onboarding, explicit seed, optimization, timeline interactions, and two scenario runs. A separate smoke passed seed, optimization and a CNC-1 outage against backend `origin/main` at `d9ae616` with a temporary SQLite DB.
- [x] `npm run build` passes.
- [x] `npm run lint` passes.
- [x] Frontend test suite passes.
- [x] Shared timeline layout validated on 1,512 observed intervals from published bottling and CNC records. Published textile scheduling inputs checked separately. See [records and field limits](PUBLIC_DATA_VALIDATION.md).
- [x] Isolated unseeded API verified in Edge at 1440 × 900, 768 × 1024 and 390 × 844. Checks cover all three empty states, text contrast, keyboard refresh, connection recovery and GET-only access. The desktop board, tablet optimizer and phone scenario screenshots were visually reviewed.
- [ ] Populated browser comparison and scenarios verified on approved historical metal injection molding records. Depends on a [permission-cleared snapshot and isolated import](BACKEND_REQUESTS.md#permission-cleared-historical-mim-snapshot).
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
- [x] `CEO_DEMO.md` describes the empty-workspace review and a populated walkthrough with approved historical records, comparison, disruption testing, and plant planner validation.
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
