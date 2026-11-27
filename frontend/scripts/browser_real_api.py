"""End-to-end smoke test using an isolated, temporary SQLite database.

Run from frontend: python scripts/browser_real_api.py
Use --historical-db with an approved SQLite snapshot to verify populated workflows.
Use --synthetic to opt in to the legacy synthetic demo smoke test.
Requires Python Playwright, Edge, npm dependencies, and the root .venv.
Starts private API/Vite processes on ephemeral ports. A historical source is opened read-only.
"""
import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import tempfile
import time
import urllib.request
from playwright.sync_api import sync_playwright, expect
from measure_contrast import check as check_text_contrast

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / 'frontend'
SCREENSHOTS = FRONTEND / 'docs' / 'screenshots'


def copy_snapshot(source_path, destination_path):
    # SQLite's backup includes committed WAL transactions and leaves the source read-only.
    with closing(sqlite3.connect(source_path.resolve().as_uri() + '?mode=ro', uri=True)) as source:
        with closing(sqlite3.connect(destination_path)) as destination:
            source.backup(destination)


def capture_screen(page, screenshots, name):
    if screenshots is not None:
        screenshots.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(screenshots / f'{name}.png'), full_page=True)


def check_populated(page, screenshots, outage_resource_id):
    expect(page.get_by_role('heading', name='Production flow overview')).to_be_visible()
    expect(page.get_by_role('heading', name='No open work orders')).to_have_count(0)
    capture_screen(page, screenshots, 'real-api-board')

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
    capture_screen(page, screenshots, 'real-api-optimizer')

    page.get_by_role('button', name='Scenario lab').click()
    machine = page.get_by_label('Machine unavailable')
    if outage_resource_id is None:
        machine.select_option(index=1)
        outage_resource_id = machine.input_value()
    else:
        machine.select_option(value=outage_resource_id)
    page.get_by_role('button', name='Run scenario').click()
    expect(page.get_by_text('Scenario inputs returned by the API')).to_be_visible(timeout=120000)
    expect(page.get_by_text(f'({outage_resource_id})', exact=False).first).to_be_visible()
    expect(page.get_by_role('heading', name='Scenario schedule')).to_be_visible()
    capture_screen(page, screenshots, 'real-api-scenario')
    page.get_by_role('button', name='Reset inputs').click()
    expect(page.get_by_role('status').filter(has_text='Inputs changed since this run')).to_be_visible()
    page.get_by_role('button', name='Run scenario').click()
    expect(page.get_by_text('Submitted inputs: Resource outage: none · Priority order: none · Demand increase: 0%')).to_be_visible(timeout=120000)


def check_schedule_requests(seen, outage_resource_id):
    optimize = [data for method, path, data in seen if method == 'POST' and path == '/api/schedule/optimize']
    simulate = [data for method, path, data in seen if method == 'POST' and path == '/api/schedule/simulate']
    assert len(optimize) == 1 and len(simulate) == 2, 'Expected one comparison and two scenarios.'
    assert len(simulate[0]['down_resource_ids']) == 1, 'Expected one resource in the outage scenario.'
    if outage_resource_id is not None:
        assert simulate[0]['down_resource_ids'] == [outage_resource_id], 'Unexpected outage resource.'
    assert simulate[1]['down_resource_ids'] == [], 'Expected no resource outage after reset.'
    assert all(request['rush_order_ids'] == [] and request['demand_spike_pct'] == 0 for request in simulate), (
        'Expected no priority orders or demand changes in either scenario.'
    )


def check_historical_catalog(api_url, outage_resource_id):
    with urllib.request.urlopen(api_url + '/api/catalog', timeout=10) as response:
        catalog = json.load(response)
    if not catalog['work_orders']:
        raise SystemExit('Historical check requires a snapshot with schedulable work orders.')
    if not any(resource['id'] == outage_resource_id and resource['status'] == 'ACTIVE'
               for resource in catalog['resources']):
        raise SystemExit('The requested outage resource must be active in the copied snapshot.')

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

