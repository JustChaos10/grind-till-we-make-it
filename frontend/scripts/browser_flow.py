"""Browser smoke test with synthetic API fixtures; never contacts the API.

Start the frontend: npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
Then run: python scripts/browser_flow.py
Requires Python Playwright and Microsoft Edge (or set BROWSER_CHANNEL).
"""
import json
import os
import time
from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get('INDOFLOW_FRONTEND_URL', 'http://127.0.0.1:5173')
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
scenario = dict(scenario_inputs=dict(down_resource_ids=['res-1'], rush_order_ids=['wo-1'], demand_spike_pct=25),
    reference_metrics=metrics, scenario_metrics=metrics,
    delta=dict(late_orders=0, avg_wip_age_hours=0, throughput=0, bottleneck_before=None, bottleneck_after=None),
    due_date_impact=[], why_late=[dict(work_order_id=f'late-{i}', wo_number=f'LATE-{i:03}',
        due_date_hours=24, completion_hours=30, delay_hours=6, priority=2,
        explanation='Synthetic capacity constraint') for i in range(1, 31)], gantt=[operation])
responses = {'/api/flow-board': board, '/api/catalog': catalog,
    '/api/schedule/optimize': optimize, '/api/schedule/simulate': scenario}
requests = []
fail_refresh = False
fail_run = ''

