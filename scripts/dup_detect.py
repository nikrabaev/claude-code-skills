#!/usr/bin/env python3
"""dup_detect.py - flag docs that paste source-of-truth content.

Principle: "Reference, don't copy." Documentation should point at canonical
files (package.json scripts, config files) instead of pasting their content,
because pasted copies silently go stale.

This validator scans fenced code blocks in Markdown docs and flags blocks that:
  1. paste a meaningful chunk of the root package.json "scripts", or
  2. are highly similar (token-set Jaccard) to a config file's raw content.

Exit codes:
  0 = no duplicated source-of-truth found
  1 = duplication found
  2 = usage / internal error
"""

import argparse
import glob as globmod
import json
import os
import re
import sys

# Fenced code blocks delimited by a line of three backticks. The opening fence
# may carry a language tag (e.g. ```json); we strip it. DOTALL so the body can
# span newlines; non-greedy so consecutive blocks don't merge.
_FENCE_RE = re.compile(r"^```[^\n]*\n(.*?)^```", re.DOTALL | re.MULTILINE)

# Token = run of alphanumerics; everything else is a separator.
_TOKEN_RE = re.compile(r"[a-z0-9]+")


def fenced_blocks(text):
    """Return the inner contents of each ``` fenced code block in ``text``.

    The opening fence's optional language tag is not included. Unterminated
    blocks (no closing fence) are ignored.
    """
    return [m.group(1) for m in _FENCE_RE.finditer(text)]


def package_scripts(root):
    """Return normalized "<name>: <command>" strings from root package.json.

    Returns an empty list if package.json is missing, unreadable, malformed,
    or has no (dict) "scripts" section.
    """
    path = os.path.join(root, "package.json")
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (ValueError, OSError):
        return []
    if not isinstance(data, dict):
        return []
    scripts = data.get("scripts")
    if not isinstance(scripts, dict):
        return []
    out = []
    for name, command in scripts.items():
        out.append("{0}: {1}".format(name, command))
    return out


def tokenize(text):
    """Lowercase ``text`` and return the set of alphanumeric tokens."""
    return set(_TOKEN_RE.findall(text.lower()))


def jaccard(a_tokens, b_tokens):
    """Jaccard similarity of two token sets. Empty/empty is 0.0."""
    a = set(a_tokens)
    b = set(b_tokens)
    if not a and not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return float(len(a & b)) / float(len(union))


def _script_name_and_command(entry):
    """Split a "<name>: <command>" entry back into (name, command)."""
    idx = entry.find(": ")
    if idx == -1:
        return entry, ""
    return entry[:idx], entry[idx + 2:]


def _config_files(root):
    """Canonical config files in ``root`` to compare doc blocks against."""
    candidates = []
    for fixed in ("package.json", "tsconfig.json"):
        path = os.path.join(root, fixed)
        if os.path.isfile(path):
            candidates.append(path)
    # Any *.config.* file in the root directory (e.g. vite.config.ts).
    for path in sorted(globmod.glob(os.path.join(root, "*.config.*"))):
        if os.path.isfile(path) and path not in candidates:
            candidates.append(path)
    return candidates


def _read_text(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


def _count_pasted_scripts(block, scripts):
    """How many script entries appear within ``block``.

    A script counts as present when both its name and its command appear in the
    block (covering the common ``"name": "command"`` paste shape), or when its
    full command string appears verbatim.
    """
    low = block.lower()
    count = 0
    for entry in scripts:
        name, command = _script_name_and_command(entry)
        command = command.strip()
        name_l = name.lower()
        cmd_l = command.lower()
        if command and cmd_l in low and name_l in low:
            count += 1
        elif command and cmd_l in low and len(command) >= 4:
            # Distinctive full command present even without the name nearby.
            count += 1
    return count


def check(root, docs, threshold=0.7):
    """Scan ``docs`` (file paths) and return a list of finding dicts.

    Each finding: {"file", "kind", "source", "detail"}.
    """
    findings = []
    scripts = package_scripts(root)
    total_scripts = len(scripts)
    config_files = _config_files(root)
    config_tokens = [(p, tokenize(_read_text(p))) for p in config_files]

    for doc in docs:
        text = _read_text(doc)
        if not text:
            continue
        for block in fenced_blocks(text):
            flagged_scripts_paste = False
            # Check 1: pasted package.json scripts.
            if total_scripts:
                hits = _count_pasted_scripts(block, scripts)
                if hits >= 3 or (hits / float(total_scripts)) >= 0.5:
                    flagged_scripts_paste = True
                    findings.append({
                        "file": doc,
                        "kind": "pasted-scripts",
                        "source": "package.json",
                        "detail": "{0} of {1} package.json scripts pasted in a "
                                  "code block; reference package.json instead".format(
                                      hits, total_scripts),
                    })

            # Check 2: generic config similarity.
            block_tokens = tokenize(block)
            for path, ctokens in config_tokens:
                # Avoid double-reporting: a block already flagged as a
                # package.json scripts paste shouldn't also be flagged as
                # generic similarity to that same package.json.
                if flagged_scripts_paste and os.path.basename(path) == "package.json":
                    continue
                score = jaccard(block_tokens, ctokens)
                if score >= threshold:
                    findings.append({
                        "file": doc,
                        "kind": "config-duplication",
                        "source": path,
                        "detail": "code block is {0:.0%} similar to {1}; "
                                  "reference it instead of copying".format(
                                      score, os.path.basename(path)),
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


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="dup_detect.py",
        description="Flag docs that paste source-of-truth content "
                    "(package.json scripts, config files).",
    )
    parser.add_argument("--root", default=".", help="repository root (default: .)")
    parser.add_argument("paths", nargs="*", help="doc files or globs (default: all *.md under root)")
    parser.add_argument("--threshold", type=float, default=0.7,
                        help="Jaccard similarity threshold for config duplication (default: 0.7)")
    parser.add_argument("--json", dest="as_json", action="store_true",
                        help="emit findings as a JSON array")

    try:
        args = parser.parse_args(argv)
    except SystemExit:
        # argparse exits 2 on usage error; preserve that contract.
        return 2

    root = args.root
    if not os.path.isdir(root):
        sys.stderr.write("error: root is not a directory: {0}\n".format(root))
        return 2

    try:
        docs = _resolve_docs(root, args.paths)
        findings = check(root, docs, threshold=args.threshold)
    except Exception as exc:  # internal error -> exit 2
        sys.stderr.write("error: {0}\n".format(exc))
        return 2

    if args.as_json:
        sys.stdout.write(json.dumps(findings, indent=2) + "\n")
    else:
        if not findings:
            sys.stdout.write("OK: no duplicated source-of-truth found\n")
        else:
            for f in findings:
                sys.stdout.write(
                    "{file}: [{kind}] {detail} (source: {source})\n".format(**f)
                )

    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
