"""Loaders that turn each source into a list of native verses.

A native verse is a dict:
    book   OSIS book code used for the spine (Gen, 1Kgs, Esth, ...)
    ch     native chapter (int)
    v      native verse (int, 0 = unnumbered title / heading before v1)
    sub    native subverse index (0 = the verse itself, 1 = 'a', 2 = 'b' ...)
    text   NFC display text
    nb/nch/nv  native reference parts as printed in that edition
           ("3 Kgdms", "2", "35a"); nb is "" when the book name matches
    fixed  optional canonical id when the loader already knows the standard
           position (used for Swete Esther, whose additions are lettered in a
           scheme TVTMS does not describe)
"""
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from .books import USFM_TO_OSIS, VULGATE_LABEL, LXX_LABEL, NAME
from .textnorm import nfc

ROOT = Path(__file__).resolve().parents[2]
PROJECTS = ROOT.parent
RAW = ROOT / "sources" / "raw"

EXISTING = {
    "en": PROJECTS / "kjv-contabulate" / "docs" / "lines" / "all_lines.json",
    "de": PROJECTS / "luther-contabulate" / "docs" / "lines" / "all_lines.json",
    "he": PROJECTS / "tanakh-contabulate" / "docs" / "lines" / "all_lines.json",
    "gnt": PROJECTS / "gnt-contabulate" / "docs" / "lines" / "all_lines.json",
}


def _label(book, ch, v, sub=0, names=None):
    bl = (names or {}).get(book) or NAME.get(book, book)
    vs = "title" if v == 0 else str(v)
    if sub:
        vs += chr(ord("a") + sub - 1)
    return f"{bl} {ch}:{vs}"


def load_existing(col):
    """KJV, Luther, Tanakh and SBLGNT from the sibling Contabulate repos.

    Their canonical_id is each text's own numbering (Luther and Tanakh follow
    Hebrew versification, SBLGNT follows NA/UBS), so it is treated as native.
    """
    data = json.loads(EXISTING[col].read_text(encoding="utf-8"))
    out = []
    for rec in data:
        book, ch, v = rec["canonical_id"].split(".")
        out.append({
            "book": book, "ch": int(ch), "v": int(v), "sub": 0,
            "text": nfc(rec["text"]).strip(),
            "nb": "", "nch": ch, "nv": v,
        })
    return out


def load_vulgate():
    """Clementine Vulgate (Tweedale / VulSearch text) from USFX."""
    src = (RAW / "vulgate" / "lat-clementine.usfx.xml").read_text(encoding="utf-8")
    out = []
    for m in re.finditer(r'<book id="(\w+)">(.*?)</book>', src, re.S):
        usfm, body = m.groups()
        book = USFM_TO_OSIS[usfm]
        body = re.sub(r"<h>.*?</h>", "", body)
        ch = 0
        for tok in re.finditer(r'<c id="(\d+)"/>|<v id="(\d+)"/>(.*?)<ve/>', body, re.S):
            if tok.group(1):
                ch = int(tok.group(1))
                continue
            v = int(tok.group(2))
            text = re.sub(r"<[^>]+>", "", tok.group(3))
            text = nfc(re.sub(r"\s+", " ", text)).strip()
            # VulSearch uses French-style spacing before : ; ? !
            text = re.sub(r"\s+([:;?!])", r"\1", text)
            out.append({"book": book, "ch": ch, "v": v, "sub": 0, "text": text,
                        "nb": VULGATE_LABEL.get(book, ""), "nch": str(ch), "nv": str(v)})
    return out


# ---------------------------------------------------------------- Swete LXX

