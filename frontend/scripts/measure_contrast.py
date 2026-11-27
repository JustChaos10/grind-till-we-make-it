"""Check solid-color text contrast in a rendered Playwright locator."""
from playwright.sync_api import expect


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
    out.push({text:direct.slice(0,100), ratio, required:large?3:4.5, unsupported});
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
