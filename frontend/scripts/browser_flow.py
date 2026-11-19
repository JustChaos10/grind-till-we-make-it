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
    is_late=False, delay_reason=None)
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
scenario = dict(reference_metrics=metrics, scenario_metrics=metrics,
    delta=dict(late_orders=0, avg_wip_age_hours=0, throughput=0, bottleneck_before=None, bottleneck_after=None),
    due_date_impact=[], why_late=[], gantt=[operation])
responses = {'/api/flow-board': board, '/api/catalog': catalog,
    '/api/schedule/optimize': optimize, '/api/schedule/simulate': scenario}
requests = []

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(channel=os.environ.get('BROWSER_CHANNEL', 'msedge'), headless=True)
    context = browser.new_context(viewport={'width': 1280, 'height': 800}, reduced_motion='reduce')
    page = context.new_page()
    def route_api(route):
        request = route.request
        path = '/' + request.url.split('/', 3)[3].split('?', 1)[0]
        requests.append((request.method, path, request.post_data_json if request.post_data else None))
        if path not in responses:
            route.abort()
            raise AssertionError(f'Unexpected API request blocked: {path}')
        route.fulfill(status=200, content_type='application/json', body=json.dumps(responses[path]))
    page.route('**/api/**', route_api)
    started = time.perf_counter()
    page.goto(BASE, wait_until='networkidle')
    assert page.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches")
    expect(page.get_by_role('heading', name='Production flow overview')).to_be_visible()
    page.get_by_role('button', name='Run comparison').click()
    expect(page.get_by_text('Proposed model schedule ready')).to_be_visible()
    bar = page.get_by_role('button', name='WO-001, SKU-1, Molding, Molding Cell 1, 0 to 1 hours, on time, batch B-42')
    bar.focus()
    page.keyboard.press('Enter')
    expect(page.get_by_text('Batch B-42')).to_be_visible()
    expect(page.get_by_role('button', name='Clear selection')).to_be_focused()
    page.keyboard.press('Escape')
    expect(bar).to_be_focused()
    expect(page.get_by_text('Batch B-42')).to_have_count(0)
    page.get_by_role('button', name='Scenario lab').click()
    page.get_by_label('Machine unavailable').select_option('res-1')
    page.get_by_label('Priority rush order').select_option('wo-1')
    slider = page.get_by_role('slider', name='Increase quantities in this model')
    slider.focus()
    for _ in range(25):
        page.keyboard.press('ArrowRight')
    page.get_by_role('button', name='Run scenario').click()
    expect(page.get_by_text('Resource outage: res-1 · Priority order: wo-1 · Demand increase: 25%')).to_be_visible()
    expect(page.get_by_role('heading', name='Scenario schedule')).to_be_visible()
    elapsed = time.perf_counter() - started
    assert ('POST', '/api/schedule/optimize', {'time_limit_seconds': 3}) in requests
    assert ('POST', '/api/schedule/simulate', {'down_resource_ids': ['res-1'],
        'rush_order_ids': ['wo-1'], 'demand_spike_pct': 25, 'time_limit_seconds': 3}) in requests
    assert not any(path == '/api/seed' for _, path, _ in requests)
    browser.close()
print(f'PASS: board, optimization, keyboard selection and focus restore, scenario, reduced motion; synthetic API fixtures; automated walkthrough {elapsed:.2f}s')
