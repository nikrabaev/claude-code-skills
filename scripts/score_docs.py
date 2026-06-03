#!/usr/bin/env python3
"""Advisory 0-100 doc-quality scorer (a calibrated, tunable rubric).

``score_docs.py`` rates a single AI-facing doc across six dimensions and reduces
them to a weighted 0-100 score. It is an **advisory proxy, never the sole gate**
(DESIGN §13 #16, §12): it reports a score and where a doc is weak; it does not
pass/fail anything. The blocking gate (``run_gate.sh``) owns pass/fail; this
score guides *improvement*.

It REUSES two existing validators that live in the same ``scripts/`` directory:

* ``no_line_refs`` -- ``find_violations(text)`` for the ref-stability dimension.
* ``drift_check`` -- ``find_drift(root, [doc], index)`` for the drift dimension.

The six dimensions, their default weights (``[SYNTHESIS]`` -- reasoned, not
authoritative; tune with ``--weights``), and the calibration formulas are the
contract; see ``references/scoring-rubric.md``.

Exit codes:
    0  always by default (advisory -- even a below-threshold doc exits 0)
    1  some doc is below threshold AND --strict
    2  usage / internal error (bad --root, malformed --weights)
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

import no_line_refs
import drift_check

DEFAULT_THRESHOLD = 70
DEFAULT_SIZE_TARGET = 12288  # 12 KiB -- the size we aim for.
DEFAULT_SIZE_CAP = 32768  # 32 KiB -- the Codex AGENTS.md concatenation cap.

# [SYNTHESIS] -- reasoned, not vendor-blessed. Tune with --weights. Sum 1.0.
DEFAULT_WEIGHTS = {
    "size_fit": 0.15,
    "evidence": 0.30,
    "ref_stability": 0.15,
    "examples": 0.15,
    "boundaries": 0.15,
    "drift": 0.10,
}

# The dimension names in stable presentation order.
_DIMENSIONS = (
    "size_fit",
    "evidence",
    "ref_stability",
    "examples",
    "boundaries",
    "drift",
)

# HTML comments. They are invisible to any reader/agent (and the generators
# delete the template comment before shipping), so their contents must NOT count
# toward the "rendered" dimensions (evidence, examples, boundaries). Otherwise an
# annotation like "<!-- boundaries missing: ✅ ⚠️ 🚫 -->" would falsely earn full
# boundary credit. (size_fit measures raw bytes -- Codex loads the whole file;
# ref_stability and drift mirror the gate's exact checks -- so those use raw text.)
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)


def _strip_html_comments(text):
    """Remove ``<!-- ... -->`` spans (including multi-line) from ``text``."""
    return _HTML_COMMENT_RE.sub("", text)


# Fenced code blocks (mirror dup_detect's fence shape).
_FENCE_RE = re.compile(r"^```[^\n]*\n(.*?)^```", re.DOTALL | re.MULTILINE)

# A single fence delimiter line (opening or closing); used to skip fenced
# regions when walking content lines.
_FENCE_LINE = re.compile(r"^\s*```")

# "e.g." / "for example" example markers.
_EG_RE = re.compile(r"\b(e\.g\.|for example)\b", re.I)

# A Boundaries/Contracts/Guardrails-style heading.
_BOUNDARY_HEADING = re.compile(r"(?im)^#+\s.*(boundar|contract|guardrail)")

# Leading bullet/number list marker to strip before counting words.
_LIST_MARKER = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)")

# A run of alphabetic characters = one "word" for the >=4-word content gate.
_ALPHA_WORD = re.compile(r"[A-Za-z]+")

# Tier emojis used by the boundaries/examples dimensions.
_TIER_EMOJIS = ("✅", "⚠️", "🚫")


def _fenced_blocks(text):
    """Return the inner contents of each ``` fenced code block in ``text``."""
    return [m.group(1) for m in _FENCE_RE.finditer(text)]


def _content_lines(text):
    """Return the *content lines* of ``text``.

    A content line is non-blank, not a heading (``#``), not a fence delimiter,
    not inside a fenced block, not a Markdown table separator, not a ``---``
    horizontal rule, and -- after stripping a leading bullet/number marker --
    has at least four alphabetic words. These are the lines that should carry
    evidence; structural/decorative lines are excluded.
    """
    lines = []
    in_fence = False
    for raw in text.splitlines():
        if _FENCE_LINE.match(raw):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        stripped = raw.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        if stripped.startswith("---"):
            continue
        # Markdown table separator row, e.g. ``|---|---|`` or ``|:--|--:|``.
        if stripped.startswith("|") and re.match(r"^\|[\s:|-]+\|?$", stripped):
            continue
        body = _LIST_MARKER.sub("", raw)
        if len(_ALPHA_WORD.findall(body)) < 4:
            continue
        lines.append(raw)
    return lines


def _has_evidence(line):
    """True if ``line`` bears evidence: an inline backtick OR NEEDS VERIFICATION."""
    return ("`" in line) or ("NEEDS VERIFICATION" in line)


