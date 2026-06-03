---
name: generate-architecture-doc
description: >
  Produce an evidence-gated architecture overview — components, boundaries, and
  data flow — with at most one validated Mermaid diagram, from the
  architecture-overview template. Use when asked to document a system's design or
  architecture for AI agents, or to add an architecture overview / request-flow doc
  to a repo.
---

# Generate an architecture overview (evidence-gated, ≤1 diagram)

**Core principle:** a hallucinated architecture is worse than none — it actively
misleads. Inspect the repo first; document only the durable shape you verified; mark
the rest `> [!WARNING] NEEDS VERIFICATION`.

`${CLAUDE_PLUGIN_ROOT}` is the plugin root. Work through
`${CLAUDE_PLUGIN_ROOT}/checklists/pre-generation.md` first.

## Workflow

### 1. Inspect (read-only — never guess)

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/scan_repo.py --root . --json        # stack, dirs, packages
bash    ${CLAUDE_PLUGIN_ROOT}/scripts/extract_symbols.sh --root .          # public symbols
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/extract_routes.py  --root . --json   # HTTP routes (the flow spine)
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/extract_schema.py  --root . --json   # tables/entities
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/extract_events.py  --root . --json   # queues/topics
```

Read the top-level entry point(s) and one or two representative modules to confirm
the boundaries. The routes/schema/events give the durable data-flow spine.

### 2. Draft from the template

Copy `${CLAUDE_PLUGIN_ROOT}/templates/architecture-overview.md.tmpl` (delete the HTML
comment so the doc starts with a `#` heading). Honor every rule:

- **Components** = top-level dirs, each with its responsibility + a public entry
  symbol (`start()` in `src/x.ts`). **Stable refs only** — no line numbers.
- **Reference, don't copy** — point to schema/config, never paste it.
- **At most ONE diagram.** Build it via `REQUIRED SUB-SKILL: repo-docs:mermaid-diagrams`
  (≤ ~15–20 nodes, validated, no `click`).
- Anything you could not confirm in the source → `> [!WARNING] NEEDS VERIFICATION`,
  never an invented component.
- Footer: `Source of truth: <module dirs>. Update when: <new component, boundary change>.`

### 3. Run the gate — no "done" until it passes

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/run_gate.sh --root . docs/architecture.md
```

It validates markdown, line refs, paths, symbols, links, Mermaid, and duplication.
Fix every FAIL (SKIP = tool absent). Show the gate output and the doc.

REQUIRED SUB-SKILL: superpowers:verification-before-completion.

## Common mistakes

- Inventing a layered/microservices story the code doesn't show → mark NEEDS
  VERIFICATION or cut it.
- More than one diagram, or a 30-node graph → one small validated diagram only.
- Pasting the schema → reference the migrations/ORM file instead.
