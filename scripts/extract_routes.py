#!/usr/bin/env python3
"""Extract HTTP route definitions from JS/TS and Python web frameworks.

Supported sources: Express/Koa/Fastify-style routers (JS/TS) and Flask /
FastAPI decorators (Python).  Stdlib only; targets Python 3.9.6.
"""
from __future__ import annotations

import argparse
import json
import os
import re

# Directories never worth descending into.
_IGNORE_DIRS = {
    ".git", "node_modules", "dist", "build", ".venv", "venv",
    "__pycache__", "vendor", "target", ".next", "coverage",
}

_JS_EXTS = (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs")

# app.get('/x', handler)  /  router.post("/y", (req, res) => ...)
_JS_ROUTE = re.compile(
    r"\b(?:app|router|r|fastify|server|api)\."
    r"(get|post|put|patch|delete|head|options|all)"
    r"\s*\(\s*[`'\"]([^`'\"]+)[`'\"]"
    r"\s*(?:,\s*([A-Za-z_$][\w$]*)\s*[,)])?"
)

# @app.get("/x") style decorators (FastAPI / framework verb decorators).
_PY_VERB_DECORATOR = re.compile(
    r"@(?:app|router|api|bp|blueprint)\."
    r"(get|post|put|patch|delete|head|options)"
    r"\s*\(\s*[`'\"]([^`'\"]+)[`'\"]"
)

# @app.route("/x", methods=[...]) style decorators (Flask).
_PY_ROUTE_DECORATOR = re.compile(
    r"@(?:app|router|api|bp|blueprint)\.route"
    r"\s*\(\s*[`'\"]([^`'\"]+)[`'\"]"
    r"\s*(?:,\s*methods\s*=\s*\[([^\]]*)\])?"
)

# A `def name(` declaration (Python handler name).
_PY_DEF = re.compile(r"^\s*(?:async\s+)?def\s+([A-Za-z_]\w*)")

# String literals inside a methods=[...] list.
_PY_METHOD_LITERAL = re.compile(r"[`'\"]([^`'\"]+)[`'\"]")


def _read(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


def _from_js_text(text, relpath):
    """Return route rows for a single JS/TS source string."""
    out = []
    for match in _JS_ROUTE.finditer(text):
        out.append({
            "method": match.group(1).upper(),
            "path": match.group(2),
            "handler": match.group(3) or "",
            "file": relpath,
        })
    return out


def _find_following_def(lines, start):
    """Return the def name within the next few non-blank lines, else ""."""
    seen = 0
    i = start
    n = len(lines)
    while i < n and seen < 3:
        line = lines[i]
        if line.strip() == "":
            i += 1
            continue
        # Stacked decorators do not count against the look-ahead budget.
        if line.lstrip().startswith("@"):
            i += 1
            continue
        match = _PY_DEF.match(line)
        if match:
            return match.group(1)
        seen += 1
        i += 1
    return ""


def _parse_methods_list(raw):
    """Parse uppercased HTTP methods from a methods=[...] inner string."""
    if not raw:
        return []
    return [m.group(1).upper() for m in _PY_METHOD_LITERAL.finditer(raw)]


def _from_python_text(text, relpath):
    """Return route rows for a single Python source string."""
    lines = text.splitlines()
    out = []
    for idx, line in enumerate(lines):
        verb_match = _PY_VERB_DECORATOR.search(line)
        if verb_match:
            handler = _find_following_def(lines, idx + 1)
            out.append({
                "method": verb_match.group(1).upper(),
                "path": verb_match.group(2),
                "handler": handler,
                "file": relpath,
            })
            continue
        route_match = _PY_ROUTE_DECORATOR.search(line)
        if route_match:
            path = route_match.group(1)
            methods = _parse_methods_list(route_match.group(2)) or ["GET"]
            handler = _find_following_def(lines, idx + 1)
            for method in methods:
                out.append({
                    "method": method,
                    "path": path,
                    "handler": handler,
                    "file": relpath,
                })
    return out


def extract(root):
    """Return a JSON-able list of {method, path, handler, file} dicts.

    Walks the tree (skipping the ignore set), parsing JS/TS and Python
    sources.  Dedups by (method, path, handler, file).  Returns [] when no
    routes are found.
    """
    out = []
    seen = set()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _IGNORE_DIRS]
        for filename in filenames:
            ext = os.path.splitext(filename)[1].lower()
            if ext in _JS_EXTS:
                parser = _from_js_text
            elif ext == ".py":
                parser = _from_python_text
            else:
                continue
            path = os.path.join(dirpath, filename)
            text = _read(path)
            if text is None:
                continue
            relpath = os.path.relpath(path, root)
            for row in parser(text, relpath):
                key = (row["method"], row["path"], row["handler"], row["file"])
                if key in seen:
                    continue
                seen.add(key)
                out.append(row)
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Extract HTTP route definitions from a project tree."
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
                row["method"], row["path"], row["handler"], row["file"]))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