def _score_size_fit(text, size_target=DEFAULT_SIZE_TARGET, size_cap=DEFAULT_SIZE_CAP):
    """1.0 at/under target; 0.0 at/over cap; linear in between.

    Penalizes only largeness: a small doc is fully size-fit (its other gaps
    surface in the other dimensions).
    """
    nbytes = len(text.encode("utf-8"))
    if nbytes <= size_target:
        return 1.0
    if nbytes >= size_cap:
        return 0.0
    return float(size_cap - nbytes) / float(size_cap - size_target)


def _score_evidence(text):
    """Fraction of content lines that bear evidence. 0.0 if no content lines."""
    lines = _content_lines(text)
    if not lines:
        return 0.0
    hits = sum(1 for ln in lines if _has_evidence(ln))
    return float(hits) / float(len(lines))


def _score_ref_stability(text):
    """1.0 with no line-number refs; otherwise decays 0.5 per violation."""
    v = len(no_line_refs.find_violations(text))
    if v == 0:
        return 1.0
    return max(0.0, 1.0 - 0.5 * v)


def _score_examples(text):
    """Presence of ✅/🚫 markers, fenced snippets, and "e.g."/"for example"."""
    signals = (
        text.count("✅")
        + text.count("🚫")
        + len(_fenced_blocks(text))
        + len(_EG_RE.findall(text))
    )
    return min(1.0, signals / 4.0)


def _score_boundaries(text):
    """1.0 with all three tiers; 0.5 with a boundary heading or one tier; else 0."""
    if all(emoji in text for emoji in _TIER_EMOJIS):
        return 1.0
    if _BOUNDARY_HEADING.search(text) or any(e in text for e in _TIER_EMOJIS):
        return 0.5
    return 0.0


def _score_drift(root, doc_path, index):
    """1.0 with no drift findings; otherwise decays 0.2 per finding."""
    f = len(drift_check.find_drift(root, [doc_path], index))
    if f == 0:
        return 1.0
    return max(0.0, 1.0 - 0.2 * f)


