#!/usr/bin/env python3
"""Build Polyglot Contabulate's static data.

    python3 scripts/build.py

Reads the sibling Contabulate corpora (KJV, Luther, Tanakh, GNT; read-only),
the raw Clementine Vulgate and Swete LXX sources in sources/raw, and the
STEPBible TVTMS versification table; writes

    docs/data/meta.json                 books, spine, columns, coverage
    docs/data/text/<col>/<Book>.json    per-column, per-book verse cells
    docs/data/tokens/<key>.json         per-verse word-type ids (Renderings)
    docs/instance.json                  hub metadata
    corpora/{vulgate,lxx}/all_lines.json  standalone-instance-ready corpora
    build/alignment_report.json         mapping statistics (not published)
"""
import datetime as dt
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from polyglot import sources as S  # noqa: E402
from polyglot import tvtms as T  # noqa: E402
from polyglot.books import BOOKS, ORDER, OSIS_TO_SIL, SIL_TO_OSIS, SECTION, NAME  # noqa: E402
from polyglot.textnorm import tokens, key, fold  # noqa: E402
from polyglot.stopwords import as_sets  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
DATA = DOCS / "data"

COLUMNS = [
    {"id": "he", "label": "Hebrew", "sub": "Masoretic Text (WLC)", "lang": "he", "dir": "rtl"},
    {"id": "grc", "label": "Greek", "sub": "LXX (Swete) · NT (SBLGNT)", "lang": "grc", "dir": "ltr"},
    {"id": "la", "label": "Latin", "sub": "Clementine Vulgate", "lang": "la", "dir": "ltr"},
    {"id": "de", "label": "German", "sub": "Luther 1912", "lang": "de", "dir": "ltr"},
    {"id": "en", "label": "English", "sub": "King James Version", "lang": "en", "dir": "ltr"},
]
COL_IDS = [c["id"] for c in COLUMNS]

# DC books whose Swete text we keep outside the TVTMS standard (no KJVA
# counterpart) are mapped by identity; EpJer is TVTMS "Lje" -> Bar 6.
EXTRA_SIL = {"EpJer": "Lje", "PssSol": "Pss", "3Macc": "3Ma", "4Macc": "4Ma"}


def sil_of(nv):
    b = nv["book"]
    return EXTRA_SIL.get(b) or OSIS_TO_SIL.get(b)


def letter(sub):
    return chr(ord("a") + sub - 1) if sub else ""


def cid_from_std(std):
    sil, ch, v, sub = std
    book = SIL_TO_OSIS.get(sil)
    if sil == "Ps2":  # TVTMS files Psalm 151 as a separate book
        return f"Ps.151.{v}"
    if book is None:
        return None
    return f"{book}.{ch}.{v}"


def cid_key(cid):
    book, ch, v = cid.split(".")
    m = re.fullmatch(r"(\d+)([a-z]*)", v)
    return (ORDER.get(book, 999), int(ch), int(m.group(1)), m.group(2))


def place(col, verses, mapping, is_standard=False):
    """Assign native verses to canonical rows.

    Returns cells: cid -> list of (native verse, role) where role is "main" or
    "cont" (the text sits in an earlier row because the native verse spans
    several standard verses), plus per-verse mapping provenance.
    """
    cells = defaultdict(list)
    prov = Counter()
    for nv, mp in zip(verses, mapping):
        book = nv["book"]
        if book == "EpJer":
            book = "Bar"  # KJVA files the Epistle of Jeremiah as Baruch 6
        if nv.get("fixed"):
            cells[nv["fixed"]].append((nv, "main"))
            prov["loader (Swete Esther additions)"] += 1
            continue
        if is_standard or mp is None:
            ch = nv["ch"] if nv["book"] != "EpJer" else 6
            cid = f"{book}.{ch}.{nv['v']}{letter(nv['sub'])}"
            cells[cid].append((nv, "main"))
            prov["identity"] += 1
            continue
        action = mp["action"].rstrip("*").strip()
        if action.startswith("CopiedFrom"):
            # LXX duplicates (3 Kgdms 2:35a-o, 12:24a-z ...): keep the copy at its
            # own position as an extra row rather than doubling the parallel verse
            ch = nv["ch"]
            cid = f"{book}.{ch}.{nv['v']}{letter(nv['sub'])}"
            cells[cid].append((nv, "main"))
            prov["tvtms:CopiedFrom (kept in place)"] += 1
            continue
        targets = [cid_from_std(s) for s in mp["std"]]
        targets = [t for t in targets if t]
        if not targets:
            cid = f"{book}.{nv['ch']}.{nv['v']}{letter(nv['sub'])}"
            cells[cid].append((nv, "main"))
            prov["identity (unmappable standard)"] += 1
            continue
        cells[targets[0]].append((nv, "main"))
        for t in targets[1:]:
            if t.split(".")[0] == targets[0].split(".")[0]:
                cells[t].append((nv, "cont"))
        prov["tvtms:" + action] += 1
    return cells, prov


