"""Build-output checks for Polyglot Contabulate.

Run after `python3 scripts/build.py`:
    python3 -m unittest discover -s tests -v

Pins corpus facts that catch parser or versification drift (alignment
coverage, spot checks at the classic divergence points, Renderings sanity),
and writes build/token_fixture.json for the browser tokenizer-agreement test.
"""
import hashlib
import json
import math
import random
import re
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "data"
sys.path.insert(0, str(ROOT / "scripts"))
from polyglot.textnorm import tokens, key, fold  # noqa: E402

COLS = ["he", "grc", "la", "de", "en"]


def expand(vs):
    out = []
    for part in vs.split(","):
        if "-" in part:
            a, z = part.split("-")
            out += [str(i) for i in range(int(a), int(z) + 1)]
        else:
            out.append(part)
    return out


def _spine(meta):
    spine, rows_of = [], {}
    for b in meta["books"]:
        ids = [f"{b['id']}.{ch}.{v}" for ch, vs in b["chapters"] for v in expand(vs)]
        rows_of[b["id"]] = ids
        spine += ids
    return spine, rows_of


class Data:
    meta = json.loads((DATA / "meta.json").read_text(encoding="utf-8"))
    spine, rows_of = _spine(meta)
    _text = {}

    @classmethod
    def cell(cls, cid, col):
        book = cid.split(".")[0]
        k = (col, book)
        if k not in cls._text:
            p = DATA / "text" / col / f"{book}.json"
            cls._text[k] = json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
        arr = cls._text[k]
        if arr is None:
            return None
        return arr[cls.rows_of[book].index(cid)]

    @staticmethod
    def text(cell):
        return None if cell is None else (cell if isinstance(cell, str) else cell[0])

    @staticmethod
    def native(cell):
        return None if cell is None or isinstance(cell, str) else cell[1]

    _tok = {}

    @classmethod
    def tokens(cls, k):
        if k not in cls._tok:
            d = json.loads((DATA / "tokens" / f"{k}.json").read_text(encoding="utf-8"))
            d["rows_i"] = [None if r is None else ([int(x, 36) for x in r.split()] if r else []) for r in d["rows"]]
            cls._tok[k] = d
        return cls._tok[k]


def renderings(src_key, match, tgt_key, scope=None, top=10, stop=True):
    """Python mirror of the browser's Renderings computation."""
    src, tgt = Data.tokens(src_key), Data.tokens(tgt_key)
    ids = {i for i, w in enumerate(src["vocab"]) if match(w)}
    stopset = set(Data.meta["stopwords"].get(tgt_key, [])) if stop else set()
    books = [cid.split(".")[0] for cid in Data.spine]
    sec = {b["id"]: b["section"] for b in Data.meta["books"]}
    N = R = 0
    df, a = Counter(), Counter()
    for g, (sr, tr) in enumerate(zip(src["rows_i"], tgt["rows_i"])):
        if sr is None or tr is None or (scope and sec[books[g]] != scope):
            continue
        N += 1
        hit = any(x in ids for x in sr)
        R += hit
        for t in tr:
            df[t] += 1
            if hit:
                a[t] += 1

    def g2(a_, b_, c_, d_):
        n = a_ + b_ + c_ + d_
        obs = [a_, b_, c_, d_]
        exp = [(a_ + b_) * (a_ + c_) / n, (a_ + b_) * (b_ + d_) / n, (c_ + d_) * (a_ + c_) / n, (c_ + d_) * (b_ + d_) / n]
        return 2 * sum(o * math.log(o / e) for o, e in zip(obs, exp) if o > 0)

    res = []
    for t, at in a.items():
        w = tgt["vocab"][t]
        if at < 2 or w in stopset or at <= R * df[t] / N:
            continue
        res.append((g2(at, R - at, df[t] - at, N - R - df[t] + at), w))
    res.sort(reverse=True)
    return [w for _, w in res[:top]]


