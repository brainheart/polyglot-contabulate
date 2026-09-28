import { META, BOOK, SPINE, GLOBAL, loadMeta, loadText, loadTexts, hasText, cellText, cellNative, cellIsCont, refLabel, rowByCid } from './data.js';
import { foldWithMap, queryRegex, matchSpans, highlight, escapeHTML } from './textnorm.js';
import { initRenderings, renderRenderings, RENDER_KEYS } from './renderings.js';

const $ = sel => document.querySelector(sel);
const COLS = ['he', 'grc', 'la', 'de', 'en'];
const PAGE_SIZES = [25, 50, 100, 250];

// ------------------------------------------------------------------ state
const DEFAULTS = {
  view: 'table', b: 'Gen', c: '1', v: '', cols: COLS.join(','), nat: '1',
  q: '', qc: 'any', mm: 'plain', acc: '1', q2: '', qc2: 'en', mm2: 'plain', acc2: '1',
  sc: 'all', p: '1', ps: '50',
  rt: '', rc: 'he', rm: 'contains', rp: '0', rsw: '1', rsc: 'all', rmin: '2',
};
const TABLE_KEYS = ['b', 'c', 'v', 'cols', 'nat', 'q', 'qc', 'mm', 'acc', 'q2', 'qc2', 'mm2', 'acc2', 'sc', 'p', 'ps'];
export const state = { ...DEFAULTS };
let armed = false;

function readURL() {
  const u = new URLSearchParams(location.search);
  Object.assign(state, DEFAULTS);
  for (const k of Object.keys(DEFAULTS)) if (u.has(k)) state[k] = u.get(k);
  state.landing = ![...u.keys()].length;
  sanitize();
}

function sanitize() {
  if (!BOOK.has(state.b)) state.b = 'Gen';
  const cols = state.cols.split(',').filter(c => COLS.includes(c));
  state.cols = [...new Set(cols)].join(',') || COLS.join(',');
  if (!['plain', 'word', 'regex'].includes(state.mm)) state.mm = 'plain';
  if (!['plain', 'word', 'regex'].includes(state.mm2)) state.mm2 = 'plain';
  if (!['any', ...COLS].includes(state.qc)) state.qc = 'any';
  if (!COLS.includes(state.qc2)) state.qc2 = 'en';
  if (!['all', 'book', 'chap'].includes(state.sc)) state.sc = 'all';
  if (!PAGE_SIZES.includes(+state.ps)) state.ps = '50';
  if (!(+state.p >= 1)) state.p = '1';
  if (!['table', 'renderings', 'about'].includes(state.view)) state.view = 'table';
}

export function writeURL(push = false) {
  if (!armed) return;
  const u = new URLSearchParams();
  u.set('view', state.view);
  const keys = state.view === 'renderings' ? RENDER_KEYS : state.view === 'table' ? TABLE_KEYS : [];
  for (const k of keys) if (state[k] !== DEFAULTS[k] && state[k] !== '') u.set(k, state[k]);
  const url = `${location.pathname}?${u.toString()}`;
  if (url === location.pathname + location.search) return;
  history[push ? 'pushState' : 'replaceState'](null, '', url);
}

export function navigate(changes, push = true) {
  Object.assign(state, changes);
  state.landing = false;
  sanitize();
  writeURL(push);
  render();
}

// ------------------------------------------------------------------ helpers
function colMeta(id) { return META.columns.find(c => c.id === id); }
function visibleCols() { return state.cols.split(','); }

function setStatus(msg) {
  const el = $('#status');
  el.textContent = msg || '';
  el.hidden = !msg;
}

function chapterList(book) {
  return BOOK.get(book).chapters.map(([ch]) => ch);
}

const foldCache = new Map(); // `${col}/${book}/${level}` -> [folded|null]
function foldedCells(col, book, level, cells) {
  const k = `${col}/${book}/${level}`;
  if (!foldCache.has(k)) {
    foldCache.set(k, cells.map(c => {
      const t = cellText(c);
      return t ? foldWithMap(t, col, level).folded : null;
    }));
  }
  return foldCache.get(k);
}

