# repo-docs

A Claude Code plugin for **AI-facing repository documentation**. It generates,
audits, compresses, and validates the docs coding agents actually read — a canonical
`AGENTS.md` (read by OpenAI Codex and ~25 other tools) plus a thin `CLAUDE.md` that
`@`-imports it — keeping one source of truth, stable references (never line numbers),
and the whole `AGENTS.md` chain under Codex's hard 32 KiB cap.

Part of the [`claude-code-skills`](../../) marketplace.

## Install

```text
/plugin marketplace add nikrabaev/claude-code-skills
/plugin install repo-docs@claude-code-skills
```

## Slash commands

| Command | Does |
|---|---|
| `/docs-audit` | Score and prioritize findings on existing AI docs (read-only). |
| `/docs-generate` | Generate `AGENTS.md`/`CLAUDE.md` or a durable doc, evidence-gated. |
| `/docs-validate` | Run the validation gate over a repo's docs. |
| `/docs-fix` | Repair findings (line refs, broken Mermaid, duplication, …). |
| `/docs-score` | Print the 0–100 quality score for a doc. |
| `/docs-refactor` | Refactor bad/oversized docs into the durable taxonomy. |

## Skills

One orchestrator (`repo-docs`) routes each request to a focused sub-skill:
`docs-audit`, `generate-agent-instructions`, `generate-architecture-doc`,
`generate-onboarding-doc`, `generate-operating-manual`, `generate-adr`,
`mermaid-diagrams`, `docs-drift-review`, `compress-docs`, `source-of-truth-map`,
`stable-refs`, `docs-quality-review`, `refactor-bad-docs`.

## What's inside

- **`scripts/`** — the validation gate (`run_gate.sh`) and its checks: markdown lint,
  no-line-refs, path/symbol existence, link checking, Mermaid validation (`maid`),
  source-of-truth duplication, size/Codex-cap budget, drift, and scoring. Each has a
  test under `scripts/tests/`.
- **`templates/`** — `AGENTS.md`, `CLAUDE.md`, architecture, onboarding, ADR, and
  operating-manual scaffolds.
- **`references/`** — the doc taxonomy, stable-reference strategy, Mermaid rules,
  verbosity budgets, Codex/AGENTS.md semantics, and evidence levels.
- **`checklists/`** — pre-generation, doc-quality, Mermaid, and pre-commit gates.
- **`examples/`** — annotated good/bad docs.
- **`docs/`** — the plugin's design blueprint (`DESIGN.md`) and implementation plans.

## Running the script tests

```bash
python3 -m pytest scripts/tests/
# or, without pytest:
for f in scripts/tests/test_*.py; do python3 "$f"; done
```

## Design

See [`docs/DESIGN.md`](docs/DESIGN.md) for the research-backed blueprint and
[`docs/plans/`](docs/plans) for the implementation history.
