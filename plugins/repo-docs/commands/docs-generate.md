---
description: Generate the canonical CLAUDE.md for this repo (evidence-gated, within a verbosity budget)
argument-hint: "[claude-md | doc type]"
---

Generate AI-facing documentation for this repository.

REQUIRED SUB-SKILL: repo-docs:generate-agent-instructions

Target: $ARGUMENTS (default: the canonical `CLAUDE.md`). Inspect the repo first
with the read-only scanners — do not guess — draft from the template (commands
first, ✅/⚠️/🚫 boundaries, source-of-truth pointer, stable references), then run
the validation gate and show its output. Keep CLAUDE.md within its verbosity
budget. No "done" until the gate passes.
