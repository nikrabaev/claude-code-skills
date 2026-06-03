---
description: Audit this repo's AI-facing docs (CLAUDE.md/docs) and emit a scored, prioritized report
argument-hint: "[path or doc to focus on]"
---

Audit the AI-facing documentation in this repository.

REQUIRED SUB-SKILL: repo-docs:docs-audit

Scope: $ARGUMENTS (if empty, audit the whole repo — root and nested `CLAUDE.md`
and `docs/`). Run the gate in read-only/report mode, read the docs
against the durability principles and anti-patterns, and produce a prioritized
findings report (severity → finding → evidence → fix → which skill repairs it).
Make no edits.