def check_accessibility(page, axe_script, scope):
    if axe_script is None:
        return
    if not page.evaluate("typeof window.axe !== 'undefined'"):
        page.add_script_tag(path=str(axe_script))
    result = page.evaluate("""async () => {
        const { testEngine, violations, incomplete } = await axe.run({
            runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'] },
        });
        return {
            version: testEngine.version,
            violations: violations.map(rule => ({
                id: rule.id,
                targets: rule.nodes.map(node => node.target),
            })),
            manual: incomplete.map(rule => ({
                id: rule.id,
                targets: rule.nodes.map(node => node.target),
            })),
        };
    }""")
    assert not result['violations'], f"{scope}: {result['violations']}"
    manual = result['manual'] or 'none flagged'
    print(f"PASS: axe-core {result['version']}, {scope}, no violations; manual review: {manual}")


def check_live_region(session, role, priority, message):
    nodes = session.send('Accessibility.getFullAXTree')['nodes']
    by_id = {node['nodeId']: node for node in nodes}
    for node in nodes:
        if node['ignored'] or node.get('role', {}).get('value') != role:
            continue
        pending = list(node.get('childIds', []))
        while pending:
            child = by_id[pending.pop()]
            if child.get('role', {}).get('value') == 'StaticText' and message in child['name']['value']:
                properties = {item['name']: item['value']['value'] for item in node['properties']}
                assert properties.get('live') == priority, properties
                assert properties.get('atomic') is True, properties
                return
            pending.extend(child.get('childIds', []))
    raise AssertionError(f'Edge accessibility tree has no {role} containing {message!r}')