function conditions() {
  const out = [];
  const add = (q, col, mode, cls, acc) => {
    const level = acc === '1' ? 'fold' : 'pointed';
    if (!q) return;
    const cols = col === 'any' ? COLS : [col];
    const res = {};
    for (const c of cols) {
      try { res[c] = queryRegex(q, mode, c, level); } catch (e) { throw new Error(`Invalid regular expression: ${e.message}`); }
    }
    out.push({ q, col, mode, cls, res, level });
  };
  add(state.q, state.qc, state.mm, 'hit1', state.acc);
  add(state.q2, state.qc2, state.mm2, 'hit2', state.acc2);
  return out;
}

// ------------------------------------------------------------------ table view
let lastResult = null; // {rows: [spine rows], title}

async function computeRows() {
  const conds = conditions();
  const book = state.b;
  if (!conds.length) {
    const ch = state.c;
    const rows = BOOK.get(book).rowList.filter(r => ch === 'all' || String(r.ch) === ch);
    return { rows, searching: false, conds };
  }
  let books;
  if (state.sc === 'all') books = META.books.map(b => b.id);
  else books = [book];
  const needCols = new Set();
  for (const c of conds) (c.col === 'any' ? COLS : [c.col]).forEach(x => needCols.add(x));
  const pairs = [];
  for (const b of books) for (const col of needCols) if (hasText(col, b)) pairs.push([col, b]);
  setStatus(`Loading text… 0/${pairs.length}`);
  await loadTexts(pairs, (d, n) => setStatus(`Loading text… ${d}/${n} book files`));
  setStatus('Searching…');
  const rows = [];
  for (const b of books) {
    const bm = BOOK.get(b);
    const cellsBy = {};
    for (const col of needCols) cellsBy[col] = await loadText(col, b);
    bm.rowList.forEach((row, i) => {
      if (state.sc === 'chap' && String(row.ch) !== state.c) return;
      for (const c of conds) {
        const cols = c.col === 'any' ? COLS : [c.col];
        let ok = false;
        for (const col of cols) {
          const f = cellsBy[col] && foldedCells(col, b, c.level, cellsBy[col])[i];
          if (!f) continue;
          const re = c.res[col];
          re.lastIndex = 0;
          if (re.test(f)) { ok = true; break; }
        }
        if (!ok) return;
      }
      rows.push(row);
    });
  }
  setStatus('');
  return { rows, searching: true, conds };
}

function renderControls() {
  const bsel = $('#bookSel');
  if (!bsel.options.length) {
    for (const [sec, label] of Object.entries(META.sections)) {
      const og = document.createElement('optgroup');
      og.label = label;
      for (const b of META.books.filter(x => x.section === sec)) {
        const o = new Option(b.name, b.id);
        og.appendChild(o);
      }
      bsel.appendChild(og);
    }
  }
  bsel.value = state.b;
  const csel = $('#chapSel');
  csel.innerHTML = '';
  csel.appendChild(new Option('All chapters', 'all'));
  for (const ch of chapterList(state.b)) csel.appendChild(new Option(ch === 0 ? 'Prologue' : `Chapter ${ch}`, String(ch)));
  if (![...csel.options].some(o => o.value === state.c)) state.c = String(chapterList(state.b)[0]);
  csel.value = state.c;
  $('#q').value = state.q;
  $('#qc').value = state.qc;
  $('#mm').value = state.mm;
  $('#acc').checked = state.acc === '1';
  $('#sc').value = state.sc;
  $('#q2').value = state.q2;
  $('#qc2').value = state.qc2;
  $('#mm2').value = state.mm2;
  $('#acc2').checked = state.acc2 === '1';
  $('#cond2').hidden = !state.q2 && !$('#cond2').dataset.open;
  $('#nat').checked = state.nat === '1';
  renderColumnChips();
}

function renderColumnChips() {
  const box = $('#colChips');
  const vis = visibleCols();
  const order = [...vis, ...COLS.filter(c => !vis.includes(c))];
  box.innerHTML = order.map(id => {
    const c = colMeta(id);
    const on = vis.includes(id);
    return `<span class="chip ${on ? 'on' : 'off'}" data-col="${id}">
      <label><input type="checkbox" ${on ? 'checked' : ''} data-act="toggle" data-col="${id}"> ${escapeHTML(c.label)}</label>
      ${on ? `<button class="mini" data-act="left" data-col="${id}" aria-label="Move ${c.label} left" title="Move left">◀</button><button class="mini" data-act="right" data-col="${id}" aria-label="Move ${c.label} right" title="Move right">▶</button>` : ''}
    </span>`;
  }).join('');
}

