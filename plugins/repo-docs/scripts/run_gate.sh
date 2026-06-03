#!/usr/bin/env bash
# run_gate.sh — the documentation validation gate (DESIGN.md §12), composed.
#
# Point this at a TARGET repo's generated AI docs (AGENTS.md/CLAUDE.md/docs). It
# validates existence claims (paths, symbols, links) against that repo's real
# source, so running it against this plugin's own teaching docs (references/,
# examples/, checklists/) WILL report false "dead path" findings — those cite
# illustrative paths on purpose. The gate is for generated docs, not meta-docs.
#
# Runs every check in order. Each step is classified by its exit code:
#   0      -> PASS
#   2      -> SKIP (the external tool or symbol index is unavailable; reported,
#             NOT counted as a failure — so the gate still runs without
#             markdownlint/maid/lychee/ctags installed)
#   other  -> FAIL (a real violation; BLOCKS — the gate exits non-zero)
#
# Order: validate_markdown -> no_line_refs -> path_exists -> symbol_exists ->
#        check_links -> validate_mermaid -> dup_detect -> size_check
#
# After the blocking steps, two ADVISORY steps run (score_docs, conflict_scan).
# They REPORT only — their output is always printed but never changes the gate's
# exit code (score_docs is a proxy, never the sole gate; conflict_scan is low-FP
# but still advisory). The blocking set above is unchanged.
#
# Usage:   run_gate.sh [--root DIR] [--cwd SUBDIR] [doc-paths ...]
#          --root   project root (default: .)
#          --cwd    deepest AGENTS.md dir for the Codex chain (size_check)
#          paths    explicit docs to lint/validate (default: the root tree)
# Exit:    0 all blocking checks passed · 1 one or more blocking checks failed
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Per-run scratch file for step output (avoid a fixed /tmp path that could collide
# across concurrent runs or be pre-created as a hostile symlink).
GATE_OUT="$(mktemp "${TMPDIR:-/tmp}/repo-docs-gate.XXXXXX")"
trap 'rm -f "$GATE_OUT"' EXIT

ROOT="."
CWD=""
PATHS=()
while [ "$#" -gt 0 ]; do
  case "$1" in
    --root) ROOT="$2"; shift 2 ;;
    --cwd)  CWD="$2"; shift 2 ;;
    --) shift; while [ "$#" -gt 0 ]; do PATHS+=("$1"); shift; done ;;
    *) PATHS+=("$1"); shift ;;
  esac
done

errors=0
skips=0
passes=0

# run_step "Label" command [args...]
run_step() {
  local label="$1"; shift
  local rc=0
  "$@" >"$GATE_OUT" 2>&1 || rc=$?
  if [ "$rc" -eq 0 ]; then
    printf '  \033[32mPASS\033[0m  %s\n' "$label"
    passes=$((passes + 1))
  elif [ "$rc" -eq 2 ]; then
    printf '  \033[33mSKIP\033[0m  %s\n' "$label"
    sed 's/^/        /' "$GATE_OUT"
    skips=$((skips + 1))
  else
    printf '  \033[31mFAIL\033[0m  %s\n' "$label"
    sed 's/^/        /' "$GATE_OUT"
    errors=$((errors + 1))
  fi
}

# run_advisory "Label" command [args...] — always prints its output; never
# affects the pass/skip/fail counters. Advisory checks (score_docs, conflict_scan)
# REPORT; they must never block the gate.
run_advisory() {
  local label="$1"; shift
  local rc=0
  "$@" >"$GATE_OUT" 2>&1 || rc=$?
  printf '  \033[36mNOTE\033[0m  %s\n' "$label"
  sed 's/^/        /' "$GATE_OUT"
}

echo "Documentation gate — root: $ROOT"
echo

# Markdown lint / Mermaid / links operate on file paths.
md_targets=("$ROOT")
if [ "${#PATHS[@]}" -gt 0 ]; then md_targets=("${PATHS[@]}"); fi

run_step "markdown lint (markdownlint-cli2)" \
  bash "$HERE/validate_markdown.sh" "${md_targets[@]}"

run_step "no line-number references" \
  python3 "$HERE/no_line_refs.py" --root "$ROOT" "${PATHS[@]+${PATHS[@]}}"

run_step "referenced paths exist" \
  python3 "$HERE/path_exists.py" --root "$ROOT" "${PATHS[@]+${PATHS[@]}}"

run_step "referenced symbols exist" \
  python3 "$HERE/symbol_exists.py" --root "$ROOT" "${PATHS[@]+${PATHS[@]}}"

run_step "links/paths resolve (lychee, offline)" \
  bash "$HERE/check_links.sh" --offline "${md_targets[@]}"

run_step "Mermaid diagrams valid (maid)" \
  bash "$HERE/validate_mermaid.sh" "${md_targets[@]}"

run_step "no duplicated source-of-truth" \
  python3 "$HERE/dup_detect.py" --root "$ROOT" "${PATHS[@]+${PATHS[@]}}"

if [ -n "$CWD" ]; then
  run_step "AGENTS.md chain < 32 KiB (Codex cap)" \
    python3 "$HERE/size_check.py" --root "$ROOT" --cwd "$CWD"
else
  run_step "AGENTS.md chain < 32 KiB (Codex cap)" \
    python3 "$HERE/size_check.py" --root "$ROOT"
fi

echo
echo "Advisory (report-only — never blocks):"
run_advisory "doc quality score (score_docs)" \
  python3 "$HERE/score_docs.py" --root "$ROOT" "${PATHS[@]+${PATHS[@]}}"
run_advisory "rule conflicts (conflict_scan)" \
  python3 "$HERE/conflict_scan.py" --root "$ROOT" "${PATHS[@]+${PATHS[@]}}"

echo
echo "Gate summary: $passes passed, $skips skipped (tool/index absent), $errors failed."
if [ "$errors" -gt 0 ]; then
  echo "RESULT: BLOCKED — fix the failing checks above before claiming done."
  exit 1
fi
echo "RESULT: PASS"
exit 0
