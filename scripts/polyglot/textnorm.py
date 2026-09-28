"""Unicode normalization and tokenization shared by the build.

The browser mirrors these rules in docs/js/textnorm.js; tests/test_data.py
checks that both agree on a sample of every column.

* Display text: NFC.
* Tokens: maximal runs of letters and combining marks (\\p{L}\\p{M}). Hebrew
  maqaf, Greek elision marks (U+1FBF, U+2019, U+02BC) and punctuation split.
* fold(): accent/nikud-insensitive key. NFD, drop all combining marks,
  lowercase, final sigma -> sigma, Latin ae/oe ligatures and j -> i.
* key(col, tok): the per-column key used by the Renderings statistics.
  Hebrew is consonantal (homographs merge: Saul/Sheol), Greek and Latin are
  folded, German and English are only lowercased so Güte stays distinct
  from gute.
* pointed(): Hebrew with vowel points kept but cantillation and meteg removed.
"""
import re
import unicodedata

def is_letter_or_mark(ch):
    cat = unicodedata.category(ch)
    return cat[0] == "L" or cat[0] == "M"


def tokens(text):
    """Return surface tokens: runs of \\p{L}\\p{M} characters (NFC input)."""
    out = []
    cur = []
    for ch in text:
        if is_letter_or_mark(ch) and ch != "ʼ":
            cur.append(ch)
        else:
            if cur:
                out.append("".join(cur))
                cur = []
    if cur:
        out.append("".join(cur))
    # a token made only of marks (e.g. stray cantillation) is not a word
    return [t for t in out if any(unicodedata.category(c)[0] == "L" for c in t)]


LATIN_LIG = str.maketrans({"æ": "ae", "Æ": "ae", "œ": "oe", "Œ": "oe"})


def fold(s):
    s = s.translate(LATIN_LIG)
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c)[0] != "M")
    s = s.lower().replace("ς", "σ").replace("j", "i")
    return unicodedata.normalize("NFC", s)


HEB_CANTILLATION = re.compile("[֑-ֽ֯]")


def pointed(s):
    """Hebrew with nikud but without cantillation/meteg; NFC."""
    s = unicodedata.normalize("NFD", s)
    s = HEB_CANTILLATION.sub("", s)
    return unicodedata.normalize("NFC", s)


def key(col, tok):
    if col in ("he", "grc", "la"):
        return fold(tok)
    if col == "he_pointed":
        return pointed(tok)
    return unicodedata.normalize("NFC", tok).lower()


def nfc(s):
    return unicodedata.normalize("NFC", s)
