# IndoFlow frontend design rules

This file records the frontend's product-specific visual and interaction rules. It complements `AGENTS.md`; it does not replace the API contract or the acceptance checklist.

## Product direction

- Product: planning workbench for small manufacturing teams.
- Character: precise, grounded, steady.
- Environment: production planning board, not a generic SaaS control panel.
- Signature: a thin teal route line through the process flow.
- Keep labels and claims tied to API responses. Call seeded fixtures synthetic example data.

## Color and meaning

- Deep green marks primary actions and selected navigation.
- Neutral gray marks structure, labels, and unavailable information.
- Stage colors distinguish manufacturing stages and must always have text labels.
- Late status uses a dashed outline and a text label as well as color.
- Never use green or red alone to imply success, failure, or schedule status.

## Type and density

- Use the existing DM Sans/system sans stack and Georgia only for intentional display emphasis.
- Use readable body text. Do not shrink chart, table, or control text to fit a fixed width.
- Preserve manufacturing units (hours, orders, percent) beside their values.
- Show unknown or absent metrics as an em dash; do not render unknown as zero.

## Components and behavior

- Keep the Gantt domain-specific. Show all API-returned operations; scroll the chart when needed.
- Each operation is a keyboard-focusable control with order, SKU, stage, resource, time range, and late status in its accessible name. Selecting it reveals the same facts as text.
- Keep tables and result lists complete. Bound their height with scrolling, not row truncation.
- Use a clear empty state with an explicit synthetic-data action. Confirm before a database seed/reset.
- Use visible field labels, explain accepted ranges, and distinguish current input from submitted scenario output.
- Every interactive element needs a visible focus ring and touch targets near 44px.
- Honor reduced-motion preferences.

## Responsive rules

- Desktop and tablet retain labeled workspace navigation.
- Phones use labeled bottom navigation; do not leave a narrow icon-only rail beside the page.
- Allow horizontal timeline scrolling with resource names visible. Do not hide essential schedule facts to fit a phone.
- At 320px and browser zoom, page content reflows without losing access to controls or data.

## Data truth

- Separate reference, optimized, and scenario outputs by name.
- Never infer savings or promise solver behavior beyond the backend contract.
- Identify the exact input snapshot and scenario inputs for comparisons.
- Represent unavailable optional metrics as unavailable, not zero.
