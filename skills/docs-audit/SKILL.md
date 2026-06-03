---
name: docs-audit
description: >
  Audit a repository's existing AI-facing docs (AGENTS.md, CLAUDE.md, architecture/
  onboarding docs) against the durability principles and anti-patterns, then emit a
  scored, prioritized findings report — each issue tagged with its cause and fix.
  Read-only; writes no files. Use when asked to review, assess, grade, or health-
  check existing agent documentation rather than generate or change it.
---

# Audit existing AI-facing docs (read-only)

**Core principle:** measure, don't modify. Run the gate's checks in report mode and
read the docs against the principles; output findings the user can act on. Make NO
edits — generation/repair is a different skill.

## Workflow

### 1. Locate the docs

Find `AGENTS.md` (root and nested), `CLAUDE.md`, and anything under `docs/` or
`/adr`. Note the Codex chain (root→cwd `AGENTS.md` files).

### 2. Run the automated checks (read-only)

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/run_gate.sh --root .
```

Record each FAIL as a finding. (SKIP = a tool isn't installed; note it, don't score
it against the repo.) `size_check` over/near 32 KiB is a top-severity finding.

### 3. Read against the principles

For every doc, check and cite concrete evidence:

| Check | Anti-pattern if violated |
|---|---|
| Always-loaded file small, under 32 KiB chain | AP-2 / AP-14 oversized, silent truncation |
| Commands present and lead | weak BP-6 |
| Boundaries (✅/⚠️/🚫) present | missing BP-5 |
| Stable refs, no line numbers | AP-1 line refs |
| References source-of-truth, no copies | AP-6 duplication |
| Claims trace to real paths/symbols | AP-4 hallucinated architecture |
| No volatile/temporary detail in always-loaded files | AP-9 |
| Human vs AI docs separated (README ≠ AGENTS.md) | AP-13 |
| CLAUDE.md just imports AGENTS.md, no duplicated facts | drift risk |
| Mermaid validated, ≤ node cap, no `click` | AP-3 / AP-15 |
| `@`-imports limited to CLAUDE.md's single `@AGENTS.md` | AP-11 force-load bloat |

### 4. Report

Emit a prioritized list: **severity → finding → evidence (file + the offending
text, never a line number) → BP/AP tag → recommended fix → which skill repairs it**
(e.g. compress-docs, stable-refs, source-of-truth-map, generate-agent-instructions).
Give a short overall verdict. Do not edit anything.
