#!/usr/bin/env python3
"""Validate explicit symbol references in documentation against a symbol index.

This validator checks ONLY explicit, stable references of the documented form:
a backticked symbol (optionally with ``()``) followed on the same line by
`` in `<file>` ``. For example::

    `processPayment()` in `src/billing/charge.ts`

Bare ``` `helper()` ``` references with no `` in `file` `` clause are ignored on
purpose -- they are too noisy and would produce false positives.

The symbol index is a JSON array of objects of the shape::

    [{"symbol": "<name>", "kind": "<function|class|...>", "file": "<relpath>"}, ...]

Stdlib only; targets Python 3.9.6.

Exit codes:
    0  all referenced symbols exist
    1  one or more referenced symbols are missing / mismatched
    2  usage/internal error, or the index is unavailable (skip, not a hard fail)
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import sys


# A backticked symbol (with optional trailing ``()``) immediately followed by
# `` in `<file>` `` on the same line. The symbol must start with a letter or
# underscore and may contain word chars or dots (e.g. ``obj.method``).
_REF_RE = re.compile(
    r"`([A-Za-z_][\w.]*)\(\)?`\s+in\s+`([^`]+)`"
    r"|"
    r"`([A-Za-z_][\w.]*)`\s+in\s+`([^`]+)`"
)


def extract_refs(text):
    """Return explicit references found in ``text``.

    Each reference is a dict ``{"symbol", "file", "line"}``. The symbol has any
    trailing ``()`` stripped. Both ``` `name()` ``` and ``` `name` ``` forms are
    accepted before the `` in `file` `` clause. References without the
    `` in `file` `` clause are ignored.
    """
    refs = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for m in _REF_RE.finditer(line):
            if m.group(1) is not None:
                symbol, fname = m.group(1), m.group(2)
            else:
                symbol, fname = m.group(3), m.group(4)
            refs.append({
                "symbol": symbol,
                "file": fname.strip(),
                "line": lineno,
            })
    return refs


def _file_matches(index_file, ref_file):
    """True if an index entry's file resolves the referenced file."""
    if index_file == ref_file:
        return True
    if index_file.endswith("/" + ref_file):
        return True
    if os.path.basename(index_file) == os.path.basename(ref_file):
        return True
    return False


def check(refs, index, root):
    """Return the subset of ``refs`` that do not resolve against ``index``.

    A reference resolves when the index contains an entry whose ``symbol`` equals
    the referenced name AND whose ``file`` matches the referenced file (exact,
    suffix after a ``/``, or same basename). Misses are annotated with a
    ``reason``: "symbol not in index" if no index entry has that symbol name, or
    "symbol exists but file mismatch" if the name exists but no file matched.
    """
    by_symbol = {}
    for entry in index:
        if not isinstance(entry, dict):
            continue
        name = entry.get("symbol")
        fpath = entry.get("file")
        if not isinstance(name, str) or not isinstance(fpath, str):
            continue
        by_symbol.setdefault(name, []).append(fpath)

    misses = []
    for ref in refs:
        symbol = ref["symbol"]
        ref_file = ref["file"]
        candidates = by_symbol.get(symbol)
        if not candidates:
            miss = dict(ref)
            miss["reason"] = "symbol not in index"
            misses.append(miss)
            continue
        if any(_file_matches(c, ref_file) for c in candidates):
            continue
        miss = dict(ref)
        miss["reason"] = "symbol exists but file mismatch"
        misses.append(miss)
    return misses


def _load_index_from_file(path):
    """Load and validate the JSON-array index. Raises ValueError on bad shape."""
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise ValueError("index must be a JSON array")
    return data


