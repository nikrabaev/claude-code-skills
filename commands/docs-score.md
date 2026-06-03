---
description: Score a doc 0–100 (size, evidence, ref stability, examples, boundaries, drift) — advisory
argument-hint: "[doc path, default .]"
---

Quality-check this repo's AI-facing docs with the advisory scorer.

Route: REQUIRED SUB-SKILL: repo-docs:docs-quality-review.

It runs `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/score_docs.py --root . $ARGUMENTS`
(if `$ARGUMENTS` is empty, scores all `*.md`), reports the 0–100 score with a
per-dimension breakdown, and routes fixes for weak dimensions. The score is an
advisory proxy — it never blocks (see `${CLAUDE_PLUGIN_ROOT}/references/scoring-rubric.md`).
