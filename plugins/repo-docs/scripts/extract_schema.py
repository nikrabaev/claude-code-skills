#!/usr/bin/env python3
"""Extract data-model definitions (tables/models) from a source tree.

Supported sources: Prisma schemas (.prisma), SQL DDL (.sql), Django models (.py).
Stdlib only; targets Python 3.9.6.
"""
from __future__ import annotations

import argparse
import json
import os
import re


_IGNORE_DIRS = frozenset({
    ".git", "node_modules", "dist", "build", ".venv", "venv",
    "__pycache__", "vendor", "target", ".next", "coverage",
})


def _read(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


_PRISMA_MODEL = re.compile(r"^\s*model\s+([A-Za-z_]\w*)\s*\{", re.MULTILINE)
_SQL_TABLE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[\"`]?([A-Za-z_][\w.]*)[\"`]?\s*\(",
    re.IGNORECASE,
)
# Match `models.Model` anywhere in the base list, so mixins before OR after the
# base are handled (e.g. `class B(models.Model, Mixin)` and
# `class C(Mixin, models.Model)`), as well as dotted bases (`django.db.models.Model`).
_DJANGO_MODEL = re.compile(
    r"^\s*class\s+([A-Za-z_]\w*)\s*\([^)]*\bmodels\.Model\b",
    re.MULTILINE,
)


def _from_prisma_text(text, relpath):
    out = []
    for match in _PRISMA_MODEL.finditer(text):
        out.append({
            "entity": match.group(1),
            "kind": "model",
            "source": "prisma",
            "file": relpath,
        })
    return out


def _from_sql_text(text, relpath):
    out = []
    for match in _SQL_TABLE.finditer(text):
        out.append({
            "entity": match.group(1),
            "kind": "table",
            "source": "sql",
            "file": relpath,
        })
    return out


def _from_python_text(text, relpath):
    out = []
    for match in _DJANGO_MODEL.finditer(text):
        out.append({
            "entity": match.group(1),
            "kind": "model",
            "source": "django",
            "file": relpath,
        })
    return out


def _parser_for(name):
    if name.endswith(".prisma"):
        return _from_prisma_text
    if name.endswith(".sql"):
        return _from_sql_text
    if name.endswith(".py"):
        return _from_python_text
    return None


def extract(root):
    """Return a JSON-able list of {entity, kind, source, file} dicts.

    Dedups by (entity, kind, source, file). Returns [] when nothing matches.
    """
    out = []
    seen = set()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _IGNORE_DIRS]
        for filename in filenames:
            parser = _parser_for(filename)
            if parser is None:
                continue
            path = os.path.join(dirpath, filename)
            text = _read(path)
            if text is None:
                continue
            relpath = os.path.relpath(path, root)
            for entry in parser(text, relpath):
                key = (entry["entity"], entry["kind"], entry["source"], entry["file"])
                if key in seen:
                    continue
                seen.add(key)
                out.append(entry)
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Extract data-model definitions from a source tree."
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
        rows = extract(root)
    except Exception as exc:  # pragma: no cover - defensive
        print("error: {0}".format(exc), file=__import__("sys").stderr)
        return 2

    if args.json:
        print(json.dumps(rows))
    else:
        for row in rows:
            print("{0}\t{1}\t{2}\t{3}".format(
                row["source"], row["kind"], row["entity"], row["file"]))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
