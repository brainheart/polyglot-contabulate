// Browser tests for Polyglot Contabulate. Run `python3 -m unittest discover -s tests`
// first (it writes build/token_fixture.json used by the tokenizer test).
const { test, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

const enc = s => encodeURIComponent(s);

async function open(page, query) {
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  await page.goto('/' + query);
  await page.waitForFunction(() => window.__polyglotReady === true);
  return errors;
}

async function rowCells(page, ref) {
  const row = page.locator('table.parallel tbody tr', { has: page.locator(`th.ref a:text-is("${ref}")`) });
  await expect(row).toHaveCount(1);
  return row;
}

async function headers(page) {
  return page.locator('table.parallel thead th.colhead').evaluateAll(ths => ths.map(t => t.dataset.col));
}

test('landing loads with samples, coverage and no console errors', async ({ page }) => {
  const errors = await open(page, '');
  await expect(page.locator('#landing')).toBeVisible();
  await expect(page.locator('.samples li')).toHaveCount(9);
  await expect(page.locator('#landing table.coverage tbody tr')).toHaveCount(6);
  await expect(page.locator('#built')).toContainText(/Built \d{4}-\d{2}-\d{2}/);
  await expect(page.locator('table.parallel tbody tr').first()).toContainText('In principio creavit Deus');
  expect(errors).toEqual([]);
});

test('Gen 1:1 in all five columns', async ({ page }) => {
  await open(page, '?view=table&b=Gen&c=1');
  const row = await rowCells(page, 'Gen 1:1');
  await expect(row.locator('td.cell-he')).toContainText('בְּרֵאשִׁ֖ית');
  await expect(row.locator('td.cell-he')).toHaveAttribute('dir', 'rtl');
  await expect(row.locator('td.cell-grc')).toContainText('ἐποίησεν ὁ θεὸς');
  await expect(row.locator('td.cell-la')).toContainText('In principio creavit Deus');
  await expect(row.locator('td.cell-de')).toContainText('Am Anfang schuf Gott');
  await expect(row.locator('td.cell-en')).toContainText('In the beginning God created');
});

test('John 1:1 deep link: focused row, Hebrew column dropped for the NT', async ({ page }) => {
  await open(page, '?view=table&b=John&c=1&v=John.1.1');
  expect(await headers(page)).toEqual(['grc', 'la', 'de', 'en']);
  await expect(page.locator('#resultInfo')).toContainText('Hebrew: no text in this book');
  const row = page.locator('tr.focus');
  await expect(row).toHaveCount(1);
  await expect(row.locator('td.cell-grc')).toContainText('Ἐν ἀρχῇ ἦν ὁ λόγος');
  await expect(row.locator('td.cell-la')).toContainText('In principio erat Verbum');
  await expect(row.locator('td.cell-de')).toContainText('Im Anfang war das Wort');
  await expect(row.locator('td.cell-en')).toContainText('In the beginning was the Word');
});

test('Ecclesiastes has Brenton Greek aligned to KJV, marked as not Swete', async ({ page }) => {
  const errors = await open(page, '?view=table&b=Eccl&c=1&v=Eccl.1.2');
  const row = await rowCells(page, 'Eccl 1:2');
  await expect(row.locator('td.cell-grc')).toContainText('Ματαιότης ματαιοτήτων');
  await expect(row.locator('td.cell-en')).toContainText('Vanity of vanities');
  await expect(row.locator('td.cell-grc .text-source')).toHaveAttribute('title', /^text: Brenton 1851/);
  await expect(row.locator('td.cell-en .text-source')).toHaveCount(0);
  await expect(page.locator('td.cell-grc .text-source')).toHaveCount(18);
  // Brenton's 4:17 is KJV 5:1
  await open(page, '?view=table&b=Eccl&c=5');
  const r51 = await rowCells(page, 'Eccl 5:1');
  await expect(r51.locator('td.cell-grc .native')).toHaveText('4:17');
  await expect(r51.locator('td.cell-grc')).toContainText('Φύλαξον τὸν πόδα σου');
  // a filled verse-1 is marked, its Swete neighbour is not; 3 Kgdms 14:1 stays a gap
  await open(page, '?view=table&b=Exod&c=20');
  await expect((await rowCells(page, 'Exod 20:1')).locator('td.cell-grc .text-source')).toHaveCount(1);
  await expect((await rowCells(page, 'Exod 20:2')).locator('td.cell-grc .text-source')).toHaveCount(0);
  await open(page, '?view=table&b=1Kgs&c=14');
  await expect((await rowCells(page, '1Kgs 14:1')).locator('td.cell-grc')).toHaveClass(/gap/);
  await open(page, '?view=about');
  await expect(page.locator('#brenton')).toContainText('not Swete');
  expect(errors).toEqual([]);
});

test('Psalm 23 shows Vulgate/LXX Psalm 22 with native references', async ({ page }) => {
  await open(page, '?view=table&b=Ps&c=23');
  const row = await rowCells(page, 'Ps 23:1');
  await expect(row.locator('td.cell-la')).toContainText('Dominus regit me');
  await expect(row.locator('td.cell-la .native')).toHaveText('22:1');
  await expect(row.locator('td.cell-grc .native')).toHaveText('22:title–1');
  await expect(row.locator('td.cell-grc')).toContainText('Ψαλμὸς τῷ Δαυείδ. Κύριος ποιμαίνει με');
  await expect(row.locator('td.cell-en')).toContainText('The LORD is my shepherd');
  await expect(page.locator('tr', { hasText: 'Ps 23 title' })).toHaveCount(0);
  // hiding native refs
  await page.locator('#nat').uncheck();
  await expect(page.locator('td.cell-la .native')).toHaveCount(0);
});

test('Malachi 4 = Hebrew 3:19-24; LXX order of 4:4-6', async ({ page }) => {
  await open(page, '?view=table&b=Mal&c=4');
  const r1 = await rowCells(page, 'Mal 4:1');
  await expect(r1.locator('td.cell-he .native')).toHaveText('3:19');
  const r5 = await rowCells(page, 'Mal 4:5');
  await expect(r5.locator('td.cell-grc')).toContainText('Ἠλίαν');
  await expect(r5.locator('td.cell-grc .native')).toHaveText('4:4');
});

test('accent-insensitive Greek search highlights and pages', async ({ page }) => {
  await open(page, `?view=table&q=${enc('λογος')}&qc=grc&mm=word`);
  await expect(page.locator('#resultInfo')).toContainText('match in the whole Bible');
  const n = parseInt((await page.locator('#resultInfo').textContent()).replace(/,/g, ''), 10);
  expect(n).toBeGreaterThan(300);
  await expect(page.locator('td.cell-grc mark.hit1').first()).toBeVisible();
  const first = await page.locator('td.cell-grc mark.hit1').first().textContent();
  expect(first.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase()).toBe('λογος');
  await expect(page.locator('.pginfo')).toContainText('Page 1 /');
});

test('nikud-insensitive Hebrew search; pointed mode separates Saul and Sheol', async ({ page }) => {
  await open(page, `?view=table&q=${enc('שאול')}&qc=he`);
  const all = parseInt((await page.locator('#resultInfo').textContent()).replace(/,/g, ''), 10);
  await open(page, `?view=table&q=${enc('שְׁאוֹל')}&qc=he&acc=0`);
  const sheol = parseInt((await page.locator('#resultInfo').textContent()).replace(/,/g, ''), 10);
  expect(all).toBeGreaterThan(350);
  expect(sheol).toBeGreaterThan(20);
  expect(sheol).toBeLessThan(80);
  await expect(page.locator('td.cell-en').filter({ hasText: /hell|grave/ }).first()).toBeVisible();
});

test('two-condition search highlights both columns', async ({ page }) => {
  await open(page, '?view=table&q=gnade&qc=de&mm=word&acc=0&q2=mercy&qc2=en&mm2=word&acc2=0');
  await expect(page.locator('#cond2')).toBeVisible();
  await expect(page.locator('td.cell-de mark.hit1').first()).toBeVisible();
  await expect(page.locator('td.cell-en mark.hit2').first()).toBeVisible();
});

test('invalid regex shows an error instead of breaking', async ({ page }) => {
  const errors = await open(page, `?view=table&q=${enc('(unclosed')}&mm=regex`);
  await expect(page.locator('#tableWrap .error')).toContainText('Invalid regular expression');
  expect(errors).toEqual([]);
});

test('column order and visibility survive a fresh load; Back retraces chapters', async ({ page }) => {
  await open(page, '?view=table&b=Gen&c=1&cols=en,la');
  expect(await headers(page)).toEqual(['en', 'la']);
  await page.locator('#colChips button[data-act="left"][data-col="la"]').click();
  await expect.poll(() => headers(page)).toEqual(['la', 'en']);
  expect(page.url()).toContain('cols=la%2Cen');
  await page.reload();
  await page.waitForFunction(() => window.__polyglotReady === true);
  expect(await headers(page)).toEqual(['la', 'en']);
  await page.locator('#nextCh').click();
  await expect(page.locator('#resultInfo')).toContainText('Genesis 2');
  await page.goBack();
  await expect(page.locator('#resultInfo')).toContainText('Genesis 1');
});

test('CSV contains every filtered row and the visible columns', async ({ page }) => {
  await open(page, '?view=table&q=Jerusalem&qc=en&mm=word&cols=en,la&ps=25');
  const n = parseInt((await page.locator('#resultInfo').textContent()).replace(/,/g, ''), 10);
  expect(n).toBeGreaterThan(25);
  const [download] = await Promise.all([page.waitForEvent('download'), page.locator('#csvBtn').click()]);
  const csv = fs.readFileSync(await download.path(), 'utf8').replace(/^﻿/, '');
  const lines = csv.trim().split(/\r\n/);
  expect(lines[0]).toBe('Verse (KJV numbering),Canonical ID,English,English own reference,Latin,Latin own reference');
  expect(lines.length).toBe(n + 1);
});

async function renderingsTop(page, col, k = 6) {
  const card = page.locator(`.rcard[data-col="${col}"]`);
  await expect(card).toHaveCount(1);
  return card.locator('tbody tr td.word').evaluateAll((tds, k) => tds.slice(0, k).map(t => t.innerText.trim().toLowerCase()), k);
}

test('Renderings: chesed -> mercy/kindness; Güte/Barmherzigkeit/Gnade', async ({ page }) => {
  await open(page, `?view=renderings&rc=he&rt=${enc('חסד')}&rm=contains`);
  await expect(page.locator('.notice')).toContainText('Statistical, not scholarly');
  const en = await renderingsTop(page, 'en');
  expect(en[0]).toBe('mercy');
  expect(en.some(w => w === 'kindness' || w === 'lovingkindness')).toBe(true);
  const de = await renderingsTop(page, 'de');
  for (const w of ['güte', 'barmherzigkeit', 'gnade']) expect(de).toContain(w);
  await expect(page.locator('.rcard[data-col="en"] td.ex a').first()).toBeVisible();
});

test('Renderings: λόγος -> Wort; γέεννα/ᾅδης -> hell', async ({ page }) => {
  await open(page, `?view=renderings&rc=grc&rm=regex&rsc=NT&rt=${enc('^λόγ(ος|ου|ῳ|ον|οι|ων|οις|ους)$')}`);
  expect((await renderingsTop(page, 'de'))[0]).toBe('wort');
  await open(page, `?view=renderings&rc=grc&rm=regex&rsc=NT&rt=${enc('^(γέεννα[νς]?|ᾅδ(ης|ου|ῃ|ην))$')}`);
  expect((await renderingsTop(page, 'en'))[0]).toBe('hell');
  await expect(page.locator('#rOut')).toContainText('Hebrew: no text in this scope');
});

test('Renderings: שאול surfaces Saul and hell, pointed forms split them', async ({ page }) => {
  await open(page, `?view=renderings&rc=he&rt=${enc('שאול')}&rm=contains`);
  const en = await renderingsTop(page, 'en', 12);
  expect(en[0]).toBe('saul');
  expect(en).toContain('hell');
  const panel = page.locator('.homograph');
  await expect(panel).toContainText('conflates homographs');
  const forms = await panel.locator('ul.forms a').allTextContents();
  expect(forms.some(f => f.includes('שָׁאוּל'))).toBe(true);
  expect(forms.some(f => /שְׁא(וֹ|ֹ)ל/.test(f))).toBe(true);
  // choose a Sheol vocalization -> pointed mode, no Saul
  await panel.locator('ul.forms a').filter({ hasText: /^שְׁאוֹל$/ }).first().click();
  await expect(page).toHaveURL(/rp=1/);
  const sheol = await renderingsTop(page, 'en', 5);
  expect(sheol).not.toContain('saul');
  expect(sheol.some(w => w === 'hell' || w === 'grave')).toBe(true);
});

test('Renderings drill-down opens the parallel table with both words highlighted', async ({ page }) => {
  await open(page, `?view=renderings&rc=he&rt=${enc('חסד')}&rm=contains`);
  await page.locator('.rcard[data-col="en"] td.word a').first().click();
  await expect(page).toHaveURL(/view=table/);
  await expect(page.locator('td.cell-he mark.hit1').first()).toBeVisible();
  await expect(page.locator('td.cell-en mark.hit2').first()).toBeVisible();
  await page.goBack();
  await expect(page.locator('.rcard[data-col="en"]')).toBeVisible();
});

test('browser tokenizer agrees with the Python build', async ({ page }) => {
  const fixture = path.join(__dirname, '..', 'build', 'token_fixture.json');
  test.skip(!fs.existsSync(fixture), 'run python tests first');
  const cases = JSON.parse(fs.readFileSync(fixture, 'utf8'));
  await open(page, '?view=about');
  const bad = await page.evaluate(async cases => {
    const tn = await import('/js/textnorm.js');
    const out = [];
    for (const c of cases) {
      const toks = tn.tokens(c.text);
      const keys = toks.map(t => tn.tokenKey(c.col, t));
      if (JSON.stringify(toks) !== JSON.stringify(c.tokens) || JSON.stringify(keys) !== JSON.stringify(c.keys)) out.push({ c, toks, keys });
      if (c.pointed) {
        const p = toks.map(t => tn.tokenKey('he_pointed', t));
        if (JSON.stringify(p) !== JSON.stringify(c.pointed)) out.push({ c, p });
      }
    }
    return out;
  }, cases);
  expect(bad.slice(0, 3)).toEqual([]);
  expect(cases.length).toBeGreaterThan(150);
});

test('narrow screens scroll the table, not the page', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await open(page, '?view=table&b=Ps&c=23');
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(1);
  const wrap = await page.locator('#tableWrap').evaluate(el => el.scrollWidth > el.clientWidth);
  expect(wrap).toBe(true);
});
