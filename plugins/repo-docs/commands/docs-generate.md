---
description: Generate the canonical AGENTS.md + a thin CLAUDE.md importer for this repo (evidence-gated, < 32 KiB)
argument-hint: "[agents-md | doc type]"
---

Generate AI-facing documentation for this repository.

REQUIRED SUB-SKILL: repo-docs:generate-agent-instructions

Target: $ARGUMENTS (default: the canonical `AGENTS.md` + a thin `CLAUDE.md` that
imports it). Inspect the repo first with the read-only scanners — do not guess —
draft from the templates (commands first, ✅/⚠️/🚫 boundaries, source-of-truth
pointer, stable references), then run the validation gate and show its output.
Keep the AGENTS.md chain under Codex's 32 KiB cap. No "done" until the gate passes.