class TestSpineAndCoverage(unittest.TestCase):
    def test_spine_ids_unique_and_parseable(self):
        self.assertEqual(len(Data.spine), len(set(Data.spine)))
        self.assertEqual(len(Data.spine), Data.meta["spine_rows"])
        for cid in Data.spine:
            b, ch, v = cid.split(".")
            self.assertTrue(ch.isdigit(), cid)
            self.assertRegex(v, r"^\d+[a-z]*$", cid)

    def test_every_kjv_verse_is_a_row(self):
        kjv = json.loads((ROOT.parent / "kjv-contabulate" / "docs" / "lines" / "all_lines.json").read_text(encoding="utf-8"))
        spine = set(Data.spine)
        missing = [r["canonical_id"] for r in kjv if r["canonical_id"] not in spine]
        self.assertEqual(missing, [])
        self.assertEqual(Data.meta["coverage"]["en"]["rows"], 31102)

    def test_coverage_floors(self):
        cov = {c: Data.meta["coverage"][c]["rows"] for c in COLS}
        self.assertGreaterEqual(cov["he"], 23100)   # WLC 23,213 native verses (some merged)
        self.assertGreaterEqual(cov["de"], 31100)
        self.assertGreaterEqual(cov["la"], 35300)   # Vulgate incl. deuterocanon
        self.assertGreaterEqual(cov["grc"], 36300)  # Swete OT+DC + SBLGNT
        # no Apocrypha in Hebrew, Luther or KJV sources
        for c in ("he", "de", "en"):
            self.assertEqual(Data.meta["coverage"][c]["by_section"].get("DC", 0), 0)
        self.assertGreater(Data.meta["coverage"]["grc"]["by_section"]["DC"], 5000)
        self.assertGreater(Data.meta["coverage"]["la"]["by_section"]["DC"], 4000)

    def test_every_native_verse_is_placed(self):
        rep = json.loads((ROOT / "build" / "alignment_report.json").read_text(encoding="utf-8"))
        for name, t in rep["texts"].items():
            self.assertEqual(sum(t["placement"].values()), t["native_verses"], name)

    def test_alignment_qa_flag_rates(self):
        qa_path = ROOT / "build" / "alignment_qa.json"
        if not qa_path.exists():
            self.skipTest("run scripts/qa_alignment.py first")
        qa = json.loads(qa_path.read_text(encoding="utf-8"))
        for pair, r in qa.items():
            self.assertLess(r["flag_rate_pct"], 2.0, pair)


