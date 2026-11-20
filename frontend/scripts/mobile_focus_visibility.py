"""Check mobile keyboard focus is not covered by bottom navigation.

Start Vite at 127.0.0.1:5189, then run python scripts/mobile_focus_visibility.py.
The test uses synthetic API fixtures and never contacts the API.
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
scenario = dict(scenario_inputs=dict(down_resource_ids=['res-1'], rush_order_ids=['wo-1'], demand_spike_pct=25),
    reference_metrics=metrics, scenario_metrics=metrics,
    delta=dict(late_orders=0, avg_wip_age_hours=0, throughput=0, bottleneck_before=None, bottleneck_after=None),
    due_date_impact=[], why_late=[dict(work_order_id=f'late-{i}', wo_number=f'LATE-{i:03}',
        due_date_hours=24, completion_hours=30, delay_hours=6, priority=2,
        explanation='Synthetic capacity constraint') for i in range(1, 31)], gantt=[operation])
responses = {'/api/flow-board': board, '/api/catalog': catalog,
    '/api/schedule/optimize': optimize, '/api/schedule/simulate': scenario}


def tab_to(page, target):
    for _ in range(80):
        page.keyboard.press('Tab')
        if target.evaluate('element => element === document.activeElement'):
            assert target.evaluate('element => element.matches(":focus-visible")')
            return
    raise AssertionError('Target was not reached by Tab')


def check_clear_of_nav(page, target, label):
    tab_to(page, target)
    box = target.bounding_box()
    nav = page.locator('.sidebar').bounding_box()
    assert box and nav, f'{label}: missing bounds'
    assert box['y'] >= 0 and box['y'] + box['height'] + 3 <= nav['y'], (
        f'{label}: focus bounds {box} overlap fixed navigation {nav}')


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(channel=os.environ.get('BROWSER_CHANNEL', 'msedge'), headless=True)
    for colors in ('none', 'active'):
        for screen in ('optimizer', 'scenario'):
            page = browser.new_page(viewport={'width': 390, 'height': 844},
                                    forced_colors=colors, reduced_motion='reduce')
            def route_api(route):
                path = '/' + route.request.url.split('/', 3)[3].split('?', 1)[0]
                if path not in responses:
                    route.abort()
                    raise AssertionError(f'Unexpected API request blocked: {path}')
                route.fulfill(status=200, content_type='application/json', body=json.dumps(responses[path]))
            page.route('**/api/**', route_api)
            page.goto(os.environ.get('INDOFLOW_FRONTEND_URL', 'http://127.0.0.1:5189'), wait_until='networkidle')
            if screen == 'optimizer':
                page.get_by_role('button', name='Run comparison').click()
                expect(page.get_by_role('status', name='Optimization run status')).to_have_text(
                    'Optimization complete. Results are available below.')
            else:
                page.get_by_role('button', name='Scenario lab').click()
                for label in ('Machine unavailable', 'Priority rush order'):
                    box = page.get_by_label(label).bounding_box()
                    assert box and box['height'] >= 44, f'{label}: touch target {box}'
                page.get_by_label('Machine unavailable').select_option('res-1')
                page.get_by_label('Priority rush order').select_option('wo-1')
                page.get_by_role('button', name='Run scenario').click()
                expect(page.get_by_role('heading', name='Scenario schedule')).to_be_visible()
            filters = page.locator('.gantt-controls')
            for label in ('Stage', 'Plant', 'Resource', 'Work order', 'Status', 'Zoom'):
                target = filters.locator('label').filter(has_text=label).locator('select')
                check_clear_of_nav(page, target, f'{screen}/{colors}/{label}')
            check_clear_of_nav(page, page.get_by_role('button', name='Skip timeline operations'),
                               f'{screen}/{colors}/skip timeline')
            page.close()
            print(f'PASS: {screen}, forced colors {colors}: mobile controls clear bottom navigation')
    browser.close()