def check_document_width(page):
    for width in (320, 390, 768, 1440):
        page.set_viewport_size({'width': width, 'height': 844})
        # Let media queries and layout settle after resizing before measuring.
        page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
        document_width = page.evaluate('document.documentElement.scrollWidth')
        assert document_width <= width, f'Page overflows at {width}px: {document_width}px'


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(channel=os.environ.get('BROWSER_CHANNEL', 'msedge'), headless=True)
    context = browser.new_context(viewport={'width': 1280, 'height': 800}, reduced_motion='reduce')
    page = context.new_page()
    def route_api(route):
        request = route.request
        path = '/' + request.url.split('/', 3)[3].split('?', 1)[0]
        requests.append((request.method, path, request.post_data_json if request.post_data else None))
        if path == fail_run:
            route.fulfill(status=503, content_type='application/json', body=json.dumps({'detail': 'Synthetic run failure'}))
            return
        if fail_refresh and path == '/api/flow-board':
            route.fulfill(status=503, content_type='application/json', body=json.dumps({'detail': 'Synthetic refresh failure'}))
            return
        if path not in responses:
            route.abort()
            raise AssertionError(f'Unexpected API request blocked: {path}')
        route.fulfill(status=200, content_type='application/json', body=json.dumps(responses[path]))
    page.route('**/api/**', route_api)
    started = time.perf_counter()
    page.goto(BASE, wait_until='networkidle')
    assert page.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches")
    expect(page.get_by_role('heading', name='Production flow overview')).to_be_visible()
    for width in (390, 1280):
        page.set_viewport_size({'width': width, 'height': 844})
        fail_refresh = True
        page.get_by_role('button', name='Refresh data').click()
        expect(page.get_by_role('alert')).to_contain_text('Synthetic refresh failure')
        dismiss = page.get_by_role('button', name='Dismiss')
        bounds = dismiss.bounding_box()
        assert bounds and bounds['width'] >= 44 and bounds['height'] >= 44, 'Error dismiss target is smaller than 44px'
        if width == 390 and os.environ.get('INDOFLOW_ERROR_SCREENSHOT'):
            page.screenshot(path=os.environ['INDOFLOW_ERROR_SCREENSHOT'])
        if width == 1280:
            expect(page.get_by_text('Refresh failed · previous data')).to_be_visible()
        page.get_by_role('button', name='Dismiss').focus()
        page.keyboard.press('Enter')
        expect(page.get_by_role('button', name='Refresh data')).to_be_focused()
        expect(page.get_by_text('Showing the last successfully loaded data. Retry to update it.')).to_be_visible()
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        fail_refresh = False
        page.get_by_role('button', name='Refresh data').click()
        expect(page.get_by_text('Refresh failed', exact=True)).to_have_count(0)
        expect(page.get_by_text('Refresh failed · previous data')).to_have_count(0)
    for width in (320, 390, 768, 1440):
        page.set_viewport_size({'width': width, 'height': 844})
        for button in page.locator('.stage-help').all():
            bounds = button.bounding_box()
            assert bounds and bounds['width'] >= 44 and bounds['height'] >= 44
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        if width == 320:
            page.screenshot(path='docs/screenshots/board-320-help.png', full_page=True)
    page.set_viewport_size({'width': 1280, 'height': 800})
    help_button = page.get_by_role('button', name='About Molding')
    help_button.focus()
    expect(help_button).to_have_attribute('aria-expanded', 'true')
    page.keyboard.press('Space')
    expect(help_button).to_have_attribute('aria-expanded', 'false')
    page.keyboard.press('Space')
    expect(help_button).to_have_attribute('aria-expanded', 'true')
    page.keyboard.press('Escape')
    expect(help_button).to_have_attribute('aria-expanded', 'false')
    page.get_by_role('button', name='View schedule').click()
    expect(page.get_by_role('heading', name='Schedule optimizer', exact=True)).to_be_focused()
    expect(page.get_by_role('heading', name='Generate a proposed schedule')).to_be_visible()
    assert not any(path == '/api/schedule/optimize' for _, path, _ in requests)
    page.get_by_role('button', name='Flow board').first.click()
    page.get_by_role('button', name='Plan for a disruption').click()
    expect(page.get_by_role('heading', name='Scenario lab', exact=True)).to_be_focused()
    page.get_by_role('button', name='Flow board').first.click()
    page.get_by_role('button', name='Run comparison').click()
    expect(page.get_by_text('Proposed model schedule ready')).to_be_visible()
    expect(page.get_by_role('heading', name='Schedule optimizer', exact=True)).to_be_focused()
    expect(page.get_by_text('All returned operations · hours from the model planning origin')).to_be_visible()
    expect(page.get_by_role('status', name='Optimization run status')).to_have_text('Optimization complete. Results are available below.')
    fail_run = '/api/schedule/optimize'
    page.get_by_role('button', name='Run optimization').click()
    expect(page.get_by_role('alert')).to_contain_text('Synthetic run failure')
    page.get_by_role('button', name='Dismiss').click()
    expect(page.get_by_text('The latest optimization failed. Showing the last successful result.')).to_be_visible()
    fail_run = ''
    page.get_by_role('button', name='Run optimization').click()
    expect(page.get_by_text('The latest optimization failed. Showing the last successful result.')).to_have_count(0)
    check_document_width(page)
    page.set_viewport_size({'width': 390, 'height': 844})
    page.get_by_text('Browse operations as a list').click()
    list_button = page.get_by_role('button', name='WO-001 · Molding · Molding Cell 1 · 0–1h · Late')
    expect(list_button).to_be_visible()
    assert list_button.bounding_box()['height'] >= 44
    list_button.scroll_into_view_if_needed()
    page.screenshot(path='docs/screenshots/gantt-list-mobile.png')
    list_button.click()
    expect(page.get_by_role('region', name='Selected operation details')).to_be_focused()
    page.keyboard.press('Escape')
    expect(list_button).to_be_focused()
    page.get_by_text('Browse operations as a list').click()
    page.set_viewport_size({'width': 1280, 'height': 800})
    bar = page.get_by_role('button', name='WO-001, SKU-1, Molding, Molding Cell 1, 0 to 1 hours, late, batch B-42')
    skip = page.get_by_role('button', name='Skip timeline operations')
    skip.focus()
    page.keyboard.press('Enter')
    expect(page.get_by_text('End of timeline')).to_be_focused()
    page.keyboard.press('Tab')
    assert not bar.evaluate('(element) => element === document.activeElement')
    bar.hover()
    hover_detail = page.locator('.gantt-detail[aria-hidden="true"]')
    expect(hover_detail).to_be_visible()
    expect(hover_detail).to_contain_text('Batch B-42')
    if os.environ.get('INDOFLOW_HOVER_SCREENSHOT'):
        page.screenshot(path=os.environ['INDOFLOW_HOVER_SCREENSHOT'])
    hover_detail.hover()
    expect(hover_detail).to_be_visible()
    lane = page.locator('.gantt-lane').first.bounding_box()
    page.mouse.move(lane['x'] + lane['width'] - 5, lane['y'] + lane['height'] / 2)
    expect(hover_detail).to_have_count(0)
    bar.hover()
    expect(hover_detail).to_be_visible()
    page.keyboard.press('Escape')
    expect(hover_detail).to_have_count(0)
    page.get_by_label('Zoom').select_option('2')
    page.mouse.move(0, 0)
    bar.hover()
    expect(hover_detail).to_be_visible()
    timeline = page.locator('.gantt').first
    assert timeline.evaluate('(element) => element.scrollWidth > element.clientWidth')
    timeline.evaluate('(element) => { element.scrollLeft = 100; }')
    expect(hover_detail).to_have_count(0)
    assert timeline.evaluate('(element) => element.scrollLeft > 0')
    bar.focus()
    assert bar.evaluate("element => getComputedStyle(element).outlineStyle") == 'dashed'
    assert bar.evaluate("element => getComputedStyle(element).boxShadow") != 'none'
    page.keyboard.press('Enter')
    expect(page.get_by_text('Batch B-42')).to_be_visible()
    expect(page.get_by_role('region', name='Selected operation details')).to_be_focused()
    page.keyboard.press('Escape')
    expect(bar).to_be_focused()
    expect(page.get_by_text('Batch B-42')).to_have_count(0)
    page.keyboard.press('Enter')
    expect(page.get_by_role('region', name='Selected operation details')).to_be_focused()
    status_filter = page.locator('.gantt-controls label').filter(has_text='Status').locator('select')
    status_filter.select_option('on-time')
    expect(page.get_by_role('region', name='Selected operation details')).to_have_count(0)
    clear_filters = page.get_by_role('button', name='Clear filters (1)')
    clear_filters.focus()
    page.keyboard.press('Enter')
    expect(page.locator('.gantt-controls label').filter(has_text='Stage').locator('select')).to_be_focused()
    expect(page.get_by_role('region', name='Selected operation details')).to_have_count(0)
    page.get_by_role('button', name='Scenario lab').click()
    page.get_by_label('Machine unavailable').select_option('res-1')
    page.get_by_label('Priority rush order').select_option('wo-1')
    slider = page.get_by_role('slider', name='Increase quantities in this model')
    slider.focus()
    for _ in range(25):
        page.keyboard.press('ArrowRight')
    page.get_by_role('button', name='Run scenario').click()
    expect(page.get_by_role('status', name='Scenario run status')).to_have_text('Simulation complete. Results are available below.')
    expect(page.get_by_text('Submitted inputs: Resource outage: Molding Cell 1 (res-1) · Priority order: WO-001 (wo-1) · Demand increase: 25%')).to_be_visible()
    expect(page.get_by_role('heading', name='Scenario schedule')).to_be_visible()
    fail_run = '/api/schedule/simulate'
    page.get_by_role('button', name='Run scenario').click()
    expect(page.get_by_role('alert')).to_contain_text('Synthetic run failure')
    page.get_by_role('button', name='Dismiss').click()
    expect(page.get_by_text('The latest simulation failed. Showing the last successful result.')).to_be_visible()
    fail_run = ''
    page.get_by_role('button', name='Run scenario').click()
    expect(page.get_by_text('The latest simulation failed. Showing the last successful result.')).to_have_count(0)
    check_document_width(page)
    page.set_viewport_size({'width': 390, 'height': 844})
    late_list = page.get_by_role('region', name='Scenario late-order explanations')
    assert late_list.evaluate('(element) => element.scrollHeight > element.clientHeight')
    late_list.focus()
    page.keyboard.press('End')
    expect(late_list.get_by_text('LATE-030')).to_be_in_viewport()
    if os.environ.get('INDOFLOW_SCENARIO_SCREENSHOT'):
        late_list.scroll_into_view_if_needed()
        page.screenshot(path=os.environ['INDOFLOW_SCENARIO_SCREENSHOT'])
    elapsed = time.perf_counter() - started
    assert ('POST', '/api/schedule/optimize', {'time_limit_seconds': 3}) in requests
    assert ('POST', '/api/schedule/simulate', {'down_resource_ids': ['res-1'],
        'rush_order_ids': ['wo-1'], 'demand_spike_pct': 25, 'time_limit_seconds': 3}) in requests
    assert not any(path == '/api/seed' for _, path, _ in requests)
    responses['/api/catalog'] = dict(
        resources=[dict(catalog['resources'][0], status='DOWN')],
        work_orders=[dict(catalog['work_orders'][0], id='wo-2')])
    page.get_by_role('button', name='Refresh data').click()
    machine = page.get_by_label('Machine unavailable')
    rush = page.get_by_label('Priority rush order')
    expect(machine).to_have_value('res-1')
    expect(rush).to_have_value('wo-1')
    expect(page.get_by_text('This machine is no longer available. Choose another option.')).to_be_visible()
    expect(page.get_by_text('This work order is no longer available. Choose another option.')).to_be_visible()
    expect(page.get_by_role('button', name='Run scenario')).to_be_disabled()
    machine.select_option('')
    rush.select_option('wo-2')
    expect(page.get_by_role('button', name='Run scenario')).to_be_enabled()
    responses['/api/catalog'] = catalog
    touch_context = browser.new_context(viewport={'width': 390, 'height': 844},
        is_mobile=True, has_touch=True)
    touch_page = touch_context.new_page()
    touch_page.route('**/api/**', route_api)
    touch_page.goto(BASE, wait_until='networkidle')
    touch_help = touch_page.get_by_role('button', name='About Molding')
    touch_help.tap()
    expect(touch_help).to_have_attribute('aria-expanded', 'true')
    expect(touch_page.get_by_text('Molding forms parts from feedstock.', exact=False)).to_be_visible()
    touch_help.tap()
    expect(touch_help).to_have_attribute('aria-expanded', 'false')
    touch_help.tap()
    expect(touch_help).to_have_attribute('aria-expanded', 'true')
    touch_context.close()
    responses['/api/flow-board'] = dict(board, total_wip_orders=0, queues=[])
    responses['/api/catalog'] = dict(resources=[], work_orders=[])
    for width in (390, 1280):
        page.set_viewport_size({'width': width, 'height': 844})
        page.reload(wait_until='networkidle')
        page.get_by_role('button', name='Scenario lab').click()
        expect(page.get_by_role('button', name='Run scenario')).to_be_disabled()
        page.get_by_role('button', name='Go to Flow board').click()
        expect(page.get_by_role('heading', name='Production flow overview')).to_be_focused()
        expect(page.get_by_role('heading', name='No work orders in this database')).to_be_visible()
    browser.close()
print(f'PASS: board, optimization, hover and scroll dismissal, keyboard selection and focus restore, scenario, reduced motion; synthetic API fixtures; automated walkthrough {elapsed:.2f}s')
