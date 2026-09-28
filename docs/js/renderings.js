// Renderings: which words do the other columns use in the verses where a
// term occurs? Verse-level co-occurrence ranked by log-likelihood (G²).
import { META, BOOK, SPINE, loadTokens, refLabel } from './data.js';
import { fold, tokenKey, escapeHTML, escapeRegex } from './textnorm.js';

export const RENDER_KEYS = ['rt', 'rc', 'rm', 'rp', 'rsw', 'rsc', 'rmin'];
const COLS = ['he', 'grc', 'la', 'de', 'en'];
const $ = sel => document.querySelector(sel);
let ctx = null;
let lastRun = null;

export function initRenderings(c) {
  ctx = c;
  const rc = $('#rc');
  for (const col of META.columns) rc.appendChild(new Option(`${col.label} (${col.sub})`, col.id));
  const rsc = $('#rsc');
  rsc.appendChild(new Option('Whole Bible', 'all'));
  for (const [sec, label] of Object.entries(META.sections)) rsc.appendChild(new Option(label, sec));
  const og = document.createElement('optgroup');
  og.label = 'One book';
  for (const b of META.books) og.appendChild(new Option(b.name, b.id));
  rsc.appendChild(og);
  $('#rForm').addEventListener('submit', e => {
    e.preventDefault();
    ctx.navigate({
      view: 'renderings', rt: $('#rt').value.trim(), rc: $('#rc').value, rm: $('#rm').value,
      rp: $('#rp').value, rsw: $('#rsw').checked ? '1' : '0', rsc: $('#rsc').value,
      rmin: String(Math.max(1, parseInt($('#rmin').value, 10) || 1)),
    }, true);
  });
  $('#rc').addEventListener('change', () => { $('#rpWrap').hidden = $('#rc').value !== 'he'; });
  $('#rOut').addEventListener('click', e => {
    const b = e.target.closest('button[data-more]');
    if (b) {
      const card = b.closest('.rcard');
      card.classList.toggle('expanded');
      b.textContent = card.classList.contains('expanded') ? 'Show top 20' : 'Show top 60';
    }
    const s = e.target.closest('th[data-sort]');
    if (s) sortCard(s);
    const f = e.target.closest('a[data-form]');
    if (f) {
      e.preventDefault();
      ctx.navigate({ view: 'renderings', rp: '1', rt: f.dataset.form, rm: 'exact' }, true);
    }
  });
}

function matcher(term, mode, col, level) {
  if (!term) return null;
  if (mode === 'regex') {
    let src = term.normalize('NFD');
    if (level === 'fold') src = src.replace(/\p{M}/gu, '').replace(/ς/g, 'σ');
    else src = src.replace(/[֑-ֽ֯]/gu, '');
    src = src.normalize('NFC');
    if (col === 'la') src = src.replace(/j/g, 'i');
    const re = new RegExp(src, 'iu');
    return w => re.test(w);
  }
  const key = tokenKey(level === 'pointed' && col === 'he' ? 'he_pointed' : col, term);
  if (mode === 'exact') return w => w === key;
  if (mode === 'prefix') return w => w.startsWith(key);
  return w => w.includes(key);
}

function inScope(row, scope) {
  if (scope === 'all') return true;
  if (scope === 'OT' || scope === 'NT' || scope === 'DC') return BOOK.get(row.book).section === scope;
  return row.book === scope;
}

function g2(a, b, c, d) {
  const n = a + b + c + d;
  const e = [(a + b) * (a + c) / n, (a + b) * (b + d) / n, (c + d) * (a + c) / n, (c + d) * (b + d) / n];
  const o = [a, b, c, d];
  let s = 0;
  for (let i = 0; i < 4; i++) if (o[i] > 0) s += o[i] * Math.log(o[i] / e[i]);
  return 2 * s;
}

// column -> [tokenKey, search level]
function keyFor(col, pointed) {
  if (col === 'he') return pointed ? ['hep', 'pointed'] : ['he', 'fold'];
  if (col === 'grc' || col === 'la') return [col, 'fold'];
  return [col, 'exact'];
}

