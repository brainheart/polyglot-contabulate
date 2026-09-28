# Polyglot Contabulate

A parallel multilingual Bible explorer in the Contabulate family, named after
the Complutensian Polyglot (Alcalá, 1514–17). Five columns, verse by verse:

| Hebrew | Greek | Latin | German | English |
|---|---|---|---|---|
| Masoretic Text (WLC) | Swete's Septuagint · SBLGNT | Clementine Vulgate | Luther 1912 | King James Version |

**Status: local prototype.** Not published; no GitHub repo, DNS or hub entry yet
(see *Publishing checklist*).

## Views

* **Parallel text** — browse by book/chapter, or search any column (contains /
  whole word / regex; accent-, breathing-, nikud- and cantillation-insensitive by
  default, pointed matching on request), optionally AND-ed with a second
  condition in another column. Hits are highlighted in every column. Columns
  can be hidden and reordered (drag headers or ◀ ▶); every state is a URL.
  Each text's own reference is shown as a grey tag where it differs from the
  KJV spine; empty striped cells are deliberate gaps. CSV export of the full
  result.
* **Renderings** — pick a term in one column and see which words the other
  columns use in the same verse rows, ranked by log-likelihood (G²), with counts
  and example verses. Hebrew can be matched consonantally (conflating
  homographs such as Saul/Sheol — the view lists the vocalized forms behind the
  match) or pointed. Labelled as statistical, not scholarly.
* **Sources & versification** — editions, licenses, method and coverage.

## Build and test

```sh
python3 scripts/fetch_sources.py        # once: fetches TVTMS (not committed), verifies hashes
python3 scripts/build.py                # ~10 s → docs/data, docs/instance.json, corpora/, build/
python3 scripts/qa_alignment.py         # independent alignment check → build/alignment_qa.json
python3 -m unittest discover -s tests -v
npm install && npx playwright test      # starts its own server on :8791
node scripts/screenshots.js             # → screenshots/*.png
python3 -m http.server 8790 -d docs     # browse locally
```

The Hebrew, Luther, KJV and GNT texts are read from the sibling repositories
`../{tanakh,luther,kjv,gnt}-contabulate` (read-only; pinned in
`sources/manifest.json`). See `SOURCES.md` for provenance, licenses and the
versification method.

## Layout

```
scripts/build.py              orchestrates the build
scripts/polyglot/sources.py   loaders (existing corpora, Vulgate USFX, Swete TEI)
scripts/polyglot/tvtms.py     TVTMS parser and test evaluator
scripts/polyglot/textnorm.py  NFC / fold / pointed / tokenizer (mirrored in docs/js/textnorm.js)
sources/raw/                  pinned raw inputs (Vulgate, Swete); TVTMS fetched
sources/*.json                manifest, Swete repairs, TVTMS corrections
docs/                         static site (vanilla ES modules, no build step)
  data/meta.json              books, spine (compressed), coverage, stopwords
  data/text/<col>/<Book>.json per-column per-book cells, loaded lazily
  data/tokens/<col>.json      per-verse word-type ids for Renderings
corpora/{vulgate,lxx}/        all_lines.json for future standalone instances
tests/                        Python data checks + Playwright
```

## Publishing checklist (needs Reinhard's approval)

1. Create `brainheart/polyglot-contabulate`, push `main`, enable Pages from `/docs`.
2. Add `docs/CNAME` = `polyglot.contabulate.org`; Cloudflare CNAME → `brainheart.github.io`; verify HTTP/HTTPS and cert.
3. Licensing: code MIT; Swete-derived data CC BY-SA 4.0 (attribute OGL/First1KGreek); SBLGNT and TVTMS attribution (CC BY 4.0) — all present in the About view and SOURCES.md. Consider reporting the Malachi correction to STEPBible.
4. Add sample queries to the hub via `instance-meta.json` (already filled), rebuild, check `docs/instance.json`.
5. Hub: append `https://polyglot.contabulate.org/` to `contabulate/docs/instances.json` and a README row.
6. Post-deploy: run the Playwright suite against the live URL; check a few deep links.
