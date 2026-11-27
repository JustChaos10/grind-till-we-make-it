# Frontend implementation handoff

## Current state

- The Edge acceptance runner defaults to an unseeded API. To test a populated workspace, it can copy an approved historical SQLite file into a temporary database and use that copy for optimization and a resource-outage scenario. The no-seed path passed on desktop, tablet and phone. A separate check verified that the copy includes committed WAL changes and leaves the source files intact. The populated path awaits approved records. See the [historical validation command](PUBLIC_DATA_VALIDATION.md).
- Windows Narrator in Edge read the three screen headings, refresh progress and gateway recovery message against the isolated, unseeded API. The shared API client now gives recovery steps for HTTP 502, 503 and 504 when the proxy gives no error detail. All 74 frontend tests, lint and the production build passed. The populated screen-reader checks still need approved historical data. See the [Narrator results](FRONTEND_AUDIT.md#manual-screen-reader-check).
- axe-core 4.14.1 reported zero violations across 21 unseeded Edge states at desktop, tablet and phone sizes against backend `d9ae616`. Edge's accessibility tree exposed loading, refresh and retained-data messages as polite live regions, and the connection error as an assertive alert. Headed Edge honored the native Windows reduced-motion setting at all three sizes. The alert dismiss icon keeps its accessible button name and keyboard focus returns to Refresh. See the [phone connection error](screenshots/unseeded-api-error-phone.png) and [scan instructions](FRONTEND_AUDIT.md#reproduce-the-unseeded-accessibility-scan).
- A 300-second Edge rehearsal followed the unseeded narration in [CEO_DEMO.md](../../docs/CEO_DEMO.md). Windows text-to-speech rendered a matching audio track. The board, optimizer and scenario lab loaded at their planned times against the GET-only API. The populated rehearsal and the presenter's spoken run still require approved records.
- The unseeded Edge smoke confirms main landmarks, named navigation destinations and readable hover states. All 600 solid-background text samples met 4.5:1. Nine hover samples met 6.09:1. Review instructions now use an isolated database and disable demo seeding.
- Compact and secondary typography, spacing and corner radii now share the existing design scale across the app and timeline. All 71 frontend tests, the production build and lint passed. Edge forced-colors emulation confirmed visible keyboard focus, navigation, onboarding and disabled run actions across desktop, tablet and phone against the unseeded API.

- On 2026-11-27, Google Dataset Search and source searches led to published bottling, CNC and textile records. The shared Gantt layout passed checks on 1,512 observed intervals. The textile scheduling input was checked separately. See [public data validation](PUBLIC_DATA_VALIDATION.md) for the sources, checksums and field limits.
- Phone users can see when API data is loading, refreshing, or stale. Edge checks passed at 1440 × 900, 768 × 1024 and 390 × 844 against an isolated, unseeded API. Checks cover each empty screen, the 44 px refresh target, keyboard focus, retained data during refresh and after failure, and recovery after an initial connection failure. The lowest contrast ratio among 591 solid-background text samples was 4.69:1. See the [desktop board](screenshots/unseeded-board-desktop.png), [tablet optimizer](screenshots/unseeded-optimizer-tablet.png) and [phone scenario lab](screenshots/unseeded-scenario-phone.png).
- The Gantt clears stale operation details while preserving focus for an unchanged selection. All 71 frontend tests passed. The production build and lint passed with zero warnings.
- Populated factory checks require an approved historical metal injection molding dataset with orders, routes, resources and calendars. Public bottling and CNC records are used for timeline geometry validation. API ingestion or optimizer results based on these files would require unsupported field mappings.

- Scenario validation alerts summarize errors shown beside fields and keep other API messages without exposing field paths. Tests cover mapped, unmapped and late responses. The synthetic 390 px Edge validation flow passed and the updated screenshot was visually reviewed. All 71 frontend tests, build and lint passed; lint retains the existing Gantt effect warning.

- Scenario API validation errors now have visible field messages and error borders, with the existing focus treatment retained. Synthetic Edge checks at 1280 x 800 and 390 x 844 verified invalid controls, text contrast and clearing errors after edits; the mobile screenshot is `screenshots/scenario-validation-errors.png`. All 70 frontend tests, build and lint passed; lint retains the existing Gantt effect warning. This is not a full accessibility audit.

- The flow board and Gantt now share the five-stage MIM configuration in `src/stages.ts`, including the optional CNC label. Stage colors and the route note still assume the current five-stage contract; changing the contract needs a coordinated UI and backend review. All 70 tests, build, lint and the synthetic Edge walkthrough passed; lint retains the existing Gantt effect warning.
- When the API is unavailable, navigation now identifies the selected optimizer or scenario screen, explains what it needs, and moves focus to the destination heading. Edge checks covered both destinations at 390, 768 and 1280 px without document overflow; the 390 px scenario screenshot was visually reviewed. See `screenshots/offline-scenario-390.png`. All 70 frontend tests, build and lint passed; lint retains the existing Gantt effect warning.
- Branch: `feat/frontend-experience`.
- Scope: React frontend and frontend documentation only. No backend logic was changed. The feature branch is pushed to origin.
- The frontend has a clear Flow Board, Schedule Optimizer, and Scenario Lab, with synthetic/demo and read-only messaging.
- Scenario controls submit only supported API inputs. The result view reports API values and compares them with the reference metrics returned by the same scenario request; it does not present modeled deltas as realized savings.
- The Gantt view shows returned operations with proportional durations, resource labels, baseline/optimized selection, and operation details.
- Seed controls require API readiness and user confirmation. The README uses a dedicated `indoflow-demo.db` SQLite database.
- `DESIGN.md` records the design workflow and the use of focused patterns from Taste, Unslop, UI UX Pro Max, Awesome Design MD, and Ant Design references. Ant Design itself was not added as a dependency.

## Verification completed

- The synthetic contrast script now checks hover text on four key board, optimizer, and scenario controls. Edge runs at 1280 and 390 px found no supported solid-color text failures in the sampled states. This does not cover all controls or non-text contrast.

- When a selected Gantt list item is removed by pagination or hidden by collapsing the list, closing its details now returns focus to the list summary. `scripts/gantt_list_focus.py` checked both paths with synthetic data in Edge at 390 px. The 14 Gantt tests and lint passed after the collapsed-list fix; lint retains the existing Gantt effect warning. Before that fix, all 68 frontend tests and the build passed.

- The synthetic contrast check now also covers stage help, scenario failure, and the retained scenario-result notice at 1280 and 390 px. No supported solid-color text pairs failed; this is not a complete contrast or screen-reader audit.

- The scenario impact table keeps work-order identifiers visible during horizontal scrolling. The synthetic Edge walkthrough checks the row header at the right edge at 1280 and 390 px; both screenshots were visually reviewed. All 67 frontend tests, build, and lint passed, with the existing Gantt effect warning.

- Scenario due-date impact now shows the API's delay change as well as completion change. A component regression covers a changed due date and delay with unchanged completion; 67 frontend tests, build, and lint passed. Lint retains the existing Gantt effect warning. The synthetic Edge walkthrough checked the rendered values and keyboard scrolling at 1280 and 390 px; the right edge was visually reviewed in `screenshots/scenario-impact-1280.png` and `screenshots/scenario-impact-390.png`.

- Furnace batch fill comparison values now use percent, while the change uses percentage points. A component regression checks 72%, 77%, and +5 pp; the synthetic Edge walkthrough checks the rendered card. All 67 frontend tests, the production build, and lint passed; lint retains the existing Gantt effect warning.

- Scenario Lab selectors now fill a minimum 44 px touch height. The synthetic Edge mobile check verifies both selectors and keyboard clearance in normal and forced colors; the production build passed.

- The board labels `total_wip_orders` as open work orders and states that quality holds are included, matching the API definition. The contrast script now compares full-precision ratios to the threshold; synthetic initial and empty-state checks at 1280 × 800 and 390 × 844 found no supported solid-color failures. The full frontend suite passed 67 tests and the production build passed. Other contrast states and assistive-technology checks remain open.

- Mobile keyboard focus could be hidden behind the fixed bottom navigation. Mobile scroll padding now keeps focused controls clear. `scripts/mobile_focus_visibility.py` passed at 390×844 for optimizer and scenario timeline controls in normal and forced colors; removing the padding reproduced the failure. Lint passed with the existing Gantt effect warning. This does not replace a full assistive-technology review.

- Throughput captions now use both reported horizons. When a horizon is missing or differs, the UI withholds the change and optimizer comparison bar. Scenario copy describes modeled quantities. Component checks cover matching and differing horizons; the synthetic Edge walkthrough passed before the final bar-only adjustment. Frontend tests: 63 passed; build passed; lint passed with the existing Gantt effect warning.

- The optimizer now describes an empty late-order explanation list without claiming that no orders are late. Its count is labeled as explanations. A fixture with one late order and no explanations passed the component and Edge browser checks. The frontend suite passed 63 tests, build passed, and lint passed with the existing Gantt effect warning.

- The timeline renders at most 100 operations per page. Its count and time axis cover the full filtered schedule, and a notice warns that overlaps may occur on other pages. Page changes clear the selected detail and preserve usable navigation focus. Tests cover 1,200 operations, filtering and shrinking data. Synthetic Edge checks covered 120 operations and the last page at 1280 and 390 px; see `screenshots/gantt-pages-mobile.png`. The full suite passed 61 tests, the build passed, and lint passed with one Gantt effect warning. The filter menus still render all distinct options, so this is not a complete large-data performance guarantee. Screen-reader speech and a founder rehearsal remain open.

- A missing or null WIP age now displays as unavailable without an hours suffix; zero remains a valid measured value. The board response types match the validator's optional fields. A component test and synthetic Edge checks at 390 and 1280 px cover the missing-age state. Frontend tests: 57 passed; build passed; lint passed with the existing Gantt effect warning.
- Gantt selection remains visible when the same operation is supplied as a cloned object. If the selected operation changes or disappears, the selection is cleared and a status message explains why; focus returns to Stage only when it was inside the removed details. Component tests cover both focus paths. The API has no stable operation ID, so selection continuity across changed data is not available. A synthetic Edge component check also verified focus return and the status message when the operation disappears.
- Added the missing screen-reader-only utility used by existing labels and the new status message. The synthetic Edge walkthrough passed, and the refreshed 320 px board and mobile Gantt screenshots were inspected. Screen-reader speech still needs a manual review.
- The error, empty and loading state colors were reviewed in source; sampled normal text meets 4.5:1 and sampled select and machine icons meet 3:1. This is not a full rendered-state contrast audit.

- Headings and metric values now use the documented sans font stack consistently. The synthetic Edge walkthrough passed after the font change; the 320 px board and mobile Gantt captures were inspected. A singular timeline count wording issue found in that review was corrected and covered by Gantt tests. Full visual-state and token audits remain open.
- A failed optimization or scenario rerun now leaves a persistent notice beside the last successful result, even after the error is dismissed. A successful rerun clears the notice. Component tests and the synthetic Edge browser flow cover both recovery paths.
- A failed refresh now changes the header status to identify the previous snapshot; a successful retry clears it. The empty Scenario Lab now links back to Flow Board and moves focus to its heading. Component tests and the synthetic Edge flow passed, including failure/recovery and empty-state navigation at 390 and 1280 px.
- Scenario late-order explanations now stay in a bounded, keyboard-focusable scroll area. An Edge fixture with 30 synthetic explanations verified keyboard access to the final item at 390 px; `screenshots/scenario-late-list-mobile.png` shows the reviewed result.
- Network failures now explain that the API connection failed, while request cancellation is preserved. Synthetic Edge checks covered loading and offline states at 1440, 1280 and 390 px, including retry focus; actual screen-reader speech remains unverified.
- Workspace navigation now moves focus to the destination heading, including repeated activation. A component regression and `scripts/keyboard_acceptance.py` passed with synthetic fixtures in headless Edge at 1280 × 800. When the board cannot be loaded, its content heading is unavailable; screen-reader review remains open.
- Shared the existing scenario accent color through a token without changing its value. The full token and visual-state audit remains open. Repeated 8 px and 12 px gaps and padding, and 8–12 px radii, now also use shared tokens with their original values; other literals still need review.
- Optimization now announces progress and completion on every run through a persistent status region; failures use the existing alert. The API error dismiss control has 4.94:1 text contrast against its banner. Synthetic component tests and the Edge fixture flow cover these changes; actual screen-reader speech remains unverified.

- Frontend unit tests: `npm test -- --run` — 52 tests passed across six files.
- Production build: `npm run build` — passed.
- Lint and formatting: `npm run lint` — passed.
- `git diff --check` — passed.
- Backend regression suite: `.venv\Scripts\python.exe -m pytest -q` — 23 passed. `.venv\Scripts\python.exe -m ruff check .` — passed. Backend source was not changed. Global Python 3.13 lacks `aiosqlite`; use the repository `.venv` (Python 3.12).
- Local API health returned `ready`. The read-only Flow Board response and rendered UI showed 150 synthetic work orders, a 31.53h average WIP age, stage queues 56/25/26/24/19, and two API-returned alerts. The startup command used `DATABASE_URL=sqlite+aiosqlite:///./indoflow-demo.db`, `APP_ENV=development`, and refused to start if that DB file already existed. That demo database was read only during this review. The isolated browser smoke confirmed seeding in its temporary database.
- Local browser review exercised the Flow Board with 150 synthetic work orders, the optimizer with 524 returned operations, and a CNC-1 downtime scenario. The Flow Board was visually reviewed at 1920×1080, 1280×800, 768×1024, and 390×844; screenshots are `screenshots/flow-desktop-1920.png`, `flow-laptop-1280.png`, `flow-tablet-768.png`, and `flow-mobile-390.png`. At all four CSS viewport widths the document had no horizontal overflow; tablet and phone client widths are 753 px and 375 px after the vertical scrollbar. Dense Gantt content stays in its own scroll region. Browser review also covered the optimizer and Scenario Lab; the scenario request completed after about 20 seconds in this local run, which should be reviewed with the backend owner.
- A keyboard-only Edge walkthrough exercised onboarding, seed confirmation, optimization, timeline scrolling and details, scenario inputs and submission. Scenario input labels and linked help resolved in the browser. A 1440 px browser check found no sampled text below 4.5:1 on the fixture board or optimizer and scenario results. Full state contrast and assistive-technology review remain open.

- Compatibility smoke used the backend at `origin/main` commit `d9ae616` in an isolated worktree with a temporary SQLite database. Empty onboarding rendered, and confirmed seed (150 orders), optimization, and a CNC-1 outage simulation each returned HTTP 200 and rendered. The smoke used the working frontend checkout. Alert classification was corrected and tested separately after that run.

## Final implementation update

- Corrected the timeline to describe hours from the model planning origin. Gantt details now show duration, batch or no batch, and modeled-operation provenance, including in the accessible description. Starting optimization moves focus to its heading so focus is not lost when the initiating control is disabled or removed. Component tests and the synthetic Edge browser flow passed; screen-reader speech remains unverified.

- Reworked the stage flow, planning hierarchy, and responsive schedule layout. The Gantt keeps the timeline and resource labels together, with keyboard selection, focus restoration, filters, zoom, and a text view of returned operation details. Queue and late-order actions connect the board, timeline, and Scenario Lab. A component test inspects the last operation in a schedule of 1,200 operations on one resource.
- Classified board alerts by message content, with distinct labels for stage queues and modeled busy-hours signals and a general label for other alerts (`fe3ad6b`).
- Added shared typed API response definitions in `src/types.ts` and hardened the Flow Board, optimizer, and scenario interactions around supported response data.
- Expanded regression tests for empty-database onboarding, seed confirmation, demand bounds, disabled empty scenarios, dense/long-horizon Gantt operations, operation details and Escape focus restoration, submitted scenario snapshots, Pydantic error arrays, and unavailable metric formatting.
- At 1280×800 in Edge with synthetic fixtures, the refresh notices were rendered and inspected on both model result screens; mixed pointer and focus use of stage help was also checked. Screenshots are `C:/IndoFlow/stale-optimizer-review.png` and `C:/IndoFlow/stale-scenario-review.png`.
- Scenario field errors clear when their values change; late validation errors do not attach to edited values. A successful board refresh marks earlier model results for rerun, including when refresh overlaps a model request. Stage help remains available across mixed pointer and keyboard use.
- Refresh now announces its progress while retaining the prior snapshot. Secondary text contrast was improved in several empty and result states, the scenario border uses the shared token, and unavailable controls no longer show a wait cursor. A headless Edge check at 1280×800 with a delayed synthetic response confirmed the refresh status and the empty-board disabled cursor.
- Gantt operation details now also open on hover, without moving focus or replacing an activated selection. Escape and timeline scrolling dismiss the hover card. Select and secondary-button borders use a darker control token; sampled borders measured 3.91:1 against white.
- Hover details now close when the pointer leaves the operation and its card, while remaining available when the pointer moves between them. A fixture browser flow checked those transitions, Escape, zoom, and scroll dismissal. Stage help now uses the shared keyboard focus ring, scenario onboarding guidance uses 14 px text, and disabled Gantt controls use the shared unavailable cursor.
- Model responses no longer change the current page after a user navigates away; results remain available on their respective screens. Stage help can be dismissed and reopened by keyboard, and a focused late Gantt operation retains its dashed status marker alongside a focus ring. Unit tests and an Edge fixture flow cover these behaviors.
- Stage help remains open on the first touch and toggles on later taps. A touch-enabled Edge fixture flow checked opening, closing, and reopening at 390 × 844. A separate computed text-contrast sample found no definite failures on populated, empty, unavailable, validation-error, and optimization-error screens at 1280 × 800; it did not cover all control, focus, or assistive-technology states.
- Successful board, catalog, optimization, and scenario responses now receive structural validation before use. Invalid data or JSON reports a recoverable error; a malformed refresh preserves the previous snapshot. Missing metrics remain unavailable rather than becoming zero.
- Scenario results distinguish API-returned inputs from submitted inputs, with names and IDs where known and ID fallback for unknown entries. A regression test covers a response that differs from the request.
- Focusing a Gantt operation scrolls it clear of the sticky resource label. `python scripts/gantt_focus_check.py` passed with Edge at 390 × 844 after horizontal scrolling, including selection and Escape. The shared focus color measured at least 4.34:1 against sampled backgrounds; this is not a full focus audit.
- Reused shared color tokens for matching surface, divider, and positive-status values. A full token audit remains open.
- The flow board's View schedule action now opens the optimizer without starting a solver run. The empty board visibly explains when demo seeding is disabled, and disabled secondary buttons no longer change on hover. Fixture browser and unit tests cover the navigation and seeding message.
- Board shortcuts now move focus to the destination heading. Selecting a Gantt operation moves focus to the named details region, whose description includes the operation fields; Escape or Clear selection returns focus to the control used to open it. Automated checks cannot establish screen-reader announcement quality.
- The timeline offers a paginated operation list with text labels and 44 px minimum-height controls. It follows the timeline filters and provides a practical target for short bars without changing timeline geometry. Component tests cover pagination, filtering and focus return; the fixture browser flow checks selection at phone width.
- A skip control moves keyboard focus past all timeline operations. The 1,200-operation component test and an Edge fixture flow check focus movement; the mobile list screenshot includes the new control.
- Scenario runs announce progress and successful completion in a persistent status region. Tests cover repeat runs and failure feedback; an Edge fixture checks the completion message in the rendered app. Screen-reader speech still needs manual review.
- Named Gantt stage surface and text color tokens reuse the existing colors; the broader token audit is still open.
- A desktop Edge sample of the scenario due-date table measured 5.33:1 for its caption and 16.51:1 for its text against white. This does not establish full-app contrast compliance.
- Extended existing shared tokens to stage and Gantt labels, tracks, and subtle dividers without changing their colors. This is a partial token cleanup, not a completed design-system audit.
- Updated the UI acceptance ledger, implementation audit, backend request list, and founder demo copy to match observed behavior and remaining verification limits.

## Final Git record

- Feature branch: `feat/frontend-experience`.
- Branch base: `6bd4c7e80dff7a2449a71f67fdc2ab290b239e34` (`main` at task setup); the design and browser verification continuation started from `6cce593`.
- Frontend implementation commit: `d2a9ace74bbd3f942a3a66a940069c371d6ef429`.
- The feature branch is pushed to `origin/feat/frontend-experience`; `main` and backend source were not edited. Use `git status --short --branch` and `git log -1` for the current working-tree status and commit.

## Local run commands (PowerShell)

From the repository root, use one terminal for the API:

```powershell
$env:DATABASE_URL = "sqlite+aiosqlite:///./indoflow-review.db"
$env:APP_ENV = "development"
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Use a second terminal for the frontend:

```powershell
cd frontend
$env:VITE_ENABLE_DEMO_SEED = "false"
npm.cmd ci
npm.cmd run dev -- --host 127.0.0.1
```

Open the Vite URL, usually `http://127.0.0.1:5173`. A new review database opens on the empty Flow board. For the required populated review, use an isolated database prepared by the backend owner from approved records. See [backend requests](BACKEND_REQUESTS.md).

## Repeatable browser verification

From `frontend`, with Vite running at `127.0.0.1:5173`, run `python scripts/browser_flow.py`. The script uses Microsoft Edge, Python Playwright, and synthetic API fixtures. It passed schedule navigation without an optimization request, optimization, Gantt hover and horizontal-scroll dismissal, keyboard details and Escape focus restoration, and scenario inputs. The automated fixture walkthrough took 1.57 seconds with reduced motion emulated; it is not a timed spoken rehearsal.

With Vite on `127.0.0.1:5187`, run `python scripts/gantt_focus_check.py` to repeat the mobile keyboard focus check.

For the keyboard navigation check, start Vite on port 5189 and run `python scripts/keyboard_acceptance.py`. Set `INDOFLOW_FRONTEND_URL` to use another local port. The script uses synthetic API fixtures and exercises navigation, a timeline selection, and Escape focus restoration.

Run `python frontend/scripts/browser_real_api.py --empty-only --screenshots "$env:TEMP\IndoFlow-review"` from the repository root. It starts its own local API and Vite processes and uses a temporary unseeded SQLite database. Install backend dependencies in the root `.venv` and Python Playwright in the outer Python environment. The script uses Microsoft Edge. Prior seeded workflow checks are recorded in the acceptance checklist.

The final responsive pass checked all three populated screens at 320, 390, 768, and 1440 px. The optimizer comparison cards stack on narrow phones, and the timeline scrolls inside its panel. All four widths fit the document without horizontal overflow.

## Screenshots

- `screenshots/baseline-board.png` records the board before the current design pass.
- `screenshots/{board,optimizer,scenario}-{desktop,tablet,mobile}.png` record all three screens at desktop, tablet and mobile sizes.
- `screenshots/gantt-list-mobile.png` shows the operation list with synthetic fixture data at 390 × 844.
- `screenshots/board-320-help.png` shows the board and enlarged stage Help controls at 320 px with synthetic fixture data.
- `screenshots/real-api-{board,optimizer,scenario}.png` document the isolated API flow.
- `screenshots/gantt-hover-desktop.png` shows the inspected hover card with synthetic fixture data at 1280×800.
- `screenshots/flow-*.png` preserve the earlier Flow Board viewport review.

## Follow-up

- Stage Help preserves a keyboard dismissal when the pointer enters another stage. Seven StageFlow component tests, the full 69-test frontend suite, and an Edge synthetic-fixture check at 1280 × 800 passed; lint and build passed, with the existing Gantt effect warning. This mixed pointer/keyboard case has not been checked with a screen reader.

- `scripts/contrast_states.py` measures solid text/background pairs across the populated board, optimizer and scenario results, plus selected error and detail states. Synthetic Edge runs at 1280 × 800 and 390 × 844 found no measured failures; the lowest supported ratios were 4.69:1 and 4.74:1 respectively. This does not cover every state, non-text contrast, images, or assistive technology.
- The empty Schedule optimizer explains that work orders are required and offers a link to the Flow board. Component tests verify the disabled run action and no optimization request; synthetic Edge checks covered navigation and overflow at 390 × 844 and 1280 × 844. See `screenshots/empty-optimizer-390.png` and `screenshots/empty-optimizer-1280.png`.
- Screen navigation now uses `#board`, `#optimizer`, and `#scenario`, so a direct link or reload opens the selected screen and browser Back/Forward restores it with heading focus. Unknown hashes fall back to the board. The synthetic Edge flow checked reload and browser history; all 63 frontend tests, lint, and build passed. Lint reports an existing Gantt effect warning.
- Stage Help now hides its detail region when no help is active, matching the controls' collapsed state. Component tests and the synthetic browser flow passed; screen-reader speech remains unverified.
- Timeline range calculation now handles large operation arrays without exceeding the JavaScript argument limit. A regression checks 200,000 synthetic operations; the fixture browser flow covers normal optimization and scenario timelines. Large-chart rendering speed is not verified.
- The disconnected welcome screen explains why demo loading is disabled and associates that help with the button. The isolated real-API smoke checks the disabled state and help association.

- If a refresh removes a selected scenario machine or work order, the draft retains and labels the unavailable ID, explains the problem, and blocks simulation until the selection is corrected. A component test and synthetic Edge flow cover both fields and recovery.
- A failed refresh now leaves a persistent notice that the last successfully loaded snapshot is shown, even after the detailed error is dismissed. The notice clears after a successful refresh. Component tests and the synthetic Edge flow checked failure, dismissal, and recovery; the browser flow checked phone and desktop widths.
- The board warning icon was darkened to 6.09:1 against its background. The isolated real-API smoke passed and the updated `screenshots/real-api-board.png` was inspected. This does not complete the full-state contrast review.
- Key explanatory copy on the board, optimizer and scenario screens now uses 13 px text. The 320 px board and 390 px operation list screenshots were refreshed and inspected; the fixture browser flow passed its viewport overflow checks. Other labels and states still need the full legibility review.
- Operation-list buttons now expose their expanded state and link to the selected details region, matching timeline bars. The Gantt component test covers selection and Escape; screen-reader speech still needs a manual check. The isolated real API walkthrough passed again after the navigation changes.
- See `BACKEND_REQUESTS.md` for requests and `UI_ACCEPTANCE_CHECKLIST.md` for the open acceptance items.
- Have a plant planner validate routings, order data, calendars, and model assumptions before using the results for shop-floor decisions.
- Production use requires a trusted authentication/proxy design. Keep shared API credentials on the server.
- Screen-reader review, full state contrast, and visible focus remain open. Scenario field-error associations are covered by component tests and a source audit; they have not been checked with a screen reader. The five-minute founder presentation requires a spoken rehearsal using `docs/CEO_DEMO.md`.
- A full token audit remains open: colors, spacing, and radii still include literal values across the stylesheets. Review all control states and affordances as listed in the acceptance checklist before calling the design complete.
- Stage Help controls now have a 44 px minimum target. The fixture browser flow checks their dimensions and document width at 320, 390, 768, and 1440 px. Text buttons show an underline on hover; an Edge fixture check confirmed the hover and focus states. These checks do not cover every state or replace screen-reader review.

- The synthetic browser flow now checks document width on populated optimizer and scenario results at 320, 390, 768, and 1440 px, after viewport layout settles. The chart retains its intentional internal scroll.
- Gantt operation-list pagination retains keyboard focus when the first or last page disables its navigation button. Component tests and an Edge check with 51 synthetic operations passed.
- Changing or clearing Gantt filters closes stale operation details; clearing filters returns keyboard focus to Stage. Dismissing an API error returns focus to Refresh data. Component tests and the synthetic Edge walkthrough cover these flows; all 53 frontend tests, lint, and the build passed.
- Repeated surface, text, border, and accent colors now use shared CSS tokens with their original values. Lint, build, and the synthetic Edge walkthrough passed. A complete token and contrast audit remains open.

- Disabled primary and secondary actions now use a muted surface with readable text instead of fading the whole control. The synthetic Edge walkthrough covered an invalid scenario and saved `screenshots/scenario-disabled-mobile.png`; the screenshot was inspected. Other disabled control types still need the full-state contrast review.
- Gantt filter and pagination buttons now share the readable disabled-control colors. The synthetic Edge walkthrough passed, and the updated `screenshots/gantt-list-mobile.png` was inspected.

- Timeline bars now include the stage in their visible label. Narrow bars expose the full stage in hover and selected details and in the operation list. The Gantt component tests and synthetic Edge flow passed; the hover screenshot was inspected. Full non-color status and contrast coverage remains open.
- Removed an unexplained green dot from Flow board navigation; it had no defined status. The synthetic Edge flow and forced-colors keyboard walkthrough passed. `scripts/contrast_states.py` measured 76 rendered text nodes in selected failure, stale-result, operation-detail and scenario states at 1280 × 800; none fell below the applicable threshold (lowest 4.94:1). This covers solid text and backgrounds only, not all states or assistive technology.

- At tablet widths from 621 to 820 px, the header keeps the demo and update status legible by hiding the redundant breadcrumb and avatar. Synthetic Edge checks covered 621, 700, 768, 820 and 821 px; the status lines fit and the document did not overflow. See `screenshots/topbar-tablet-review.png`. The fixture flow, 69 tests, lint and build passed; lint retains the existing Gantt effect warning.

- The footer messages stack at widths up to 820 px to preserve their reading order. Edge layout checks at 320, 390, 621, 768, 820 and 821 px found no page overflow; the production build passed.