def score_doc(
    text,
    root=None,
    doc_path=None,
    index=None,
    weights=None,
    threshold=DEFAULT_THRESHOLD,
    size_target=DEFAULT_SIZE_TARGET,
    size_cap=DEFAULT_SIZE_CAP,
):
    """Score one doc's ``text``; return the rubric dict (see module docstring).

    ``drift`` is applicable ONLY when ``root`` is given (it needs the
    filesystem); otherwise it is excluded and the remaining weights are
    renormalized -- an unmeasurable dimension is dropped, never scored 0.

    ``weights`` (if given) is merged over ``DEFAULT_WEIGHTS`` and renormalized
    over the applicable dimensions.
    """
    merged = dict(DEFAULT_WEIGHTS)
    if weights:
        merged.update(weights)

    drift_applicable = root is not None

    # "Rendered" dimensions ignore HTML comments (invisible to readers/agents).
    # size_fit (raw bytes -> Codex cap), ref_stability and drift (mirror the gate)
    # operate on the raw text.
    visible = _strip_html_comments(text)

    scores = {
        "size_fit": _score_size_fit(text, size_target, size_cap),
        "evidence": _score_evidence(visible),
        "ref_stability": _score_ref_stability(text),
        "examples": _score_examples(visible),
        "boundaries": _score_boundaries(visible),
    }
    if drift_applicable:
        scores["drift"] = _score_drift(root, doc_path, index)
    else:
        scores["drift"] = 0.0  # not applicable -> excluded from the weighting

    details = {
        "size_fit": "%d bytes (target %d, cap %d)" % (
            len(text.encode("utf-8")), size_target, size_cap),
        "evidence": "%d/%d content lines bear evidence" % (
            sum(1 for ln in _content_lines(visible) if _has_evidence(ln)),
            len(_content_lines(visible)),
        ),
        "ref_stability": "%d line-number reference(s)" % len(
            no_line_refs.find_violations(text)),
        "examples": "%d example signal(s)" % (
            visible.count("✅") + visible.count("🚫")
            + len(_fenced_blocks(visible)) + len(_EG_RE.findall(visible))
        ),
        "boundaries": _boundaries_detail(visible),
        "drift": (
            "%d drift finding(s)" % len(
                drift_check.find_drift(root, [doc_path], index))
            if drift_applicable
            else "not measured (no --root)"
        ),
    }

    applicable = {name: (name != "drift" or drift_applicable) for name in _DIMENSIONS}

    weight_sum = sum(merged[name] for name in _DIMENSIONS if applicable[name])
    if weight_sum > 0:
        weighted = sum(
            merged[name] * scores[name]
            for name in _DIMENSIONS
            if applicable[name]
        )
        final = round(100.0 * weighted / weight_sum)
    else:
        final = 0

    dimensions = {}
    for name in _DIMENSIONS:
        dimensions[name] = {
            "score": scores[name],
            "weight": merged[name],
            "applicable": applicable[name],
            "detail": details[name],
        }

    return {
        "score": int(final),
        "threshold": int(threshold),
        "above_threshold": int(final) >= int(threshold),
        "dimensions": dimensions,
    }


def _boundaries_detail(text):
    present = [e for e in _TIER_EMOJIS if e in text]
    if len(present) == len(_TIER_EMOJIS):
        return "all three tiers present (✅ ⚠️ 🚫)"
    if _BOUNDARY_HEADING.search(text):
        return "boundary heading present; %d/3 tiers" % len(present)
    return "%d/3 tier markers present" % len(present)


def _parse_weights(s):
    """Parse a ``name=float,name=float`` string into a weights dict.

    Raises ``ValueError`` on a non-float value or an unknown dimension name.
    """
    out = {}
    for chunk in s.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "=" not in chunk:
            raise ValueError("malformed weight (expected name=value): %r" % chunk)
        name, _, value = chunk.partition("=")
        name = name.strip()
        if name not in DEFAULT_WEIGHTS:
            raise ValueError("unknown dimension name: %r" % name)
        try:
            out[name] = float(value.strip())
        except ValueError:
            raise ValueError("non-float weight for %r: %r" % (name, value.strip()))
    return out


def _default_md_files(root):
    """All ``*.md`` files under ``root`` (recursive)."""
    return sorted(glob.glob(os.path.join(root, "**", "*.md"), recursive=True))


