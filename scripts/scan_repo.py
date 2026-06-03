#!/usr/bin/env python3
"""Scan a repository and report languages, manifests, stack, and structure.

Python 3 standard library only. Targets Python 3.9.6.
"""
from __future__ import annotations

import argparse
import json
import os
import re

# Directory names pruned during the walk.
IGNORE_DIRS = frozenset(
    [
        ".git",
        "node_modules",
        "dist",
        "build",
        ".venv",
        "venv",
        "__pycache__",
        "vendor",
        "target",
        ".next",
        "coverage",
        ".mypy_cache",
    ]
)

# File extension -> language name.
EXT_TO_LANG = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".java": "java",
    ".sh": "shell",
    ".md": "markdown",
}

# Manifest filenames detected anywhere in the tree.
MANIFEST_NAMES = frozenset(
    [
        "package.json",
        "pyproject.toml",
        "setup.py",
        "Cargo.toml",
        "go.mod",
        "Gemfile",
        "pom.xml",
        "requirements.txt",
        "Makefile",
        "justfile",
        "Taskfile.yml",
    ]
)

# Candidate entry-point paths checked for existence (relative to root).
ENTRY_CANDIDATES = [
    "src/index.ts",
    "src/index.js",
    "main.py",
    "src/main.rs",
    "cmd",
]

MAX_DEPTH = 8

_CARGO_DEP_RE = re.compile(r"^\s*([A-Za-z_][\w-]*)\s*=\s*(.*)$")
_GOMOD_LINE_RE = re.compile(r"^\s*([^\s]+)\s+(v[^\s]+)")


def _rel(root, path):
    """Return a normalized relative path from root."""
    return os.path.relpath(path, root).replace(os.sep, "/")


def _depth(root, current):
    """Return directory depth of current relative to root (root == 0)."""
    rel = os.path.relpath(current, root)
    if rel == ".":
        return 0
    return rel.count(os.sep) + 1


def _read_text(path):
    """Best-effort text read; returns '' on failure."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except (OSError, UnicodeError):
        return ""


def _load_json(path):
    """Best-effort JSON load; returns {} on failure."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def parse_package_json_stack(path):
    """Return stack entries from a package.json's deps and devDeps."""
    data = _load_json(path)
    out = []
    for key in ("dependencies", "devDependencies"):
        deps = data.get(key)
        if isinstance(deps, dict):
            for name, version in deps.items():
                out.append(
                    {
                        "name": str(name),
                        "version": str(version),
                        "source": "package.json",
                    }
                )
    return out


def parse_cargo_stack(path):
    """Return stack entries from a Cargo.toml [dependencies] section."""
    text = _read_text(path)
    out = []
    in_deps = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            in_deps = section == "dependencies"
            continue
        if not in_deps or not line or line.startswith("#"):
            continue
        m = _CARGO_DEP_RE.match(line)
        if not m:
            continue
        name = m.group(1)
        rest = m.group(2).strip()
        version = rest
        # Plain quoted version, e.g. serde = "1.0".
        if rest.startswith('"') and rest.endswith('"') and len(rest) >= 2:
            version = rest[1:-1]
        else:
            # Table form, e.g. serde = { version = "1.0", ... }.
            vm = re.search(r'version\s*=\s*"([^"]*)"', rest)
            if vm:
                version = vm.group(1)
        out.append({"name": name, "version": version, "source": "Cargo.toml"})
    return out


def parse_gomod_stack(path):
    """Return stack entries from a go.mod's require directives."""
    text = _read_text(path)
    out = []
    in_block = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("//"):
            continue
        if in_block:
            if line.startswith(")"):
                in_block = False
                continue
            _add_gomod_require(out, line)
            continue
        if line.startswith("require ("):
            in_block = True
            continue
        if line.startswith("require "):
            _add_gomod_require(out, line[len("require "):].strip())
    return out


def _add_gomod_require(out, spec):
    """Append a parsed go.mod require entry from a single spec line."""
    # Drop a trailing comment.
    spec = spec.split("//", 1)[0].strip()
    if not spec:
        return
    m = _GOMOD_LINE_RE.match(spec)
    if m:
        out.append(
            {"name": m.group(1), "version": m.group(2), "source": "go.mod"}
        )
        return
    parts = spec.split()
    if len(parts) >= 2:
        out.append(
            {"name": parts[0], "version": parts[1], "source": "go.mod"}
        )


def _workspace_globs(pkg_data):
    """Extract workspace glob patterns from a parsed package.json dict."""
    ws = pkg_data.get("workspaces")
    if isinstance(ws, list):
        return [g for g in ws if isinstance(g, str)]
    if isinstance(ws, dict):
        pkgs = ws.get("packages")
        if isinstance(pkgs, list):
            return [g for g in pkgs if isinstance(g, str)]
    return []


def _subdirs_for_glob(root, glob):
    """Resolve a simple workspace glob to immediate subdir names.

    Supports 'prefix/*' and bare 'prefix' forms; best-effort.
    """
    names = []
    if glob.endswith("/*"):
        base = glob[:-2]
    elif glob.endswith("*"):
        base = glob[:-1].rstrip("/")
    else:
        base = glob
    base_dir = os.path.join(root, base) if base else root
    if not os.path.isdir(base_dir):
        return names
    for entry in sorted(os.listdir(base_dir)):
        if entry in IGNORE_DIRS:
            continue
        if os.path.isdir(os.path.join(base_dir, entry)):
            names.append(entry)
    return names


