---
name: compress-docs
description: >
  Compress an oversized agent doc by routing detail to on-demand sub-docs, cutting
  filler and duplication, and getting the CLAUDE.md chain back within its verbosity
  budget — without losing any fact an agent needs on every task. Use when a doc is
  bloated, fails the size check, or the user says it is too long or over budget.
---

# Compress an over-budget agent doc

**Core principle:** the dividing question is *frequency of need*, not importance.
Facts needed on **every** task stay in the always-loaded file; everything else moves
to a sub-doc with a one-line pointer. Cutting bytes must not cut meaning.

## Workflow

### 1. Measure

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/size_check.py --root . --cwd <deepest-pkg-dir>
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/dup_detect.py --root .
```

`size_check` gives the chain bytes vs the verbosity budget; `dup_detect` finds pasted
source-of-truth. Note both before touching anything.

### 2. Reduce, in this order

1. **Delete duplicated source-of-truth** — replace pasted `package.json` scripts /
   config bodies with a pointer (`see package.json scripts`). Biggest, safest win.
2. **Apply the filler test** — "would the agent behave identically if this line were
   deleted?" If yes, delete it. Cut hedge words ("generally", "try to", "consider").
3. **Route low-frequency depth out** — any section needed on < ~50% of tasks (API
   tables, schema, troubleshooting matrices, long architecture prose) moves to a
   `docs/<topic>.md`; leave a one-line pointer with a *when-to-read* hint.
4. **Strip volatile detail and historical narration** — "mid-migration", "for now",
   dated TODOs, and before/after history ("used to … now …") don't belong in an
   always-loaded file; history lives in changelogs / migration guides.
5. **Keep:** commands, hard guardrails/Boundaries, "where things live", the
   source-of-truth pointer and update triggers.

Preserve stable references and the ✅/⚠️/🚫 Boundaries while trimming.

### 3. Verify within budget

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/run_gate.sh --root .
```

`size_check` must report the chain within budget and `dup_detect` must be clean.
Show the before/after byte counts and the gate output. No "done" until it passes —
REQUIRED SUB-SKILL: superpowers:verification-before-completion.
