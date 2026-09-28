// Unicode normalization shared by search, highlighting and Renderings.
// Mirrors scripts/polyglot/textnorm.py (tests/test_data.py checks agreement).
//
// level "fold":   drop every combining mark (accents, breathings, nikud,
//                 cantillation), lowercase, final sigma -> sigma, æ/œ -> ae/oe,
//                 and for Latin j -> i.  Accent/nikud-insensitive.
// level "pointed": keep marks except Hebrew cantillation and meteg; lowercase.

const MARK = /\p{M}/u;
const HEB_CANT = /[֑-ֽ֯]/u;
const LIG = { 'æ': 'ae', 'Æ': 'ae', 'œ': 'oe', 'Œ': 'oe' };

export function foldChar(ch, col, level = 'fold') {
  let s = LIG[ch] || ch;
  s = s.normalize('NFD');
  let out = '';
  for (const c of s) {
    if (level === 'fold' ? MARK.test(c) : HEB_CANT.test(c)) continue;
    out += c;
  }
  out = out.toLowerCase();
  if (level === 'fold') {
    out = out.replace(/ς/g, 'σ');
    if (col === 'la') out = out.replace(/j/g, 'i');
  }
  return out;
}

export function fold(str, col, level = 'fold') {
  let out = '';
  for (const ch of str.normalize('NFC')) out += foldChar(ch, col, level);
  return out.normalize('NFC');
}

// Folded text plus a map from each folded UTF-16 index back to the index of
// the original character, so matches on folded text can be highlighted in
// the original (accents and nikud included).
export function foldWithMap(str, col, level = 'fold') {
  let folded = '';
  const map = [];
  let i = 0;
  for (const ch of str) {
    const f = foldChar(ch, col, level);
    for (let k = 0; k < f.length; k++) map.push(i);
    folded += f;
    i += ch.length;
  }
  map.push(str.length);
  return { folded, map };
}

const TOKEN_RE = /(?:(?!ʼ)[\p{L}\p{M}])+/gu;
const HAS_LETTER = /\p{L}/u;

export function tokens(text) {
  const out = [];
  for (const m of text.normalize('NFC').matchAll(TOKEN_RE)) {
    if (HAS_LETTER.test(m[0])) out.push(m[0]);
  }
  return out;
}

// Per-column Renderings key; see textnorm.key() in Python.
export function tokenKey(col, tok) {
  if (col === 'he' || col === 'grc' || col === 'la') return fold(tok, col, 'fold');
  if (col === 'he_pointed') return fold(tok, 'he', 'pointed');
  return tok.normalize('NFC').toLowerCase();
}

export function escapeRegex(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

export function escapeHTML(s) {
  return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

// Build a RegExp that runs on folded text for a user query.
// mode: plain (substring), word (whole word), regex.
export function queryRegex(query, mode, col, level = 'fold') {
  if (!query) return null;
  if (mode === 'regex') {
    let src = query.normalize('NFD');
    if (level === 'fold') src = src.replace(/\p{M}/gu, '').replace(/ς/g, 'σ');
    else src = src.replace(HEB_CANT, '');
    src = src.normalize('NFC');
    if (col === 'la' && level === 'fold') src = src.replace(/j/g, 'i');
    return new RegExp(src, 'giu');
  }
  const f = escapeRegex(fold(query.trim(), col, level));
  if (!f) return null;
  if (mode === 'word') return new RegExp(`(?<![\\p{L}\\p{M}])${f}(?![\\p{L}\\p{M}])`, 'giu');
  return new RegExp(f, 'giu');
}

// Return [[start, end], ...] spans in the ORIGINAL text for regex matches on
// its folded form. Zero-width matches are skipped; at most `limit` spans.
export function matchSpans(text, re, col, level = 'fold', limit = 200) {
  if (!re || !text) return [];
  const { folded, map } = foldWithMap(text, col, level);
  re.lastIndex = 0;
  const spans = [];
  let m;
  while ((m = re.exec(folded)) && spans.length < limit) {
    if (m[0].length === 0) { re.lastIndex++; continue; }
    let s = map[m.index];
    let e = map[m.index + m[0].length];
    if (e === undefined) e = text.length;
    // extend over trailing combining marks of the last matched character
    while (e < text.length && MARK.test(text[e])) e++;
    spans.push([s, e]);
  }
  return spans;
}

export function highlight(text, spansByClass) {
  // spansByClass: [[cls, spans], ...]; later classes win on overlap
  const marks = new Array(text.length).fill(null);
  for (const [cls, spans] of spansByClass) {
    for (const [s, e] of spans) for (let i = s; i < e; i++) marks[i] = cls;
  }
  let out = '';
  let cur = null;
  let buf = '';
  const flush = () => {
    if (!buf) return;
    out += cur ? `<mark class="${cur}">${escapeHTML(buf)}</mark>` : escapeHTML(buf);
    buf = '';
  };
  for (let i = 0; i < text.length; i++) {
    if (marks[i] !== cur) { flush(); cur = marks[i]; }
    buf += text[i];
  }
  flush();
  return out;
}