def _resolve_docs(root, patterns):
    """Resolve doc targets. Default: all *.md under root (recursive).

    Mirrors ``dup_detect._resolve_docs``.
    """
    if not patterns:
        return _default_md_files(root)
    docs = []
    for pat in patterns:
        if os.path.isabs(pat):
            matches = glob.glob(pat, recursive=True)
        else:
            matches = glob.glob(os.path.join(root, pat), recursive=True)
        if matches:
            for m in sorted(matches):
                if os.path.isfile(m) and m not in docs:
                    docs.append(m)
        elif os.path.isfile(pat) and pat not in docs:
            docs.append(pat)
    return docs


def _load_index(path):
    """Load a symbol index JSON array; return None on any failure."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    if isinstance(data, list):
        return data
    return None


def _read_text(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def _print_report(out, doc, result):
    """Write a human-readable per-doc report block."""
    flag = "ABOVE" if result["above_threshold"] else "BELOW"
    out.write(
        "%s: score %d/100 (threshold %d -- %s)\n" % (
            doc, result["score"], result["threshold"], flag)
    )
    for name in _DIMENSIONS:
        dim = result["dimensions"][name]
        if dim["applicable"]:
            out.write(
                "  %-14s %.2f (w=%.2f)  %s\n" % (
                    name, dim["score"], dim["weight"], dim["detail"])
            )
        else:
            out.write(
                "  %-14s   n/a        %s\n" % (name, dim["detail"])
            )


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="score_docs.py",
        description="Advisory 0-100 doc-quality rubric (a proxy, never the "
        "sole gate).",
    )
    parser.add_argument("--root", default=".", help="project root (default: .)")
    parser.add_argument(
        "paths", nargs="*", help="doc files or globs (default: all *.md under root)"
    )
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="emit a JSON array of per-doc results")
    parser.add_argument("--strict", action="store_true",
                        help="exit 1 if any doc is below threshold (default: 0)")
    parser.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD,
                        help="pass threshold 0-100 (default: %d)" % DEFAULT_THRESHOLD)
    parser.add_argument("--weights", help="override weights, e.g. 'evidence=0.4,size_fit=0.1'")
    parser.add_argument("--index", help="symbol index JSON array for the drift dimension")
    parser.add_argument("--size-target", type=int, default=DEFAULT_SIZE_TARGET,
                        dest="size_target", help="size-fit target bytes (default: %d)" % DEFAULT_SIZE_TARGET)
    parser.add_argument("--size-cap", type=int, default=DEFAULT_SIZE_CAP,
                        dest="size_cap", help="size-fit cap bytes (default: %d)" % DEFAULT_SIZE_CAP)

    try:
        args = parser.parse_args(argv)
    except SystemExit:
        # argparse exits 2 on usage error; preserve that contract.
        return 2

    root = args.root
    if not os.path.isdir(root):
        sys.stderr.write("error: --root is not a directory: %s\n" % root)
        return 2

    weights = None
    if args.weights:
        try:
            weights = _parse_weights(args.weights)
        except ValueError as exc:
            sys.stderr.write("error: %s\n" % exc)
            return 2

    index = _load_index(args.index) if args.index else None

    try:
        docs = _resolve_docs(root, args.paths)
    except (IOError, OSError) as exc:
        sys.stderr.write("error: %s\n" % exc)
        return 2

    results = []
    any_below = False
    for doc in docs:
        try:
            text = _read_text(doc)
        except (IOError, OSError):
            continue
        result = score_doc(
            text,
            root=root,
            doc_path=doc,
            index=index,
            weights=weights,
            threshold=args.threshold,
            size_target=args.size_target,
            size_cap=args.size_cap,
        )
        if not result["above_threshold"]:
            any_below = True
        results.append({"file": doc, **result})

    if args.as_json:
        sys.stdout.write(json.dumps(results, indent=2, ensure_ascii=False) + "\n")
    else:
        if not results:
            sys.stdout.write("no docs to score\n")
        for entry in results:
            doc = entry["file"]
            result = {k: v for k, v in entry.items() if k != "file"}
            _print_report(sys.stdout, doc, result)

    if args.strict and any_below:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