// Translate a word-level match into a parallel-table search condition.
function tableQuery(term, mode, level) {
  const acc = level === 'fold' ? '1' : '0';
  if (mode === 'exact') return { q: term, mm: 'word', acc };
  if (mode === 'prefix') return { q: `(?<![\\p{L}\\p{M}])${escapeRegex(term)}`, mm: 'regex', acc };
  if (mode === 'contains') return { q: term, mm: 'plain', acc };
  let src = term;
  let pre = '', post = '';
  if (src.startsWith('^')) { src = src.slice(1); pre = '(?<![\\p{L}\\p{M}])'; }
  if (src.endsWith('$') && !src.endsWith('\\$')) { src = src.slice(0, -1); post = '(?![\\p{L}\\p{M}])'; }
  return { q: `${pre}(?:${src})${post}`, mm: 'regex', acc };
}

export async function renderRenderings(state) {
  $('#rt').value = state.rt;
  $('#rc').value = state.rc;
  $('#rm').value = state.rm;
  $('#rp').value = state.rp;
  $('#rpWrap').hidden = state.rc !== 'he';
  $('#rsw').checked = state.rsw === '1';
  $('#rsc').value = state.rsc;
  $('#rmin').value = state.rmin;
  const out = $('#rOut');
  if (!state.rt) {
    out.innerHTML = '<p class="muted">Pick a column and a word (or a regular expression over word forms). The table then lists the words the other columns use most distinctively in the same verses.</p>';
    return;
  }
  const pointed = state.rc === 'he' && state.rp === '1';
  const [srcKey, level] = keyFor(state.rc, pointed);
  let match;
  try {
    match = matcher(state.rt, state.rm, state.rc, level === 'exact' ? 'exact' : level);
  } catch (e) {
    out.innerHTML = `<p class="error">Invalid regular expression: ${escapeHTML(e.message)}</p>`;
    return;
  }
  ctx.setStatus('Loading word tables…');
  const targets = COLS.filter(c => c !== state.rc);
  let src, tgts, hep = null;
  try {
    [src, ...tgts] = await Promise.all([loadTokens(srcKey), ...targets.map(c => loadTokens(keyFor(c, false)[0]))]);
    if (state.rc === 'he' && !pointed) hep = await loadTokens('hep');
  } catch (e) {
    ctx.setStatus('');
    out.innerHTML = `<p class="error">Could not load word tables: ${escapeHTML(e.message)}</p>`;
    return;
  }
  ctx.setStatus('Counting…');
  const matchedIds = new Set();
  src.vocab.forEach((w, i) => { if (match(w)) matchedIds.add(i); });
  const scopeRows = [];
  const isTerm = new Uint8Array(SPINE.length);
  const formCount = new Map();
  for (const row of SPINE) {
    if (!inScope(row, state.rsc)) continue;
    const ids = src.rows[row.g];
    if (!ids) continue;
    scopeRows.push(row.g);
    let hit = false;
    for (const id of ids) if (matchedIds.has(id)) { hit = true; formCount.set(id, (formCount.get(id) || 0) + 1); }
    if (hit) isTerm[row.g] = 1;
  }
  const termRows = scopeRows.filter(g => isTerm[g]);
  const stop = META.stopwords;
  const minA = Math.max(1, +state.rmin || 1);
  const srcQ = tableQuery(state.rt, state.rm, level === 'exact' ? 'pointed' : level);

  const cards = targets.map((col, ti) => {
    const t = tgts[ti];
    const V = t.vocab.length;
    const df = new Int32Array(V);
    const a = new Int32Array(V);
    let N = 0, R = 0;
    for (const g of scopeRows) {
      const ids = t.rows[g];
      if (!ids) continue;
      N++;
      const inR = isTerm[g] === 1;
      if (inR) R++;
      for (const id of ids) { df[id]++; if (inR) a[id]++; }
    }
    const stopSet = new Set(state.rsw === '1' ? (stop[t.key] || []) : []);
    const res = [];
    for (let id = 0; id < V; id++) {
      const ai = a[id];
      if (ai < minA) continue;
      const w = t.vocab[id];
      if (stopSet.has(w)) continue;
      const E = R * df[id] / N;
      if (ai <= E) continue;
      res.push({ id, w, d: t.disp[id], a: ai, df: df[id], E, g2: g2(ai, R - ai, df[id] - ai, N - R - df[id] + ai), share: R ? ai / R : 0 });
    }
    res.sort((x, y) => y.g2 - x.g2 || y.a - x.a);
    const top = res.slice(0, 60);
    // example verses: first three term rows containing the rendering
    const want = new Map(top.map(r => [r.id, []]));
    for (const g of termRows) {
      const ids = t.rows[g];
      if (!ids) continue;
      for (const id of ids) {
        const ex = want.get(id);
        if (ex && ex.length < 3) ex.push(g);
      }
    }
    for (const r of top) r.ex = want.get(r.id);
    return { col, key: t.key, N, R, rows: top };
  });

  // Hebrew consonantal: which vocalized forms stand behind the match?
  let formsHTML = '';
  if (hep) {
    const hmatch = matcher(state.rt, state.rm, 'he', 'fold');
    const pc = new Map();
    for (const g of termRows) {
      const ids = hep.rows[g];
      if (!ids) continue;
      for (const id of ids) {
        const w = hep.vocab[id];
        if (hmatch(fold(w, 'he', 'fold'))) pc.set(w, (pc.get(w) || 0) + 1);
      }
    }
    const list = [...pc.entries()].sort((x, y) => y[1] - x[1]).slice(0, 16);
    formsHTML = `<div class="homograph">
      <h3>Vocalized forms behind this unpointed match</h3>
      <p>Consonantal (unpointed) matching treats every vocalization of a spelling as one word, so it conflates homographs — for example <span lang="he" dir="rtl">שאול</span> is both <em>Saul</em> (<span lang="he" dir="rtl">שָׁאוּל</span>) and <em>Sheol</em> (<span lang="he" dir="rtl">שְׁאוֹל</span>). The pointed forms in the matching verses are listed below; click one to match that vocalization exactly (pointed mode).</p>
      <ul class="forms">${list.map(([w, n]) => `<li><a href="#" data-form="${escapeHTML(w)}" lang="he" dir="rtl">${escapeHTML(w)}</a> <span class="n">${n}</span></li>`).join('')}</ul>
    </div>`;
  }
  const forms = [...formCount.entries()].sort((x, y) => y[1] - x[1]);
  const colLabel = id => META.columns.find(c => c.id === id).label;
  const scopeLabel = state.rsc === 'all' ? 'the whole Bible' : META.sections[state.rsc] || BOOK.get(state.rsc)?.name || state.rsc;
  const srcCol = META.columns.find(c => c.id === state.rc);
  const header = `<div class="rsummary">
    <p><strong>${escapeHTML(state.rt)}</strong> in ${escapeHTML(srcCol.label)}${state.rc === 'he' ? (pointed ? ' (pointed)' : ' (consonantal)') : ''}, ${escapeHTML(state.rm)} match:
      <strong>${forms.length.toLocaleString()}</strong> word form${forms.length === 1 ? '' : 's'} in <strong>${termRows.length.toLocaleString()}</strong> verse rows of ${escapeHTML(scopeLabel)}.
      <a href="${tableHref(srcQ, state.rc, null, null)}" data-nav="1">Show these verses →</a></p>
    ${forms.length ? `<p class="formlist">Forms: ${forms.slice(0, 24).map(([id, n]) => `<span ${langAttr(state.rc)}>${escapeHTML(src.disp[id])}</span> <span class="n">${n}</span>`).join(' · ')}${forms.length > 24 ? ` · … ${forms.length - 24} more` : ''}</p>` : ''}
  </div>`;
  const shown = cards.filter(card => card.N > 0);
  const missing = cards.filter(card => card.N === 0).map(card => colLabel(card.col));
  const cardsHTML = shown.map(card => cardHTML(card, srcQ, state)).join('')
    + (missing.length ? `<p class="muted">${escapeHTML(missing.join(', '))}: no text in this scope.</p>` : '');
  out.innerHTML = header + formsHTML + (termRows.length ? `<div class="rcards">${cardsHTML}</div>` : '<p class="empty">No verse rows match this term. Try “contains”, a shorter stem, or switch off pointed matching.</p>');
  lastRun = { cards };
  ctx.setStatus('');
}