# First1KGreek work number -> (OSIS book, role). role "main" goes into the
# parallel table; "alt" (Old Greek Daniel/Susanna/Bel, where the table uses
# Theodotion) is kept only in the standalone LXX corpus.
SWETE_WORKS = {
    "001": ("Gen", "main"), "002": ("Exod", "main"), "003": ("Lev", "main"),
    "004": ("Num", "main"), "005": ("Deut", "main"), "006": ("Josh", "main"),
    "008": ("Judg", "main"), "010": ("Ruth", "main"), "011": ("1Sam", "main"),
    "012": ("2Sam", "main"), "013": ("1Kgs", "main"), "014": ("2Kgs", "main"),
    "015": ("1Chr", "main"), "016": ("2Chr", "main"), "017": ("1Esd", "main"),
    "018": ("Ezra", "main"),  # Esdras B; chapters 11-23 become Nehemiah 1-13
    "019": ("Esth", "main"), "020": ("Jdt", "main"), "021": ("Tob", "main"),
    "023": ("1Macc", "main"), "024": ("2Macc", "main"), "025": ("3Macc", "main"),
    "026": ("4Macc", "main"), "027": ("Ps", "main"), "028": ("Odes", "main"),
    "029": ("Prov", "main"), "031": ("Song", "main"), "032": ("Job", "main"),
    "033": ("Wis", "main"), "034": ("Sir", "main"), "035": ("PssSol", "main"),
    "036": ("Hos", "main"), "037": ("Amos", "main"), "038": ("Mic", "main"),
    "039": ("Joel", "main"), "040": ("Obad", "main"), "041": ("Jonah", "main"),
    "042": ("Nah", "main"), "043": ("Hab", "main"), "044": ("Zeph", "main"),
    "045": ("Hag", "main"), "046": ("Zech", "main"), "047": ("Mal", "main"),
    "048": ("Isa", "main"), "049": ("Jer", "main"), "050": ("Bar", "main"),
    "051": ("Lam", "main"), "052": ("EpJer", "main"), "053": ("Ezek", "main"),
    "054": ("Sus", "alt"), "055": ("Sus", "main"), "056": ("Dan", "alt"),
    "057": ("Dan", "main"), "058": ("Bel", "alt"), "059": ("Bel", "main"),
}
SWETE_FILE = {"034": "tlg0527.tlg034.1st1K-grc2.xml"}  # grc1 there is Hart's edition

# OCR in the OGL transcription occasionally uses Latin capitals inside Greek
# words (e.g. "ΜΑΚAPΙΟΣ"); map them back when the word is otherwise Greek.
LATIN_TO_GREEK = str.maketrans("ABEHIKMNOPTXYZ", "ΑΒΕΗΙΚΜΝΟΡΤΧΥΖ")
GREEK_RE = re.compile(r"[Ͱ-Ͽἀ-῿]")
TEI = "{http://www.tei-c.org/ns/1.0}"


def _fix_mixed_script(text):
    def fix(m):
        w = m.group(0)
        if GREEK_RE.search(w) and re.search(r"[A-Z]", w):
            return w.translate(LATIN_TO_GREEK)
        return w
    return re.sub(r"[^\s,.;:·()\[\]]+", fix, text)


def _tei_text(el):
    """Text of an element, skipping notes (apparatus, marginalia) and heads."""
    parts = []

    def walk(e):
        tag = e.tag.replace(TEI, "")
        if tag in ("note", "head"):
            if e.tail:
                parts.append(e.tail)
            return
        if tag in ("l", "lb", "p", "lg"):
            parts.append(" ")
        if e.text:
            parts.append(e.text)
        for c in e:
            walk(c)
        if tag in ("l", "p", "lg"):
            parts.append(" ")
        if e.tail:
            parts.append(e.tail)

    walk(el)
    s = "".join(parts)
    s = s.replace("¶", " ").replace("§", " ")
    # stray superscript digits from the OCR (e.g. "⁷ἰός")
    s = re.sub(r"[¹²³⁰-⁹]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\s+([,.;:·])", r"\1", s)
    return nfc(_fix_mixed_script(s))


def _verse_key(n):
    """'35' -> (35, 0); '35a' -> (35, 1); '35I' -> (35, 9)."""
    m = re.fullmatch(r"(\d+)([A-Za-z]?)(\d*)", n)
    if not m:
        return None
    v = int(m.group(1))
    letter = m.group(2).lower()
    return v, (ord(letter) - ord("a") + 1) if letter else 0