class TestBrentonGapFiller(unittest.TestCase):
    """Ecclesiastes and four lost verse-1 texts come from Brenton, flagged."""

    def test_ecclesiastes_greek_aligned_to_kjv(self):
        eccl = next(b for b in Data.meta["books"] if b["id"] == "Eccl")
        self.assertEqual(eccl["present"]["grc"], 222)
        self.assertEqual(len(eccl["chapters"]), 12)
        self.assertIn("Ματαιότης ματαιοτήτων", Data.text(Data.cell("Eccl.1.2", "grc")))
        self.assertIn("Vanity of vanities", Data.text(Data.cell("Eccl.1.2", "en")))
        # Brenton breaks chapter 4/5 like the Hebrew; TVTMS maps it to KJV
        self.assertIn("Φύλαξον τὸν πόδα σου", Data.text(Data.cell("Eccl.5.1", "grc")))
        self.assertEqual(Data.native(Data.cell("Eccl.5.1", "grc")), "4:17")
        self.assertEqual(Data.native(Data.cell("Eccl.5.20", "grc")), "5:19")
        self.assertIn("Ὅτι σύμπαν τὸ ποίημα", Data.text(Data.cell("Eccl.12.14", "grc")))

    def test_brenton_cells_are_flagged_and_numerals_gone(self):
        src = Data.meta["text_sources"]
        self.assertEqual(set(src), {"grc"})
        self.assertEqual(set(src["grc"].values()), {"Brenton 1851"})
        eccl = [c for c in src["grc"] if c.startswith("Eccl.")]
        self.assertEqual(len(eccl), 222)
        self.assertEqual(set(src["grc"]) - set(eccl), {"Exod.20.1", "Num.17.1", "Num.19.1", "1Kgs.16.1"})
        self.assertIn("Καὶ ἐλάλησε Κύριος πάντας τοὺς λόγους", Data.text(Data.cell("Exod.20.1", "grc")))
        self.assertIn("Καὶ ἐλάλησε Κύριος πρὸς Μωυσῆν, λέγων", Data.text(Data.cell("Num.17.1", "grc")))
        self.assertIn("πρὸς Μωυσῆν καὶ Ἀαρὼν", Data.text(Data.cell("Num.19.1", "grc")))
        self.assertIn("ἐν χειρὶ Ἰοὺ", Data.text(Data.cell("1Kgs.16.1", "grc")))
        self.assertIsNone(Data.cell("1Kgs.14.1", "grc"))  # absent from Codex B: a real gap
        for cid in ("Exod.20.2", "Num.17.2", "1Kgs.14.21", "Ps.23.1"):
            self.assertNotIn(cid, src["grc"])
        numerals = [cid for cid in Data.spine if re.fullmatch(r"[IVXLC]+", Data.text(Data.cell(cid, "grc")) or "")]
        self.assertEqual(numerals, [])

    def test_standalone_lxx_and_manifest(self):
        lxx = json.loads((ROOT / "corpora" / "lxx" / "all_lines.json").read_text(encoding="utf-8"))
        flagged = [r for r in lxx if r.get("text_source")]
        self.assertEqual(len(flagged), 226)
        self.assertEqual({r["canonical_id"] for r in flagged if not r["canonical_id"].startswith("Eccl.")},
                         {"Exod.20.1", "Num.17.1", "Num.19.1", "1Kgs.16.1"})
        man = json.loads((ROOT / "sources" / "manifest.json").read_text())
        brenton = [f for f in man["downloaded"] if f["path"].startswith("sources/raw/brenton/")]
        self.assertEqual(len(brenton), 5)
        for f in brenton:
            self.assertEqual(f["zip_sha256"], "964b96f1de0d47aabde9e2178a6776ea7851bcab2d6c8c115a94807f61293429")
            self.assertEqual(hashlib.sha256((ROOT / f["path"]).read_bytes()).hexdigest(), f["sha256"])
        self.assertIn("Public Domain", (ROOT / "sources/raw/brenton/copr.htm").read_text())


