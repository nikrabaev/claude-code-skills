---
description: Diagnose and rewrite a low-quality doc — smaller, higher-evidence — with before/after proof
argument-hint: "[doc path to refactor]"
---

These docs are bad — fix them.

Route: REQUIRED SUB-SKILL: repo-docs:refactor-bad-docs.

It scores `$ARGUMENTS` (or the repo's docs) with `score_docs.py` + `size_check.py`,
diagnoses each weak dimension, repairs by orchestrating the existing repair skills
(compress-docs / stable-refs / source-of-truth-map / generate-agent-instructions),
re-runs the gate, and shows before/after score + size to prove it improved.
