"""Measure the production Gantt component with published manufacturing intervals."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import shutil
from statistics import median
import subprocess
from tempfile import TemporaryDirectory
from threading import Thread

from playwright.sync_api import expect, sync_playwright


FRONTEND = Path(__file__).resolve().parents[1]

ENTRY = """
import { createRoot } from 'react-dom/client'
import { Gantt } from '../../src/Gantt'
import { scheduleEndHour } from '../../src/scheduleRange'
import '../../src/styles.css'
import observations from './observed-timeline.json'

const intervals = Object.entries(observations).flatMap(([row, records]) =>
  records.map(({ id, start_hour, end_hour }) => ({
    work_order_id: id, wo_number: id, sku_code: '',
    resource_id: row, resource_name: row, plant: '', stage: row.split(' ')[0],
    start_hour, end_hour, batch_id: null, is_late: null, delay_reason: null,
  })),
)
const start = performance.now()
const root = document.getElementById('root')
const observer = new MutationObserver(() => {
  if (!root.querySelector('.gantt-bar')) return
  observer.disconnect()
  requestAnimationFrame(() => requestAnimationFrame(() => {
    window.initialRenderMs = performance.now() - start
  }))
})
observer.observe(root, { childList: true, subtree: true })
createRoot(root).render(<Gantt operations={intervals} maxHour={scheduleEndHour(intervals)} />)
"""


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def record_interaction(page, event, action):
    page.evaluate('''event => {
      window.interactionMs = null
      window.addEventListener(event, () => {
        const start = performance.now()
        requestAnimationFrame(() => requestAnimationFrame(() => {
          window.interactionMs = performance.now() - start
        }))
      }, { capture: true, once: true })
    }''', event)
    action()
    page.wait_for_function('Number.isFinite(window.interactionMs)')
    return page.evaluate('window.interactionMs')


def check_viewport(browser, url, width, height, row, row_count, total, repeats):
    page = browser.new_page(viewport={'width': width, 'height': height})
    page.set_default_timeout(5000)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    samples = {step: [] for step in ('initial', 'pagination', 'zoom', 'filter', 'reset')}
    bars = page.locator('.gantt-bar')
    pages = page.get_by_role('navigation', name='Timeline operation pages')
    next_button = pages.get_by_role('button', name='Next timeline operations')
    previous_button = pages.get_by_role('button', name='Previous timeline operations')
    zoom = page.get_by_label('Zoom')
    resource_filter = page.get_by_role('combobox', name='Resource', exact=True)
    status_filter = page.get_by_role('combobox', name='Status', exact=True)

    for _ in range(repeats):
        page.goto(url)
        page.wait_for_function('Number.isFinite(window.initialRenderMs)')
        samples['initial'].append(page.evaluate('window.initialRenderMs'))
        expect(bars).to_have_count(100)
        first_label = bars.first.get_attribute('aria-label')
        assert first_label and first_label.endswith('status unavailable')
        samples['pagination'].append(record_interaction(page, 'click', next_button.click))
        expect(pages).to_contain_text(f'Timeline showing 101 to 200 of {total} operations')
        expect(bars).to_have_count(100)
        assert bars.first.get_attribute('aria-label') != first_label
        samples['zoom'].append(record_interaction(page, 'change', lambda: zoom.select_option('2')))
        expect(page.locator('.gantt-canvas')).to_have_attribute('style', 'width: 200%;')
        samples['filter'].append(record_interaction(
            page, 'change', lambda: resource_filter.select_option(row),
        ))
        expect(page.locator('.gantt-summary')).to_contain_text(f'{row_count} operations across 1 resource')
        expect(bars).to_have_count(row_count)
        reset = page.get_by_role('button', name='Clear filters (1)')
        samples['reset'].append(record_interaction(page, 'click', reset.click))
        expect(pages).to_contain_text(f'Timeline showing 1 to 100 of {total} operations')
        expect(previous_button).to_be_disabled()
        expect(bars).to_have_count(100)

    for status in ('late', 'on-time'):
        status_filter.select_option(status)
        expect(page.get_by_text('No operations match these filters.', exact=False)).to_be_visible()
        expect(bars).to_have_count(0)
    status_filter.select_option('')

    while next_button.is_enabled():
        next_button.click()
        assert 0 < bars.count() <= 100
    last_page_size = (total - 1) % 100 + 1
    expect(pages).to_contain_text(
        f'Timeline showing {total - last_page_size + 1} to {total} of {total} operations',
    )
    expect(bars).to_have_count(last_page_size)
    assert not errors, errors
    page.close()
    print(f'{width}x{height} median / max ms ({repeats} samples per step)')
    for step, timings in samples.items():
        print(f'  {step:12} {median(timings):5.1f} / {max(timings):.1f}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('observed', type=Path, help='observed-timeline.json from public_data_records.py')
    parser.add_argument('--repeats', type=int, default=5, choices=range(1, 21), metavar='1-20')
    args = parser.parse_args()
    rows = json.loads(args.observed.read_text(encoding='utf-8'))
    total = sum(len(records) for records in rows.values())
    row = next(name for name, records in rows.items() if 1 < len(records) < 100)
    dependencies = FRONTEND / 'node_modules'
    with TemporaryDirectory(dir=dependencies, prefix='public-gantt-') as directory:
        scratch = Path(directory)
        shutil.copyfile(args.observed, scratch / 'observed-timeline.json')
        (scratch / 'entry.tsx').write_text(ENTRY, encoding='utf-8')
        (scratch / 'index.html').write_text(
            '<!doctype html><html lang="en"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>Public interval render measurement</title><div id="root"></div>'
            '<script type="module" src="/entry.tsx"></script></html>',
            encoding='utf-8',
        )
        subprocess.run([
            'node', str(dependencies / 'vite/bin/vite.js'), 'build', str(scratch),
            '--config', str(FRONTEND / 'vite.config.ts'), '--logLevel', 'warn',
        ], cwd=FRONTEND, check=True)
        handler = partial(QuietHandler, directory=scratch / 'dist')
        with ThreadingHTTPServer(('127.0.0.1', 0), handler) as server:
            worker = Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch(channel='msedge', headless=True)
                    print(f'Edge {browser.version}, {total:,} published intervals, {len(rows)} rows', flush=True)
                    url = f'http://127.0.0.1:{server.server_port}/'
                    for width, height in ((1440, 900), (1280, 800), (768, 1024), (390, 844)):
                        check_viewport(browser, url, width, height, row, len(rows[row]), total, args.repeats)
                    browser.close()
            finally:
                server.shutdown()
                worker.join()


if __name__ == '__main__':
    main()
