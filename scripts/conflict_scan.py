#!/usr/bin/env python3
"""conflict_scan.py - advisory detector for contradictory rules in a doc.

A doc that says both "use tabs" and "use spaces" (or "named exports only" while
also showing a live ``export default``) gives the agent mutually exclusive
instructions. This scanner surfaces such contradictions.

It is deliberately LOW false-positive: it only fires on a curated table of
antonym rule pairs, and only when BOTH sides of a pair appear in the doc. Sides
whose ``kind`` is ``"instance"`` (e.g. a literal ``export default`` in a code
block) are skipped on prohibition/negation lines, so an anti-pattern shown as
the forbidden thing (``🚫 `export default```) is NOT counted as a conflict.

Detection is per-document; a conflict spanning two separate files is a
documented limitation.

Like the sibling drift_check, this script is ADVISORY: it defaults to exit 0
even when it has findings. Pass ``--strict`` to make findings exit non-zero.

Exit codes:
    0  no findings, OR findings without --strict (advisory default)
    1  findings AND --strict
    2  usage error (e.g. --root is not a directory)
"""
from __future__ import annotations

import argparse
import glob as globmod
import json
import os
import re
import sys

# Curated table of antonym rule pairs. A finding fires when BOTH ``a`` and ``b``
# produce a hit in the doc. Each side is (compiled_regex, kind); kind is "rule"
# (a prescriptive statement) or "instance" (a literal occurrence in source/text,
# negation-filtered so a forbidden example is not mistaken for a directive).
CONFLICTS = [
    {
        "category": "indentation",
        "a": (re.compile(r"\b(use|prefer|indent\w* with|indent\w* using) tabs\b",
                         re.IGNORECASE), "rule"),
        "b": (re.compile(r"\b(use|prefer|indent\w* with|indent\w* using)\s+(?:\d+\s+)?spaces\b",
                         re.IGNORECASE), "rule"),
        "detail": "doc tells the agent to indent with tabs AND with spaces",
    },
    {
        "category": "quotes",
        "a": (re.compile(r"\b(use|prefer)\s+single quotes\b", re.IGNORECASE), "rule"),
        "b": (re.compile(r"\b(use|prefer)\s+double quotes\b", re.IGNORECASE), "rule"),
        "detail": "doc prescribes both single quotes AND double quotes",
    },
    {
        "category": "semicolons",
        "a": (re.compile(r"\b(use|require|always use)\s+semicolons\b|semicolons?\s+(?:are\s+)?required\b",
                         re.IGNORECASE), "rule"),
        "b": (re.compile(r"\bno semicolons\b|\bomit semicolons\b|\bsemicolon-free\b|\bwithout semicolons\b|\bnever\s+(?:use\s+)?semicolons\b",
                         re.IGNORECASE), "rule"),
        "detail": "doc both requires AND forbids semicolons",
    },
    {
        "category": "exports",
        "a": (re.compile(r"named exports?\s+only\b|no default exports?\b|avoid default exports?\b|don'?t use default exports?\b|never use default exports?\b",
                         re.IGNORECASE), "rule"),
        "b": (re.compile(r"\bexport default\b", re.IGNORECASE), "instance"),
        "detail": "doc says named exports only but also uses a default export",
    },
]

# Negation / prohibition context. A line matching this is treated as showing the
# forbidden thing, not prescribing it -- so an "instance" hit on such a line is
# skipped (low false-positive).
_NEG_RE = re.compile(
    r"🚫|❌|⚠️|"
    r"\bnot\b|\bnever\b|\bavoid\b|\bdon'?t\b|\bdo not\b|\binstead\b|"
    r"\brather than\b|deprecat|\blegacy\b|\baway from\b|\bno default\b",
    re.IGNORECASE,
)


def _first_hit(lines, regex, kind):
    """Return (lineno, matchtext) for the first matching line, or None.

    ``lines`` is iterated 1-based. For ``kind == "instance"`` any line that
    ``_NEG_RE`` matches is skipped, so a forbidden example (shown as the thing
    NOT to do) is not treated as a directive.
    """
    for lineno, line in enumerate(lines, start=1):
        if kind == "instance" and _NEG_RE.search(line):
            continue
        m = regex.search(line)
        if m:
            return (lineno, m.group(0))
    return None


def find_conflicts(text):
    """Return contradictory-rule findings for ``text``.

    Each finding is a dict: {"category", "lines": [a_line, b_line], "detail",
    "a": a_match, "b": b_match}. A finding fires only when BOTH sides of a
    CONFLICTS entry produce a ``_first_hit``.
    """
    lines = text.split("\n")
    findings = []
    for spec in CONFLICTS:
        a_regex, a_kind = spec["a"]
        b_regex, b_kind = spec["b"]
        a_hit = _first_hit(lines, a_regex, a_kind)
        if a_hit is None:
            continue
        b_hit = _first_hit(lines, b_regex, b_kind)
        if b_hit is None:
            continue
        findings.append({
            "category": spec["category"],
            "lines": [a_hit[0], b_hit[0]],
            "detail": spec["detail"],
            "a": a_hit[1],
            "b": b_hit[1],
        })
    return findings


def _resolve_docs(root, patterns):
    """Resolve doc targets. Default: all *.md under root (recursive)."""
    if not patterns:
        return sorted(
            globmod.glob(os.path.join(root, "**", "*.md"), recursive=True)
        )
    docs = []
    for pat in patterns:
        if os.path.isabs(pat):
            matches = globmod.glob(pat, recursive=True)
        else:
            matches = globmod.glob(os.path.join(root, pat), recursive=True)
        if matches:
            for m in sorted(matches):
                if os.path.isfile(m) and m not in docs:
                    docs.append(m)
        elif os.path.isfile(pat) and pat not in docs:
            docs.append(pat)
    return docs


def _read_text(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="conflict_scan.py",
        description="Advisory: detect contradictory rules within a doc "
                    "(e.g. tabs vs spaces, named-only vs export default).",
    )
    parser.add_argument("--root", default=".", help="repository root (default: .)")
    parser.add_argument("paths", nargs="*",
                        help="doc files or globs (default: all *.md under root)")
    parser.add_argument("--json", dest="as_json", action="store_true",
                        help="emit findings as a JSON array")
    parser.add_argument("--strict", action="store_true",
                        help="exit 1 when there are findings (default is advisory exit 0)")

    try:
        args = parser.parse_args(argv)
    except SystemExit:
        # argparse exits 2 on usage error; preserve that contract.
        return 2

    root = args.root
    if not os.path.isdir(root):
        sys.stderr.write("error: --root is not a directory: {0}\n".format(root))
        return 2

    docs = _resolve_docs(root, args.paths)
    all_findings = []
    for doc in docs:
        try:
            text = _read_text(doc)
        except (IOError, OSError):
            continue
        for finding in find_conflicts(text):
            entry = {"file": doc}
            entry.update(finding)
            all_findings.append(entry)

    if args.as_json:
        sys.stdout.write(json.dumps(all_findings, indent=2) + "\n")
    else:
        if not all_findings:
            sys.stdout.write("OK: no contradictory rules found\n")
        else:
            for f in all_findings:
                sys.stdout.write(
                    "{file}: [{category}] {detail} "
                    "(lines {l0} & {l1}: {a!r} vs {b!r})\n".format(
                        file=f["file"],
                        category=f["category"],
                        detail=f["detail"],
                        l0=f["lines"][0],
                        l1=f["lines"][1],
                        a=f["a"],
                        b=f["b"],
                    )
                )

    if args.strict and all_findings:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
