# Verbosity & compression budgets

Condensed from DESIGN §11. Two things bound how much you write: a **hard cap** you
must never exceed, and **authoring targets** that keep always-loaded context cheap.

## Hard ceiling (non-negotiable)

- **Codex: 32 KiB** on the concatenated root→cwd `AGENTS.md` chain
  (`project_doc_max_bytes`, default 32768). Codex **skips empty files, stops at the
  limit, and silently truncates** anything past it. `size_check.py` sums the chain
  and warns before the cap. This is the single cap you cannot cross.

## Authoring targets (Superpowers) — strong targets, not gates

- Always-loaded text (orchestrator body, getting-started): **< 150–200 words**.
- On-demand skills: **< 500 words**.
- Split reference material **> ~100 lines** into a separate file.
- `AGENTS.md`: aim **≤ ~1–2 pages**, comfortably under 32 KiB.
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

Every domain gets a one-line summary in `AGENTS.md` (or the operating-manual index)
and a detail doc loaded on demand. The summary *is* the routing description — the
same metadata→body pattern as skills.
