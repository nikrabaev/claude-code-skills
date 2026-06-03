---
name: repo-docs
description: >
  Generate, audit, compress, and validate AI-facing repository documentation for
  Claude Code and OpenAI Codex — the canonical AGENTS.md plus a thin CLAUDE.md
  importer, with stable references and source-of-truth discipline under Codex's
  32 KiB cap. Use when the user asks to create, set up, improve, audit, compress,
  de-duplicate, fix, or validate AGENTS.md / CLAUDE.md or other documentation
  meant for AI coding agents.
---

# Managing AI-facing repository documentation (Claude Code + Codex)

**Route, don't do.** Classify the request and delegate to ONE sub-skill below.
Never do the work in this skill; never `@path`-force-load a sub-skill — invoke it
by name with a `REQUIRED SUB-SKILL:` marker.

## Decision table

| User intent | Action |
|---|---|
| "create / set up / improve AGENTS.md or CLAUDE.md" | REQUIRED SUB-SKILL: repo-docs:generate-agent-instructions |
| "audit / review / grade our AI docs" | REQUIRED SUB-SKILL: repo-docs:docs-audit |
| "docs too long / over the cap / compress" | REQUIRED SUB-SKILL: repo-docs:compress-docs |
| "fix references / no line numbers / how should we reference X?" | REQUIRED SUB-SKILL: repo-docs:stable-refs |
| "what owns this fact? / remove duplication" | REQUIRED SUB-SKILL: repo-docs:source-of-truth-map |
| "architecture overview / system design / a diagram of the system" | REQUIRED SUB-SKILL: repo-docs:generate-architecture-doc |
| "onboarding / dev setup / getting-started docs" | REQUIRED SUB-SKILL: repo-docs:generate-onboarding-doc |
| "record a decision / write an ADR" | REQUIRED SUB-SKILL: repo-docs:generate-adr |
| "make / fix / validate a Mermaid diagram" | REQUIRED SUB-SKILL: repo-docs:mermaid-diagrams |
| "AI operating manual / how should an agent work here" | REQUIRED SUB-SKILL: repo-docs:generate-operating-manual |
| "are our docs stale / drifting / out of date?" | REQUIRED SUB-SKILL: repo-docs:docs-drift-review |

If the request spans several (e.g. "set up and validate"), route to the primary
generator first; it runs the validation gate itself at the end.

## Non-negotiables (every sub-skill obeys)

1. **Inspect before you write** — run the read-only scanners
   (`${CLAUDE_PLUGIN_ROOT}/scripts/scan_repo.py`, `extract_scripts.py`). Do NOT guess.
2. **AGENTS.md is canonical; CLAUDE.md is `@AGENTS.md` + a short Claude-only block.**
3. **Keep the AGENTS.md chain < 32 KiB** — Codex silently truncates past it.
4. **Reference, never copy** source-of-truth. **No line numbers** — stable refs only.
5. Mark unknowns `> [!WARNING] NEEDS VERIFICATION`. Never invent.
6. **Run the gate** (`${CLAUDE_PLUGIN_ROOT}/scripts/run_gate.sh`) and show its output
   before claiming done. REQUIRED SUB-SKILL: superpowers:verification-before-completion.
