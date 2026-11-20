"""Measure selected rendered text states with synthetic API responses.

Start Vite on port 5187; then run python scripts/contrast_states.py.
Set INDOFLOW_VIEWPORT_WIDTH and INDOFLOW_VIEWPORT_HEIGHT to check another size.
This checks solid-color text/background pairs only, not full accessibility compliance.
"""
import ast
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

# Reuse the fixture literals without executing the browser_flow walkthrough.
tree = ast.parse(Path(__file__).with_name('browser_flow.py').read_text(encoding='utf-8'))
names = {'operation', 'metrics', 'board', 'catalog', 'optimize', 'scenario', 'responses'}
assignments = [node for node in tree.body if isinstance(node, ast.Assign)
               and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
               and node.targets[0].id in names]
fixtures = {}
exec(compile(ast.Module(body=assignments, type_ignores=[]), '<fixtures>', 'exec'), fixtures)
responses = fixtures['responses']
fail_path = ''

MEASURE = r'''root => {
  const parse = s => { const m = s.match(/[\d.]+/g); return m ? m.map(Number) : [0,0,0,0]; };
  const blend = (f,b) => { const a = f[3] === undefined ? 1 : f[3]; return [0,1,2].map(i => f[i]*a+b[i]*(1-a)); };
  const lum = c => c.map(v => {v /= 255; return v <= .04045 ? v / 12.92 : ((v+.055)/1.055)**2.4}).reduce((a,v,i)=>a+v*[.2126,.7152,.0722][i],0);
  const out = [];
  for (const e of [root, ...root.querySelectorAll('*')]) {
    const direct = [...e.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent.trim()).filter(Boolean).join(' ');
    if (!direct || !e.getClientRects().length) continue;
    const style = getComputedStyle(e);
    if (style.visibility !== 'visible' || style.display === 'none') continue;
    let bg = [255,255,255], chain = [], unsupported = '';
    for (let p=e; p; p=p.parentElement) {
      const s=getComputedStyle(p);
      if (s.backgroundImage !== 'none') unsupported='background image';
      if (Number(s.opacity) < 1) unsupported='opacity';
      chain.push(parse(s.backgroundColor));
    }
    for (const c of chain.reverse()) bg=blend(c,bg);
    const color=parse(style.color); const fg=blend(color,bg);
    const a=lum(fg), b=lum(bg), ratio=(Math.max(a,b)+.05)/(Math.min(a,b)+.05);
    const large=parseFloat(style.fontSize)>=24 || (parseFloat(style.fontSize)>=18.6667 && parseInt(style.fontWeight)>=700);
    out.push({text:direct.slice(0,100), ratio:+ratio.toFixed(2), required:large?3:4.5, unsupported});
  }
  return out;
}'''

def check(label, locator):
    expect(locator).to_be_visible()
    rows = locator.evaluate(MEASURE)
    if not rows:
        raise AssertionError(f'{label}: no rendered text measured')
    print(f'\n{label}: {len(rows)} rendered text nodes')
    for row in rows:
        if row['unsupported']:
            print('  SKIP', row)
        elif row['ratio'] < row['required']:
            print('  FAIL', row)
    print('  minimum supported ratio:', min((r['ratio'] for r in rows if not r['unsupported']), default='none'))
    return sum(not r['unsupported'] and r['ratio'] < r['required'] for r in rows)

with sync_playwright() as p:
    browser = p.chromium.launch(channel=os.environ.get('BROWSER_CHANNEL', 'msedge'), headless=True)
    page = browser.new_page(viewport={
        'width': int(os.environ.get('INDOFLOW_VIEWPORT_WIDTH', '1280')),
        'height': int(os.environ.get('INDOFLOW_VIEWPORT_HEIGHT', '800')),
    }, reduced_motion='reduce')
    def route_api(route):
        path = '/' + route.request.url.split('/', 3)[3].split('?', 1)[0]
        if path == fail_path:
            route.fulfill(status=503, content_type='application/json', body=json.dumps({'detail': 'Synthetic failure'}))
        elif path in responses:
            route.fulfill(status=200, content_type='application/json', body=json.dumps(responses[path]))
        else:
            route.abort()
            raise AssertionError(f'Unexpected API request: {path}')
    page.route('**/api/**', route_api)
    page.goto(os.environ.get('INDOFLOW_FRONTEND_URL', 'http://127.0.0.1:5187'), wait_until='networkidle')
    expect(page.get_by_role('heading', name='Production flow overview')).to_be_visible()
    failures = check('Populated Flow board', page.locator('body'))
    fail_path = '/api/flow-board'
    page.get_by_role('button', name='Refresh data').click()
    failures += check('Refresh failure alert', page.get_by_role('alert'))
    page.get_by_role('button', name='Dismiss').click()
    failures += check('Previous data warning', page.get_by_text('Showing the last successfully loaded data. Retry to update it.'))
    fail_path = ''
    page.get_by_role('button', name='Run comparison').click()
    expect(page.get_by_text('Proposed model schedule ready')).to_be_visible()
    failures += check('Optimization results', page.locator('body'))
    bar = page.get_by_role('button', name='WO-001, SKU-1, Molding, Molding Cell 1, 0 to 1 hours, late, batch B-42')
    bar.click()
    failures += check('Selected operation details', page.get_by_role('region', name='Selected operation details'))
    page.keyboard.press('Escape')
    fail_path = '/api/schedule/optimize'
    page.get_by_role('button', name='Run optimization').click()
    expect(page.get_by_role('alert')).to_be_visible()
    page.get_by_role('button', name='Dismiss').click()
    failures += check('Stale optimization result', page.get_by_text('The latest optimization failed. Showing the last successful result.'))
    fail_path = ''
    page.get_by_role('button', name='Scenario lab').click()
    page.get_by_role('button', name='Run scenario').click()
    expect(page.get_by_role('status', name='Scenario run status')).to_have_text('Simulation complete. Results are available below.')
    failures += check('Scenario results', page.locator('body'))
    failures += check('Submitted scenario inputs', page.get_by_text('Submitted inputs:', exact=False))
    failures += check('Scenario late-order explanations', page.get_by_role('region', name='Scenario late-order explanations'))
    browser.close()
print(f'\nMeasured contrast failures: {failures}')
raise SystemExit(1 if failures else 0)
