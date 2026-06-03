#!/usr/bin/env python3
"""Validator: backticked path-like tokens in Markdown must resolve to an
existing file or directory relative to the repo root.

Exit codes:
    0  all referenced paths exist
    1  one or more dead (non-existent) paths found
    2  usage / internal error
"""
import argparse
import json
import os
import re
import sys

# Directories that are never scanned for *.md files.
IGNORED_DIRS = frozenset([".git", "node_modules", ".hg", ".svn", "__pycache__"])

# A single-backtick inline-code span: `...` (not spanning newlines, no backticks
# inside). Double/triple backtick fences are handled by requiring exactly one
# backtick on each side via the surrounding negative checks below.
_INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")

# ENV-VAR style token, e.g. PATH, MENV_PASSPHRASE.
_ENV_VAR_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")

# Bare filename with an extension, e.g. config.json, README.md.
_FILENAME_EXT_RE = re.compile(r"^[\w.-]+\.[A-Za-z0-9]+$")

_TRAILING_PUNCT = ".,;:"


def _iter_inline_spans(text):
    """Yield (line_number, span_content) for each single-backtick inline-code
    span in ``text``. Double-backtick (``...``) and longer runs are skipped so
    that fenced code blocks and double-backtick spans are not treated as inline
    single-backtick spans.
    """
    for match in _INLINE_CODE_RE.finditer(text):
        start, end = match.start(), match.end()
        # Reject if the backtick run is longer than one on either side.
        if start - 1 >= 0 and text[start - 1] == "`":
            continue
        if end < len(text) and text[end] == "`":
            continue
        content = match.group(1)
        line = text.count("\n", 0, start) + 1
        yield line, content


def _is_url(token):
    if token.startswith("http://") or token.startswith("https://"):
        return True
    if token.startswith("mailto:"):
        return True
    if "://" in token:
        return True
    return False


def _is_symbol_or_call(token):
    return "(" in token or token.endswith("()")


def _has_glob(token):
    return "*" in token or "?" in token


def _looks_like_path(token):
    """Decide whether a (already filtered) span content should be treated as a
    path token. Returns the candidate (no normalisation) or ``None``.
    """
    if not token:
        return None
    if any(ch.isspace() for ch in token):
        return None
    if _is_url(token):
        return None
    if _is_symbol_or_call(token):
        return None
    if _ENV_VAR_RE.match(token):
        return None
    if _has_glob(token):
        return None
    if "/" in token or _FILENAME_EXT_RE.match(token):
        return token
    return None


def _normalize(token):
    """Strip a single trailing '/' and trailing punctuation before resolving."""
    if token.endswith("/"):
        token = token[:-1]
    while token and token[-1] in _TRAILING_PUNCT:
        token = token[:-1]
    return token


def extract_path_tokens(text):
    """Return the list of path-like tokens (raw, un-normalised span content)
    found in single-backtick inline-code spans, in document order.
    """
    tokens = []
    for _line, content in _iter_inline_spans(text):
        candidate = _looks_like_path(content)
        if candidate is not None:
            tokens.append(candidate)
    return tokens


def _exists(token, root):
    norm = _normalize(token)
    if not norm:
        return True  # nothing left to resolve; treat as not a violation
    return os.path.exists(os.path.join(root, norm))


def check_doc(text, root):
    """Return a list of dead-path records ``[{"token", "line"}]`` for ``text``."""
    dead = []
    for line, content in _iter_inline_spans(text):
        candidate = _looks_like_path(content)
        if candidate is None:
            continue
        if not _exists(candidate, root):
            dead.append({"token": _normalize(candidate), "line": line})
    return dead


def _read_text(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def scan_paths(paths, root):
    """Scan a list of markdown file paths. Return a list of records
    ``[{"file", "line", "token"}]`` for every dead path found.
    """
    records = []
    for path in paths:
        try:
            text = _read_text(path)
        except (IOError, OSError):
            continue
        for rec in check_doc(text, root):
            records.append({"file": path, "line": rec["line"], "token": rec["token"]})
    return records


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


def _resolve_targets(path_args, root):
    """Expand explicit path/glob arguments into a sorted list of files.
    With no arguments, default to all ``*.md`` under ``root``.
    """
    if not path_args:
        return _default_md_files(root)

    import glob

    files = []
    for arg in path_args:
        candidate = arg if os.path.isabs(arg) else os.path.join(root, arg)
        if os.path.isdir(candidate):
            for sub in _default_md_files(candidate):
                files.append(sub)
        elif os.path.isfile(candidate):
            files.append(candidate)
        else:
            matches = glob.glob(candidate)
            for m in matches:
                if os.path.isfile(m):
                    files.append(m)
    # De-duplicate while preserving order.
    seen = set()
    unique = []
    for f in files:
        if f not in seen:
            seen.add(f)
            unique.append(f)
    return unique


def _build_parser():
    parser = argparse.ArgumentParser(
        description="Validate backticked path-like tokens in Markdown resolve "
        "to existing files/dirs relative to the repo root.",
    )
    parser.add_argument("--root", default=".", help="Repo root (default: cwd).")
    parser.add_argument(
        "paths",
        nargs="*",
        help="Files or globs to check (default: all *.md under root).",
    )
    parser.add_argument(
        "--json", action="store_true", help="Emit JSON records instead of text."
    )
    return parser


def main(argv=None):
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        # argparse exits with 2 on usage error; normalise to our contract.
        return 2

    root = args.root
    if not os.path.isdir(root):
        sys.stderr.write("path_exists: root not found: %s\n" % root)
        return 2

    try:
        targets = _resolve_targets(args.paths, root)
        records = scan_paths(targets, root)
    except (IOError, OSError) as exc:
        sys.stderr.write("path_exists: internal error: %s\n" % exc)
        return 2

    if args.json:
        sys.stdout.write(json.dumps(records))
        sys.stdout.write("\n")
    else:
        for rec in records:
            sys.stdout.write(
                "%s:%d: %s (not found)\n" % (rec["file"], rec["line"], rec["token"])
            )

    return 1 if records else 0


if __name__ == "__main__":
    sys.exit(main())
