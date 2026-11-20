# Frontend implementation handoff

## Current state

- Branch: `feat/frontend-experience`.
- Scope: React frontend and frontend documentation only. No backend logic was changed and nothing was pushed.
- The frontend has a clear Flow Board, Schedule Optimizer, and Scenario Lab, with synthetic/demo and read-only messaging.
- Scenario controls submit only supported API inputs. The result view reports API values and compares them with the reference metrics returned by the same scenario request; it does not present modeled deltas as realized savings.
- The Gantt view shows returned operations with proportional durations, resource labels, baseline/optimized selection, and operation details.
- Seed controls require API readiness and user confirmation. The README uses a dedicated `indoflow-demo.db` SQLite database.
- `DESIGN.md` records the design workflow and the use of focused patterns from Taste, Unslop, UI UX Pro Max, Awesome Design MD, and Ant Design references. Ant Design itself was not added as a dependency.

## Verification completed

- Optimization now announces progress and completion on every run through a persistent status region; failures use the existing alert. The API error dismiss control has 4.94:1 text contrast against its banner. Synthetic component tests and the Edge fixture flow cover these changes; actual screen-reader speech remains unverified.

- Frontend unit tests: `npm test -- --run` — 48 tests passed across five files.
- Production build: `npm run build` — passed.
- Lint and formatting: `npm run lint` — passed.
- `git diff --check` — passed.
- Backend regression suite: `.venv\Scripts\python.exe -m pytest -q` — 23 passed. `.venv\Scripts\python.exe -m ruff check .` — passed. Backend source was not changed. Global Python 3.13 lacks `aiosqlite`; use the repository `.venv` (Python 3.12).
- Local API health returned `ready`. The read-only Flow Board response and rendered UI showed 150 synthetic work orders, a 31.53h average WIP age, stage queues 56/25/26/24/19, and two API-returned alerts. The startup command used `DATABASE_URL=sqlite+aiosqlite:///./indoflow-demo.db`, `APP_ENV=development`, and refused to start if that DB file already existed. That demo database was read only during this review. The isolated browser smoke confirmed seeding in its temporary database.
- Local browser review exercised the Flow Board with 150 synthetic work orders, the optimizer with 524 returned operations, and a CNC-1 downtime scenario. The Flow Board was visually reviewed at 1920×1080, 1280×800, 768×1024, and 390×844; screenshots are `screenshots/flow-desktop-1920.png`, `flow-laptop-1280.png`, `flow-tablet-768.png`, and `flow-mobile-390.png`. At all four CSS viewport widths the document had no horizontal overflow; tablet and phone client widths are 753 px and 375 px after the vertical scrollbar. Dense Gantt content stays in its own scroll region. Browser review also covered the optimizer and Scenario Lab; the scenario request completed after about 20 seconds in this local run, which should be reviewed with the backend owner.
- A keyboard-only Edge walkthrough exercised onboarding, seed confirmation, optimization, timeline scrolling and details, scenario inputs and submission. Scenario input labels and linked help resolved in the browser. A 1440 px browser check found no sampled text below 4.5:1 on the fixture board or optimizer and scenario results. Full state contrast and assistive-technology review remain open.

- Compatibility smoke used the backend at `origin/main` commit `d9ae616` in an isolated worktree with a temporary SQLite database. Empty onboarding rendered, and confirmed seed (150 orders), optimization, and a CNC-1 outage simulation each returned HTTP 200 and rendered. The smoke used the working frontend checkout. Alert classification was corrected and tested separately after that run.

## Final implementation update

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
- No changes were pushed; `main` and backend source were not edited. The final documentation commit SHA and working-tree status are reported in the handoff message.

## Local run commands (PowerShell)

From the repository root, use one terminal for the API:

```powershell
$env:DATABASE_URL = "sqlite+aiosqlite:///./indoflow-demo.db"
$env:APP_ENV = "development"
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Use a second terminal for the frontend:

```powershell
cd frontend
$env:VITE_ENABLE_DEMO_SEED = "true"
npm ci
npm run dev -- --host 127.0.0.1
```

Open the Vite URL, usually `http://localhost:5173`. Load synthetic data only in the dedicated demo database. See the root README for the explicit seed warning.

## Repeatable browser verification

From `frontend`, with Vite running at `127.0.0.1:5173`, run `python scripts/browser_flow.py`. The script uses Microsoft Edge, Python Playwright, and synthetic API fixtures. It passed schedule navigation without an optimization request, optimization, Gantt hover and horizontal-scroll dismissal, keyboard details and Escape focus restoration, and scenario inputs. The automated fixture walkthrough took 1.57 seconds with reduced motion emulated; it is not a timed spoken rehearsal.

With Vite on `127.0.0.1:5187`, run `python scripts/gantt_focus_check.py` to repeat the mobile keyboard focus check.

Run `python scripts/browser_real_api.py` from `frontend` for the isolated API smoke. It starts its own local API and Vite processes, uses a temporary synthetic SQLite database, and passed retry, empty onboarding, explicit seed confirmation, optimization, keyboard timeline selection, baseline and proposed tabs, status filtering, zoom, an outage scenario, and a reset followed by a zero-input scenario. The root `.venv` must have the backend dependencies installed. Python Playwright and Microsoft Edge are also required.

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

- See `BACKEND_REQUESTS.md` for requests and `UI_ACCEPTANCE_CHECKLIST.md` for the open acceptance items.
- Have a plant planner validate routings, order data, calendars, and model assumptions before using the results for shop-floor decisions.
- Production use requires a trusted authentication/proxy design. Keep shared API credentials on the server.
- Screen-reader review, full state contrast, and visible focus remain open. Scenario field-error associations are covered by component tests and a source audit; they have not been checked with a screen reader. The five-minute founder presentation requires a spoken rehearsal using `docs/CEO_DEMO.md`.
- A full token audit remains open: colors, spacing, and radii still include literal values across the stylesheets. Review all control states and affordances as listed in the acceptance checklist before calling the design complete.
- Stage Help controls now have a 44 px minimum target. The fixture browser flow checks their dimensions and document width at 320, 390, 768, and 1440 px. Text buttons show an underline on hover; an Edge fixture check confirmed the hover and focus states. These checks do not cover every state or replace screen-reader review.
