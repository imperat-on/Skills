#!/usr/bin/env python3
"""Find dead code, dead CSS classes and dead i18n keys using a repo-wide search.

Usage:
  python3 dead_scan.py ROOT --css src/index.css --i18n src/i18n [--json out.json]

Prints candidates only. Apply the false-positive gates in the parent SKILL.md
(lazy imports, siblings/variants, dynamically built class names, migration
flags) before deleting anything.
"""
import argparse
import json
import os
import re
import sys

TEXT_EXT = {
    ".ts", ".tsx", ".js", ".jsx", ".cjs", ".mjs", ".json", ".css",
    ".md", ".html", ".yml", ".yaml", ".sh", ".txt", ".toml", ".ini", ".patch",
}
MAX_BYTES = 4_000_000


def build_corpus(root, ignore):
    corpus = []
    for d, dirs, fs in os.walk(root):
        dirs[:] = [x for x in dirs if x not in ignore]
        for f in fs:
            if os.path.splitext(f)[1].lower() not in TEXT_EXT:
                continue
            p = os.path.join(d, f)
            try:
                if os.path.getsize(p) > MAX_BYTES:
                    continue
                corpus.append(
                    (os.path.relpath(p, root), open(p, encoding="utf-8", errors="replace").read())
                )
            except OSError:
                pass
    return corpus


def occ(corpus, term, skip=()):
    """Occurrences of `term` as a whole identifier (`_`, `-` and `.` belong to it)."""
    pat = re.compile(r"(?<![\w.-])" + re.escape(term) + r"(?![\w.-])")
    out = []
    for path, s in corpus:
        if path in skip:
            continue
        n = len(pat.findall(s))
        if n:
            out.append((path, n))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--css", required=True, help="stylesheet, relative to root")
    ap.add_argument("--i18n", required=True, help="dir with the locale catalogs")
    ap.add_argument("--ignore", nargs="*", default=["node_modules", ".git", "dist", "release"])
    ap.add_argument("--json", help="write the report here")
    a = ap.parse_args()

    root = os.path.abspath(a.root)
    corpus = build_corpus(root, set(a.ignore))
    css_rel = os.path.relpath(os.path.join(root, a.css), root)
    css = next((s for p, s in corpus if p == css_rel), "")
    if not css:
        sys.exit(f"css not found in corpus: {a.css}")
    print(f"text files in corpus: {len(corpus)}")

    # ---- 0) is the CSS flat enough to edit by line ranges? ----
    depth = mx = 0
    for ch in css:
        if ch == "{":
            depth += 1
            mx = max(mx, depth)
        elif ch == "}":
            depth -= 1
    print("\n=== CSS shape ===")
    print(f"  lines: {css.count(chr(10)) + 1}  max brace depth: {mx}")
    for tag in ("@apply", "@layer", "@utility", "@media", "@keyframes"):
        print(f"  {tag:<12} {css.count(tag)}")
    if mx > 2 or "@apply" in css or "@layer" in css:
        print("  WARNING: nested or layered CSS - do not use line-range surgery")

    # ---- 1) files with no reference anywhere ----
    print("\n=== files with no reference (verify lazy()/registry before deleting) ===")
    dead_files = []
    for path, s in corpus:
        if not path.endswith((".ts", ".tsx")) or path.endswith((".d.ts", ".d.cts")):
            continue
        stem = os.path.basename(path).rsplit(".", 1)[0]
        hits = [h for h in occ(corpus, stem) if h[0] != path]
        if not hits:
            dead_files.append(path)
            print(f"  {len(s.splitlines()):>5} lines  {path}")

    # ---- 2) classes never cited outside the stylesheet ----
    definidas = sorted(set(re.findall(r"\.([a-zA-Z][\w-]*)", css)))
    dead_classes = []
    for c in definidas:
        hits = [h for h in occ(corpus, c, skip={css_rel}) if not h[0].endswith(".css")]
        if not hits:
            dead_classes.append(c)
    print(f"\n=== classes ===\n  defined: {len(definidas)}  with no external use: {len(dead_classes)}")
    print("  ", dead_classes[:30])

    # ---- 3) the gate that matters: full name in code (must be 0) ----
    print("\n=== GATE: dead class whose FULL name appears in code (must be 0) ===")
    bad = 0
    for c in dead_classes:
        for path, s in corpus:
            if css_rel == path:
                continue
            if re.search(r"(?<![\w-])" + re.escape(c) + r"(?![\w-])", s):
                print(f"  {c} -> {path}")
                bad += 1
    print(f"  total: {bad}" + ("  <-- OK" if bad == 0 else "  <-- detector is wrong, stop"))

    # ---- 4) GATE: family stem in code = possible dynamic build, read by hand ----
    print("\n=== GATE: dead class whose FAMILY stem appears in code (read the context) ===")
    stems = {}
    for c in dead_classes:
        if "__" in c:
            st = c.split("__")[0]
            if len(st) >= 4:
                stems.setdefault(st, set()).add(c)
    for st, classes in sorted(stems.items()):
        onde = [p for p, s in corpus if css_rel != p and st in s]
        if onde:
            print(f"  {st}  ({len(classes)} dead classes) -> {onde[:4]}")

    # ---- 5) i18n keys (catalogs excluded!) ----
    i18n_dir = os.path.join(root, a.i18n)
    catalogs = sorted(
        os.path.relpath(os.path.join(i18n_dir, f), root)
        for f in os.listdir(i18n_dir)
        if f.endswith(".json")
    ) if os.path.isdir(i18n_dir) else []
    keys = {}
    if catalogs:
        data = json.load(open(os.path.join(root, catalogs[0]), encoding="utf-8"))
        dinamic = set()
        for path, s in corpus:
            if not path.endswith((".ts", ".tsx")):
                continue
            for m in re.finditer(r"\bt\(\s*`([^`$]*)\$\{", s):
                dinamic.add(m.group(1))
            for m in re.finditer(r'\bt\(\s*"([^"]*)"\s*\+', s):
                dinamic.add(m.group(1))
        dead_keys = [
            k for k in data
            if not any(k.startswith(d) for d in dinamic) and not occ(corpus, k, skip=set(catalogs))
        ]
        keys = {"catalogs": catalogs, "prefixes": sorted(dinamic), "dead": dead_keys}
        print("\n=== i18n ===")
        print(f"  catalogs: {catalogs}")
        print(f"  dynamic key prefixes: {sorted(dinamic) or '(none)'}")
        print(f"  defined: {len(data)}  with no reference: {len(dead_keys)}")
        print("  ", dead_keys[:25])

    if a.json:
        json.dump(
            {"dead_files": dead_files, "dead_classes": dead_classes, "i18n": keys},
            open(a.json, "w"), indent=1, ensure_ascii=False,
        )
        print(f"\nreport: {a.json}")


if __name__ == "__main__":
    main()
