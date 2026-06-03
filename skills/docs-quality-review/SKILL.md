---
name: docs-quality-review
description: >
  Score a documentation file 0–100 across six dimensions — size-fit, evidence
  density, reference stability, example coverage, boundary presence, and drift —
  with score_docs and report the per-dimension breakdown with routed fixes. Use
  when asked to quality-check, grade, score, rate, or assess the quality of a
  specific doc.
---

# Quality-review a doc (advisory score)

**Core principle:** the score is a **proxy, never the sole gate** (DESIGN §13 #16).
It tells you *where* a doc is weak so you can fix the right thing — it does not
pass/fail the doc. This skill reports; it does not edit.

`${CLAUDE_PLUGIN_ROOT}` is the plugin root.

## Workflow

### 1. Score

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/score_docs.py --root . <doc.md>
```

(Default: all `*.md` under root. Add `--root` so the **drift** dimension can
resolve paths/symbols; without it, drift is reported as not-applicable.) Read the
0–100 score and the per-dimension breakdown. The rubric and weights are in
`${CLAUDE_PLUGIN_ROOT}/references/scoring-rubric.md` (weights are reasoned, not
authoritative — tune with `--weights`).

### 2. Route fixes for weak dimensions

| Weak dimension | Fix via |
|---|---|
| `size_fit` (near/over cap) | REQUIRED SUB-SKILL: repo-docs:compress-docs |
| `ref_stability` (line refs) | REQUIRED SUB-SKILL: repo-docs:stable-refs |
| `evidence` (unbacked claims) | re-inspect with the scanners; mark unknowns `> [!WARNING] NEEDS VERIFICATION` |
| `examples` / `boundaries` | REQUIRED SUB-SKILL: repo-docs:generate-agent-instructions (templates supply ✅/⚠️/🚫 + examples) |
| `drift` (dead/stale refs) | REQUIRED SUB-SKILL: repo-docs:docs-drift-review |

For an end-to-end rewrite rather than a targeted fix, route to
`REQUIRED SUB-SKILL: repo-docs:refactor-bad-docs`.

### 3. Report

State the score, the weakest dimensions, and the fix routed for each. End with the
report — this skill does not edit docs.

## Common mistakes

- Treating the score as pass/fail — it is advisory; the blocking gate is `run_gate.sh`.
- Scoring without `--root`, then claiming the doc has no drift — drift is simply
  unmeasured without a root.