function moveCol(id, delta) {
  const vis = visibleCols();
  const i = vis.indexOf(id);
  const j = i + delta;
  if (i < 0 || j < 0 || j >= vis.length) return;
  [vis[i], vis[j]] = [vis[j], vis[i]];
  navigate({ cols: vis.join(',') }, false);
}

async function renderTable() {
  renderControls();
  let res;
  try {
    res = await computeRows();
  } catch (e) {
    setStatus('');
    $('#tableWrap').innerHTML = `<p class="error">${escapeHTML(e.message)}</p>`;
    $('#resultInfo').textContent = '';
    return;
  }
  lastResult = res;
  let vis = visibleCols();
  // browsing one book: drop columns that have no text in it (e.g. Hebrew in the NT)
  const absent = res.searching ? [] : vis.filter(c => !hasText(c, state.b));
  if (absent.length && absent.length < vis.length) vis = vis.filter(c => !absent.includes(c));
  res.cols = vis;
  // a single chapter is shown whole; search results and whole books are paged
  const ps = !res.searching && state.c !== 'all' ? Math.max(res.rows.length, 1) : +state.ps;
  const total = res.rows.length;
  const pages = Math.max(1, Math.ceil(total / ps));
  let page = Math.min(+state.p, pages);
  // a deep-linked verse opens on its page
  if (state.v && !res.searching) {
    const i = res.rows.findIndex(r => r.cid === state.v);
    if (i >= 0) page = Math.floor(i / ps) + 1;
  }
  state.p = String(page);
  const slice = res.rows.slice((page - 1) * ps, page * ps);
  // load visible columns for the books on this page
  const pairs = [];
  const seen = new Set();
  for (const r of slice) for (const col of vis) {
    const k = col + r.book;
    if (!seen.has(k) && hasText(col, r.book)) { seen.add(k); pairs.push([col, r.book]); }
  }
  await loadTexts(pairs);
  const texts = {};
  for (const [col, b] of pairs) texts[col + b] = await loadText(col, b);

  const where = res.searching
    ? `${total.toLocaleString()} verse row${total === 1 ? '' : 's'} match` + (state.sc === 'all' ? ' in the whole Bible' : state.sc === 'book' ? ` in ${BOOK.get(state.b).name}` : ` in ${BOOK.get(state.b).name} ${state.c}`)
    : `${BOOK.get(state.b).name}${state.c === 'all' ? '' : ' ' + (state.c === '0' ? 'prologue' : state.c)} · ${total.toLocaleString()} verse rows`;
  $('#resultInfo').textContent = where + (absent.length ? ` · ${absent.map(c => colMeta(c).label).join(', ')}: no text in this book` : '');
  renderPager(page, pages, total);

  const head = `<tr><th scope="col" class="refcol">Verse <span class="thsub">KJV numbering</span></th>${vis.map(id => {
    const c = colMeta(id);
    return `<th scope="col" draggable="true" data-col="${id}" class="colhead" title="Drag to reorder">${escapeHTML(c.label)} <span class="thsub">${escapeHTML(c.sub)}</span><button class="mini hide" data-act="hide" data-col="${id}" aria-label="Hide ${c.label}" title="Hide column">×</button></th>`;
  }).join('')}</tr>`;
  const body = slice.map(r => {
    const tds = vis.map(col => cellHTML(col, r, texts[col + r.book], res.conds)).join('');
    const focus = r.cid === state.v ? ' class="focus"' : '';
    const ctx = res.searching ? ` <a class="ctx" href="?view=table&b=${r.book}&c=${r.ch}&v=${encodeURIComponent(r.cid)}${keepCols()}" data-nav="1" title="Show in context">context</a>` : '';
    return `<tr id="r-${cssId(r.cid)}"${focus}><th scope="row" class="ref"><a href="?view=table&b=${r.book}&c=${r.ch}&v=${encodeURIComponent(r.cid)}${keepCols()}" data-nav="1">${escapeHTML(refLabel(r))}</a>${ctx}</th>${tds}</tr>`;
  }).join('');
  $('#tableWrap').innerHTML = total
    ? `<table class="parallel"><thead>${head}</thead><tbody>${body}</tbody></table>`
    : `<p class="empty">No verse rows match. ${res.searching ? 'Try plain mode, switch off “whole word”, or widen the scope.' : ''}</p>`;
  if (state.v) {
    const el = document.getElementById(`r-${cssId(state.v)}`);
    if (el) el.scrollIntoView({ block: 'center' });
  }
}

