#!/usr/bin/env python3
"""Validate the CLAUDE.md verbosity budget.

CLAUDE.md is Claude Code's always-loaded project memory: it loads on every task,
so a bloated file spends context budget and invites context rot. Claude Code
merges the CLAUDE.md chain from the project root DOWN to the working directory,
so this script reproduces that chain (root approximated by --root, no git
discovery), sums it in BYTES, and warns before a soft budget so the always-loaded
layer stays small.

The budget is a soft, configurable target (--budget, default 32 KiB), not a hard
cap; aim for ~1-2 pages per file rather than treating the budget as a ceiling to
fill.

Exit codes:
    0  chain under budget (may print a WARNING line if near it)
    1  chain >= budget (over_budget)
    2  usage / internal error
"""

import argparse
import json
import os
import sys

DEFAULT_BUDGET = 32768
DEFAULT_WARN_RATIO = 0.9
JOIN_SEP = "\n\n"
DOC_NAME = "CLAUDE.md"


def _read_text(path):
    """Read a file as UTF-8 text. Returns None if it cannot be read."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except (OSError, UnicodeDecodeError):
        return None


def _chain_dirs(root, cwd):
    """Yield directories from root DOWN to root/cwd inclusive (root first).

    cwd is a subdirectory relative to root. Each successive ancestor of
    root/cwd between root and root/cwd is included.
    """
    root = os.path.abspath(root)
    dirs = [root]
    if cwd:
        # Normalize and reject paths that escape the root.
        rel = os.path.normpath(cwd)
        if os.path.isabs(rel) or rel == os.pardir or rel.startswith(os.pardir + os.sep):
            raise ValueError("--cwd must be a subdirectory of --root: %r" % (cwd,))
        parts = [p for p in rel.split(os.sep) if p and p != os.curdir]
        current = root
        for part in parts:
            current = os.path.join(current, part)
            dirs.append(current)
    return dirs


def _is_nonempty_doc(path):
    """True if path is a readable file with non-empty UTF-8 content.

    An empty or unreadable file contributes nothing to the always-loaded layer,
    so it is treated as absent.
    """
    if not os.path.isfile(path):
        return False
    text = _read_text(path)
    if text is None:
        return False
    return len(text.encode("utf-8")) != 0


def chain_files(root, cwd=None):
    """Return ordered list of existing, NON-EMPTY CLAUDE.md paths in the chain.

    Order is root first, deepest last. Empty files (0 bytes / no non-empty
    content) are skipped — they add nothing to the always-loaded context.
    """
    result = []
    for directory in _chain_dirs(root, cwd):
        path = os.path.join(directory, DOC_NAME)
        if _is_nonempty_doc(path):
            result.append(path)
    return result


def check(root, cwd=None, budget=DEFAULT_BUDGET, warn_ratio=DEFAULT_WARN_RATIO):
    """Sum the CLAUDE.md chain in BYTES and report budget status.

    Returns a dict with keys:
        chain_files: list[str]   ordered chain paths (non-empty only)
        chain_bytes: int         len(joined.encode("utf-8"))
        budget: int
        over_budget: bool        chain_bytes >= budget
        near_budget: bool        budget*warn_ratio <= chain_bytes < budget
        files: list[{path, bytes}]
    """
    files = chain_files(root, cwd)
    contents = []
    per_file = []
    for path in files:
        text = _read_text(path)
        if text is None:
            text = ""
        nbytes = len(text.encode("utf-8"))
        per_file.append({"path": path, "bytes": nbytes})
        contents.append(text)

    joined = JOIN_SEP.join(contents)
    chain_bytes = len(joined.encode("utf-8"))

    over_budget = chain_bytes >= budget
    near_budget = (budget * warn_ratio) <= chain_bytes < budget

    return {
        "chain_files": files,
        "chain_bytes": chain_bytes,
        "budget": budget,
        "over_budget": over_budget,
        "near_budget": near_budget,
        "files": per_file,
    }


def _build_parser():
    parser = argparse.ArgumentParser(
        prog="size_check.py",
        description="Validate the CLAUDE.md chain against a soft verbosity budget.",
    )
    parser.add_argument("--root", default=".", help="project root (chain top). Default: current dir.")
    parser.add_argument("--cwd", default=None, help="working subdirectory relative to --root (chain bottom).")
    parser.add_argument("--budget", type=int, default=DEFAULT_BUDGET, help="soft byte budget. Default: %d." % DEFAULT_BUDGET)
    parser.add_argument(
        "--warn-ratio",
        type=float,
        default=DEFAULT_WARN_RATIO,
        help="warn when chain_bytes >= budget*ratio. Default: %s." % DEFAULT_WARN_RATIO,
    )
    parser.add_argument("--json", action="store_true", help="emit JSON instead of a human summary.")
    return parser


def _print_human(result):
    budget = result["budget"]
    chain_bytes = result["chain_bytes"]
    print("CLAUDE.md chain: %d file(s), %d bytes (budget %d)" % (len(result["chain_files"]), chain_bytes, budget))
    for entry in result["files"]:
        print("  %8d  %s" % (entry["bytes"], entry["path"]))
    if not result["files"]:
        print("  (no non-empty CLAUDE.md files found)")
    if result["over_budget"]:
        print(
            "ERROR: chain is %d bytes, at or above the %d byte budget. Trim CLAUDE.md to keep the always-loaded layer small."
            % (chain_bytes, budget)
        )
    elif result["near_budget"]:
        print(
            "WARNING: chain is %d bytes, within %.0f%% of the %d byte budget. Trim before it grows further."
            % (chain_bytes, result.get("warn_ratio_pct", 90), budget)
        )
    else:
        print("OK: chain is within budget.")


def main(argv=None):
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        # argparse exits with code 2 on usage error; preserve that contract.
        return 2

    root = args.root
    if not os.path.isdir(root):
        sys.stderr.write("error: --root is not a directory: %s\n" % root)
        return 2

    try:
        result = check(
            root,
            cwd=args.cwd,
            budget=args.budget,
            warn_ratio=args.warn_ratio,
        )
    except ValueError as exc:
        sys.stderr.write("error: %s\n" % exc)
        return 2
    except OSError as exc:
        sys.stderr.write("error: %s\n" % exc)
        return 2

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        result_for_print = dict(result)
        result_for_print["warn_ratio_pct"] = args.warn_ratio * 100
        _print_human(result_for_print)

    return 1 if result["over_budget"] else 0


if __name__ == "__main__":
    sys.exit(main())
