#!/usr/bin/env python3
"""Extract runnable script/task definitions from common project manifests.

Supported sources: package.json, Makefile, justfile, Taskfile.yml.
Stdlib only; targets Python 3.9.6.
"""
from __future__ import annotations

import argparse
import json
import os
import re


def _read(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


def _from_package_json(path):
    raw = _read(path)
    if raw is None:
        return []
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return []
    if not isinstance(data, dict):
        return []
    scripts = data.get("scripts")
    if not isinstance(scripts, dict):
        return []
    out = []
    for name, command in scripts.items():
        out.append({
            "source": "package.json",
            "name": str(name),
            "command": "" if command is None else str(command),
        })
    return out


_MAKE_TARGET = re.compile(r"^([A-Za-z0-9_.\-]+):")


def _from_makefile(path):
    raw = _read(path)
    if raw is None:
        return []
    lines = raw.splitlines()
    out = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        match = _MAKE_TARGET.match(line)
        if match:
            name = match.group(1)
            # Skip pattern rules and dotted/special targets like .PHONY.
            if name.startswith(".") or "%" in name:
                i += 1
                continue
            command = ""
            if i + 1 < n and lines[i + 1].startswith("\t"):
                command = lines[i + 1].strip()
            out.append({"source": "Makefile", "name": name, "command": command})
        i += 1
    return out


_JUST_HEADER = re.compile(r"^([a-z0-9_\-]+)(\s+[^:]*)?:")


def _from_justfile(path):
    raw = _read(path)
    if raw is None:
        return []
    lines = raw.splitlines()
    out = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        match = _JUST_HEADER.match(line)
        if match:
            name = match.group(1)
            command = ""
            if i + 1 < n:
                body = lines[i + 1]
                if body[:1] in (" ", "\t") and body.strip():
                    command = body.strip()
            out.append({"source": "justfile", "name": name, "command": command})
        i += 1
    return out


_TASK_KEY = re.compile(r"^  ([A-Za-z0-9_\-]+):")


def _from_taskfile(path):
    raw = _read(path)
    if raw is None:
        return []
    lines = raw.splitlines()
    out = []
    in_tasks = False
    for line in lines:
        stripped = line.strip()
        if not line.startswith(" ") and stripped == "tasks:":
            in_tasks = True
            continue
        if in_tasks:
            # A new top-level (column 0, non-blank) key ends the tasks block.
            if line and not line.startswith(" ") and stripped:
                in_tasks = False
                continue
            match = _TASK_KEY.match(line)
            if match:
                out.append({
                    "source": "Taskfile.yml",
                    "name": match.group(1),
                    "command": "",
                })
    return out


_SOURCES = (
    ("package.json", _from_package_json),
    ("Makefile", _from_makefile),
    ("justfile", _from_justfile),
    ("Taskfile.yml", _from_taskfile),
)


def extract(root):
    """Return a JSON-able list of {source, name, command} dicts.

    Dedups by (source, name). Returns [] when no manifests are present.
    """
    out = []
    seen = set()
    for filename, parser in _SOURCES:
        path = os.path.join(root, filename)
        if not os.path.isfile(path):
            continue
        for entry in parser(path):
            key = (entry["source"], entry["name"])
            if key in seen:
                continue
            seen.add(key)
            out.append(entry)
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Extract script/task definitions from project manifests."
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
        entries = extract(root)
    except Exception as exc:  # pragma: no cover - defensive
        print("error: {0}".format(exc), file=__import__("sys").stderr)
        return 2

    if args.json:
        print(json.dumps(entries))
    else:
        for entry in entries:
            print("{0}\t{1}\t{2}".format(entry["source"], entry["name"], entry["command"]))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
