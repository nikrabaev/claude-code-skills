---
name: generate-operating-manual
description: >
  Generate docs/ai/OPERATING-MANUAL.md — an INDEX that points to a repo's doc set
  (one-line purpose + when-to-read per doc), the safe read-only inspection commands,
  and the do-not-guess / update-trigger rules. Use when asked to set up an AI
  operating manual or make a repo legible to coding agents.
---

# Generate the AI operating manual (an index, never a copy)

**Core principle:** the operating manual is an **index of pointers**. Its whole job is
to say *which doc owns what* and *when to read it*. If you are tempted to copy a fact
into it, link to the doc that owns that fact instead — duplication here is the one
thing that breaks it.

`${CLAUDE_PLUGIN_ROOT}` is the plugin root.

## Workflow

### 1. Enumerate what docs exist

```bash
ls AGENTS.md CLAUDE.md docs/ adr/ docs/adr/ 2>/dev/null
```

Note which durable docs are present: `AGENTS.md` (always-on rules), architecture,
onboarding, ADRs, deployment/troubleshooting. Only index docs that actually exist.

### 2. Draft from the template

Copy `${CLAUDE_PLUGIN_ROOT}/templates/ai-operating-manual.md.tmpl` (delete the HTML
comment) into `docs/ai/OPERATING-MANUAL.md`. Fill:

- **Where to read what** — one table row per existing doc: when-to-read → the doc →
  what it owns. Pure pointers, **no copied facts**.
- **Safe inspection** — the read-only commands an agent should run before writing here
  (the repo's scan/list + test commands).
- **Working rules** — reference don't copy; stable refs; mark unknowns NEEDS
  VERIFICATION; run the gate.
- **Update triggers** — when to add a row / where a fact actually belongs (e.g.
  command changes go in `AGENTS.md`, not here).

### 3. Run the gate — no "done" until it passes

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/run_gate.sh --root . docs/ai/OPERATING-MANUAL.md
```

`dup_detect` and `path_exists` are the key checks here: the manual must duplicate
nothing and every doc it points to must exist. Show the gate output and the manual.

REQUIRED SUB-SKILL: superpowers:verification-before-completion.

## Common mistakes

- Copying the boundaries or commands out of `AGENTS.md` into the manual → link to
  `AGENTS.md` instead; it owns those facts.
- Listing a doc that doesn't exist yet → only index what's there (or generate it
  first).
