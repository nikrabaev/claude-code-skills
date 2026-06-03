#!/usr/bin/env bash
set -euo pipefail

# extract_symbols.sh — emit a repository symbol index as JSON to stdout.
#
# Output contract (FIXED — another script depends on it exactly):
#   [{"symbol":"<name>","kind":"<function|class|method|const|...>","file":"<relpath-from-root>"}, ...]
#
# Usage: extract_symbols.sh [--root DIR] [--no-ctags]
#   --root DIR    root directory to scan (default: ".")
#   --no-ctags    skip Universal Ctags even if installed (force rg fallback)
#
# Notes go to stderr; ONLY the JSON array goes to stdout. Always exits 0 on success.

ROOT="."
USE_CTAGS=1

while [ "$#" -gt 0 ]; do
  case "$1" in
    --root)
      shift
      [ "$#" -gt 0 ] || { echo "extract_symbols.sh: --root requires an argument" >&2; exit 2; }
      ROOT="$1"
      ;;
    --no-ctags)
      USE_CTAGS=0
      ;;
    -h|--help)
      echo "Usage: extract_symbols.sh [--root DIR] [--no-ctags]" >&2
      exit 0
      ;;
    *)
      echo "extract_symbols.sh: unknown argument: $1" >&2
      exit 2
      ;;
  esac
  shift
done

if [ ! -d "$ROOT" ]; then
  echo "extract_symbols.sh: root is not a directory: $ROOT" >&2
  exit 2
fi

# Normalize root to an absolute path (so we can compute relative paths reliably).
ROOT_ABS="$(cd "$ROOT" && pwd)"

# ---------------------------------------------------------------------------
# Python helper: read TAB-separated "symbol<TAB>kind<TAB>file" lines from stdin
# and print a JSON array. Handles all JSON string escaping safely.
# ---------------------------------------------------------------------------
emit_json_from_tsv() {
  python3 -c '
import json, sys

out = []
for line in sys.stdin:
    line = line.rstrip("\n")
    if not line:
        continue
    parts = line.split("\t")
    if len(parts) < 3:
        continue
    symbol, kind, path = parts[0], parts[1], parts[2]
    if not symbol:
        continue
    out.append({"symbol": symbol, "kind": kind, "file": path})

json.dump(out, sys.stdout, separators=(",", ":"))
sys.stdout.write("\n")
'
}

# ---------------------------------------------------------------------------
# Python helper: parse Universal Ctags JSON-lines from stdin, map fields,
# and rewrite "path" relative to root, then print the final JSON array.
# ---------------------------------------------------------------------------
emit_json_from_ctags() {
  # $1 = root absolute path
  python3 -c '
import json, os, sys

root = sys.argv[1]
out = []
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        continue
    # ctags json emits objects with _type == "tag" for tags.
    if obj.get("_type") != "tag":
        continue
    name = obj.get("name")
    kind = obj.get("kind", "")
    path = obj.get("path", "")
    if not name or not path:
        continue
    # Make path relative to root.
    try:
        rel = os.path.relpath(path, root)
    except ValueError:
        rel = path
    out.append({"symbol": name, "kind": kind, "file": rel})

json.dump(out, sys.stdout, separators=(",", ":"))
sys.stdout.write("\n")
' "$1"
}

# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------
have_universal_ctags() {
  command -v ctags >/dev/null 2>&1 || return 1
  ctags --version 2>/dev/null | grep -qi 'universal ctags'
}

have_rg() {
  command -v rg >/dev/null 2>&1
}

# ---------------------------------------------------------------------------
# Path 1: Universal Ctags
# ---------------------------------------------------------------------------
if [ "$USE_CTAGS" -eq 1 ] && have_universal_ctags; then
  echo "extract_symbols.sh: using Universal Ctags" >&2
  # Languages limited to the set we care about; ctags ignores unknown ones gracefully.
  if ctags -R -f - \
      --output-format=json \
      --languages=JavaScript,TypeScript,Python,Go \
      "$ROOT_ABS" 2>/dev/null | emit_json_from_ctags "$ROOT_ABS"; then
    exit 0
  fi
  # If ctags somehow failed, fall through to rg below.
  echo "extract_symbols.sh: ctags run failed; falling back to ripgrep" >&2
fi

# ---------------------------------------------------------------------------
# Path 2: ripgrep fallback
# ---------------------------------------------------------------------------
if have_rg; then
  echo "extract_symbols.sh: using ripgrep fallback" >&2

  # We run rg once per (pattern, kind) so we can attach the correct kind.
  # rg prints "<file>:<match>" with --with-filename and -o (no line numbers).
  # We capture the symbol via a separate -r replacement run is not used;
  # instead we re-extract the symbol name with the pattern's capture group
  # by post-processing in awk-free fashion: use rg's -r to print just the
  # filename + captured name.
  #
  # Approach: for each pattern, run rg twice is wasteful — instead use
  # `rg --with-filename -o -r '$1'` so the matched output is replaced by the
  # captured symbol name. Output lines look like: <relfile>:<symbol>.
  #
  # We cd into ROOT_ABS so rg prints paths relative to root.

  run_pattern() {
    # $1 = PCRE2 pattern with one capture group for the symbol
    # $2 = kind
    local pattern="$1" kind="$2"
    local matches=""
    # rg exits 1 when there are no matches; tolerate that so set -e/pipefail
    # do not abort the script. Capture matches first, then format them.
    matches="$(rg --no-heading --no-line-number --with-filename \
                  --pcre2 -o -r '$1' "$pattern" "." 2>/dev/null || true)"
    [ -n "$matches" ] || return 0
    printf '%s\n' "$matches" | while IFS= read -r line; do
      [ -n "$line" ] || continue
      # line is "<relfile>:<symbol>" — split on the LAST colon. Symbol names
      # are \w+ so they never contain a colon; filenames may.
      local file="${line%:*}"
      local symbol="${line##*:}"
      [ -n "$symbol" ] || continue
      printf '%s\t%s\t%s\n' "$symbol" "$kind" "$file"
    done
    return 0
  }

  {
    cd "$ROOT_ABS"
    run_pattern 'export\s+(?:async\s+)?function\s+(\w+)' 'function'
    run_pattern 'export\s+const\s+(\w+)'                 'const'
    run_pattern '^\s*def\s+(\w+)'                        'function'
    run_pattern '^\s*class\s+(\w+)'                      'class'
    run_pattern '^\s*func\s+(\w+)'                       'function'
    true
  } | emit_json_from_tsv

  exit 0
fi

# ---------------------------------------------------------------------------
# Path 3: neither tool available
# ---------------------------------------------------------------------------
echo "extract_symbols.sh: neither Universal Ctags nor ripgrep is available; emitting empty index" >&2
printf '[]\n'
exit 0
