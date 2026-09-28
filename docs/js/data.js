// Lazy data access: meta, per-column/per-book text, per-column token tables.

export let META = null;
export const BOOK = new Map();      // id -> book meta (+ rows)
export const GLOBAL = new Map();    // cid -> global spine index
export let SPINE = [];              // global list of {cid, book, ch, v}

export async function loadMeta() {
  if (META) return META;
  const res = await fetch('data/meta.json');
  if (!res.ok) throw new Error(`meta.json: HTTP ${res.status}`);
  META = await res.json();
  let g = 0;
  for (const b of META.books) {
    b.rowList = [];
    for (const [ch, vs] of b.chapters) {
      for (const part of vs.split(',')) {
        const m = part.match(/^(\d+)-(\d+)$/);
        const list = m ? range(+m[1], +m[2]).map(String) : [part];
        for (const v of list) {
          const cid = `${b.id}.${ch}.${v}`;
          const row = { cid, book: b.id, ch, v, g, i: b.rowList.length };
          b.rowList.push(row);
          SPINE.push(row);
          GLOBAL.set(cid, g++);
        }
      }
    }
    BOOK.set(b.id, b);
  }
  return META;
}

function range(a, z) {
  const out = [];
  for (let i = a; i <= z; i++) out.push(i);
  return out;
}

const textCache = new Map();
export function hasText(col, book) {
  const b = BOOK.get(book);
  return !!(b && b.present[col]);
}

export async function loadText(col, book) {
  if (!hasText(col, book)) return null;
  const k = `${col}/${book}`;
  if (!textCache.has(k)) {
    textCache.set(k, fetch(`data/text/${col}/${book}.json`).then(r => {
      if (!r.ok) throw new Error(`${k}: HTTP ${r.status}`);
      return r.json();
    }));
  }
  return textCache.get(k);
}

export async function loadTexts(pairs, onProgress) {
  let done = 0;
  const out = await Promise.all(pairs.map(([col, book]) => loadText(col, book).then(x => {
    done++;
    if (onProgress) onProgress(done, pairs.length);
    return x;
  })));
  return out;
}

// cell helpers: null | "text" | [text, native] | ["", native, "cont"]
export function cellText(cell) {
  if (cell == null) return '';
  return typeof cell === 'string' ? cell : cell[0];
}
export function cellNative(cell) {
  return cell == null || typeof cell === 'string' ? null : cell[1];
}
export function cellIsCont(cell) {
  return Array.isArray(cell) && cell[2] === 'cont';
}

const tokenCache = new Map();
export async function loadTokens(key) {
  if (!tokenCache.has(key)) {
    tokenCache.set(key, fetch(`data/tokens/${key}.json`).then(r => {
      if (!r.ok) throw new Error(`tokens ${key}: HTTP ${r.status}`);
      return r.json();
    }).then(d => {
      const rows = d.rows.map(r => r == null ? null : (r === '' ? new Int32Array(0) : Int32Array.from(r.split(' '), x => parseInt(x, 36))));
      const disp = d.disp ? d.disp.map((x, i) => x || d.vocab[i]) : d.vocab;
      return { key, col: d.col, vocab: d.vocab, disp, rows };
    }));
  }
  return tokenCache.get(key);
}

export function refLabel(row, short = true) {
  const b = BOOK.get(row.book);
  const name = short ? b.id : b.name;
  if (row.v === '0') return `${name} ${row.ch} title`;
  if (row.ch === 0) return `${name} prol. ${row.v}`;
  return `${name} ${row.ch}:${row.v}`;
}

export function rowByCid(cid) {
  const g = GLOBAL.get(cid);
  return g === undefined ? null : SPINE[g];
}
