---
name: mermaid-diagrams
description: >
  Generate, fix, and validate Mermaid diagrams within size and syntax limits —
  the five maid-validated types (flowchart/sequence/class/state/pie), ≤ ~15–20
  nodes, quoted labels, correct arrows, no click/interactive links. Use when a
  diagram is requested, embedded in a generated doc, or fails to render on
  GitHub (renders blank).
---

# Mermaid diagrams (validated, GitHub-safe)

**Core principle:** never commit a diagram that has not passed `maid`. A broken
Mermaid block renders blank on GitHub — negative value. Pipe every diagram through
`maid --fix`, then re-validate.

`${CLAUDE_PLUGIN_ROOT}` is the plugin root. Full rules:
`${CLAUDE_PLUGIN_ROOT}/references/mermaid-rules.md`.

## Use one of the five validated types

`maid` actively validates **flowchart/`graph`, `sequenceDiagram`, `classDiagram`,
`stateDiagram-v2`, `pie`** — and only these. Other types pass through unvalidated;
do not commit them.

## Workflow

### 1. Draft with the rules in mind

- Quote any label containing `()[]{}:;,"#` → `A["process(payment)"]` (the #1 AI
  failure).
- Flowchart arrows `-->` (never `->`); sequence `->>` / `-->>`.
- Capitalize `end` (`End`/`END`); no leading `o`/`x` on an edge.
- `≤ ~15–20 nodes`; split per subsystem/flow if larger.
- **No `click` / interactive links** — GitHub's CSP blocks them (diagrams render in a
  sandboxed iframe). Put links in prose.

### 2. Auto-fix, then re-validate (do both)

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/validate_mermaid.sh --fix path/to/doc.md
bash ${CLAUDE_PLUGIN_ROOT}/scripts/validate_mermaid.sh      path/to/doc.md
```

`--fix` applies safe rewrites (`->` → `-->`, quoting, etc.); the second run confirms a
clean exit. Exit 2 = `maid` not installed (SKIP, not a pass) — say so.

### 3. Check what the tools can't

`maid` and markdownlint do **not** catch `click`/CSP problems — verify by hand against
`${CLAUDE_PLUGIN_ROOT}/checklists/mermaid.md`.

When the diagram is embedded in a doc being generated, the host generator runs the
full gate (`run_gate.sh`) at the end; this skill owns the Mermaid step.

## Common mistakes

- Unquoted parentheses in a label → blank render. Quote the label.
- `->` in a flowchart → `maid` flags it; `--fix` rewrites to `-->`.
- A clickable node linking to a URL → silently inert on GitHub. Move it to prose.
- A 40-node graph → split it; a diagram that needs scrolling is a smell.
