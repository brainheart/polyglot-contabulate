# polyglot-contabulate — agent notes

* Independent repo; never edit the sibling `*-contabulate` repos from here (they are read-only inputs).
* Generated output (`docs/data`, `docs/instance.json`, `corpora/`) comes only from `python3 scripts/build.py`; fix the generator, not the JSON.
* Versification changes go through TVTMS evaluation (`scripts/polyglot/tvtms.py`); data errors in TVTMS go in `sources/tvtms_corrections.json` with a reason; Swete transcription defects go in `sources/swete_fixes.json`. No silent offsets.
* Keep `scripts/polyglot/textnorm.py` and `docs/js/textnorm.js` in lockstep; the Playwright tokenizer test compares them.
* Before handing off: build → qa_alignment → unittest → playwright → screenshots. Do not publish, push, or touch DNS without Reinhard's approval.
