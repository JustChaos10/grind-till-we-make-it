"""Exercise keyboard-only navigation with synthetic API data.

Start Vite on port 5189, then run python scripts/keyboard_acceptance.py.
Set INDOFLOW_FRONTEND_URL or BROWSER_CHANNEL to override defaults.
"""
import json
import os
from playwright.sync_api import sync_playwright, expect

operation = dict(work_order_id='wo-1', wo_number='WO-001', sku_code='SKU-1',
    resource_id='res-1', resource_name='Molding Cell 1', plant='Synthetic plant',
    stage='Molding', batch_id='B-42', start_hour=0, end_hour=1,
    is_late=True, delay_reason=None)
metrics = dict(late_orders=1, avg_wip_age_hours=12, throughput=2,
    throughput_horizon_hours=168, furnace_batch_efficiency_pct=72, makespan_hours=42,
    bottleneck_resource_id='res-1', resource_busy_hours={'res-1': 18},
    weighted_tardiness_hours=4, schedule_version_id='test-1')
board = dict(total_wip_orders=1, avg_wip_age_hours=4,
    queues=[dict(stage='Molding', queue_depth=1, avg_wip_age_hours=4)],
    active_bottleneck_alerts=[])
catalog = dict(resources=[dict(id='res-1', name='Molding Cell 1', plant='Synthetic plant',
    stage='Molding', status='ACTIVE')], work_orders=[dict(id='wo-1', wo_number='WO-001',
    sku_code='SKU-1', stage='Molding', status='QUEUED', due_date_hours=24, priority=2)])
optimize = dict(comparison=dict(baseline=metrics, optimized=metrics,
    delta=dict(late_orders=0, avg_wip_age_hours=0, throughput=0, furnace_batch_efficiency_pct=0)),
    gantt=dict(baseline=[operation], optimized=[operation]), why_late=dict(baseline=[], optimized=[]))
responses = {'/api/flow-board': board, '/api/catalog': catalog,
             '/api/schedule/optimize': optimize}


def tab_to(page, target, limit=80):
    """Reach a visible control through the actual sequential focus order."""
    for _ in range(limit):
        page.keyboard.press('Tab')
        if target.evaluate('(element) => element === document.activeElement'):
            assert target.evaluate('(element) => element.matches(":focus-visible")')
            return
    raise AssertionError(f'Could not reach {target} in {limit} Tab presses')


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(channel=os.environ.get('BROWSER_CHANNEL', 'msedge'), headless=True)
    page = browser.new_page(viewport={'width': 1280, 'height': 800}, reduced_motion='reduce',
                            forced_colors=os.environ.get('INDOFLOW_FORCED_COLORS', 'none'))

    def route_api(route):
        path = '/' + route.request.url.split('/', 3)[3].split('?', 1)[0]
        if path not in responses:
            route.abort()
            raise AssertionError(f'Unexpected API request blocked: {path}')
        route.fulfill(status=200, content_type='application/json', body=json.dumps(responses[path]))

    page.route('**/api/**', route_api)
    page.goto(os.environ.get('INDOFLOW_FRONTEND_URL', 'http://127.0.0.1:5189'), wait_until='networkidle')
    tab_to(page, page.get_by_role('button', name='Run comparison'))
    page.keyboard.press('Enter')
    expect(page.get_by_role('heading', name='Schedule optimizer', exact=True)).to_be_focused()
    expect(page.get_by_role('status', name='Optimization run status')).to_have_text('Optimization complete. Results are available below.')
    bar = page.get_by_role('button', name='WO-001, SKU-1, Molding, Molding Cell 1, 0 to 1 hours, late, batch B-42')
    tab_to(page, bar)
    page.keyboard.press('Enter')
    expect(page.get_by_role('region', name='Selected operation details')).to_be_focused()
    page.keyboard.press('Escape')
    expect(bar).to_be_focused()
    scenario_nav = page.get_by_role('button', name='Scenario lab')
    tab_to(page, scenario_nav)
    page.keyboard.press('Enter')
    expect(page.get_by_role('heading', name='Scenario lab', exact=True)).to_be_focused()
    expect(scenario_nav).to_have_attribute("aria-current", "page")
    if os.environ.get('INDOFLOW_FORCED_COLORS') == 'active':
        for label in ('Machine unavailable', 'Priority rush order'):
            control = page.get_by_label(label)
            tab_to(page, control)
            wrapper = control.locator('..')
            assert wrapper.evaluate("element => { const style = getComputedStyle(element); return style.outlineStyle !== 'none' && parseFloat(style.outlineWidth) >= 2; }"), f'{label} has no visible forced-colors focus outline'
            if os.environ.get('INDOFLOW_FOCUS_SCREENSHOT'):
                page.screenshot(path=os.environ['INDOFLOW_FOCUS_SCREENSHOT'])
    board_nav = page.get_by_role('button', name='Flow board').first
    tab_to(page, board_nav)
    page.keyboard.press('Enter')
    expect(page.get_by_role('heading', name='Production flow overview')).to_be_focused()
    expect(board_nav).to_have_attribute('aria-current', 'page')
    browser.close()
print('PASS: keyboard-only navigation, timeline selection, Escape focus restoration, and scenario navigation')
