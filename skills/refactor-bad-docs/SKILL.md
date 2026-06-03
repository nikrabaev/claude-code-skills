---
name: refactor-bad-docs
description: >
  Diagnose and rewrite a low-quality doc end-to-end — split monoliths, fix
  references, de-duplicate, add evidence and boundaries — by orchestrating the
  existing repair skills, then prove it improved with before/after score and size.
  Use when the user says their docs are bad and wants them fixed, refactored,
  cleaned up, or rewritten.
---

# Refactor a bad doc (measurably smaller, higher-evidence)

**Core principle:** don't hand-wave "better" — **measure it.** A refactor is done
only when the doc scores higher and is no larger than before, and the gate passes.
This skill does no new authoring itself; it **routes** to the repair skills.

`${CLAUDE_PLUGIN_ROOT}` is the plugin root.

## Workflow

### 1. Baseline — capture BEFORE numbers

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/score_docs.py    --root . <doc.md>
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/size_check.py    --root .
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/conflict_scan.py --root . <doc.md>
```

Record the score, per-dimension breakdown, chain bytes, and any rule conflicts.

### 2. Diagnose, then repair by routing

Map each weakness to a repair skill and apply them in this order (biggest, safest
wins first):

1. Duplicated source-of-truth → REQUIRED SUB-SKILL: repo-docs:source-of-truth-map
2. Over cap / bloated (low `size_fit`) → REQUIRED SUB-SKILL: repo-docs:compress-docs
3. Line refs / volatile refs (low `ref_stability`) → REQUIRED SUB-SKILL: repo-docs:stable-refs
4. Missing boundaries/examples/structure or unbacked claims (low `evidence`/`examples`/`boundaries`)
   → REQUIRED SUB-SKILL: repo-docs:generate-agent-instructions
5. Contradictory rules (conflict_scan findings) → consolidate to one rule.

### 3. Re-run the gate and prove the delta

```bash
bash    ${CLAUDE_PLUGIN_ROOT}/scripts/run_gate.sh   --root . <doc.md>
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/score_docs.py --root . <doc.md>
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/size_check.py --root .
```

Show BEFORE vs AFTER score and bytes. **Not done until** the gate passes AND the
AFTER score ≥ BEFORE AND the doc is no larger.
REQUIRED SUB-SKILL: superpowers:verification-before-completion.

## Red flags — STOP

- Claiming "better" without the before/after score + size numbers.
- A higher score but a larger doc, or a passing score with a failing gate — not done.
- Rewriting from scratch instead of routing to the repair skills (you'll drop facts).