function langAttr(col) {
  const c = META.columns.find(x => x.id === col);
  return `lang="${c.lang}" dir="${c.dir}"`;
}

function tableHref(srcQ, rc, word, tcol) {
  const p = new URLSearchParams({ view: 'table', sc: 'all', q: srcQ.q, qc: rc, mm: srcQ.mm, acc: srcQ.acc });
  if (word) {
    p.set('q2', word);
    p.set('qc2', tcol);
    p.set('mm2', 'word');
    p.set('acc2', tcol === 'de' || tcol === 'en' ? '0' : '1');
  }
  return `?${p.toString()}`;
}

function cardHTML(card, srcQ, state) {
  const c = META.columns.find(x => x.id === card.col);
  const fmt = x => x.toLocaleString(undefined, { maximumFractionDigits: 1 });
  const rows = card.rows.map((r, i) => `<tr class="${i >= 20 ? 'extra' : ''}" data-g2="${r.g2}" data-a="${r.a}" data-df="${r.df}" data-share="${r.share}">
      <td class="num rank">${i + 1}</td>
      <td class="word"><a href="${tableHref(srcQ, state.rc, r.w, card.col)}" data-nav="1" ${langAttr(card.col)} title="Show verses with both words">${escapeHTML(r.d)}</a></td>
      <td class="num">${r.a.toLocaleString()}</td>
      <td class="num">${(100 * r.share).toFixed(0)}%</td>
      <td class="num">${r.df.toLocaleString()}</td>
      <td class="num">${fmt(r.g2)}</td>
      <td class="ex">${r.ex.map(g => `<a href="?view=table&b=${SPINE[g].book}&c=${SPINE[g].ch}&v=${encodeURIComponent(SPINE[g].cid)}" data-nav="1">${escapeHTML(refLabel(SPINE[g]))}</a>`).join(', ')}</td>
    </tr>`).join('');
  return `<section class="rcard" data-col="${card.col}">
    <h3>${escapeHTML(c.label)} <span class="thsub">${escapeHTML(c.sub)}</span></h3>
    <p class="rmeta">${card.R.toLocaleString()} of the term's verse rows have ${escapeHTML(c.label)} text (out of ${card.N.toLocaleString()} rows with both texts in scope).</p>
    ${card.rows.length ? `<table class="rtable">
      <thead><tr><th>#</th><th>Rendering</th>
        <th data-sort="a" title="Verse rows containing both the term and this word. Click to sort.">Together</th>
        <th data-sort="share" title="Share of the term's verse rows (with text in this column) that contain this word. Click to sort.">Share</th>
        <th data-sort="df" title="Verse rows in scope containing this word at all. Click to sort.">Overall</th>
        <th data-sort="g2" class="sorted-desc" title="Log-likelihood G² for verse-level association (higher = more distinctive). Click to sort.">G²</th>
        <th>Examples</th></tr></thead>
      <tbody>${rows}</tbody></table>
      ${card.rows.length > 20 ? '<button class="link-btn" data-more="1">Show top 60</button>' : ''}` : '<p class="empty">No positively associated words at this minimum count.</p>'}
  </section>`;
}

function sortCard(th) {
  const table = th.closest('table');
  const key = th.dataset.sort;
  const desc = !th.classList.contains('sorted-desc');
  table.querySelectorAll('th').forEach(x => x.classList.remove('sorted-desc', 'sorted-asc'));
  th.classList.add(desc ? 'sorted-desc' : 'sorted-asc');
  const tb = table.tBodies[0];
  const rows = [...tb.rows].sort((x, y) => (desc ? -1 : 1) * ((+x.dataset[key]) - (+y.dataset[key])) || (+y.dataset.g2) - (+x.dataset.g2));
  rows.forEach((r, i) => { r.cells[0].textContent = i + 1; r.classList.toggle('extra', i >= 20); tb.appendChild(r); });
}
