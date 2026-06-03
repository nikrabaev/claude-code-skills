#!/usr/bin/env python3
"""Validator: docs must not contain line-number references (they go stale).

Scans Markdown for two kinds of line-number references and flags them:

1. file-with-extension followed by ``:NNN``   e.g. ``src/app.ts:412``
2. the phrase ``line NNN`` (case-insensitive)

It avoids false-flagging URLs, ``host:port`` (e.g. ``localhost:3000``,
``example.com:8080``) and C++ ``::`` scope (e.g. ``std::vector``) by only
matching a ``:NNN`` suffix when the token ends in a known code/file extension.

Fenced code blocks (``` ``` ``` and ``~~~``) are stripped before scanning so
example code is not flagged.

Exit codes:
    0  no violations
    1  line-number references found
    2  usage / internal error
"""

import argparse
import json
import os
import re
import sys

# CODE / FILE extensions whose tokens may carry a meaningful ``:NNN`` suffix.
_EXTENSIONS = [
    "ts", "tsx", "js", "jsx", "mjs", "cjs", "py", "go", "rs", "rb", "java",
    "kt", "c", "cc", "cpp", "cxx", "h", "hpp", "cs", "php", "swift", "scala",
    "sql", "sh", "bash", "zsh", "md", "txt", "json", "yaml", "yml", "toml",
    "ini", "cfg", "css", "scss", "html", "xml", "vue", "svelte",
]

# Pattern 1: a ``name.ext`` token immediately followed by ``:`` and digits,
# where ``ext`` is in the allowlist. The leading negative lookbehind prevents
# matching when preceded by a word char or a slash, so we anchor on token
# starts. Extension match is case-insensitive.
_FILE_REF = re.compile(
    r"(?<![\w/])([\w./-]*\.(?:" + "|".join(_EXTENSIONS) + r")):(\d+)\b",
    re.IGNORECASE,
)

# Pattern 2: the phrase ``line NNN`` (case-insensitive).
_LINE_PHRASE = re.compile(r"\bline\s+\d+\b", re.IGNORECASE)

# Directory names to skip during recursive discovery.
_SKIP_DIRS = frozenset(
    [".git", "node_modules", ".venv", "venv", "__pycache__", ".tox",
     "dist", "build", ".mypy_cache", ".pytest_cache"]
)

# Fence openers: triple backticks or triple tildes (with optional indent and
# an info string after the fence).
_FENCE = re.compile(r"^\s*(`{3,}|~{3,})")


def _line_violations(line):
    """Return a list of {"match": str} for a single (non-fenced) line."""
    found = []
    for m in _FILE_REF.finditer(line):
        found.append({"match": m.group(0)})
    for m in _LINE_PHRASE.finditer(line):
        found.append({"match": m.group(0)})
    return found


def find_violations(text):
    """Return violations for one document's text.

    Result: ``[{"line": <1-based original line no>, "match": <str>}]``.

    Fenced code blocks are skipped: we process the document line-by-line and
    track whether each line lies inside a ``` ``` or ``~~~ fence, mapping
    matches back to their original 1-based line numbers.
    """
    results = []
    fence_char = None  # None, "`" or "~" while inside a fence
    for idx, line in enumerate(text.splitlines(), start=1):
        m = _FENCE.match(line)
        if m:
            marker = m.group(1)[0]
            if fence_char is None:
                # Opening fence: enter fenced region, skip this line.
                fence_char = marker
                continue
            if marker == fence_char:
                # Closing fence of the same kind: leave fenced region.
                fence_char = None
                continue
            # A different fence marker while inside a fence is literal content.
        if fence_char is not None:
            # Inside a fenced code block: skip.
            continue
        for v in _line_violations(line):
            results.append({"line": idx, "match": v["match"]})
    return results


def scan_paths(paths):
    """Scan an iterable of file paths.

    Result: ``[{"file", "line", "match"}]`` across all readable files.
    """
    results = []
    for path in paths:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except (IOError, OSError):
            continue
        for v in find_violations(text):
            results.append(
                {"file": path, "line": v["line"], "match": v["match"]}
            )
    return results


def _discover_markdown(root):
    """Recursively find ``*.md`` files under ``root``, skipping noise dirs."""
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for name in filenames:
            if name.lower().endswith(".md"):
                found.append(os.path.join(dirpath, name))
    return sorted(found)


def _resolve_targets(root, patterns):
    """Resolve the list of files to scan.

    With no explicit patterns, discover all ``*.md`` under ``root``. Otherwise
    expand each pattern via glob (relative to ``root`` when not absolute).
    """
    if not patterns:
        return _discover_markdown(root)

    import glob

    files = []
    for pat in patterns:
        target = pat if os.path.isabs(pat) else os.path.join(root, pat)
        matched = glob.glob(target, recursive=True)
        for m in matched:
            if os.path.isfile(m):
                files.append(m)
            elif os.path.isdir(m):
                files.extend(_discover_markdown(m))
    # De-duplicate while preserving order.
    seen = set()
    unique = []
    for f in files:
        if f not in seen:
            seen.add(f)
            unique.append(f)
    return unique


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Flag stale line-number references in Markdown docs.",
    )
    parser.add_argument("--root", default=".", help="root directory to scan")
    parser.add_argument(
        "paths", nargs="*", help="explicit files or globs (default: all *.md)"
    )
    parser.add_argument(
        "--json", action="store_true", dest="as_json", help="emit JSON output"
    )

    try:
        args = parser.parse_args(argv)
    except SystemExit:
        # argparse exits with code 2 on usage errors; honor the contract.
        return 2

    if not os.path.isdir(args.root):
        sys.stderr.write("error: root is not a directory: %s\n" % args.root)
        return 2

    try:
        targets = _resolve_targets(args.root, args.paths)
        violations = scan_paths(targets)
    except (IOError, OSError) as exc:
        sys.stderr.write("error: %s\n" % exc)
        return 2

    if args.as_json:
        sys.stdout.write(json.dumps(violations, indent=2) + "\n")
    else:
        for v in violations:
            sys.stdout.write(
                "%s:%d: %s\n" % (v["file"], v["line"], v["match"])
            )

    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
