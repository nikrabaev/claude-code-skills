# Verbosity & compression budgets

Condensed from DESIGN §11. Two things bound how much you write: a **soft budget**
for the always-loaded file, and **authoring targets** that keep always-loaded
context cheap.

## Soft budget for the always-loaded file

- **CLAUDE.md: stay well under ~32 KiB** for the root→cwd chain Claude Code loads
  on every task. `size_check.py` sums the chain and warns as it approaches the
  budget. This is a soft target, not a hard cap — an oversized always-loaded file
  spends context budget and invites context rot, so trim rather than fill it.

## Authoring targets (Superpowers) — strong targets, not gates

- Always-loaded text (orchestrator body, getting-started): **< 150–200 words**.
- On-demand skills: **< 500 words**.
- Split reference material **> ~100 lines** into a separate file.
- `CLAUDE.md`: aim **≤ ~1–2 pages**, comfortably within the budget.
- The "hard 500-line SKILL.md" rule is **refuted** — it is a target, not a gate.

## Links vs duplication

If a fact has a source-of-truth file, **reference it — never inline a copy**. Inline
only facts with no canonical home. (Copies drift; `dup_detect.py` flags pasted
`package.json`/config.)

## When to move material to a sub-doc

Move a section out (leaving a one-line pointer with a *when-to-read* hint) when it:

- exceeds its tier budget,
- is needed on **< 50%** of tasks, or
- is deep reference (API tables, schema, troubleshooting matrices).

## Two failure poles (the test for every line)

- **Filler test** — "would the agent behave identically if this line were deleted?"
  If yes, delete it.
- **Under-spec test** — "can the agent verify it complied?" If no, add a concrete
  criterion or example.

A good line is one the agent **cannot already infer** and **can act on / verify**.

## Summary/detail layering

Every domain gets a one-line summary in `CLAUDE.md` (or the operating-manual index)
and a detail doc loaded on demand. The summary *is* the routing description — the
same metadata→body pattern as skills.