class TestSpotChecks(unittest.TestCase):
    def assertCell(self, cid, col, contains=None, native=None, empty=False):
        cell = Data.cell(cid, col)
        if empty:
            self.assertIsNone(cell, f"{cid} {col} should be a gap")
            return
        self.assertIsNotNone(cell, f"{cid} {col} missing")
        if contains:
            self.assertIn(contains, Data.text(cell), f"{cid} {col}")
        if native is not None:
            self.assertEqual(Data.native(cell), native, f"{cid} {col} native ref")

    def test_gen_1_1(self):
        self.assertCell("Gen.1.1", "he", "בְּרֵאשִׁ֖ית", native=None)
        self.assertCell("Gen.1.1", "grc", "ἐποίησεν ὁ θεὸς τὸν οὐρανὸν")
        self.assertCell("Gen.1.1", "la", "In principio creavit Deus cælum et terram")
        self.assertCell("Gen.1.1", "de", "Am Anfang schuf Gott Himmel und Erde")
        self.assertCell("Gen.1.1", "en", "In the beginning God created the heaven and the earth")

    def test_psalm_23_is_22_in_vulgate_and_lxx(self):
        self.assertCell("Ps.23.1", "la", "Dominus regit me", native="22:1")
        self.assertCell("Ps.23.1", "grc", "Ψαλμὸς τῷ Δαυείδ. Κύριος ποιμαίνει με", native="22:title–1")
        self.assertCell("Ps.23.1", "he", "רֹ֝עִ֗י")
        self.assertCell("Ps.23.1", "de", "Der HERR ist mein Hirte")
        self.assertCell("Ps.23.1", "en", "The LORD is my shepherd")
        self.assertNotIn("Ps.23.0", Data.rows_of["Ps"])  # no title-only Greek row
        self.assertCell("Ps.51.0", "grc", "Εἰς τὸ τέλος")  # Hebrew title row keeps the Greek title

    def test_john_1_1(self):
        self.assertCell("John.1.1", "grc", "Ἐν ἀρχῇ ἦν ὁ λόγος")
        self.assertCell("John.1.1", "la", "In principio erat Verbum")
        self.assertCell("John.1.1", "de", "Im Anfang war das Wort")
        self.assertCell("John.1.1", "en", "In the beginning was the Word")
        self.assertCell("John.1.1", "he", empty=True)

    def test_hebrew_vs_english_splits(self):
        self.assertCell("Mal.4.1", "he", native="3:19")
        self.assertCell("Mal.4.1", "de", native="3:19")
        self.assertCell("Mal.4.6", "he", native="3:24")
        self.assertCell("Joel.2.28", "he", native="3:1")
        self.assertCell("Joel.3.1", "he", native="4:1")
        self.assertCell("1Chr.6.1", "he", native="5:27")
        self.assertCell("Gen.32.1", "he", native="32:2")
        self.assertCell("Isa.9.1", "he", native="8:23")
        self.assertCell("Dan.4.1", "he", native="3:31")

    def test_psalm_titles_and_numbering(self):
        self.assertCell("Ps.51.0", "he", "לַמְנַצֵּ֗חַ", native="51:1–2")
        self.assertCell("Ps.51.1", "he", native="51:3")
        self.assertCell("Ps.51.1", "la", "Miserere mei, Deus", native="50:3")
        self.assertCell("Ps.3.0", "la", "Psalmus David", native="3:1")
        self.assertCell("Ps.116.10", "la", "Credidi", native="115:1")
        self.assertCell("Ps.147.12", "grc", native="147:1")
        self.assertCell("Ps.92.1", "grc", "Ἀγαθὸν", native="91:2")   # needed the Ps 91 last-verse fix

    def test_lxx_jeremiah_kingdoms_esdras(self):
        self.assertCell("Jer.25.15", "grc", native="32:1")
        self.assertCell("1Kgs.1.1", "grc", native="3 Kgdms 1:1")
        self.assertCell("1Kgs.1.1", "la", native="3 Reg 1:1")
        self.assertCell("1Kgs.2.35a", "grc", native="3 Kgdms 2:35a")
        self.assertCell("Neh.1.1", "grc", native="2 Esdr 11:1")
        self.assertCell("Exod.20.13", "grc", "φονεύσεις", native="20:15")

    def test_daniel_and_esther_additions(self):
        self.assertCell("PrAzar.1.1", "la", native="3:24")
        self.assertCell("PrAzar.1.1", "grc", native="Dan θ 3:24")
        self.assertCell("Dan.3.24", "la", native="3:91")
        self.assertCell("Sus.1.1", "la", native="13:1")
        self.assertCell("Bel.1.2", "la", native="14:1")
        self.assertCell("Esth.11.2", "la", "Anno secundo")
        self.assertCell("Esth.11.2", "grc", "Ἀρταξέρξου")
        self.assertCell("Esth.13.1", "he", empty=True)
        self.assertCell("Esth.13.1", "en", empty=True)
        self.assertCell("Bar.6.1", "la", "Propter peccata")
        self.assertCell("Bar.6.1", "grc", "Διὰ τὰς ἁμαρτίας")

    def test_nt_versification(self):
        self.assertCell("3John.1.14", "grc", native="1:14–15")
        self.assertCell("Rev.13.1", "grc", native="12:18; 13:1")
        self.assertCell("2Cor.13.14", "grc", native="13:13")
        self.assertTrue(isinstance(Data.cell("2Cor.13.13", "grc"), list) and Data.cell("2Cor.13.13", "grc")[2] == "cont")