def _swete_chapters(path):
    tree = ET.parse(path)
    edition = tree.getroot().find(f".//{TEI}div[@type='edition']")
    chapters = edition.findall(f"{TEI}div[@subtype='chapter']")
    if not chapters:  # Epistle of Jeremiah has verses directly under the edition
        chapters = [edition]
    for chdiv in chapters:
        cn = chdiv.get("n", "1") if chdiv is not edition else "1"
        verses = []
        pre = []
        for child in chdiv:
            tag = child.tag.replace(TEI, "")
            if tag == "div" and child.get("subtype") == "verse":
                verses.append((child.get("n"), _tei_text(child)))
            elif tag in ("lg", "p", "l") and not verses:
                pre.append(_tei_text(child))
        title = " ".join(x for x in pre if x).strip()
        yield cn, title, verses


def _esther_fixed(cn, n):
    """Swete prints the Greek additions to Esther with its own letters.
    Map them onto KJV-Apocrypha numbering (Esth 10:4-16:24)."""
    if cn == "prologue":  # Addition A = 11:2-12:6
        k = int(n)
        return f"Esth.11.{k + 1}" if k <= 11 else f"Esth.12.{k - 11}"
    m = re.fullmatch(r"(\d+)([ab])(\d*)", n)
    if not m:
        if cn == "10":  # Addition F follows 10:3 as 1-11 = 10:4-13, 11:1
            k = int(n)
            return f"Esth.10.{k + 3}" if k <= 10 else "Esth.11.1"
        return None
    k = int(m.group(1) + m.group(3)) if m.group(3) else int(m.group(1))
    if n == "1a1":
        k = 11  # OCR label for 11a
    letter = m.group(2)
    if cn == "3" and letter == "a":  # Addition B = 13:1-7
        return f"Esth.13.{k}"
    if cn == "4" and letter == "a":  # Addition C = 13:8-18, 14:1-19
        return f"Esth.13.{k + 7}" if k <= 11 else f"Esth.14.{k - 11}"
    if cn == "4" and letter == "b":  # Addition D = 15:1-16
        return f"Esth.15.{k}"
    if cn == "8" and letter == "a":  # Addition E = 16:1-24
        return f"Esth.16.{k}"
    if cn == "10" and letter == "a":  # 10:1-3 (the Hebrew ending)
        return f"Esth.10.{k}"
    return None


SKIP_SWETE = {"028"}  # Odes: Swete's order (A) duplicates canticles; see SOURCES.md

# ------------------------------------------------- Brenton (gap filler, not Swete)

# Brenton's Greek (1851, public domain; ebible.org grcbrent USFM) fills what the
# OGL transcription lacks. Every record taken from it has src = BRENTON, which
# the build carries into meta.json "text_sources" and the UI marks.
BRENTON = "Brenton 1851"
BRENTON_BOOKS = {"Eccl": "22-ECCgrcbrent.usfm"}  # First1KGreek tlg0527.tlg030 has no text
# Swete verse divisions that hold only a marginal chapter numeral (text lost in
# the transcription): Swete ref -> Brenton (file, chapter, verse). Neighbours
# were compared with Brenton's; tests re-check them. 1Kgs (3 Kgdms) 14:1 is not
# here: 14:1-20 is absent from Codex B, Swete and Brenton alike.
BRENTON_VERSES = {
    ("Exod", 20, 1): ("03-EXOgrcbrent.usfm", "20", "1"),
    # Brenton numbers Num 16:36-50 as 17:1-15, so Swete 17:1 is Brenton 17:16.
    ("Num", 17, 1): ("05-NUMgrcbrent.usfm", "17", "16"),
    ("Num", 19, 1): ("05-NUMgrcbrent.usfm", "19", "1"),
    ("1Kgs", 16, 1): ("12-1KIgrcbrent.usfm", "16", "1"),
}
USFM_NOTE_RE = re.compile(r"\\(f|fe|x|fig)\s.*?\\\1\*", re.S)  # footnotes, cross-refs
USFM_WORD_RE = re.compile(r"\\(\+?w)\s+([^|\\]*)(?:\|[^\\]*)?\\\1\*")  # \w word|lemma="…"\w*
USFM_SKIP_LINE_RE = re.compile(  # identification, titles, headings, remarks
    r"^\\(?:id|ide|h|toc\d*|toca\d*|mt\d*|mte\d*|ms\d*|mr|s\d*|sr|r|rem|sts|cl|cp)\b.*$", re.M)
