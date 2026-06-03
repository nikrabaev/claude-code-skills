---
name: docs-drift-review
description: >
  Detect stale documentation — references whose target path or symbol no longer
  exists, and docs older than the code they reference (git mtime) — and report them
  as advisory findings to triage. Use when asked whether the docs are out of date,
  drifting, or still match the code.
---

# Docs drift review (advisory)

**Core principle:** drift is the dominant long-term doc failure, and it is
detectable. This review **reports**; it does not auto-edit. Findings are **advisory**
(git mtime ≠ semantic staleness) — triage them, don't blindly rewrite.

`${CLAUDE_PLUGIN_ROOT}` is the plugin root.

## Workflow

### 1. Run the drift check

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/drift_check.py --root . docs/ AGENTS.md
```

It surfaces three finding kinds:

- **dead-path** — a backticked path in a doc no longer resolves.
- **dead-symbol** — a `` `symbol()` in `file` `` reference is gone (uses the
  `extract_symbols.sh` index; skips gracefully if the index is unavailable).
- **stale-vs-code** — a source file the doc references is newer than the doc (git
  commit time, falling back to filesystem mtime).

It is **advisory**: default exit 0 even with findings. Pass `--strict` to make it
exit 1 (for gating in CI) and `--json` for machine-readable output.

### 2. Triage each finding

- **dead-path / dead-symbol** → the reference rotted. Fix it via
  `REQUIRED SUB-SKILL: repo-docs:stable-refs` (rewrite to the current path+symbol), or
  remove the claim if the thing is gone.
- **stale-vs-code** → re-read the referenced code; if the doc's described shape still
  holds, it's a false positive (note it); if not, refresh the doc (route a rewrite to
  the matching generator, e.g. `repo-docs:generate-architecture-doc`).

### 3. Report

Summarize: counts by kind, which are real vs. false positives, and the fix routed for
each real one. This skill ends with the report — it does not silently edit docs.

## Notes

- For CI, wire `drift_check.py` as a **non-blocking** step (`continue-on-error: true`)
  — see `${CLAUDE_PLUGIN_ROOT}/references/ci-workflow.md`. Use `--strict` only if a
  team decides drift should block a merge.
- The hard gate (`run_gate.sh`) already blocks on dead paths/symbols at generation
  time; this review is for docs that drifted *after* they were written.
