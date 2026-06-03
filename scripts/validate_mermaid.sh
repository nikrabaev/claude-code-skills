#!/usr/bin/env bash
# validate_mermaid.sh — wrap @probelabs/maid (the browserless Mermaid validator).
#
# BOUNDARY (verified): maid actively validates flowchart/graph, sequenceDiagram,
# classDiagram, stateDiagram-v2, and pie. OTHER diagram types pass through
# UNVALIDATED — do not commit those unless render-tested. maid's "render
# guarantee": when it says valid, the diagram renders (for the five types).
# It does NOT catch GitHub-specific issues like `click` directives (blocked by
# GitHub CSP) — keep diagrams free of interactive links by hand.
#
# Usage:   validate_mermaid.sh [--fix] [paths-or-globs ...]   (default: ".")
# Exit:    0 valid · 1 diagram error · 2 tool unavailable (skip, not a failure)
set -euo pipefail

if ! command -v npx >/dev/null 2>&1; then
  echo "skip: 'npx' (Node.js) not found — cannot run @probelabs/maid." >&2
  echo "      install Node.js, or: npm i -g @probelabs/maid" >&2
  exit 2
fi

fix=""
if [ "${1:-}" = "--fix" ]; then fix="--fix"; shift; fi
if [ "$#" -eq 0 ]; then set -- "."; fi

# --format json keeps output machine-readable for the gate; warnings do not fail.
exec npx -y @probelabs/maid --format json ${fix:+$fix} "$@"