class TestRenderings(unittest.TestCase):
    def test_chesed(self):
        m = lambda w: "חסד" in w  # noqa: E731
        en = renderings("he", m, "en")
        de = renderings("he", m, "de")
        self.assertEqual(en[0], "mercy")
        self.assertTrue({"kindness", "lovingkindness"} & set(en[:5]), en)
        self.assertTrue({"güte", "barmherzigkeit", "gnade"} <= set(de[:6]), de)

    def test_logos_wort(self):
        forms = {fold(f) for f in ["λόγος", "λόγου", "λόγῳ", "λόγον", "λόγοι", "λόγων", "λόγοις", "λόγους"]}
        de = renderings("grc", lambda w: w in forms, "de", scope="NT")
        self.assertEqual(de[0], "wort")

    def test_gehenna_hades_hell(self):
        forms = {fold(f) for f in ["γέεννα", "γέενναν", "γεέννης", "γεέννῃ", "ᾅδης", "ᾅδου", "ᾅδῃ", "ᾅδην"]}
        en = renderings("grc", lambda w: w in forms, "en", scope="NT")
        self.assertEqual(en[0], "hell")
        for f, label in ((["γέεννα", "γέενναν", "γεέννης", "γεέννῃ"], "gehenna"), (["ᾅδης", "ᾅδου", "ᾅδῃ", "ᾅδην"], "hades")):
            fs = {fold(x) for x in f}
            self.assertIn("hell", renderings("grc", lambda w: w in fs, "en", scope="NT")[:2], label)

    def test_sheol_saul_homograph(self):
        en = renderings("he", lambda w: "שאול" in w, "en", top=12)
        self.assertEqual(en[0], "saul")
        self.assertIn("hell", en)
        sheol = renderings("hep", lambda w: key("he_pointed", "שְׁאוֹל") in w, "en", top=6)
        self.assertTrue({"hell", "grave"} <= set(sheol[:3]), sheol)
        self.assertNotIn("saul", sheol)
        saul = renderings("hep", lambda w: key("he_pointed", "שָׁאוּל") in w, "en", top=3)
        self.assertEqual(saul[0], "saul")


class TestTokenizer(unittest.TestCase):
    def test_unicode_rules(self):
        self.assertEqual(fold("Λόγος"), "λογοσ")
        self.assertEqual(fold("ᾅδης"), "αδησ")
        self.assertEqual(fold("cælum"), "caelum")
        self.assertEqual(fold("ejus"), "eius")
        self.assertEqual(key("he", "וְחֶ֫סֶד"), "וחסד")
        self.assertEqual(key("he_pointed", "וְחֶ֫סֶד"), key("he_pointed", "וְחֶסֶד"))
        self.assertEqual(key("de", "Güte"), "güte")
        self.assertEqual(tokens("ἀλλʼ ἐγώ, κύριε·"), ["ἀλλ", "ἐγώ", "κύριε"])
        self.assertEqual(tokens("עַל־פְּנֵי"), ["עַל", "פְּנֵי"])

    def test_write_browser_fixture(self):
        """Sample verse texts with Python tokens/keys for the Playwright
        tokenizer-agreement test."""
        rnd = random.Random(7)
        cases = []
        for col in COLS:
            books = [b["id"] for b in Data.meta["books"] if b["present"][col]]
            for b in rnd.sample(books, min(8, len(books))):
                arr = json.loads((DATA / "text" / col / f"{b}.json").read_text(encoding="utf-8"))
                texts = [Data.text(c) for c in arr if c is not None and Data.text(c)]
                for t in rnd.sample(texts, min(6, len(texts))):
                    toks = tokens(t)
                    keys = [key(col, x) for x in toks]
                    case = {"col": col, "text": t, "tokens": toks, "keys": keys}
                    if col == "he":
                        case["pointed"] = [key("he_pointed", x) for x in toks]
                    cases.append(case)
        (ROOT / "build").mkdir(exist_ok=True)
        (ROOT / "build" / "token_fixture.json").write_text(json.dumps(cases, ensure_ascii=False), encoding="utf-8")
        self.assertGreater(len(cases), 150)


if __name__ == "__main__":
    unittest.main()
