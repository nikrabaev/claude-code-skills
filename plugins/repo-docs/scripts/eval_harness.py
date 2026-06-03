#!/usr/bin/env python3
"""eval_harness.py -- Tier-A objective doc-quality delta.

Measures two documentation sets against a repository's *real* source and reports
a side-by-side comparison plus per-metric deltas. This is the **Tier-A** (no
live agent required) deliverable: a rigorous, objective answer to "does this doc
set measurably beat the baseline?".

It is a REPORT, not a gate: ``main`` always returns 0 on a successful run;
exit 2 is reserved for genuine usage problems (a bad ``--root`` or ``--dir-*``).

It REUSES the sibling validators in this same ``scripts/`` directory:

* ``score_docs``  -- ``score_doc(text, root=, doc_path=, index=)`` for the
  0-100 quality score and the evidence dimension.
* ``path_exists`` -- ``extract_path_tokens(text)`` (total path refs) and
  ``check_doc(text, root)`` (dead refs).
* ``no_line_refs`` -- ``find_violations(text)`` (line-number refs).
* ``dup_detect``  -- ``check(root, doc_paths)`` (duplicated source-of-truth).

CLI:
    eval_harness.py --root REPO --dir-a DIR --dir-b DIR \
        [--label-a A] [--label-b B] [--index FILE] [--json]

Exit codes:
    0  report produced (default)
    2  usage error (bad --root, bad --dir-a/--dir-b)
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

import score_docs
import path_exists
import no_line_refs
import dup_detect

SIZE_CAP = 32768  # 32 KiB -- the soft CLAUDE.md verbosity budget.

# Numeric metrics that ``compare`` diffs (delta = a - b).
COMPARE_METRICS = (
    "score",
    "total_bytes",
    "evidence_density",
    "path_resolve_pct",
    "line_refs",
    "duplication_findings",
)


def _read_text(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def measure(root, doc_paths, index=None):
    """Measure ``doc_paths`` (file paths) against ``root``'s real source.

    Returns the contract dict (see module docstring / plan): docs (relpaths),
    count, score (mean), total_bytes, under_cap, evidence_density (mean),
    path_refs_total, path_refs_resolved, path_resolve_pct, line_refs,
    duplication_findings.
    """
    docs = []
    scores = []
    evidences = []
    total_bytes = 0
    path_refs_total = 0
    path_refs_dead = 0
    line_refs = 0

    for doc in doc_paths:
        try:
            text = _read_text(doc)
        except (IOError, OSError):
            continue  # skip unreadable docs (TOCTOU / broken symlink), like the validators
        docs.append(os.path.relpath(doc, root))

        result = score_docs.score_doc(text, root=root, doc_path=doc, index=index)
        scores.append(result["score"])
        evidences.append(result["dimensions"]["evidence"]["score"])

        total_bytes += len(text.encode("utf-8"))

        path_refs_total += len(path_exists.extract_path_tokens(text))
        path_refs_dead += len(path_exists.check_doc(text, root))

        line_refs += len(no_line_refs.find_violations(text))

    count = len(docs)
    mean_score = (sum(scores) / count) if count else 0.0
    mean_evidence = (sum(evidences) / count) if count else 0.0
    path_refs_resolved = path_refs_total - path_refs_dead
    path_resolve_pct = (
        (path_refs_resolved / path_refs_total * 100) if path_refs_total else 100.0
    )
    duplication_findings = len(dup_detect.check(root, doc_paths))

    return {
        "docs": docs,
        "count": count,
        "score": mean_score,
        "total_bytes": total_bytes,
        "under_cap": total_bytes < SIZE_CAP,
        "evidence_density": mean_evidence,
        "path_refs_total": path_refs_total,
        "path_refs_resolved": path_refs_resolved,
        "path_resolve_pct": path_resolve_pct,
        "line_refs": line_refs,
        "duplication_findings": duplication_findings,
    }


def compare(a, b):
    """Diff two ``measure`` dicts over the numeric metrics.

    Returns ``{metric: {"a": a[m], "b": b[m], "delta": a[m] - b[m]}}``.
    ``delta = a - b`` -- how much A beats B.
    """
    return {
        m: {"a": a[m], "b": b[m], "delta": a[m] - b[m]}
        for m in COMPARE_METRICS
    }


def _markdown_files(directory):
    """Return all ``*.md`` paths under ``directory`` (recursive, sorted)."""
    return sorted(
        glob.glob(os.path.join(directory, "**", "*.md"), recursive=True)
    )


def _format_table(out):
    """Render a readable side-by-side table + deltas for ``out``."""
    a, b, delta = out["a"], out["b"], out["delta"]
    label_a, label_b = a["label"], b["label"]
    lines = []

    def fmt(v):
        if isinstance(v, bool):
            return "yes" if v else "no"
        if isinstance(v, float):
            return "%.2f" % v
        return str(v)

    rows = [
        ("docs measured", a["count"], b["count"], None),
        ("score (0-100)", a["score"], b["score"], delta["score"]["delta"]),
        ("total_bytes", a["total_bytes"], b["total_bytes"],
         delta["total_bytes"]["delta"]),
        ("under budget (<32KiB)", a["under_cap"], b["under_cap"], None),
        ("evidence_density", a["evidence_density"], b["evidence_density"],
         delta["evidence_density"]["delta"]),
        ("path refs total", a["path_refs_total"], b["path_refs_total"], None),
        ("path resolve %", a["path_resolve_pct"], b["path_resolve_pct"],
         delta["path_resolve_pct"]["delta"]),
        ("line refs", a["line_refs"], b["line_refs"],
         delta["line_refs"]["delta"]),
        ("duplication", a["duplication_findings"], b["duplication_findings"],
         delta["duplication_findings"]["delta"]),
    ]

    name_w = max(len(r[0]) for r in rows)
    col_w = max(len(label_a), len(label_b), 10)
    header = "%-*s  %*s  %*s  %s" % (
        name_w, "metric", col_w, label_a, col_w, label_b, "delta (a-b)"
    )
    lines.append(header)
    lines.append("-" * len(header))
    for name, av, bv, dv in rows:
        dcell = "" if dv is None else fmt(dv)
        lines.append("%-*s  %*s  %*s  %s" % (
            name_w, name, col_w, fmt(av), col_w, fmt(bv), dcell
        ))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Tier-A objective doc-quality delta between two doc sets."
    )
    parser.add_argument("--root", default=".",
                        help="repo root the docs are measured against")
    parser.add_argument("--dir-a", required=True,
                        help="directory of *.md for set A")
    parser.add_argument("--dir-b", required=True,
                        help="directory of *.md for set B")
    parser.add_argument("--label-a", default="a", help="label for set A")
    parser.add_argument("--label-b", default="b", help="label for set B")
    parser.add_argument("--index", default=None,
                        help="optional symbol-index file for scoring")
    parser.add_argument("--json", action="store_true",
                        help="emit JSON instead of a table")

    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 2

    for d in (args.root, args.dir_a, args.dir_b):
        if not os.path.isdir(d):
            sys.stderr.write("error: not a directory: %s\n" % d)
            return 2

    # Load the symbol index FROM the file (score_docs._load_index returns None on
    # any failure). Passing the raw path string would make every symbol resolve
    # as "not in index" -> spurious drift -> a corrupted A-vs-B delta.
    index = score_docs._load_index(args.index) if args.index else None

    measure_a = measure(args.root, _markdown_files(args.dir_a), index=index)
    measure_b = measure(args.root, _markdown_files(args.dir_b), index=index)

    out = {
        "a": {"label": args.label_a, **measure_a},
        "b": {"label": args.label_b, **measure_b},
        "delta": compare(measure_a, measure_b),
    }

    if args.json:
        print(json.dumps(out, indent=2))
    else:
        print(_format_table(out))

    return 0


if __name__ == "__main__":
    sys.exit(main())
