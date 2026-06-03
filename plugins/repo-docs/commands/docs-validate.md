---
description: Run the documentation validation gate (line refs, dead paths/symbols, links, Mermaid, duplication, 32 KiB cap)
argument-hint: "[path to validate, default .]"
---

Validate this repo's AI-facing documentation against the full gate.

Run: `bash ${CLAUDE_PLUGIN_ROOT}/scripts/run_gate.sh --root $ARGUMENTS`
(if `$ARGUMENTS` is empty, use `--root .`).

The gate runs, in order: markdown lint → no line refs → paths exist → symbols
exist → links → Mermaid → no duplicated source-of-truth → AGENTS.md chain < 32 KiB.
Report the output verbatim. FAIL blocks; SKIP means that tool isn't installed.
If anything fails, route the fix: repo-docs:stable-refs (line refs / bad refs),
repo-docs:source-of-truth-map (duplication), or repo-docs:compress-docs (over cap).
