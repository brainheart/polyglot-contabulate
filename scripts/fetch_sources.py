#!/usr/bin/env python3
"""Download the pinned raw sources listed in sources/manifest.json and verify
their SHA-256. Committed files are only re-fetched with --force; TVTMS is not
committed (STEPBible asks users not to redistribute the raw file), so a fresh
clone must run this once before building.

    python3 scripts/fetch_sources.py [--force]
    python3 scripts/fetch_sources.py --verify   # hashes only, incl. sibling corpora
"""
import hashlib
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    man = json.loads((ROOT / "sources" / "manifest.json").read_text())
    force = "--force" in sys.argv
    verify = "--verify" in sys.argv
    bad = 0
    for f in man["downloaded"]:
        p = ROOT / f["path"]
        if not verify and (force or not p.exists()):
            p.parent.mkdir(parents=True, exist_ok=True)
            print("fetch", f["path"])
            with urllib.request.urlopen(f["url"]) as r:
                p.write_bytes(r.read())
        if not p.exists():
            print("MISSING", f["path"]); bad += 1
        elif sha(p) != f["sha256"]:
            print("HASH MISMATCH", f["path"]); bad += 1
    for col, s in man["sibling_corpora"].items():
        p = ROOT.parent / s["repo"] / s["file"]
        state = "ok" if p.exists() and sha(p) == s["sha256"] else "CHANGED (rebuild will differ)"
        head = subprocess.run(["git", "-C", str(p.parents[2]), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        print(f"{s['repo']}: {state}; pinned {s['commit'][:10]}, now {head[:10]}")
    print("all downloaded sources verified" if not bad else f"{bad} problem(s)")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