def detect_monorepo_packages(root):
    """Return immediate monorepo package subdir names (best-effort)."""
    names = []

    pkg_path = os.path.join(root, "package.json")
    if os.path.isfile(pkg_path):
        globs = _workspace_globs(_load_json(pkg_path))
        for glob in globs:
            names.extend(_subdirs_for_glob(root, glob))

    has_pnpm = os.path.isfile(os.path.join(root, "pnpm-workspace.yaml"))
    has_lerna = os.path.isfile(os.path.join(root, "lerna.json"))
    packages_dir = os.path.join(root, "packages")
    has_packages = os.path.isdir(packages_dir)

    if (has_pnpm or has_lerna or has_packages) and os.path.isdir(packages_dir):
        for entry in sorted(os.listdir(packages_dir)):
            if entry in IGNORE_DIRS:
                continue
            if os.path.isdir(os.path.join(packages_dir, entry)):
                names.append(entry)

    # De-duplicate while preserving order.
    seen = set()
    unique = []
    for name in names:
        if name not in seen:
            seen.add(name)
            unique.append(name)
    return unique


def detect_entry_points(root):
    """Return entry points from root package.json plus known file paths."""
    entries = []

    pkg_path = os.path.join(root, "package.json")
    if os.path.isfile(pkg_path):
        data = _load_json(pkg_path)
        main = data.get("main")
        if isinstance(main, str) and main:
            entries.append(main)
        bin_field = data.get("bin")
        if isinstance(bin_field, str) and bin_field:
            entries.append(bin_field)
        elif isinstance(bin_field, dict):
            for value in bin_field.values():
                if isinstance(value, str) and value:
                    entries.append(value)

    for candidate in ENTRY_CANDIDATES:
        if os.path.exists(os.path.join(root, candidate)):
            entries.append(candidate)

    seen = set()
    unique = []
    for entry in entries:
        if entry not in seen:
            seen.add(entry)
            unique.append(entry)
    return unique


def scan(root):
    """Scan a repository tree and return a structured summary dict."""
    root = os.path.abspath(root)

    languages = {}
    top_dirs = []
    manifests = []
    stack = []

    for dirpath, dirnames, filenames in os.walk(root):
        # Capture immediate child directories of root (post-prune).
        if os.path.abspath(dirpath) == root:
            top_dirs = sorted(
                d for d in dirnames if d not in IGNORE_DIRS
            )

        # Prune ignored directories in place.
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]

        # Enforce depth cap: do not descend past MAX_DEPTH.
        if _depth(root, dirpath) >= MAX_DEPTH:
            dirnames[:] = []

        for fname in filenames:
            ext = os.path.splitext(fname)[1].lower()
            lang = EXT_TO_LANG.get(ext)
            if lang:
                languages[lang] = languages.get(lang, 0) + 1

            if fname in MANIFEST_NAMES:
                fpath = os.path.join(dirpath, fname)
                manifests.append({"type": fname, "path": _rel(root, fpath)})

    # Root-priority ordering for manifests: root-level first, then by path.
    manifests.sort(key=lambda m: (m["path"].count("/"), m["path"]))

    # Stack parsing per manifest type.
    for m in manifests:
        full = os.path.join(root, m["path"])
        if m["type"] == "package.json":
            stack.extend(parse_package_json_stack(full))
        elif m["type"] == "Cargo.toml":
            stack.extend(parse_cargo_stack(full))
        elif m["type"] == "go.mod":
            stack.extend(parse_gomod_stack(full))

    return {
        "root": root,
        "languages": languages,
        "top_dirs": top_dirs,
        "manifests": manifests,
        "stack": stack,
        "monorepo_packages": detect_monorepo_packages(root),
        "entry_points": detect_entry_points(root),
    }


def _format_summary(result):
    """Return a short human-readable summary string."""
    lines = []
    lines.append("Repository: %s" % result["root"])

    langs = result["languages"]
    if langs:
        parts = ", ".join(
            "%s=%d" % (k, langs[k]) for k in sorted(langs)
        )
        lines.append("Languages: %s" % parts)
    else:
        lines.append("Languages: (none detected)")

    lines.append("Top dirs: %s" % (", ".join(result["top_dirs"]) or "(none)"))
    lines.append("Manifests: %d" % len(result["manifests"]))
    lines.append("Stack deps: %d" % len(result["stack"]))

    if result["monorepo_packages"]:
        lines.append(
            "Monorepo packages: %s"
            % ", ".join(result["monorepo_packages"])
        )
    if result["entry_points"]:
        lines.append(
            "Entry points: %s" % ", ".join(result["entry_points"])
        )
    return "\n".join(lines)


def main(argv=None):
    """CLI entry point. Returns 0 on success, 2 on usage/internal error."""
    parser = argparse.ArgumentParser(
        description="Scan a repository for languages, manifests, and stack."
    )
    parser.add_argument("--root", default=None, help="Root directory to scan.")
    parser.add_argument(
        "--json", action="store_true", help="Emit JSON instead of a summary."
    )

    try:
        args = parser.parse_args(argv)
    except SystemExit:
        # argparse exits with code 2 on bad usage; normalize to our contract.
        return 2

    root = args.root if args.root is not None else os.getcwd()
    if not os.path.isdir(root):
        import sys as _sys

        _sys.stderr.write("error: not a directory: %s\n" % root)
        return 2

    try:
        result = scan(root)
    except Exception as exc:  # noqa: BLE001 - report any internal failure as code 2
        import sys as _sys

        _sys.stderr.write("error: %s\n" % exc)
        return 2

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(_format_summary(result))
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