USFM_MARKER_RE = re.compile(r"\\\+?[a-z]+\d*\*?")
NUMERAL_ONLY_RE = re.compile(r"[IVXLC]+")


def parse_usfm(path):
    """{(chapter, verse): text} of one USFM book, markup stripped and
    normalized like the Swete text (NFC, spacing, ’ for elision)."""
    usfm = USFM_NOTE_RE.sub(" ", path.read_text(encoding="utf-8"))
    usfm = USFM_SKIP_LINE_RE.sub("", USFM_WORD_RE.sub(r"\2", usfm))
    parts = re.split(r"\\([cv])\s+(\S+)", usfm)
    verses, chapter = {}, None
    for kind, number, body in zip(parts[1::3], parts[2::3], parts[3::3]):
        if kind == "c":
            chapter = number
            continue
        text = re.sub(r"\s+", " ", USFM_MARKER_RE.sub(" ", body).replace("\u02bc", "’")).strip()
        verses[(chapter, number)] = nfc(re.sub(r"\s+([,.;:·])", r"\1", text))
    return verses


def load_brenton_book(book):
    out = []
    for (ch, v), text in parse_usfm(RAW / "brenton" / BRENTON_BOOKS[book]).items():
        rec = {"book": book, "ch": int(ch), "v": int(v), "sub": 0, "text": text, "src": BRENTON}
        rec.update(_nat(book, "", int(ch), int(v)))
        out.append(rec)
    return out


def fill_from_brenton(out):
    """Swete verse divisions that hold only a marginal chapter numeral ("XX")
    take Brenton's text where BRENTON_VERSES has it; the rest are dropped
    (1Kgs 14:1, a real gap)."""
    kept = []
    for rec in out:
        if not NUMERAL_ONLY_RE.fullmatch(rec["text"]):
            kept.append(rec)
            continue
        ref = BRENTON_VERSES.get((rec["book"], rec["ch"], rec["v"]))
        if ref:
            rec.update(text=parse_usfm(RAW / "brenton" / ref[0])[(ref[1], ref[2])], src=BRENTON)
            kept.append(rec)
    filled = {(r["book"], r["ch"], r["v"]) for r in kept if r.get("src")}
    if set(BRENTON_VERSES) - filled:
        raise ValueError(f"no numeral-only Swete verse for {sorted(set(BRENTON_VERSES) - filled)}")
    out[:] = kept
    return out


def _nat(book, native_book_label, ch, v, sub=0, nch=None):
    vs = "title" if v == 0 else str(v)
    if sub:
        vs += chr(ord("a") + sub - 1)
    return {"nb": native_book_label or "", "nch": str(nch if nch is not None else ch), "nv": vs}


FIXES = json.loads((ROOT / "sources" / "swete_fixes.json").read_text(encoding="utf-8"))
REPAIRS = []  # (ref, old, new) applied by _repair_numbers, reported by the build


