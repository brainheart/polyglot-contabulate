"""STEPBible TVTMS reader and test evaluator.

TVTMS ("Translators Versification Traditions with Methodology for
Standardisation", STEPBible.org, CC BY 4.0) lists, for every place where
Bible traditions number verses differently, lines of the form

    SourceType  SourceRef  StandardRef  Action  ...  Tests

A line applies to a given Bible when all of its Tests are TRUE for *that
Bible's own verse inventory* (e.g. "Gen.32:33=Last", "Psa.9:30=Exist",
"Mal.3:23*2<Mal.3:22+Mal.3:24" comparing word counts). We evaluate the tests
against each of our texts, so each text is mapped by the tradition it
actually follows, without hand-picking "Hebrew" or "Latin" columns.

Standard = KJV/KJVA numbering (TVTMS's English standard), which is our spine.
"""
import re
from collections import defaultdict
from pathlib import Path

from .books import SIL_TO_OSIS
from .textnorm import tokens

ROOT = Path(__file__).resolve().parents[2]
TVTMS_PATH = ROOT / "sources" / "raw" / "tvtms" / "TVTMS.txt"

# case-insensitive SIL lookup (the file uses PSA, LJe, ... occasionally)
_SIL = {k.lower(): k for k in list(SIL_TO_OSIS) + ["Lje", "S3Y", "Ps2", "Oda", "Esg", "Ade"]}

REF_RE = re.compile(r"^([1-4]?[A-Za-z][A-Za-z0-9]{1,3})\.(\w+):(\d+|Title|TextBeforeV1)(?:([.!])(\w+))?$")


def _sub_index(tok):
    """'a' -> 1, 'b' -> 2, '0' -> 0, '2' -> 2."""
    if tok is None:
        return None
    if tok.isdigit():
        return int(tok)
    if len(tok) == 1 and tok.isalpha():
        return ord(tok.lower()) - ord("a") + 1
    m = re.fullmatch(r"([a-z])(\d+)", tok)
    if m:  # "!a1" style: rare, treat as the letter
        return ord(m.group(1)) - ord("a") + 1
    return None


def parse_ref(s, default_book=None):
    s = s.strip()
    if default_book and re.match(r"^\d+:", s):
        s = f"{default_book}.{s}"
    m = REF_RE.match(s)
    if not m:
        return None
    book, ch, v, sep, sub = m.groups()
    book = _SIL.get(book.lower(), book)
    return book, ch, v, _sub_index(sub) if sep else None


class Inventory:
    """Verse inventory of one text, keyed by TVTMS book codes.

    last_override: {(sil, ch): last verse} for documented transcription
    defects (two verses merged under one number)."""

    def __init__(self, verses, sil_of, last_override=None):
        self.words = defaultdict(int)      # (b, ch, v, sub) -> words
        self.whole = defaultdict(int)      # (b, ch, v) -> words incl. subverses
        self.last = {}                     # (b, ch) -> last verse number
        self.title = set()                 # (b, ch) with text before v1
        self.subs = defaultdict(int)       # (b, ch, v) -> number of subverses
        for nv in verses:
            b = sil_of(nv)
            if b is None:
                continue
            ch, v, sub = str(nv["ch"]), nv["v"], nv["sub"]
            # count words as letter runs, so Hebrew maqaf-joined words count
            # separately; skip the setuma/petucha paragraph letters
            n = sum(1 for t in tokens(nv["text"]) if t not in ("ס", "פ"))
            self.words[(b, ch, v, sub)] += n
            self.whole[(b, ch, v)] += n
            if v == 0:
                self.title.add((b, ch))
            else:
                self.last[(b, ch)] = max(self.last.get((b, ch), 0), v)
            if sub:
                self.subs[(b, ch, v)] = max(self.subs[(b, ch, v)], sub)
        self.last.update(last_override or {})

    def exists(self, ref):
        b, ch, v, sub = ref
        if v == "TextBeforeV1":
            return (b, ch) in self.title
        if v == "Title":
            return (b, ch) in self.title
        v = int(v)
        if sub is None or sub == 0:
            return self.whole.get((b, ch, v), 0) > 0
        return self.words.get((b, ch, v, sub), 0) > 0

    def count(self, ref):
        b, ch, v, sub = ref
        if v in ("Title", "TextBeforeV1"):
            return 0
        v = int(v)
        if sub is None:
            return self.whole.get((b, ch, v), 0)
        return self.words.get((b, ch, v, sub), 0)

    def is_last(self, ref):
        b, ch, v, _ = ref
        return v.isdigit() and self.last.get((b, ch)) == int(v)


