---
name: generate-agent-instructions
description: >
  Generate the canonical AGENTS.md (six high-signal sections — commands first,
  structure, code style with ✅/🚫 examples, testing, git workflow, ✅/⚠️/🚫
  boundaries — plus a source-of-truth pointer and update triggers, kept under
  Codex's 32 KiB cap) and a thin CLAUDE.md that imports it. Use when asked to
  create, set up, or improve Claude Code or Codex project instructions
  (AGENTS.md / CLAUDE.md) for a repository.
---

# Generate AGENTS.md (canonical) + CLAUDE.md (importer)

**Core principle:** evidence-gated and progressive. Inspect the repo first, write
only what you verified, keep the always-loaded file tiny, route depth elsewhere.

`${CLAUDE_PLUGIN_ROOT}` is the plugin root. Run scripts with `python3`/`bash`.

## Workflow

### 1. Inspect (read-only — never guess)

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/scan_repo.py --root . --json      # stack, dirs, manifests, monorepo
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/extract_scripts.py --root . --json # build/test/lint commands
```

Read the top-level entry points and one or two representative source files to
confirm the stack. Anything you cannot verify becomes a
`> [!WARNING] NEEDS VERIFICATION` line — never an invented fact.

### 2. Draft AGENTS.md from the template

Copy `${CLAUDE_PLUGIN_ROOT}/templates/AGENTS.md.tmpl` and fill it from the scan.
Honor every rule:

- **Commands first**, with flags (single-test command too) — agents waste turns
  rediscovering these.
- **Specificity with versions** — "Bun runtime (not Node); Ink+React TUI", not
  "a TypeScript app". Pull versions from the scan.
- **Reference, don't copy** — "Build/test: see `package.json` scripts", never paste
  the scripts list or config bodies.
- **Stable references only** — path+symbol, route, table, command, test name.
  NEVER line numbers. (See REQUIRED SUB-SKILL: repo-docs:stable-refs for the ranking.)
- **Boundaries** with three tiers (✅ Always / ⚠️ Ask first / 🚫 Never) and
  5–10 specific rules. "Never commit secrets" is the single highest-value line.
- **Code-style rules carry ✅/🚫 examples**, not vague adjectives.
- **Footer**: `Source of truth: <dirs>. Update when: <triggers>.`
- **No volatile detail** ("mid-migration", "for now", dated TODOs) in this
  always-loaded file.
- Keep it to ~1–2 pages — comfortably under 32 KiB. Markdown must be lint-clean
  (blank lines around headings; every fenced block has a language).

For a monorepo, put repo-wide rules in the root `AGENTS.md` and package-specific
overrides in nested `packages/<x>/AGENTS.md` (Codex: nearest wins). The whole
root→cwd chain must stay under the cap.

### 3. Write CLAUDE.md (thin importer)

Copy `${CLAUDE_PLUGIN_ROOT}/templates/CLAUDE.md.tmpl` verbatim-ish: its only
substance is `@AGENTS.md` plus a short "Claude Code specifics" block (which
skills/commands/deep docs exist). Put NO fact in CLAUDE.md that belongs in
AGENTS.md — zero duplication, no cross-file drift.

### 4. Run the gate — no "done" until it passes

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/run_gate.sh --root .
```

It runs: markdown lint → no line refs → paths exist → symbols exist → links →
Mermaid → no duplicated source-of-truth → **AGENTS.md chain < 32 KiB**. Fix every
FAIL (SKIP just means a tool isn't installed). Then show the gate output and both
files. Work through `${CLAUDE_PLUGIN_ROOT}/checklists/doc-quality.md`.

REQUIRED SUB-SKILL: superpowers:verification-before-completion.

## Common mistakes

- Pasting `package.json` scripts → `dup_detect` blocks. Reference them instead.
- A 400-line AGENTS.md → context rot + risk of the Codex tail being dropped. Route
  detail to `docs/` and leave one-line pointers.
- Claiming an architecture you didn't read in the source → mark NEEDS VERIFICATION.
- Line numbers (`foo.ts:NNN`) → `no_line_refs` blocks. Use path + symbol.