def _repair_numbers(verses, book, cn):
    """Fix OCR'd verse numbers that sit between two consecutive neighbours:
    [19, 220, 21] -> 220 is 20. Genuine LXX reorderings ([23, 27, 24]) are
    left alone because their neighbours are not two apart."""
    nums = []
    for n, text in verses:
        k = _verse_key(n)
        nums.append(k[0] if k and not k[1] else None)
    out = list(verses)
    for i, n in enumerate(nums):
        if n is None or i == 0 or i + 1 >= len(nums):
            continue
        prev, nxt = nums[i - 1], nums[i + 1]
        if prev is None or nxt is None:
            continue
        if nxt - prev == 2 and not (prev < n < nxt):
            REPAIRS.append((f"{book} {cn}:{n}", n, prev + 1))
            out[i] = (str(prev + 1), verses[i][1])
            nums[i] = prev + 1
    for i, (n, text) in enumerate(out):
        manual = FIXES["renumber"].get(f"{book} {cn}:{n}")
        if manual:
            REPAIRS.append((f"{book} {cn}:{n}", n, manual))
            out[i] = (str(manual), text)
    return out


def load_swete(role="main"):
    del REPAIRS[:]
    out = []
    for work, (book, wrole) in sorted(SWETE_WORKS.items()):
        if work in SKIP_SWETE or (wrole != role and role != "all"):
            continue
        fname = SWETE_FILE.get(work, f"tlg0527.tlg{work}.1st1K-grc1.xml")
        path = RAW / "swete" / fname
        names = dict(LXX_LABEL)
        if work in ("054", "056", "058"):
            names = {"Sus": "Sus OG", "Dan": "Dan OG", "Bel": "Bel OG"}
        for cn, title, verses in _swete_chapters(path):
            if cn in ("praef", "prologue"):
                ch = 0  # Sirach prologue; Esther Addition A
            elif cn.isdigit():
                ch = int(cn)
                fixed_ch = FIXES.get("chapter_renumber", {}).get(book, {}).get(cn)
                if fixed_ch:
                    REPAIRS.append((f"{book} chapter {cn}", cn, fixed_ch))
                    ch = fixed_ch
            else:
                raise ValueError(f"unexpected chapter {cn} in {fname}")
            obook, nch = book, ch
            if book == "Ezra" and ch >= 11:  # Esdras B 11-23 = Nehemiah 1-13
                obook, ch = "Neh", ch - 10
            nb = names.get(obook, "")
            if book == "EpJer":
                nb = "EpJer"
            if title:
                rec = {"book": obook, "ch": ch, "v": 0, "sub": 0, "text": _clean_swete(title)}
                rec.update(_nat(obook, nb, ch, 0, nch=nch))
                out.append(rec)
            prev = None
            verses = _repair_numbers(verses, book, cn)
            for n, text in verses:
                text = _clean_swete(text)
                if not text:
                    continue
                rec = {"book": obook, "ch": ch, "text": text}
                if book == "Esth" and work == "019":
                    fixed = _esther_fixed(cn, n)
                    key = _verse_key(n) or (0, 0)
                    rec.update({"v": key[0], "sub": key[1], "nb": "", "nch": "prol." if cn == "prologue" else cn, "nv": n})
                    if fixed:
                        rec["fixed"] = fixed
                    out.append(rec)
                    continue
                if n == "head" and book == "Isa":
                    # Swete prints the end of 31:9 as a heading of ch. 32
                    last = [r for r in out if r["book"] == "Isa" and r["ch"] == ch - 1][-1]
                    last["text"] += " " + text
                    continue
                key = _verse_key(n)
                if key is None:
                    raise ValueError(f"bad verse {n} in {fname} {cn}")
                v, sub = key
                if sub:
                    # number subverses by position (a=1, b=2, ...), which also
                    # absorbs OCR letter confusions such as 35I / 35i for 35l
                    sub = prev[1] + 1 if prev and prev[0] == v else 1
                prev = (v, sub)
                rec.update({"v": v, "sub": sub})
                rec.update(_nat(obook, nb, ch, v, sub, nch=nch))
                out.append(rec)
    if role in ("main", "all"):
        fill_from_brenton(out)
        out += load_brenton_book("Eccl")
    return out


def _clean_swete(text):
    text = re.sub(r"\d+", "", text)  # stray OCR digits; Greek numerals are letters
    return re.sub(r"\s+", " ", text).strip()