function keepCols() {
  return state.cols !== DEFAULTS.cols ? `&cols=${state.cols}` : '';
}

function cssId(cid) { return cid.replace(/\./g, '-'); }

function cellHTML(col, row, cells, conds) {
  const c = colMeta(col);
  const attrs = `lang="${c.lang}" dir="${c.dir}" class="cell cell-${col}"`;
  const cell = cells ? cells[row.i] : null;
  if (cell == null) {
    return `<td ${attrs.replace('class="cell', 'class="cell gap')} title="No text at this reference in this edition (a deliberate gap, not an error)"><span class="gapmark">—</span></td>`;
  }
  const nat = cellNative(cell);
  const natHTML = nat && state.nat === '1' ? `<span class="native" title="Reference in this edition's own numbering">${escapeHTML(nat)}</span> ` : '';
  if (cellIsCont(cell)) {
    return `<td ${attrs.replace('class="cell', 'class="cell cont')} title="This edition joins this verse with the previous row; its text is shown there"><span class="native">${escapeHTML(nat)}</span> <span class="contmark">↑ text shown above</span></td>`;
  }
  const text = cellText(cell);
  const spans = [];
  for (const cd of conds) {
    const re = cd.res[col] || (cd.col !== 'any' ? queryRegex(cd.q, cd.mode, col, cd.level) : null);
    if (re) spans.push([cd.cls, matchSpans(text, re, col, cd.level)]);
  }
  return `<td ${attrs}>${natHTML}${spans.length ? highlight(text, spans) : escapeHTML(text)}</td>`;
}

function renderPager(page, pages, total) {
  const el = $('#pager');
  const dis = b => b ? 'disabled' : '';
  el.innerHTML = `
    <button class="pg" data-page="1" ${dis(page <= 1)} aria-label="First page">«</button>
    <button class="pg" data-page="${page - 1}" ${dis(page <= 1)} aria-label="Previous page">‹</button>
    <span class="pginfo">Page ${page} / ${pages}</span>
    <button class="pg" data-page="${page + 1}" ${dis(page >= pages)} aria-label="Next page">›</button>
    <button class="pg" data-page="${pages}" ${dis(page >= pages)} aria-label="Last page">»</button>
    <label class="ps">Rows <select id="psSel">${PAGE_SIZES.map(n => `<option ${+state.ps === n ? 'selected' : ''}>${n}</option>`).join('')}</select></label>
    <button id="csvBtn" class="download-btn" ${dis(!total)}>Download CSV</button>`;
}

