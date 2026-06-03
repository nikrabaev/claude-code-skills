#!/usr/bin/env python3
"""Validate the OpenAI Codex AGENTS.md chain against the project_doc_max_bytes cap.

Codex concatenates the AGENTS.md chain from the git root DOWN to the working
directory, joins file contents with a single blank line ("\\n\\n"), and enforces
a HARD byte cap (project_doc_max_bytes, default 32768 = 32 KiB). It SKIPS EMPTY
files and SILENTLY TRUNCATES any content past the cap.

This script reproduces that chain (root approximated by --root, no git discovery),
sums it in BYTES, and warns BEFORE the cap so the truncation never bites.

Optional Codex scope layers (OFF by default; the default root->cwd AGENTS.md chain
behavior is unchanged):
    --with-overrides  also include each chain directory's AGENTS.override.md
                      precedence layer (appended right after that dir's AGENTS.md).
    --global          also prepend the global ~/.codex/AGENTS.md to the top of the
                      chain when it exists and is non-empty.

Exit codes:
    0  chain under cap (may print a WARNING line if near cap)
    1  chain >= cap (over_cap)
    2  usage / internal error
"""

import argparse
import json
import os
import sys

DEFAULT_CAP = 32768
DEFAULT_WARN_RATIO = 0.9
JOIN_SEP = "\n\n"
DOC_NAME = "AGENTS.md"
OVERRIDE_NAME = "AGENTS.override.md"
GLOBAL_DIR = os.path.expanduser("~/.codex")


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

    Mirrors the Codex empty-file skipping logic: a file that cannot be read or
    has zero bytes is treated as absent.
    """
    if not os.path.isfile(path):
        return False
    text = _read_text(path)
    if text is None:
        return False
    # Codex skips empty files. Treat a file with no bytes as empty.
    return len(text.encode("utf-8")) != 0


def chain_files(root, cwd=None, with_overrides=False, include_global=False):
    """Return ordered list of existing, NON-EMPTY AGENTS.md paths in the chain.

    Order is root first, deepest last. Empty files (0 bytes / no non-empty
    content) are skipped to match Codex behavior.

    Optional Codex scope layers (OFF by default; default chain is unchanged):
        include_global   when set, PREPEND the global ~/.codex/AGENTS.md to the
                         top of the chain if it exists and is non-empty.
        with_overrides   when set, for each chain directory append that dir's
                         AGENTS.override.md (right after its AGENTS.md) if it
                         exists and is non-empty.
    """
    result = []
    if include_global:
        global_path = os.path.join(GLOBAL_DIR, DOC_NAME)
        if _is_nonempty_doc(global_path):
            result.append(global_path)
    for directory in _chain_dirs(root, cwd):
        path = os.path.join(directory, DOC_NAME)
        if _is_nonempty_doc(path):
            result.append(path)
        if with_overrides:
            override_path = os.path.join(directory, OVERRIDE_NAME)
            if _is_nonempty_doc(override_path):
                result.append(override_path)
    return result


def check(root, cwd=None, cap=DEFAULT_CAP, warn_ratio=DEFAULT_WARN_RATIO,
          with_overrides=False, include_global=False):
    """Sum the AGENTS.md chain in BYTES and report cap status.

    Returns a dict with keys:
        chain_files: list[str]   ordered chain paths (non-empty only)
        chain_bytes: int         len(joined.encode("utf-8"))
        cap: int
        over_cap: bool           chain_bytes >= cap
        near_cap: bool           cap*warn_ratio <= chain_bytes < cap
        files: list[{path, bytes}]

    with_overrides / include_global enable the optional Codex scope layers (see
    chain_files); both default OFF so the default chain behavior is unchanged.
    """
    files = chain_files(root, cwd, with_overrides=with_overrides, include_global=include_global)
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

    over_cap = chain_bytes >= cap
    near_cap = (cap * warn_ratio) <= chain_bytes < cap

    return {
        "chain_files": files,
        "chain_bytes": chain_bytes,
        "cap": cap,
        "over_cap": over_cap,
        "near_cap": near_cap,
        "files": per_file,
    }


def _build_parser():
    parser = argparse.ArgumentParser(
        prog="size_check.py",
        description="Validate the AGENTS.md chain against Codex's project_doc_max_bytes cap.",
    )
    parser.add_argument("--root", default=".", help="git/project root (chain top). Default: current dir.")
    parser.add_argument("--cwd", default=None, help="working subdirectory relative to --root (chain bottom).")
    parser.add_argument("--cap", type=int, default=DEFAULT_CAP, help="hard byte cap. Default: %d." % DEFAULT_CAP)
    parser.add_argument(
        "--warn-ratio",
        type=float,
        default=DEFAULT_WARN_RATIO,
        help="warn when chain_bytes >= cap*ratio. Default: %s." % DEFAULT_WARN_RATIO,
    )
    parser.add_argument("--json", action="store_true", help="emit JSON instead of a human summary.")
    parser.add_argument(
        "--with-overrides",
        action="store_true",
        help="also include each chain dir's AGENTS.override.md precedence layer (off by default).",
    )
    parser.add_argument(
        "--global",
        dest="include_global",
        action="store_true",
        help="also prepend the global ~/.codex/AGENTS.md to the chain (off by default).",
    )
    return parser


def _print_human(result):
    cap = result["cap"]
    chain_bytes = result["chain_bytes"]
    print("AGENTS.md chain: %d file(s), %d bytes (cap %d)" % (len(result["chain_files"]), chain_bytes, cap))
    for entry in result["files"]:
        print("  %8d  %s" % (entry["bytes"], entry["path"]))
    if not result["files"]:
        print("  (no non-empty AGENTS.md files found)")
    if result["over_cap"]:
        print(
            "ERROR: chain is %d bytes, at or above the %d byte cap. Codex will SILENTLY TRUNCATE."
            % (chain_bytes, cap)
        )
    elif result["near_cap"]:
        print(
            "WARNING: chain is %d bytes, within %.0f%% of the %d byte cap. Trim before it truncates."
            % (chain_bytes, result.get("warn_ratio_pct", 90), cap)
        )
    else:
        print("OK: chain is under the cap.")


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
            cap=args.cap,
            warn_ratio=args.warn_ratio,
            with_overrides=args.with_overrides,
            include_global=args.include_global,
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

    return 1 if result["over_cap"] else 0


if __name__ == "__main__":
    sys.exit(main())
