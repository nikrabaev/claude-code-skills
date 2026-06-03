#!/usr/bin/env bash
# validate_markdown.sh — wrap markdownlint-cli2.
#
# BOUNDARY (verified): markdownlint-cli2 checks Markdown SYNTAX/STYLE and
# IN-DOC anchors only (MD051) plus link-defect rules (MD011/034/039/042/052/
# 053/054/059). It does NOT hit the network and does NOT check whether file
# paths exist — use check_links.sh (lychee) for that.
#
# Usage:   validate_markdown.sh [--config FILE] [paths-or-globs ...]   (default: ".")
# Config:  uses the bundled relaxed AI-doc config (markdownlint.jsonc) UNLESS the
#          target repo ships its own .markdownlint* / .markdownlint-cli2* (then that
#          wins), or you pass --config explicitly.
# Exit:    0 clean · 1 lint problems · 2 tool unavailable (skip, not a failure)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v npx >/dev/null 2>&1; then
  echo "skip: 'npx' (Node.js) not found — cannot run markdownlint-cli2." >&2
  echo "      install Node.js, or: npm i -g markdownlint-cli2" >&2
  exit 2
fi

config_arg=()
if [ "${1:-}" = "--config" ]; then
  config_arg=(--config "$2"); shift 2
elif ! ls .markdownlint.json .markdownlint.jsonc .markdownlint.yaml .markdownlint.yml \
        .markdownlint-cli2.jsonc .markdownlint-cli2.yaml .markdownlint-cli2.cjs \
        >/dev/null 2>&1; then
  # No user config in CWD -> apply the bundled relaxed AI-doc config.
  config_arg=(--config "$HERE/markdownlint.jsonc")
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
exec npx -y markdownlint-cli2 "${config_arg[@]+${config_arg[@]}}" "${args[@]}"
