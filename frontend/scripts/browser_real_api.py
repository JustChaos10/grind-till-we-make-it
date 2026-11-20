"""End-to-end smoke test using an isolated, temporary SQLite database.

Run from frontend: python scripts/browser_real_api.py
Requires Python Playwright, Edge, npm dependencies, and the root .venv.
Starts private API/Vite processes on ephemeral ports; removes only its own temp DB.
"""
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import urllib.request
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / 'frontend'
SCREENSHOTS = FRONTEND / 'docs' / 'screenshots'

def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]

def ready(url, process):
    for _ in range(120):
        if process.poll() is not None:
            raise RuntimeError(f'Process exited before ready: {url}')
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(.25)
    raise RuntimeError(f'Timed out waiting for {url}')

with tempfile.TemporaryDirectory(prefix='indoflow-browser-smoke-') as tmp:
    api_port, web_port = free_port(), free_port()
    while web_port == api_port:
        web_port = free_port()
    api_url = f'http://127.0.0.1:{api_port}'
    web_url = f'http://127.0.0.1:{web_port}'
    env = os.environ.copy()
    env.update(DATABASE_URL='sqlite+aiosqlite:///' + (Path(tmp) / 'isolated.db').as_posix(),
               APP_ENV='development', INDOFLOW_API_TOKEN='', INDOFLOW_ADMIN_TOKEN='',
               VITE_ENABLE_DEMO_SEED='true')
    log = open(Path(tmp) / 'servers.log', 'w', encoding='utf-8')
    processes = []
    try:
        processes.append(subprocess.Popen([str(ROOT / '.venv' / 'Scripts' / 'python.exe'), '-m',
            'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', str(api_port)],
            cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT))
        ready(api_url + '/health', processes[-1])
        # Invoke Vite directly so terminating the process does not leave an npm child behind.
        processes.append(subprocess.Popen(['node', str(FRONTEND / 'node_modules' / 'vite' / 'bin' / 'vite.js'),
            '--host', '127.0.0.1', '--port', str(web_port), '--strictPort'], cwd=FRONTEND,
            env=env, stdout=log, stderr=subprocess.STDOUT))
        ready(web_url, processes[-1])
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel=os.environ.get('BROWSER_CHANNEL', 'msedge'), headless=True)
            page = browser.new_page(viewport={'width': 1280, 'height': 800}, reduced_motion='reduce')
            page.set_default_timeout(30000)
            seen = []
            fail_first = [True]
            def route_api(route):
                req = route.request
                path = '/' + req.url.split('/', 3)[3]
                seen.append((req.method, path, req.post_data_json if req.post_data else None))
                if path == '/api/flow-board' and fail_first[0]:
                    route.fulfill(status=503, content_type='application/json', body='{"detail":"Smoke test outage"}')
                    return
                response = route.fetch(url=api_url + path, timeout=120000)
                route.fulfill(response=response)
            page.route('**/api/**', route_api)
            page.goto(web_url)
            expect(page.get_by_role('alert')).to_contain_text('Smoke test outage')
            seed_button = page.get_by_role('button', name='Load synthetic demo data')
            expect(seed_button).to_be_disabled()
            expect(seed_button).to_have_attribute('aria-describedby', 'welcome-seed-help')
            expect(page.locator('#welcome-seed-help')).to_be_visible()
            fail_first[0] = False
            retry = page.get_by_role('button', name='Retry API connection')
            retry.focus()
            page.keyboard.press('Enter')
            expect(page.get_by_role('heading', name='No open work orders')).to_be_visible()
            expect(page.get_by_role('button', name='Refresh data')).to_be_focused()
            page.once('dialog', lambda dialog: dialog.accept())
            page.get_by_role('button', name='Load synthetic example').click()
            expect(page.get_by_role('heading', name='Production flow overview')).to_be_visible()
            expect(page.get_by_role('heading', name='No open work orders')).to_have_count(0)
            SCREENSHOTS.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(SCREENSHOTS / 'real-api-board.png'), full_page=True)
            page.get_by_role('button', name='Run comparison').click()
            expect(page.get_by_text('Proposed model schedule ready')).to_be_visible(timeout=120000)
            timeline = page.get_by_role('region', name='Schedule timeline. Use the scroll area to review all resources and hours.')
            bar = timeline.locator('button.gantt-bar').first
            expect(bar).to_be_visible()
            bar.focus()
            page.keyboard.press('Enter')
            expect(page.get_by_role('region', name='Selected operation details')).to_be_focused()
            page.keyboard.press('Escape')
            expect(bar).to_be_focused()
            page.get_by_role('button', name='Baseline', exact=True).click()
            expect(timeline.locator('button.gantt-bar').first).to_be_visible()
            page.get_by_role('button', name='Optimized', exact=True).click()
            page.get_by_label('Zoom').select_option('2')
            expect(timeline.locator('.gantt-canvas')).to_have_attribute('style', 'width: 200%;')
            page.locator('.gantt-controls').get_by_label('Status').select_option('late')
            expect(page.get_by_role('button', name='Clear filters (1)')).to_be_enabled()
            page.get_by_role('button', name='Clear filters (1)').click()
            expect(timeline.locator('button.gantt-bar').first).to_be_visible()
            page.screenshot(path=str(SCREENSHOTS / 'real-api-optimizer.png'), full_page=True)
            page.get_by_role('button', name='Scenario lab').click()
            machine = page.get_by_label('Machine unavailable')
            machine.select_option(index=1)
            selected = machine.input_value()
            page.get_by_role('button', name='Run scenario').click()
            expect(page.get_by_text('Scenario inputs returned by the API')).to_be_visible(timeout=120000)
            expect(page.get_by_text(f'({selected})', exact=False).first).to_be_visible()
            expect(page.get_by_role('heading', name='Scenario schedule')).to_be_visible()
            page.screenshot(path=str(SCREENSHOTS / 'real-api-scenario.png'), full_page=True)
            page.get_by_role('button', name='Reset inputs').click()
            expect(page.get_by_role('status').filter(has_text='Inputs changed since this run')).to_be_visible()
            page.get_by_role('button', name='Run scenario').click()
            expect(page.get_by_text('Submitted inputs: Resource outage: none · Priority order: none · Demand increase: 0%')).to_be_visible(timeout=120000)
            assert sum(method == 'POST' and path == '/api/seed' for method, path, _ in seen) == 1
            assert sum(method == 'POST' and path == '/api/schedule/simulate' for method, path, _ in seen) == 2
            assert any(path == '/api/schedule/simulate' and data['down_resource_ids'] == [] and data['demand_spike_pct'] == 0 for _, path, data in seen)
            browser.close()
        print('PASS: isolated real API, outage/retry, empty/seed, optimize, timeline keyboard/tabs, outage and zero-input scenarios')
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], capture_output=True, check=False)
            process.wait(timeout=10)
        log.close()