function csvEscape(s) {
  s = String(s ?? '');
  return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

async function downloadCSV() {
  if (!lastResult) return;
  const vis = lastResult.cols || visibleCols();
  const pairs = [];
  const seen = new Set();
  for (const r of lastResult.rows) for (const col of vis) {
    const k = col + r.book;
    if (!seen.has(k) && hasText(col, r.book)) { seen.add(k); pairs.push([col, r.book]); }
  }
  setStatus('Preparing CSV…');
  await loadTexts(pairs);
  const header = ['Verse (KJV numbering)', 'Canonical ID'];
  for (const col of vis) header.push(colMeta(col).label, `${colMeta(col).label} own reference`);
  const lines = [header.map(csvEscape).join(',')];
  for (const r of lastResult.rows) {
    const out = [refLabel(r), r.cid];
    for (const col of vis) {
      const cells = await loadText(col, r.book);
      const cell = cells ? cells[r.i] : null;
      out.push(cellIsCont(cell) ? '' : cellText(cell), cellNative(cell) || '');
    }
    lines.push(out.map(csvEscape).join(','));
  }
  setStatus('');
  const blob = new Blob(['﻿' + lines.join('\r\n')], { type: 'text/csv;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  const tag = state.q ? `search-${state.q.replace(/[^\p{L}\p{N}]+/gu, '_').slice(0, 30)}` : `${state.b}-${state.c}`;
  a.download = `polyglot-${tag}.csv`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

// ------------------------------------------------------------------ landing / about
function renderLanding() {
  $('#landing').hidden = !state.landing;
}

function renderCoverage() {
  const rows = META.columns.map(c => {
    const cv = META.coverage[c.id];
    const s = cv.by_section;
    return `<tr><th scope="row">${escapeHTML(c.label)} <span class="thsub">${escapeHTML(c.sub)}</span></th>
      <td class="num">${(s.OT || 0).toLocaleString()}</td><td class="num">${(s.DC || 0).toLocaleString()}</td><td class="num">${(s.NT || 0).toLocaleString()}</td>
      <td class="num">${cv.rows.toLocaleString()}</td><td class="num">${cv.pct}%</td></tr>`;
  }).join('');
  const rs = META.rows_by_section;
  const html = `<table class="coverage"><thead><tr><th>Column</th><th>OT rows</th><th>DC rows</th><th>NT rows</th><th>Total</th><th>Share of ${META.spine_rows.toLocaleString()} rows</th></tr></thead>
    <tbody>${rows}<tr class="total"><th scope="row">Spine (all rows)</th><td class="num">${(rs.OT || 0).toLocaleString()}</td><td class="num">${(rs.DC || 0).toLocaleString()}</td><td class="num">${(rs.NT || 0).toLocaleString()}</td><td class="num">${META.spine_rows.toLocaleString()}</td><td></td></tr></tbody></table>`;
  document.querySelectorAll('.coverage-slot').forEach(el => { el.innerHTML = html; });
}

// ------------------------------------------------------------------ render / events
export async function render() {
  document.body.dataset.view = state.view;
  document.querySelectorAll('.tab').forEach(t => t.setAttribute('aria-selected', String(t.dataset.view === state.view)));
  $('#tableView').hidden = state.view !== 'table';
  $('#renderView').hidden = state.view !== 'renderings';
  $('#aboutView').hidden = state.view !== 'about';
  renderLanding();
  if (state.view === 'table') await renderTable();
  else if (state.view === 'renderings') await renderRenderings(state);
  writeURL(false);
}

function bindEvents() {
  document.querySelectorAll('.tab').forEach(t => t.addEventListener('click', e => {
    e.preventDefault();
    navigate({ view: t.dataset.view }, true);
  }));
  $('#bookSel').addEventListener('change', e => navigate({ b: e.target.value, c: String(chapterList(e.target.value)[0]), v: '', p: '1', q: state.sc === 'all' ? state.q : state.q }, true));
  $('#chapSel').addEventListener('change', e => navigate({ c: e.target.value, v: '', p: '1' }, true));
  $('#prevCh').addEventListener('click', () => stepChapter(-1));
  $('#nextCh').addEventListener('click', () => stepChapter(1));
  $('#searchForm').addEventListener('submit', e => {
    e.preventDefault();
    navigate({
      q: $('#q').value.trim(), qc: $('#qc').value, mm: $('#mm').value, acc: $('#acc').checked ? '1' : '0',
      sc: $('#sc').value, q2: $('#q2').value.trim(), qc2: $('#qc2').value, mm2: $('#mm2').value,
      acc2: $('#acc2').checked ? '1' : '0', p: '1', v: '',
    }, true);
  });
  $('#clearSearch').addEventListener('click', () => {
    $('#cond2').dataset.open = '';
    navigate({ q: '', q2: '', p: '1' }, true);
  });
  $('#addCond').addEventListener('click', () => {
    $('#cond2').hidden = false;
    $('#cond2').dataset.open = '1';
    $('#q2').focus();
  });
  $('#nat').addEventListener('change', e => navigate({ nat: e.target.checked ? '1' : '0' }, false));
  $('#colChips').addEventListener('click', e => {
    const t = e.target.closest('[data-act]');
    if (!t || t.tagName === 'INPUT') return;
    moveCol(t.dataset.col, t.dataset.act === 'left' ? -1 : 1);
  });
  $('#colChips').addEventListener('change', e => {
    const t = e.target;
    if (t.dataset.act !== 'toggle') return;
    let vis = visibleCols();
    if (t.checked) vis.push(t.dataset.col); else vis = vis.filter(c => c !== t.dataset.col);
    if (!vis.length) { t.checked = true; return; }
    navigate({ cols: vis.join(',') }, false);
  });
  $('#pager').addEventListener('click', e => {
    const b = e.target.closest('button.pg');
    if (b && !b.disabled) { navigate({ p: b.dataset.page, v: '' }, true); window.scrollTo(0, $('#tableWrap').offsetTop - 80); }
    if (e.target.id === 'csvBtn') downloadCSV();
  });
  $('#pager').addEventListener('change', e => {
    if (e.target.id === 'psSel') navigate({ ps: e.target.value, p: '1' }, false);
  });
  // header: hide buttons + drag reorder
  const wrap = $('#tableWrap');
  wrap.addEventListener('click', e => {
    const hide = e.target.closest('button[data-act="hide"]');
    if (hide) {
      const vis = visibleCols().filter(c => c !== hide.dataset.col);
      if (vis.length) navigate({ cols: vis.join(',') }, false);
    }
  });
  let dragCol = null;
  wrap.addEventListener('dragstart', e => {
    const th = e.target.closest('th.colhead');
    if (!th) return;
    dragCol = th.dataset.col;
    th.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', dragCol);
  });
  wrap.addEventListener('dragover', e => {
    const th = e.target.closest('th.colhead');
    if (!th || !dragCol) return;
    e.preventDefault();
    wrap.querySelectorAll('th.drag-over').forEach(x => x.classList.remove('drag-over'));
    th.classList.add('drag-over');
  });
  wrap.addEventListener('drop', e => {
    const th = e.target.closest('th.colhead');
    if (!th || !dragCol) return;
    e.preventDefault();
    const vis = visibleCols().filter(c => c !== dragCol);
    vis.splice(vis.indexOf(th.dataset.col), 0, dragCol);
    dragCol = null;
    navigate({ cols: vis.join(',') }, false);
  });
  wrap.addEventListener('dragend', () => { dragCol = null; wrap.querySelectorAll('.dragging,.drag-over').forEach(x => x.classList.remove('dragging', 'drag-over')); });
  // internal navigation links keep history
  document.addEventListener('click', e => {
    const a = e.target.closest('a[data-nav]');
    if (!a || e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return;
    e.preventDefault();
    const u = new URL(a.href);
    history.pushState(null, '', u.pathname + u.search);
    readURL();
    render();
  });
  window.addEventListener('popstate', () => { readURL(); render(); });
}

function stepChapter(d) {
  const chs = chapterList(state.b);
  if (state.c === 'all') return;
  const i = chs.indexOf(+state.c);
  if (i + d >= 0 && i + d < chs.length) return navigate({ c: String(chs[i + d]), v: '', p: '1' }, true);
  const bi = META.books.findIndex(b => b.id === state.b);
  const nb = META.books[bi + d];
  if (nb) {
    const nchs = chapterList(nb.id);
    navigate({ b: nb.id, c: String(d > 0 ? nchs[0] : nchs[nchs.length - 1]), v: '', p: '1' }, true);
  }
}

async function main() {
  try {
    await loadMeta();
  } catch (e) {
    $('#status').hidden = false;
    $('#status').textContent = `Could not load data: ${e.message}`;
    $('#loading').classList.add('is-hidden');
    return;
  }
  $('#built').textContent = `Built ${META.built}`;
  for (const sel of ['#qc', '#qc2']) {
    const s = $(sel);
    if (sel === '#qc') s.appendChild(new Option('any column', 'any'));
    for (const c of META.columns) s.appendChild(new Option(c.label, c.id));
  }
  renderCoverage();
  initRenderings({ state, navigate, writeURL, setStatus });
  bindEvents();
  readURL();
  armed = true;
  await render();
  $('#loading').classList.add('is-hidden');
  window.__polyglotReady = true;
}

main();
