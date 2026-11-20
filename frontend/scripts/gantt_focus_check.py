"""Check keyboard focus visibility in the horizontally scrolled mobile Gantt.

Start Vite on port 5187, then run python scripts/gantt_focus_check.py.
The API responses are synthetic and all other API calls are blocked.
"""
import json
import os
from playwright.sync_api import sync_playwright, expect

operation = dict(work_order_id='wo-1', wo_number='WO-001', sku_code='SKU-1', resource_id='res-1', resource_name='Molding Cell 1', plant='Synthetic plant', stage='Molding', batch_id='B-42', start_hour=0, end_hour=1, is_late=True, delay_reason=None)
metrics = dict(late_orders=1, avg_wip_age_hours=12, throughput=2, throughput_horizon_hours=168, furnace_batch_efficiency_pct=72, makespan_hours=42, bottleneck_resource_id='res-1', resource_busy_hours={'res-1': 18}, weighted_tardiness_hours=4, schedule_version_id='test-1')
board = dict(total_wip_orders=1, avg_wip_age_hours=4, queues=[dict(stage='Molding', queue_depth=1, avg_wip_age_hours=4)], active_bottleneck_alerts=[])
catalog = dict(resources=[dict(id='res-1', name='Molding Cell 1', plant='Synthetic plant', stage='Molding', status='ACTIVE')], work_orders=[dict(id='wo-1', wo_number='WO-001', sku_code='SKU-1', stage='Molding', status='QUEUED', due_date_hours=24, priority=2)])
optimize = dict(comparison=dict(baseline=metrics, optimized=metrics, delta=dict(late_orders=0, avg_wip_age_hours=0, throughput=0, furnace_batch_efficiency_pct=0)), gantt=dict(baseline=[operation], optimized=[operation]), why_late=dict(baseline=[], optimized=[]))
responses = {'/api/flow-board': board, '/api/catalog': catalog, '/api/schedule/optimize': optimize}

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(channel=os.environ.get('BROWSER_CHANNEL', 'msedge'), headless=True)
    page = browser.new_page(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
    def api(route):
        path = '/' + route.request.url.split('/', 3)[3].split('?', 1)[0]
        assert path in responses, f'Unexpected API request: {path}'
        route.fulfill(status=200, content_type='application/json', body=json.dumps(responses[path]))
    page.route('**/api/**', api)
    page.goto(os.environ.get('INDOFLOW_FRONTEND_URL', 'http://127.0.0.1:5187'), wait_until='networkidle')
    page.get_by_role('button', name='Run comparison').click()
    page.get_by_label('Zoom').select_option('2')
    timeline = page.locator('.gantt').first
    timeline.focus()
    timeline.evaluate('(element) => { element.scrollLeft = 200 }')
    assert timeline.evaluate('(element) => element.scrollLeft') >= 200
    page.keyboard.press('Tab')
    bar = timeline.locator('.gantt-bar').first
    expect(bar).to_be_focused()
    bounds = bar.evaluate('''bar => {
      const timeline = bar.closest('.gantt');
      const resource = bar.closest('.gantt-row').querySelector('.gantt-resource');
      const b = bar.getBoundingClientRect(), t = timeline.getBoundingClientRect(), r = resource.getBoundingClientRect();
      return {left: b.left, right: b.right, resourceRight: r.right,
        viewportRight: t.left + timeline.clientLeft + timeline.clientWidth,
        hit: document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2) === bar || bar.contains(document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2))};
    }''')
    assert bounds['left'] >= bounds['resourceRight'] + 3, bounds
    assert bounds['right'] <= bounds['viewportRight'] - 3, bounds
    assert bounds['hit'], bounds
    page.keyboard.press('Enter')
    page.keyboard.press('Escape')
    expect(bar).to_be_focused()
    browser.close()
print('PASS: mobile keyboard focus and ring clear the sticky resource label and viewport; selection restores focus')
