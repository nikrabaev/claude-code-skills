#!/usr/bin/env python3
"""Advisory drift detector: surface documentation that has drifted from code.

This script REUSES two existing validators that live in the same ``scripts/``
directory:

* ``path_exists`` -- backticked path-like tokens must resolve to a real file/dir.
* ``symbol_exists`` -- explicit ``` `symbol` in `file` ``` refs must exist in a
  symbol index.

On top of those it adds a *stale-vs-code* heuristic: if a source file a doc
references was modified (per git commit time, falling back to filesystem mtime)
more recently than the doc itself, the doc may be out of date.

Unlike the validators it reuses, this script is ADVISORY: it defaults to exit 0
even when it has findings. Pass ``--strict`` to make findings exit non-zero.

Exit codes:
    0  no findings, OR findings without --strict (advisory default)
    1  findings AND --strict
    2  usage error (e.g. --root is not a directory)
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
import sys

import path_exists
import symbol_exists

# Directories that are never scanned for *.md files.
IGNORED_DIRS = frozenset([".git", "node_modules", ".hg", ".svn", "__pycache__"])


def _mtime(root, relpath):
    """Return a modification timestamp for ``relpath`` (relative to ``root``).

    Prefer the last git commit time (``git -C root log -1 --format=%ct``) so that
    checkouts -- which reset filesystem mtimes -- still reflect real change
    history. On ANY failure (git missing, not a repo, file untracked so output is
    empty, or non-zero exit) fall back to ``os.path.getmtime``. Never raises.
    """
    try:
        proc = subprocess.run(
            ["git", "-C", root, "log", "-1", "--format=%ct", "--", relpath],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if proc.returncode == 0:
            out = proc.stdout.decode("utf-8", "replace").strip()
            if out:
                return float(int(out))
    except (OSError, ValueError):
        pass
    return os.path.getmtime(os.path.join(root, relpath))


def _read_text(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def find_drift(root, doc_paths, index):
    """Return drift findings across ``doc_paths``.

    ``doc_paths`` is a list of absolute doc file paths. ``index`` is either a
    symbol index (list) or ``None``; when ``None`` the dead-symbol check is
    skipped entirely.

    Each finding is a dict ``{"doc", "line", "kind", "detail"}`` where ``kind``
    is one of ``dead-path``, ``dead-symbol``, or ``stale-vs-code``.
    """
    findings = []
    for doc in doc_paths:
        try:
            text = _read_text(doc)
        except (IOError, OSError):
            continue
        rel = os.path.relpath(doc, root)

        # 1. dead-path: backticked path tokens that do not resolve.
        for item in path_exists.check_doc(text, root):
            findings.append({
                "doc": rel,
                "line": item["line"],
                "kind": "dead-path",
                "detail": item["token"],
            })

        # 2. dead-symbol: explicit `symbol` in `file` refs absent from the index.
        if index is not None:
            refs = symbol_exists.extract_refs(text)
            for miss in symbol_exists.check(refs, index, root):
                findings.append({
                    "doc": rel,
                    "line": miss["line"],
                    "kind": "dead-symbol",
                    "detail": "{symbol} in {file} ({reason})".format(
                        symbol=miss["symbol"],
                        file=miss["file"],
                        reason=miss["reason"],
                    ),
                })

        # 3. stale-vs-code: existing source files this doc references that are
        #    newer than the doc itself.
        sources = set()
        for tok in path_exists.extract_path_tokens(text):
            norm = path_exists._normalize(tok)
            if norm and os.path.isfile(os.path.join(root, norm)):
                sources.add(norm)
        for ref in symbol_exists.extract_refs(text):
            ref_file = ref.get("file")
            if ref_file and os.path.isfile(os.path.join(root, ref_file)):
                sources.add(ref_file)

        doc_mtime = _mtime(root, rel)
        seen_stale = set()
        for src in sorted(sources):
            if (rel, src) in seen_stale:
                continue
            if _mtime(root, src) > doc_mtime:
                seen_stale.add((rel, src))
                findings.append({
                    "doc": rel,
                    "line": 0,
                    "kind": "stale-vs-code",
                    "detail": "{src} is newer than this doc".format(src=src),
                })

    return findings


def _default_md_files(root):
    """All ``*.md`` files under ``root``, skipping ignored directories."""
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
        for name in filenames:
            if name.endswith(".md"):
                found.append(os.path.join(dirpath, name))
    found.sort()
    return found


def _resolve_docs(path_args, root):
    """Expand explicit path/glob args into a sorted, de-duplicated file list.

    With no arguments, default to all ``*.md`` under ``root``. An explicit
    argument may be a file, a directory (expands to ``*.md`` under it), or a
    glob.
    """
    if not path_args:
        return _default_md_files(root)

    files = []
    for arg in path_args:
        candidate = arg if os.path.isabs(arg) else os.path.join(root, arg)
        if os.path.isdir(candidate):
            files.extend(_default_md_files(candidate))
        elif os.path.isfile(candidate):
            files.append(candidate)
        else:
            for m in glob.glob(candidate, recursive=True):
                if os.path.isfile(m):
                    files.append(m)
    seen = set()
    unique = []
    for f in files:
        if f not in seen:
            seen.add(f)
            unique.append(f)
    return unique


def _obtain_index(args, root):
    """Resolve the symbol index for the run, or ``None``.

    Advisory contract: NEVER hard-fail on index trouble. If ``--index`` is given
    but unloadable, or if auto-building via ``extract_symbols.sh`` fails or yields
    an empty index, return ``None`` (the dead-symbol check is then skipped).
    """
    if args.index:
        try:
            with open(args.index, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, list):
                return data
        except (OSError, ValueError):
            pass
        return None
    # No --index: try to build one, but tolerate any failure.
    try:
        data = symbol_exists._build_index_via_script(root)
    except (OSError, ValueError):
        return None
    if isinstance(data, list) and data:
        return data
    return None


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="drift_check.py",
        description="Advisory: surface docs that have drifted from code "
        "(dead paths/symbols, sources newer than the doc).",
    )
    parser.add_argument("--root", default=".", help="Project root directory (default: .).")
    parser.add_argument("--index", help="Path to the symbol index JSON array.")
    parser.add_argument("--json", action="store_true", help="Emit findings as JSON.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 when there are findings (default is advisory exit 0).",
    )
    parser.add_argument(
        "paths", nargs="*", help="Doc files, dirs, or globs (default: *.md under root)."
    )
    args = parser.parse_args(argv)

    root = args.root
    if not os.path.isdir(root):
        sys.stderr.write("error: --root is not a directory: %s\n" % root)
        return 2

    docs = _resolve_docs(args.paths, root)
    index = _obtain_index(args, root)
    findings = find_drift(root, docs, index)

    if args.json:
        sys.stdout.write(json.dumps(findings) + "\n")
    else:
        for f in findings:
            sys.stdout.write(
                "%s:%d: [%s] %s\n" % (f["doc"], f["line"], f["kind"], f["detail"])
            )

    if args.strict and findings:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
