#!/usr/bin/env python3
"""Independent check of the verse alignment.

For each column paired with English (and Latin–Greek), learn a crude
translation dictionary from the aligned rows themselves (Dice association of
word types that co-occur in the same row), then score every row against its
own partner and against the partner's neighbours (±1, ±2 rows). A row whose
neighbour fits clearly better than itself is flagged; clusters of flags in
one chapter point to a systematic offset in the versification mapping.

    python3 scripts/qa_alignment.py            # summary
    python3 scripts/qa_alignment.py --rows he  # list flagged rows for Hebrew
Writes build/alignment_qa.json.
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "data"


def load_tokens(k):
    d = json.loads((DATA / "tokens" / f"{k}.json").read_text(encoding="utf-8"))
    rows = [None if r is None else [int(x, 36) for x in r.split()] if r else [] for r in d["rows"]]
    return d["vocab"], rows


def spine():
    meta = json.loads((DATA / "meta.json").read_text(encoding="utf-8"))
    out = []
    for b in meta["books"]:
        for ch, vs in b["chapters"]:
            for part in vs.split(","):
                if "-" in part:
                    a, z = part.split("-")
                    out += [f"{b['id']}.{ch}.{v}" for v in range(int(a), int(z) + 1)]
                else:
                    out.append(f"{b['id']}.{ch}.{part}")
    return out, meta


def dictionary(ra, rb, maxdf_a, maxdf_b):
    dfa, dfb, co = Counter(), Counter(), Counter()
    for a, b in zip(ra, rb):
        if a is None or b is None:
            continue
        a = [x for x in a if x >= maxdf_a]  # vocab is sorted by df: skip the most frequent
        b = [y for y in b if y >= maxdf_b]
        dfa.update(a)
        dfb.update(b)
        for x in a:
            for y in b:
                co[(x, y)] += 1
    best = {}
    for (x, y), c in co.items():
        if c < 3:
            continue
        d = 2 * c / (dfa[x] + dfb[y])
        if d > best.get(x, (0, None))[0]:
            best[x] = (d, y)
    return {x: y for x, (d, y) in best.items() if d >= 0.2}, maxdf_a


def score(a, b, dic, cut):
    if not a or not b:
        return 0.0
    bs = set(b)
    ws = [x for x in a if x >= cut and x in dic]
    if not ws:
        return 0.0
    return sum(1 for x in ws if dic[x] in bs) / len(ws)


def main():
    cids, meta = spine()
    book_of = [c.split(".")[0] for c in cids]
    toks = {k: load_tokens(k)[1] for k in ("he", "grc", "la", "de", "en")}
    pairs = [("he", "en"), ("grc", "en"), ("la", "en"), ("de", "en"), ("grc", "la")]
    report = {}
    for a, b in pairs:
        dic, cut = dictionary(toks[a], toks[b], 60, 60)
        flagged = []
        n = 0
        scores = []
        for i, (ra, rb) in enumerate(zip(toks[a], toks[b])):
            if ra is None or rb is None:
                continue
            s0 = score(ra, rb, dic, cut)
            n += 1
            scores.append(s0)
            best, where = s0, 0
            for d in (-2, -1, 1, 2):
                j = i + d
                if 0 <= j < len(cids) and book_of[j] == book_of[i] and toks[b][j] is not None:
                    s = score(ra, toks[b][j], dic, cut)
                    if s > best:
                        best, where = s, d
            if where and best >= s0 + 0.3 and best >= 0.5:
                flagged.append((cids[i], round(s0, 2), round(best, 2), where))
        by_ch = Counter(c.rsplit(".", 1)[0] for c, *_ in flagged)
        report[f"{a}-{b}"] = {
            "rows_compared": n,
            "mean_score": round(sum(scores) / max(1, len(scores)), 3),
            "flagged": len(flagged),
            "flag_rate_pct": round(100 * len(flagged) / max(1, n), 2),
            "chapters_with_3plus_flags": {k: v for k, v in by_ch.most_common() if v >= 3},
            "rows": flagged,
        }
        print(f"{a}-{b}: {n} rows, mean score {report[f'{a}-{b}']['mean_score']}, "
              f"flagged {len(flagged)} ({report[f'{a}-{b}']['flag_rate_pct']}%); "
              f"clusters: {dict(list(report[f'{a}-{b}']['chapters_with_3plus_flags'].items())[:12])}")
    (ROOT / "build").mkdir(exist_ok=True)
    (ROOT / "build" / "alignment_qa.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    if "--rows" in sys.argv:
        k = sys.argv[sys.argv.index("--rows") + 1]
        for p, r in report.items():
            if p.startswith(k + "-"):
                for row in r["rows"]:
                    print(p, *row)


if __name__ == "__main__":
    main()
