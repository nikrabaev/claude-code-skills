# Documentation taxonomy

For each doc type: purpose · audience · allowed · forbidden · length · update
triggers · source-of-truth. Lengths are reasoned targets ([SYNTHESIS]). The plugin
has generators for `CLAUDE.md` (the first), architecture, onboarding, ADRs, and the
AI operating manual; request-flow and domain-model are documented as part of the
architecture overview.

## CLAUDE.md (canonical agent instructions)

- **Purpose:** the small set of facts any agent needs on *every* task here.
  **Audience:** Claude Code (always-loaded project memory).
- **Allowed:** the six high-signal sections — commands+flags, testing, structure,
  code-style *examples*, git workflow, **✅/⚠️/🚫 boundaries** — plus pointers to
  deep docs. **Forbidden:** architecture essays, volatile state, historical
  narration ("used to … now …"), duplicated `package.json`/config, line numbers,
  large `@`-imports.
- **Length:** ≤ ~1–2 pages; the whole root→cwd chain within the verbosity budget
  (soft ~32 KiB). **Triggers:** command/stack/version change, new guardrail,
  structural move, new skill/command.
- **Source of truth:** reference, never copy; nested per-package files for monorepos
  (Claude Code merges the nearest).

## Architecture overview (`docs/architecture.md`)

- **Purpose:** durable mental model — components, boundaries, data flow.
  **Allowed:** stable structure, public contracts, *one* small validated Mermaid.
  **Forbidden:** implementation minutiae, line refs, volatile detail, historical
  narration, invented components. **Length:** ~1–3 pages. **Triggers:** new top-level component,
  boundary change. **Stable refs:** module paths + exported symbols.

## Request-flow docs

Trace one representative request: ordered hops by route + handler symbol +
queue/topic; one sequence diagram. **Forbidden:** every branch, line refs.
**Stable refs:** `POST /api/orders` → `createOrder()` in `src/api/orders.ts` →
`orders.created` topic.

## Domain-model docs

Entities, relationships, invariants, table/collection names. **Forbidden:** full
schemas (reference migrations), volatile columns. **Stable refs:** `orders` table;
`Order` in `src/domain/order.ts`.

## Onboarding doc

Setup commands, repo tour by directory, a "first change" walkthrough referencing
real files. **Forbidden:** duplicating README quickstart, line refs.

## Local-dev / Deployment / Troubleshooting

- **Local-dev:** run/test/debug locally; commands + ports + env *key names*.
- **Deployment:** pipeline stages, environments, where config lives (reference, not
  secrets).
- **Troubleshooting:** symptom → cause → fix table, each tied to a command.
- **Forbidden everywhere:** secrets, line refs, copied config.

## ADRs (`/adr/NNNN-imperative-name.md`)

Capture *why* a significant decision was made. Nygard (Context/Decision/
Consequences) or MADR (+ options & pros/cons). One decision per file.
**Immutable — supersede, don't edit.** Link supersedes/superseded-by.

## Mermaid diagrams (embedded)

≤ ~15–20 nodes, quoted labels, validated with `maid`, no `click`/interactive links.
See `mermaid-rules.md`.

## AI operating manual (`docs/ai/OPERATING-MANUAL.md`, optional)

The repo-specific "how an agent should work *here*": a doc index (one-line purpose +
when-to-read per doc), the safe-inspection command set, the "do not document / do
not guess" rules, the update-trigger policy. **Forbidden:** duplicating the docs it
indexes — it is an *index* of pointers.

## Separation principle

README is for **humans** (quickstart); `CLAUDE.md` is the **agent's** operating
context. Don't mix audiences — it bloats both (anti-pattern AP-13).

## Current-state principle (temporal scope)

Durable docs describe the system **as it is now** — not how it got here. Narrating
history ("the auth flow used to use sessions; now it uses JWT"; "before v2 …, now …")
is anti-pattern **AP-16**: it bloats always-loaded files and can trap an agent into
following the obsolete description. **BP-14:** document the current state only;
relegate history to the channels built for it.

- **Allowed homes for history:** migration/upgrade guides, changelogs, ADRs (the
  *why* of a past decision), and — rarely — examples that intentionally show a prior
  refactoring.
- **Distinct from AP-9 / BP-11** (volatile/temporary detail like "mid-migration"):
  AP-9 is something *currently in flux*; AP-16 is a *settled past* narrated next to
  the present. Both are kept out of durable docs.
