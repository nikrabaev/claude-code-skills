#!/usr/bin/env bash
# validate_markdown.sh — wrap markdownlint-cli2.
#
# BOUNDARY (verified): markdownlint-cli2 checks Markdown SYNTAX/STYLE and
# IN-DOC anchors only (MD051) plus link-defect rules (MD011/034/039/042/052/
# 053/054/059). It does NOT hit the network and does NOT check whether file
# paths exist — use check_links.sh (lychee) for that.
#
# Usage:   validate_markdown.sh [paths-or-globs ...]      (default: ".")
# Exit:    0 clean · 1 lint problems · 2 tool unavailable (skip, not a failure)
set -euo pipefail

if ! command -v npx >/dev/null 2>&1; then
  echo "skip: 'npx' (Node.js) not found — cannot run markdownlint-cli2." >&2
  echo "      install Node.js, or: npm i -g markdownlint-cli2" >&2
  exit 2
fi

if [ "$#" -eq 0 ]; then set -- "."; fi

# markdownlint-cli2 takes GLOBS, not bare directories. Expand any directory
# argument to "<dir>/**/*.md" so we never lint non-Markdown files (a bare dir
# arg makes it pick up .ts/.json/etc. and emit bogus MD041 errors).
args=()
for a in "$@"; do
  if [ -d "$a" ]; then
    args+=("${a%/}/**/*.md")
  else
    args+=("$a")
  fi
done

# npx -y fetches markdownlint-cli2 on demand if it is not already installed.
exec npx -y markdownlint-cli2 "${args[@]}"