def _eval_side(expr, inv, default_book):
    total = 0
    for term in expr.split("+"):
        term = term.strip()
        mult = 1
        if "*" in term:
            term, m = term.split("*", 1)
            mult = float(m)
        ref = parse_ref(term, default_book)
        if ref is None:
            raise ValueError(f"cannot parse term {term!r}")
        total += inv.count(ref) * mult
    return total


def eval_test(test, inv, default_book):
    test = test.strip()
    if not test:
        return True
    m = re.match(r"^(.*)=\s*(Exist|NotExist|Last)\s*$", test, re.I)
    if m:
        ref = parse_ref(m.group(1), default_book)
        if ref is None:
            raise ValueError(f"cannot parse {test!r}")
        kw = m.group(2).lower()
        if kw == "exist":
            return inv.exists(ref)
        if kw == "notexist":
            return not inv.exists(ref)
        return inv.is_last(ref)
    m = re.match(r"^(.*?)([<>])(.*)$", test)
    if m:
        a = _eval_side(m.group(1), inv, default_book)
        b = _eval_side(m.group(3), inv, default_book)
        return a < b if m.group(2) == "<" else a > b
    raise ValueError(f"unknown test {test!r}")


class Line:
    __slots__ = ("lineno", "stype", "src", "std", "action", "tests", "src_raw", "std_raw")


CORRECTIONS_PATH = ROOT / "sources" / "tvtms_corrections.json"
APPLIED_CORRECTIONS = []


def load_lines(path=TVTMS_PATH, corrections_path=CORRECTIONS_PATH):
    import json
    fixes = {}
    if corrections_path.exists():
        for c in json.loads(corrections_path.read_text(encoding="utf-8"))["changes"]:
            fixes[(c["stype"], c["src"])] = c["std"]
    del APPLIED_CORRECTIONS[:]
    text = path.read_text(encoding="utf-8-sig")
    lines = text.split("\n")
    start = next(i for i, l in enumerate(lines) if l.startswith("#DataStart(Expanded)"))
    end = next(i for i, l in enumerate(lines) if l.startswith("#DataEnd(Expanded)"))
    out = []
    for i in range(start + 1, end):
        f = lines[i].rstrip("\r").split("\t")
        if len(f) < 9:
            continue
        src = parse_ref(f[1])
        if src is None or src[2] in ("Title", "TextBeforeV1"):
            continue
        action = f[3].strip()
        if action.startswith("IfEmpty"):
            continue  # applies only to verses without text; ours always have text
        ln = Line()
        ln.lineno = i + 1
        ln.stype = f[0].strip()
        ln.src = src
        ln.src_raw = f[1].strip()
        ln.std_raw = f[2].strip()
        fix = fixes.get((ln.stype, ln.src_raw))
        if fix:
            APPLIED_CORRECTIONS.append((ln.lineno, ln.stype, ln.src_raw, ln.std_raw, fix))
            ln.std_raw = fix
        ln.std = parse_std(ln.std_raw)
        ln.action = action
        ln.tests = [t for t in f[8].split("&") if t.strip()]
        if not ln.std:
            continue
        out.append(ln)
    return out


