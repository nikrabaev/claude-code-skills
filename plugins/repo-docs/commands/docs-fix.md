---
description: Fix problems in this repo's AI docs — compress over-cap files, stabilize references, remove duplication
argument-hint: "[what to fix, e.g. 'too long' | 'line numbers' | 'duplication']"
---

Fix issues in this repo's AI-facing documentation.

REQUIRED SUB-SKILL: repo-docs (route by the problem)

Request: $ARGUMENTS. Route to the right repair skill:

- too long / over the 32 KiB cap / bloated → repo-docs:compress-docs
- line numbers / volatile or copied references → repo-docs:stable-refs
- duplicated source-of-truth / where should this fact live → repo-docs:source-of-truth-map
- broad rewrite of AGENTS.md / CLAUDE.md → repo-docs:generate-agent-instructions

If unsure what is wrong, run repo-docs:docs-audit first, then fix the top findings.
End by running the gate and showing its output — no "done" until it passes.
