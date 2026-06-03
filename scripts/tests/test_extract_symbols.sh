#!/usr/bin/env bash
set -euo pipefail

# Test for extract_symbols.sh — forces the ripgrep fallback (--no-ctags)
# for deterministic results across machines.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXTRACT="$SCRIPT_DIR/extract_symbols.sh"

# Robustness: skip cleanly if ripgrep is not installed (fallback can't run).
if ! command -v rg >/dev/null 2>&1; then
  echo "SKIP: ripgrep not installed"
  exit 0
fi

if [ ! -x "$EXTRACT" ]; then
  echo "FAIL: $EXTRACT not found or not executable"
  exit 1
fi

# --- Build fixture ---------------------------------------------------------
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

mkdir -p "$TMP/src"

cat > "$TMP/src/a.ts" <<'EOF'
export function processPayment() {}
export const TAX = 0.2
EOF

# b.py: def charge(): / pass  and  class Wallet: / pass
printf 'def charge():\n    pass\n\nclass Wallet:\n    pass\n' > "$TMP/src/b.py"

# --- Run -------------------------------------------------------------------
OUT="$("$EXTRACT" --root "$TMP" --no-ctags)"

echo "---- extract_symbols.sh output ----" >&2
echo "$OUT" >&2
echo "-----------------------------------" >&2

# --- Assert (parse JSON with python3) --------------------------------------
if printf '%s' "$OUT" | python3 -c '
import json, sys

data = json.load(sys.stdin)

def has(symbol, kind=None, file_suffix=None):
    for e in data:
        if e.get("symbol") != symbol:
            continue
        if kind is not None and e.get("kind") != kind:
            continue
        if file_suffix is not None and not str(e.get("file", "")).endswith(file_suffix):
            continue
        return True
    return False

problems = []
if not has("processPayment", "function", "src/a.ts"):
    problems.append("missing processPayment/function/src/a.ts")
if not has("TAX", "const"):
    problems.append("missing TAX/const")
if not has("charge", "function"):
    problems.append("missing charge/function")
if not has("Wallet", "class"):
    problems.append("missing Wallet/class")

if problems:
    print("ASSERT FAILURES:", file=sys.stderr)
    for p in problems:
        print("  - " + p, file=sys.stderr)
    sys.exit(1)
sys.exit(0)
'; then
  echo "PASS"
  exit 0
else
  echo "FAIL"
  exit 1
fi