def _build_index_via_script(root):
    """Try to build the index by running scripts/extract_symbols.sh.

    Returns the parsed JSON array, or raises on any failure (missing script,
    non-zero exit, or unparseable output).
    """
    here = os.path.dirname(os.path.abspath(__file__))
    script = os.path.join(here, "extract_symbols.sh")
    if not os.path.isfile(script):
        raise OSError("extract_symbols.sh not found at %s" % script)
    proc = subprocess.run(
        [script, "--root", root],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise OSError(
            "extract_symbols.sh exited %d: %s"
            % (proc.returncode, proc.stderr.decode("utf-8", "replace").strip())
        )
    data = json.loads(proc.stdout.decode("utf-8", "replace"))
    if not isinstance(data, list):
        raise ValueError("extract_symbols.sh did not emit a JSON array")
    return data


def _iter_doc_files(root, paths):
    """Yield absolute paths of docs to scan.

    With explicit ``paths`` (files or globs), expand those. Otherwise default to
    all ``*.md`` under ``root`` recursively.
    """
    seen = set()
    if paths:
        for p in paths:
            if not os.path.isabs(p):
                p = os.path.join(root, p)
            matches = glob.glob(p, recursive=True)
            targets = matches if matches else [p]
            for t in targets:
                if os.path.isfile(t):
                    rp = os.path.realpath(t)
                    if rp not in seen:
                        seen.add(rp)
                        yield t
    else:
        for path in sorted(glob.glob(os.path.join(root, "**", "*.md"), recursive=True)):
            if os.path.isfile(path):
                rp = os.path.realpath(path)
                if rp not in seen:
                    seen.add(rp)
                    yield path


def _read_text(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="symbol_exists.py",
        description="Validate explicit `symbol` in `file` references against a symbol index.",
    )
    parser.add_argument("--root", default=".", help="Project root directory (default: .).")
    parser.add_argument("--index", help="Path to the symbol index JSON array.")
    parser.add_argument("--json", action="store_true", help="Emit violations as JSON.")
    parser.add_argument("paths", nargs="*", help="Doc files or globs (default: *.md under root).")
    args = parser.parse_args(argv)

    root = args.root
    if not os.path.isdir(root):
        sys.stderr.write("error: --root is not a directory: %s\n" % root)
        return 2

    # Obtain the index, or skip (return 2) if it is unavailable.
    if args.index:
        try:
            index = _load_index_from_file(args.index)
        except (OSError, ValueError) as exc:
            sys.stderr.write("skip: could not load index %s: %s\n" % (args.index, exc))
            return 2
    else:
        try:
            index = _build_index_via_script(root)
        except (OSError, ValueError) as exc:
            sys.stderr.write(
                "skip: symbol index unavailable (no --index and could not build "
                "it via extract_symbols.sh): %s\n" % exc
            )
            return 2
        # An auto-built index that is empty means extraction found no symbols
        # (unsupported language, missing tool, or nothing to index). Validating
        # against it would flag every documented symbol as missing -- a
        # false-positive avalanche -- so skip instead. (An explicit --index is
        # trusted as given, even if empty.)
        if not index:
            sys.stderr.write(
                "skip: auto-built symbol index is empty (extract_symbols.sh found "
                "no symbols under %s); pass --index to validate explicitly.\n" % root
            )
            return 2

    # Collect references across all doc files.
    all_refs = []
    for doc in _iter_doc_files(root, args.paths):
        try:
            text = _read_text(doc)
        except OSError as exc:
            sys.stderr.write("warning: could not read %s: %s\n" % (doc, exc))
            continue
        rel = os.path.relpath(doc, root)
        for ref in extract_refs(text):
            ref = dict(ref)
            ref["doc"] = rel
            all_refs.append(ref)

    misses = check(all_refs, index, root)

    if args.json:
        sys.stdout.write(json.dumps(misses, indent=2) + "\n")
    else:
        for m in misses:
            sys.stdout.write(
                "%s:%d: %s in %s (%s)\n"
                % (m.get("doc", "?"), m["line"], m["symbol"], m["file"], m["reason"])
            )

    return 1 if misses else 0


if __name__ == "__main__":
    sys.exit(main())
