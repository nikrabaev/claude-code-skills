#!/usr/bin/env python3
"""Extract pub/sub event usage (emit/publish/subscribe/consume) from source.

Scans common source files for event-bus / message-queue calls. The noisy
``.on(...)`` and ``.send(...)`` forms are intentionally EXCLUDED.
Stdlib only; targets Python 3.9.6.
"""
from __future__ import annotations

import argparse
import json
import os
import re

_IGNORE_DIRS = frozenset(
    [
        ".git",
        "node_modules",
        "dist",
        "build",
        ".venv",
        "venv",
        "__pycache__",
        "vendor",
        "target",
        ".next",
        "coverage",
    ]
)

_SOURCE_EXTS = frozenset(
    [".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".py", ".go", ".rb", ".java"]
)

_EVENT = re.compile(
    r"\.(emit|publish|subscribe|consume)\s*\(\s*[`'\"]([^`'\"]+)[`'\"]"
)


def _read(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


def _from_text(text, relpath):
    """Return a list of {name, action, file} for every matched event call."""
    out = []
    for match in _EVENT.finditer(text):
        out.append({
            "name": match.group(2),
            "action": match.group(1),
            "file": relpath,
        })
    return out


def extract(root):
    """Return a JSON-able list of {name, action, file} dicts.

    Walks the tree (skipping the standard ignore set), scans source files,
    and dedups by (name, action, file). Returns [] when nothing is found.
    """
    out = []
    seen = set()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _IGNORE_DIRS]
        for filename in filenames:
            ext = os.path.splitext(filename)[1]
            if ext not in _SOURCE_EXTS:
                continue
            path = os.path.join(dirpath, filename)
            text = _read(path)
            if text is None:
                continue
            relpath = os.path.relpath(path, root)
            for entry in _from_text(text, relpath):
                key = (entry["name"], entry["action"], entry["file"])
                if key in seen:
                    continue
                seen.add(key)
                out.append(entry)
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Extract event usage (emit/publish/subscribe/consume) from source."
    )
    parser.add_argument("--root", default=".", help="Directory to scan (default: .)")
    parser.add_argument(
        "--json", action="store_true", help="Emit results as a JSON array."
    )
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 2

    root = args.root
    if not os.path.isdir(root):
        print("error: root is not a directory: {0}".format(root), file=__import__("sys").stderr)
        return 2

    try:
        entries = extract(root)
    except Exception as exc:  # pragma: no cover - defensive
        print("error: {0}".format(exc), file=__import__("sys").stderr)
        return 2

    if args.json:
        print(json.dumps(entries))
    else:
        for entry in entries:
            print("{0}\t{1}\t{2}".format(entry["action"], entry["name"], entry["file"]))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