def parse_std(s):
    """'Gen.5:32; 6:1' / 'Gen.2:25-3:1' / 'Psa.3:Title' / 'Est.1:1; 11:2-12'
    -> list of (book, ch, v, sub) with ranges expanded inside a chapter.
    v is an int, or 0 for a psalm title."""
    s = s.replace("*", "").strip()
    m = re.match(r"^([1-4]?[A-Za-z][A-Za-z0-9]{1,3})\.(.*)$", s)
    if not m:
        return []
    book = _SIL.get(m.group(1).lower(), m.group(1))
    out = []
    ch = None
    for part in re.split(r"[;,]\s*", m.group(2)):
        part = part.strip()
        if not part:
            continue
        mm = re.match(r"^(?:(\d+):)?(\d+|Title)(?:!(\w+))?(?:-(?:(\d+):)?(\d+))?", part)
        if not mm:
            continue
        if mm.group(1):
            ch = int(mm.group(1))
        if ch is None:
            continue
        if mm.group(2) == "Title":
            out.append((book, ch, 0, 0))
            continue
        v1 = int(mm.group(2))
        sub = _sub_index(mm.group(3)) or 0
        if mm.group(5):
            ch2 = int(mm.group(4)) if mm.group(4) else ch
            v2 = int(mm.group(5))
            if ch2 == ch:
                out.extend((book, ch, v, 0) for v in range(v1, v2 + 1))
            else:
                out.append((book, ch, v1, sub))
                out.extend((book, ch2, v, 0) for v in range(1, v2 + 1))
                ch = ch2
        else:
            out.append((book, ch, v1, sub))
    return out


def map_text(verses, lines, sil_of, last_override=None):
    """Return (mapping, stats). mapping[i] = dict(std=[...], action, line) for
    native verse i, or None when no TVTMS line mentions its reference
    (identity mapping)."""
    inv = Inventory(verses, sil_of, last_override)
    by_src = defaultdict(list)
    for ln in lines:
        by_src[(ln.src[0], ln.src[1], int(ln.src[2]), ln.src[3])].append(ln)
    by_type_src = {(ln.stype, ln.src_raw): ln for ln in lines}
    cache = {}

    def raw_pass(ln):
        if ln.lineno not in cache:
            cache[ln.lineno] = all(eval_test(t, inv, ln.src[0]) for t in ln.tests)
        return cache[ln.lineno]

    def passes(ln):
        if not raw_pass(ln):
            return False
        if ln.action.startswith("Concatenation"):
            # A concatenation line is followed by "!0"/"!a" lines for the same
            # tradition; those carry the discriminating length tests that the
            # concatenation line sometimes omits (e.g. Greek Esther 1:1).
            for suffix in ("!0", "!a"):
                sub = by_type_src.get((ln.stype, ln.src_raw + suffix))
                if sub is not None:
                    return raw_pass(sub)
        return True

    mapping = []
    stats = defaultdict(int)
    for nv in verses:
        b = sil_of(nv)
        if b is None or nv.get("fixed"):
            mapping.append(None)
            stats["not-in-tvtms-scope" if b is None else "fixed-by-loader"] += 1
            continue
        ch, v, sub = str(nv["ch"]), nv["v"], nv["sub"]
        if sub:
            cands = by_src.get((b, ch, v, sub), [])
        else:
            has_subs = inv.subs.get((b, ch, v), 0) > 0
            cands = (by_src.get((b, ch, v, 0), []) if has_subs else []) + by_src.get((b, ch, v, None), [])
        if not cands:
            mapping.append(None)
            stats["identity"] += 1
            continue
        hit = next((ln for ln in cands if passes(ln)), None)
        if hit is None:
            mapping.append(None)
            stats["identity (no passing line)"] += 1
            continue
        mapping.append({"std": hit.std, "action": hit.action, "line": hit.lineno, "stype": hit.stype})
        stats["tvtms:" + hit.action.rstrip("*").strip()] += 1
    return mapping, dict(stats)


def kjva_chapter_counts(path=TVTMS_PATH):
    """Verses per chapter in KJV(A) from the table at the end of TVTMS."""
    text = path.read_text(encoding="utf-8-sig").split("\n")
    i = next(i for i, l in enumerate(text) if l.startswith("SIL abbrev (used in this data)"))
    out = {}
    for l in text[i + 1:]:
        f = l.split("\t")
        if len(f) < 3 or not f[0].strip() or f[0].startswith("'"):
            continue
        sil = f[0].strip()
        counts = {}
        for m in re.finditer(r"(\d+):(\d+)", f[2]):
            counts[int(m.group(1))] = int(m.group(2))
        if counts:
            out[sil] = counts
    return out