def check_unseeded(browser, web_url, api_url, screenshots, axe_script, system_reduced_motion):
    screens = (
        ('Flow board', 'Production flow overview', 'No open work orders', None, 'board'),
        ('Schedule optimizer', 'Schedule optimizer', 'No work orders to schedule', 'Run optimization', 'optimizer'),
        ('Scenario lab', 'Scenario lab', 'No schedulable work orders are available.', 'Run scenario', 'scenario'),
    )
    viewports = ((1440, 900, 'desktop'), (768, 1024, 'tablet'), (390, 844, 'phone'))
    screenshots.mkdir(parents=True, exist_ok=True)
    for capture, (width, height, device) in enumerate(viewports):
        page = browser.new_page(
            viewport={'width': width, 'height': height},
            reduced_motion='null' if system_reduced_motion else 'reduce',
        )
        accessibility = page.context.new_cdp_session(page)
        requests = []
        connection_interrupted = False
        reads_held = True
        pending_reads = []

        def forward_read(route, path):
            route.fulfill(response=route.fetch(url=api_url + path))

        def release_reads():
            nonlocal reads_held
            reads_held = False
            for route, path in pending_reads:
                forward_read(route, path)
            pending_reads.clear()

        def route_api(route):
            path = route.request.url.removeprefix(web_url)
            requests.append((route.request.method, path))
            if route.request.method != 'GET':
                route.abort()
                return
            if connection_interrupted and path == '/api/flow-board':
                route.abort('connectionfailed')
                return
            if reads_held:
                pending_reads.append((route, path))
                return
            forward_read(route, path)

        page.route('**/api/**', route_api)
        page.goto(web_url, wait_until='domcontentloaded')
        expect(page.get_by_role('heading', name='Loading factory data')).to_be_visible()
        expect(page.get_by_role('status').filter(has_text='Loading API data')).to_be_visible()
        check_live_region(accessibility, 'status', 'polite', 'Loading API data')
        assert page.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches"), (
            'Enable reduced motion in your OS before using --system-reduced-motion.'
        )
        motion = page.locator('html').evaluate("""element => {
            const style = getComputedStyle(element);
            return {
                scrollBehavior: style.scrollBehavior,
                animationSeconds: parseFloat(style.animationDuration),
                animationIterations: style.animationIterationCount,
                transitionSeconds: parseFloat(style.transitionDuration),
            };
        }""")
        assert motion['scrollBehavior'] == 'auto' and motion['animationIterations'] == '1', motion
        assert motion['animationSeconds'] <= 0.00001 and motion['transitionSeconds'] <= 0.00001, motion
        motion_source = 'system setting' if system_reduced_motion else 'browser emulation'
        print(f'PASS: {device}: reduced motion via {motion_source}')
        assert check_text_contrast(f'{device}: initial load', page.locator('body')) == 0
        check_accessibility(page, axe_script, f'{device}: initial load')
        release_reads()
        board_heading = page.get_by_role('heading', name='No open work orders')
        expect(board_heading).to_be_visible()
        expect(page.get_by_role('main')).to_be_visible()
        refresh = page.get_by_role('button', name='Refresh data')
        target = refresh.bounding_box()
        assert target and target['width'] >= 44 and target['height'] >= 44, target
        page.keyboard.press('Tab')
        for _ in range(10):
            if refresh.evaluate("element => element.matches(':focus-visible')"):
                break
            page.keyboard.press('Tab')
        expect(refresh).to_be_focused()
        expect(refresh).to_have_css('outline-style', 'solid')
        expect(refresh).to_have_css('outline-width', '3px')
        reads_held = True
        with page.expect_response('**/api/flow-board') as board_response, page.expect_response('**/api/catalog') as catalog_response:
            page.keyboard.press('Enter')
            expect(board_heading).to_be_visible()
            expect(page.get_by_role('status').filter(has_text='Refreshing API data')).to_be_visible()
            check_live_region(accessibility, 'status', 'polite', 'Refreshing API data')
            expect(refresh).to_be_focused()
            assert check_text_contrast(f'{device}: refresh in progress', page.locator('body')) == 0
            check_accessibility(page, axe_script, f'{device}: refresh in progress')
            release_reads()
        assert board_response.value.json()['total_wip_orders'] == 0
        assert catalog_response.value.json()['work_orders'] == []
        expect(board_heading).to_be_visible()
        expect(page.get_by_role('button', name='Run comparison')).to_be_disabled()

        for index, (nav, title, empty_message, action, filename) in enumerate(screens):
            nav_button = page.get_by_role('navigation').get_by_role('button', name=nav, exact=True)
            if index:
                nav_button.click()
                expect(page.get_by_role('heading', name=title, exact=True)).to_be_focused()
            expect(nav_button).to_have_attribute('aria-current', 'page')
            expect(page.get_by_text(empty_message, exact=True)).to_be_visible()
            if index != 1:
                expect(page.get_by_text('factory data administrator', exact=False)).to_be_visible()
            expect(page.get_by_text('synthetic', exact=False)).to_have_count(0)
            expect(page.get_by_text('demo data only', exact=False)).to_have_count(0)
            if action:
                expect(page.get_by_role('button', name=action, exact=True)).to_be_disabled()
            assert page.evaluate('document.documentElement.scrollWidth <= document.documentElement.clientWidth'), (device, nav)
            assert check_text_contrast(f'{device}: {nav}', page.locator('body')) == 0
            check_accessibility(page, axe_script, f'{device}: {nav}')
            if index == capture:
                page.screenshot(path=str(screenshots / f'unseeded-{filename}-{device}.png'))
            if action:
                back = page.get_by_role('button', name='Go to Flow board')
                back.hover()
                assert check_text_contrast(f'{device}: {nav} return link hover', back) == 0
                back.focus()
                page.keyboard.press('Enter')
                expect(page.get_by_role('heading', name='Production flow overview')).to_be_focused()

        connection_interrupted = True
        refresh.press('Enter')
        expect(page.get_by_role('alert')).to_be_visible()
        expect(board_heading).to_be_visible()
        failed_refresh = page.get_by_role('status').filter(has_text='Showing the last successfully loaded data')
        expect(failed_refresh).to_be_visible()
        check_live_region(accessibility, 'status', 'polite', 'Showing the last successfully loaded data')
        assert check_text_contrast(f'{device}: refresh failed', page.locator('body')) == 0
        check_accessibility(page, axe_script, f'{device}: refresh failed')
        dismiss = page.get_by_role('button', name='Dismiss', exact=True)
        target = dismiss.bounding_box()
        assert target and target['width'] >= 44 and target['height'] >= 44, target
        expect(dismiss.locator('svg')).to_have_attribute('aria-hidden', 'true')
        dismiss.press('Enter')
        expect(refresh).to_be_focused()
        expect(page.get_by_role('alert')).to_have_count(0)
        expect(failed_refresh).to_be_visible()
        connection_interrupted = False
        refresh.press('Enter')
        expect(failed_refresh).to_have_count(0)
        expect(board_heading).to_be_visible()

        connection_interrupted = True
        page.reload()
        expect(page.get_by_role('alert')).to_be_visible()
        check_live_region(accessibility, 'alert', 'assertive', 'Something needs attention')
        retry = page.get_by_role('button', name='Retry API connection')
        expect(retry).to_be_enabled()
        assert check_text_contrast(f'{device}: connection interrupted', page.locator('body')) == 0
        check_accessibility(page, axe_script, f'{device}: connection interrupted')
        if device == 'phone':
            page.screenshot(path=str(screenshots / 'unseeded-api-error-phone.png'))
        retry.hover()
        assert check_text_contrast(f'{device}: retry hover', retry) == 0
        connection_interrupted = False
        retry.press('Enter')
        expect(board_heading).to_be_visible()
        expect(refresh).to_be_focused()
        expect(page.get_by_role('alert')).to_have_count(0)

        page.emulate_media(forced_colors='active')
        assert page.evaluate("matchMedia('(forced-colors: active)').matches")
        expect(refresh).to_be_focused()
        expect(refresh).to_have_css('outline-style', 'solid')
        expect(refresh).to_have_css('outline-width', '3px')
        for nav, _, empty_message, action, _ in screens:
            nav_button = page.get_by_role('navigation').get_by_role('button', name=nav, exact=True)
            nav_button.press('Enter')
            expect(nav_button).to_have_attribute('aria-current', 'page')
            expect(page.get_by_text(empty_message, exact=True)).to_be_visible()
            if action:
                expect(page.get_by_role('button', name=action, exact=True)).to_be_disabled()

        assert set(requests) == {('GET', '/api/flow-board'), ('GET', '/api/catalog')}, requests
        accessibility.detach()
        page.close()
        print(f'PASS: {device} ({width}×{height}), loading, empty screens, keyboard actions, refresh and outage recovery, live regions, forced colors, read-only API')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--empty-only', action='store_true', help='Verify an isolated API with no factory records (default).')
    mode.add_argument('--historical-db', type=Path, help='Approved historical SQLite snapshot to copy read-only.')
    mode.add_argument('--synthetic', action='store_true', help='Opt in to seeding a temporary synthetic demo database.')
    parser.add_argument('--outage-resource-id', help='Active resource with a feasible outage, required for --historical-db.')
    parser.add_argument('--screenshots', type=Path, help='Directory for screenshots. Historical mode captures only when supplied.')
    parser.add_argument('--axe-script', type=Path, help='Path to a local axe.min.js for the unseeded WCAG scan.')
    parser.add_argument('--system-reduced-motion', action='store_true',
                        help='Use the OS reduced-motion setting in headed Edge. Requires --empty-only and reduced motion enabled.')
    parser.add_argument('--backend-root', type=Path, default=ROOT,
                        help='Backend checkout to launch with the local virtual environment.')
    args = parser.parse_args()
    empty_only = not (args.synthetic or args.historical_db)
    if args.historical_db:
        if not args.historical_db.is_file():
            parser.error('--historical-db must point to a readable SQLite snapshot')
        if not args.outage_resource_id:
            parser.error('--historical-db requires --outage-resource-id')
        if args.screenshots is not None:
            capture_folder = args.screenshots.resolve()
            if any(capture_folder.is_relative_to(repo.resolve()) for repo in (ROOT, args.backend_root)):
                parser.error('--historical-db requires a screenshot directory outside both checkouts')
    elif args.outage_resource_id:
        parser.error('--outage-resource-id requires --historical-db')
    if args.axe_script is not None and (not empty_only or not args.axe_script.is_file()):
        parser.error('--axe-script requires --empty-only and a readable axe.min.js file')
    if args.system_reduced_motion and not empty_only:
        parser.error('--system-reduced-motion requires --empty-only')
    if not (args.backend_root / 'main.py').is_file():
        parser.error('--backend-root must point to a checkout containing main.py')

    with tempfile.TemporaryDirectory(prefix='indoflow-browser-smoke-') as tmp:
        api_port, web_port = free_port(), free_port()
        while web_port == api_port:
            web_port = free_port()
        api_url = f'http://127.0.0.1:{api_port}'
        web_url = f'http://127.0.0.1:{web_port}'
        database = Path(tmp) / 'isolated.db'
        if args.historical_db:
            try:
                copy_snapshot(args.historical_db, database)
            except sqlite3.Error as error:
                raise SystemExit(f'Cannot copy historical SQLite snapshot: {error}') from None
        env = os.environ.copy()
        env.update(DATABASE_URL='sqlite+aiosqlite:///' + database.as_posix(),
                   APP_ENV='development', INDOFLOW_API_TOKEN='', INDOFLOW_ADMIN_TOKEN='',
                   VITE_ENABLE_DEMO_SEED='true' if args.synthetic else 'false')
        log = open(Path(tmp) / 'servers.log', 'w', encoding='utf-8')
        processes = []
        try:
            processes.append(subprocess.Popen([str(ROOT / '.venv' / 'Scripts' / 'python.exe'), '-m',
                'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', str(api_port)],
                cwd=args.backend_root.resolve(), env=env, stdout=log, stderr=subprocess.STDOUT))
            ready(api_url + '/health', processes[-1])
            if args.historical_db:
                check_historical_catalog(api_url, args.outage_resource_id)
            # Invoke Vite directly so terminating the process does not leave an npm child behind.
            processes.append(subprocess.Popen(['node', str(FRONTEND / 'node_modules' / 'vite' / 'bin' / 'vite.js'),
                '--host', '127.0.0.1', '--port', str(web_port), '--strictPort'], cwd=FRONTEND,
                env=env, stdout=log, stderr=subprocess.STDOUT))
            ready(web_url, processes[-1])
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(
                    channel=os.environ.get('BROWSER_CHANNEL', 'msedge'),
                    headless=not args.system_reduced_motion,
                )
                if empty_only:
                    check_unseeded(browser, web_url, api_url, args.screenshots or SCREENSHOTS,
                                   args.axe_script, args.system_reduced_motion)
                    browser.close()
                    return
                page = browser.new_page(viewport={'width': 1280, 'height': 800}, reduced_motion='reduce')
                page.set_default_timeout(30000)
                seen = []
                fail_first = args.synthetic
                allowed = {('GET', '/api/flow-board'), ('GET', '/api/catalog'),
                           ('POST', '/api/schedule/optimize'), ('POST', '/api/schedule/simulate')}
                if args.synthetic:
                    allowed.add(('POST', '/api/seed'))

                def route_api(route):
                    req = route.request
                    path = '/' + req.url.split('/', 3)[3]
                    if (req.method, path) not in allowed:
                        seen.append((req.method, path, None))
                        route.abort()
                        return
                    seen.append((req.method, path, req.post_data_json if req.post_data else None))
                    if path == '/api/flow-board' and fail_first:
                        route.fulfill(status=503, content_type='application/json', body='{"detail":"Smoke test outage"}')
                        return
                    response = route.fetch(url=api_url + path, timeout=120000)
                    route.fulfill(response=response)
                page.route('**/api/**', route_api)
                page.goto(web_url)
                if args.synthetic:
                    expect(page.get_by_role('alert')).to_contain_text('Smoke test outage')
                    seed_button = page.get_by_role('button', name='Load synthetic demo data')
                    expect(seed_button).to_be_disabled()
                    expect(seed_button).to_have_attribute('aria-describedby', 'welcome-seed-help')
                    expect(page.locator('#welcome-seed-help')).to_be_visible()
                    fail_first = False
                    retry = page.get_by_role('button', name='Retry API connection')
                    retry.focus()
                    page.keyboard.press('Enter')
                    expect(page.get_by_role('heading', name='No open work orders')).to_be_visible()
                    expect(page.get_by_role('button', name='Refresh data')).to_be_focused()
                    page.once('dialog', lambda dialog: dialog.accept())
                    page.get_by_role('button', name='Load synthetic example').click()
                screenshots = args.screenshots
                if args.synthetic and screenshots is None:
                    screenshots = SCREENSHOTS
                check_populated(page, screenshots, args.outage_resource_id)
                assert all((method, path) in allowed for method, path, _ in seen), 'Unexpected API request.'
                check_schedule_requests(seen, args.outage_resource_id)
                if args.synthetic:
                    assert sum(path == '/api/seed' for _, path, _ in seen) == 1
                browser.close()
            mode_name = 'historical snapshot copy' if args.historical_db else 'temporary synthetic demo'
            print(f'PASS: {mode_name}, comparison, timeline keyboard controls, outage and reset scenarios')
        finally:
            for process in reversed(processes):
                if process.poll() is None:
                    subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], capture_output=True, check=False)
                process.wait(timeout=10)
            log.close()


if __name__ == '__main__':
    main()
