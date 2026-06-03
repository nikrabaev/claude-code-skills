#!/usr/bin/env bash
# check_links.sh — wrap lychee (the link + path checker).
#
# BOUNDARY (verified): lychee checks URLs, local FILE-PATH existence, and URL
# fragments/anchors (--include-fragments). It is the right tool for "does this
# linked path/file actually exist" — markdownlint cannot do that. lychee is a
# Rust binary (NOT an npm package): install via `brew install lychee` or
# `cargo install lychee`.
#
# Usage:   check_links.sh [--offline] [paths-or-globs ...]    (default: ".")
#          --offline skips external HTTP (good for pre-commit); omit it for a
#          full nightly check.
# Exit:    0 clean · 1 broken links/paths · 2 tool unavailable (skip)
set -euo pipefail

if ! command -v lychee >/dev/null 2>&1; then
  echo "skip: 'lychee' not found — cannot check links/paths." >&2
  echo "      install: brew install lychee   (or: cargo install lychee)" >&2
  exit 2
fi

offline=""
if [ "${1:-}" = "--offline" ]; then offline="--offline"; shift; fi
if [ "$#" -eq 0 ]; then set -- "."; fi

exec lychee ${offline:+$offline} --include-fragments "$@"
