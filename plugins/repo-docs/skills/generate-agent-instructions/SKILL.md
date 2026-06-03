---
name: generate-agent-instructions
description: >
  Generate the canonical CLAUDE.md (six high-signal sections — commands first,
  structure, code style with ✅/🚫 examples, testing, git workflow, ✅/⚠️/🚫
  boundaries — plus a source-of-truth pointer and update triggers, kept within a
  soft verbosity budget). Use when asked to create, set up, or improve Claude Code
  project instructions (CLAUDE.md) for a repository.
---

# Generate CLAUDE.md (canonical agent instructions)

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

### 2. Draft CLAUDE.md from the template

Copy `${CLAUDE_PLUGIN_ROOT}/templates/CLAUDE.md.tmpl` and fill it from the scan.
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
- Keep it to ~1–2 pages — within the verbosity budget. Markdown must be lint-clean
  (blank lines around headings; every fenced block has a language).
- **Deep docs as pointers** — link `docs/architecture.md`, `docs/onboarding.md`,
  and any repo-specific skills/`/commands`; never paste their content.

For a monorepo, put repo-wide rules in the root `CLAUDE.md` and package-specific
overrides in nested `packages/<x>/CLAUDE.md` (Claude Code merges the nearest).
Keep the whole chain within the verbosity budget.

### 3. Run the gate — no "done" until it passes

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/run_gate.sh --root .
```

It runs: markdown lint → no line refs → paths exist → symbols exist → links →
Mermaid → no duplicated source-of-truth → **CLAUDE.md within verbosity budget**. Fix
every FAIL (SKIP just means a tool isn't installed). Then show the gate output and
the file. Work through `${CLAUDE_PLUGIN_ROOT}/checklists/doc-quality.md`.

REQUIRED SUB-SKILL: superpowers:verification-before-completion.

## Common mistakes

- Pasting `package.json` scripts → `dup_detect` blocks. Reference them instead.
- A 400-line CLAUDE.md → context rot. Route detail to `docs/` and leave one-line
  pointers.
- Claiming an architecture you didn't read in the source → mark NEEDS VERIFICATION.
- Line numbers (`foo.ts:NNN`) → `no_line_refs` blocks. Use path + symbol.