def native_label(nv):
    return (nv["nb"] + " " if nv["nb"] else "") + f"{nv['nch']}:{nv['nv']}"


def encode_cell(cid, entries, col):
    """-> None | "text" | [text, native] | ["", native, "cont"]"""
    book, ch, v = cid.split(".")
    mains = [e for e, r in entries if r == "main"]
    conts = [e for e, r in entries if r == "cont"]
    if mains:
        text = " ".join(e["text"] for e in mains)
        labels = [native_label(e) for e in mains]
        same = (len(mains) == 1 and not mains[0]["nb"] and mains[0]["nch"] == ch
                and mains[0]["nv"] == (v if v != "0" else "title"))
        if same:
            return text
        if len(mains) > 1 and all(e["nb"] == mains[0]["nb"] and e["nch"] == mains[0]["nch"] for e in mains):
            lab = (mains[0]["nb"] + " " if mains[0]["nb"] else "") + f"{mains[0]['nch']}:{mains[0]['nv']}–{mains[-1]['nv']}"
        else:
            lab = "; ".join(dict.fromkeys(labels))
        return [text, lab]
    if conts:
        return ["", native_label(conts[0]), "cont"]
    return None


def build():
    stamp = dt.datetime.now().astimezone()
    lines = T.load_lines()
    kjva = T.kjva_chapter_counts()

    print("loading texts ...")
    texts = {
        "he": S.load_existing("he"),
        "de": S.load_existing("de"),
        "la": S.load_vulgate(),
        "lxx": S.load_swete("main"),
        "gnt": S.load_existing("gnt"),
        "en": S.load_existing("en"),
    }
    report = {"built": stamp.isoformat(timespec="seconds"), "texts": {}}
    placed = {}
    for name, verses in texts.items():
        if name == "en":
            mapping, stats = [None] * len(verses), {"standard (identity)": len(verses)}
        else:
            override = None
            if name == "lxx":
                override = {}
                for ref, v in S.FIXES["last_verse"].items():
                    bk, ch = ref.split()
                    override[(OSIS_TO_SIL[bk], ch)] = v["last"]
            mapping, stats = T.map_text(verses, lines, sil_of, override)
        cells, prov = place(name, verses, mapping, is_standard=(name == "en"))
        placed[name] = cells
        report["texts"][name] = {"native_verses": len(verses), "tvtms": stats, "placement": dict(prov)}
        print(f"  {name}: {len(verses)} verses -> {len(cells)} rows; {dict(prov)}")

    # Greek column = Swete LXX (OT/DC) + SBLGNT (NT)
    col_cells = {
        "he": placed["he"], "de": placed["de"], "la": placed["la"], "en": placed["en"],
        "grc": {**placed["lxx"], **placed["gnt"]},
    }

    spine = sorted({cid for c in col_cells.values() for cid in c}, key=cid_key)
    unknown = [c for c in spine if c.split(".")[0] not in ORDER]
    if unknown:
        raise SystemExit(f"unknown books in spine: {unknown[:10]}")

    # ------------------------------------------------------------ per book files
    by_book = defaultdict(list)
    for cid in spine:
        by_book[cid.split(".")[0]].append(cid)

    for sub in ("text", "tokens"):
        d = DATA / sub
        if d.exists():
            for p in sorted(d.rglob("*.json")):
                p.unlink()
    (DATA / "text").mkdir(parents=True, exist_ok=True)

    books_meta = []
    coverage = {c: Counter() for c in COL_IDS}
    total_rows = Counter()
    for b in BOOKS:
        book = b[0]
        cids = by_book.get(book)
        if not cids:
            continue
        chapters = []
        for cid in cids:
            _, ch, v = cid.split(".")
            if not chapters or chapters[-1][0] != int(ch):
                chapters.append([int(ch), []])
            chapters[-1][1].append(v)
        present = {}
        for col in COL_IDS:
            arr = [encode_cell(cid, col_cells[col].get(cid, []), col) for cid in cids]
            n = sum(1 for x in arr if x is not None and (isinstance(x, str) or x[0]))
            present[col] = n
            coverage[col][b[2]] += n
            if n:
                out = DATA / "text" / col / f"{book}.json"
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(json.dumps(arr, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        total_rows[b[2]] += len(cids)
        books_meta.append({
            "id": book, "name": b[3], "names": {"la": b[4], "grc": b[5], "he": b[6], "de": b[7]},
            "section": b[2], "rows": len(cids), "present": present,
            "chapters": [[ch, compress_verses(vs)] for ch, vs in chapters],
        })

    # ------------------------------------------------------------ tokens (Renderings)
    (DATA / "tokens").mkdir(parents=True, exist_ok=True)
    stop = {k: sorted({key(k, w) for w in ws}) for k, ws in as_sets().items()}
    stop["hep"] = stop["he"]
    token_stats = {}
    for tkey, col in (("he", "he"), ("hep", "he"), ("grc", "grc"), ("la", "la"), ("de", "de"), ("en", "en")):
        kname = "he_pointed" if tkey == "hep" else col
        per_row = []
        df = Counter()
        tf = Counter()
        for cid in spine:
            entries = [e for e, r in col_cells[col].get(cid, []) if r == "main"]
            if not entries:
                per_row.append(None)
                continue
            toks = [key(kname, t) for e in entries for t in tokens(e["text"])]
            tf.update(toks)
            types = set(toks)
            df.update(types)
            per_row.append(types)
        vocab = [w for w, _ in sorted(df.items(), key=lambda x: (-x[1], x[0]))]
        idx = {w: i for i, w in enumerate(vocab)}
        rows = []
        for types in per_row:
            if types is None:
                rows.append(None)
            else:
                rows.append(" ".join(to36(i) for i in sorted(idx[t] for t in types)))
        payload = {"key": tkey, "col": col, "vocab": vocab, "tf": [tf[w] for w in vocab], "rows": rows}
        (DATA / "tokens" / f"{tkey}.json").write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        token_stats[tkey] = {"types": len(vocab), "tokens": sum(tf.values()),
                             "rows": sum(1 for r in rows if r is not None)}

    # ------------------------------------------------------------ meta
    cov_total = {c: sum(coverage[c].values()) for c in COL_IDS}
    rows_total = sum(total_rows.values())
    both = Counter()
    for cid in spine:
        have = [c for c in COL_IDS if has_text(col_cells[c].get(cid))]
        both[len(have)] += 1
    meta = {
        "built": stamp.strftime("%Y-%m-%d %H:%M %Z"),
        "columns": COLUMNS,
        "books": books_meta,
        "spine_rows": rows_total,
        "sections": {"OT": "Old Testament", "DC": "Deuterocanon / Apocrypha", "NT": "New Testament"},
        "coverage": {c: {"rows": cov_total[c], "by_section": dict(coverage[c]),
                         "pct": round(100 * cov_total[c] / rows_total, 1)} for c in COL_IDS},
        "rows_by_section": dict(total_rows),
        "rows_by_column_count": {str(k): v for k, v in sorted(both.items())},
        "tokens": token_stats,
        "stopwords": stop,
    }
    (DATA / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    report["swete_verse_number_repairs"] = [list(r) for r in S.REPAIRS]
    report["spine_rows"] = rows_total
    report["coverage"] = meta["coverage"]
    report["rows_by_column_count"] = meta["rows_by_column_count"]
    (ROOT / "build").mkdir(exist_ok=True)
    (ROOT / "build" / "alignment_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    write_standalone(texts, placed)
    write_instance(meta, stamp)
    print(f"spine rows: {rows_total}")
    for c in COL_IDS:
        print(f"  {c}: {cov_total[c]} rows ({meta['coverage'][c]['pct']}%) {dict(coverage[c])}")
    print("tokens:", token_stats)


def has_text(entries):
    return bool(entries) and any(r == "main" for _, r in entries)


def to36(n):
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    if n == 0:
        return "0"
    s = ""
    while n:
        n, r = divmod(n, 36)
        s = digits[r] + s
    return s


def compress_verses(vs):
    """['0','1','2','3','5','35a'] -> '0-3,5,35a'"""
    out = []
    run = None
    for v in vs:
        if v.isdigit():
            n = int(v)
            if run and n == run[1] + 1:
                run[1] = n
                continue
            if run:
                out.append(f"{run[0]}-{run[1]}" if run[1] > run[0] else str(run[0]))
            run = [n, n]
        else:
            if run:
                out.append(f"{run[0]}-{run[1]}" if run[1] > run[0] else str(run[0]))
                run = None
            out.append(v)
    if run:
        out.append(f"{run[0]}-{run[1]}" if run[1] > run[0] else str(run[0]))
    return ",".join(out)


def write_standalone(texts, placed):
    """all_lines.json in the shape used by the other Contabulate instances,
    with native numbering as canonical_id plus the KJV-spine standard id."""
    std_of = {}
    for name in ("la", "lxx"):
        for cid, entries in placed[name].items():
            for nv, role in entries:
                if role == "main":
                    std_of[id(nv)] = cid
    specs = {
        "vulgate": texts["la"],
        "lxx": texts["lxx"] + S.load_swete("alt"),
    }
    for name, verses in specs.items():
        recs = []
        order = sorted(range(len(verses)), key=lambda i: (
            ORDER.get(verses[i]["book"] if verses[i]["book"] != "EpJer" else "Bar", 999),
            verses[i].get("nb", ""), verses[i]["ch"], verses[i]["v"], verses[i]["sub"]))
        play_ids = {}
        for n, i in enumerate(order, 1):
            nv = verses[i]
            book = nv["book"]
            pid = play_ids.setdefault(book + nv.get("nb", ""), len(play_ids) + 1)
            vlab = f"{nv['v']}{letter(nv['sub'])}"
            native_id = f"{book}.{nv['ch']}.{vlab}"
            if nv.get("nb", "").endswith("OG"):
                native_id = f"{book}OG.{nv['ch']}.{vlab}"
            recs.append({
                "play_id": pid, "canonical_id": native_id,
                "location": f"{pid:02d}.{book}.{nv['ch']:03d}.{nv['v']:03d}{letter(nv['sub'])}",
                "act": nv["ch"], "scene": nv["v"], "line_num": n, "speaker": "",
                "text": nv["text"], "native_ref": native_label(nv),
                "standard_id": std_of.get(id(nv)),
            })
        out = ROOT / "corpora" / name / "all_lines.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(recs, ensure_ascii=False, indent=0), encoding="utf-8")
        print(f"  corpora/{name}/all_lines.json: {len(recs)} records")


def write_instance(meta, stamp):
    im = json.loads((ROOT / "instance-meta.json").read_text(encoding="utf-8"))
    tok = meta["tokens"]
    stats = {
        "texts": len(meta["books"]), "text_label": im.pop("text_label", "books"),
        "segments": meta["spine_rows"], "segment_label": im.pop("segment_label", "verse rows"),
        "words": sum(tok[k]["tokens"] for k in ("he", "grc", "la", "de", "en")),
        "distinct_words": sum(tok[k]["types"] for k in ("he", "grc", "la", "de", "en")),
        "commentaries": 0, "comments": 0,
    }
    inst = {"schema": 1, **im, "updated": stamp.strftime("%Y-%m-%d"), "stats": stats}
    (DOCS / "instance.json").write_text(json.dumps(inst, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    build()
