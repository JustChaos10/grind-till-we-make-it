"""Check list pagination focus with synthetic API responses and local Vite."""
import json
import os
from playwright.sync_api import expect, sync_playwright

operation = dict(work_order_id='wo-1', wo_number='WO-001', sku_code='SKU-1',
    resource_id='res-1', resource_name='Molding Cell 1', plant='Synthetic plant',
    stage='Molding', batch_id=None, start_hour=0, end_hour=1,
    is_late=False, delay_reason=None)
operations = [dict(operation, work_order_id=f'wo-{i}', wo_number=f'WO-{i:03}') for i in range(51)]
metrics = dict(late_orders=0, avg_wip_age_hours=1, throughput=1,
    throughput_horizon_hours=168, furnace_batch_efficiency_pct=72, makespan_hours=42,
    bottleneck_resource_id='res-1', resource_busy_hours={'res-1': 18},
    weighted_tardiness_hours=0, schedule_version_id='test-1')
responses = {
    '/api/flow-board': dict(total_wip_orders=1, avg_wip_age_hours=1, queues=[], active_bottleneck_alerts=[]),
    '/api/catalog': dict(resources=[dict(id='res-1', name='Molding Cell 1', plant='Synthetic plant',
        stage='Molding', status='ACTIVE')], work_orders=[dict(id='wo-1', wo_number='WO-001',
        sku_code='SKU-1', stage='Molding', status='QUEUED', due_date_hours=24, priority=2)]),
    '/api/schedule/optimize': dict(comparison=dict(baseline=metrics, optimized=metrics,
        delta=dict(late_orders=0, avg_wip_age_hours=0, throughput=0, furnace_batch_efficiency_pct=0)),
        gantt=dict(baseline=operations, optimized=operations), why_late=dict(baseline=[], optimized=[])),
}

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(channel=os.environ.get('BROWSER_CHANNEL', 'msedge'), headless=True)
    page = browser.new_page(viewport={'width': 390, 'height': 844})
    def route_api(route):
        path = '/' + route.request.url.split('/', 3)[3].split('?', 1)[0]
        if path not in responses:
            raise AssertionError(f'Unexpected API request: {path}')
        route.fulfill(status=200, content_type='application/json', body=json.dumps(responses[path]))
    page.route('**/api/**', route_api)
    page.goto(os.environ.get('INDOFLOW_FRONTEND_URL', 'http://127.0.0.1:5173') + '/#optimizer', wait_until='networkidle')
    page.get_by_role('button', name='Run optimization').first.click()
    summary = page.get_by_text('Browse operations as a list')
    summary.click()
    page.get_by_role('button', name='WO-000 · Molding · Molding Cell 1 · 0–1h · On time').click()
    expect(page.get_by_role('region', name='Selected operation details')).to_be_focused()
    summary.click()
    page.keyboard.press('Escape')
    expect(summary).to_be_focused()
    summary.click()
    page.get_by_role('button', name='WO-000 · Molding · Molding Cell 1 · 0–1h · On time').click()
    page.get_by_role('button', name='Next operations', exact=True).click()
    page.keyboard.press('Escape')
    expect(summary).to_be_focused()
    browser.close()
print('PASS: hidden and removed list items restore focus to list summary with synthetic data at 390px')
