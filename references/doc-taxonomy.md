# Documentation taxonomy

For each doc type: purpose · audience · allowed · forbidden · length · update
triggers · source-of-truth. Lengths are reasoned targets ([SYNTHESIS]) unless a
vendor number is cited. MVP/v1 of this plugin generates the first two; the rest are
the taxonomy the audit and (later, v2) generators work against.

## AGENTS.md (canonical — Codex + interop)

- **Purpose:** the small set of facts any agent needs on *every* task here.
  **Audience:** Codex (direct), Claude (via import), ~10 other tools.
- **Allowed:** the six high-signal sections — commands+flags, testing, structure,
  code-style *examples*, git workflow, **✅/⚠️/🚫 boundaries** — plus pointers to
  deep docs. **Forbidden:** architecture essays, volatile state, duplicated
  `package.json`/config, line numbers.
- **Length:** ≤ ~1–2 pages; the whole root→cwd chain **< 32 KiB** (hard Codex cap).
  **Triggers:** command/stack/version change, new guardrail, structural move.
- **Source of truth:** reference, never copy; nested per-package files for monorepos
  (nearest wins).

## CLAUDE.md (thin importer)

- **Purpose:** give Claude Code the same always-on context + Claude-only pointers.
  **Audience:** Claude Code only (Codex ignores it).
- **Allowed:** `@AGENTS.md` import; a short "Claude Code specifics" block.
  **Forbidden:** any fact that duplicates `AGENTS.md`; large `@`-imports.
- **Length:** tiny (≤ ~15 lines + the import). **Triggers:** new skill/command.

## Architecture overview (`docs/architecture.md`) — v2

- **Purpose:** durable mental model — components, boundaries, data flow.
  **Allowed:** stable structure, public contracts, *one* small validated Mermaid.
  **Forbidden:** implementation minutiae, line refs, volatile detail, invented
  components. **Length:** ~1–3 pages. **Triggers:** new top-level component,
  boundary change. **Stable refs:** module paths + exported symbols.

## Request-flow docs — v2

Trace one representative request: ordered hops by route + handler symbol +
queue/topic; one sequence diagram. **Forbidden:** every branch, line refs.
**Stable refs:** `POST /api/orders` → `createOrder()` in `src/api/orders.ts` →
`orders.created` topic.

## Domain-model docs — v2

Entities, relationships, invariants, table/collection names. **Forbidden:** full
schemas (reference migrations), volatile columns. **Stable refs:** `orders` table;
`Order` in `src/domain/order.ts`.

## Onboarding doc — v2

Setup commands, repo tour by directory, a "first change" walkthrough referencing
real files. **Forbidden:** duplicating README quickstart, line refs.

## Local-dev / Deployment / Troubleshooting — v2

- **Local-dev:** run/test/debug locally; commands + ports + env *key names*.
- **Deployment:** pipeline stages, environments, where config lives (reference, not
  secrets).
- **Troubleshooting:** symptom → cause → fix table, each tied to a command.
- **Forbidden everywhere:** secrets, line refs, copied config.

## ADRs (`/adr/NNNN-imperative-name.md`) — v2

Capture *why* a significant decision was made. Nygard (Context/Decision/
Consequences) or MADR (+ options & pros/cons). One decision per file.
**Immutable — supersede, don't edit.** Link supersedes/superseded-by.

## Mermaid diagrams (embedded)

≤ ~15–20 nodes, quoted labels, validated with `maid`, no `click`/interactive links.
See `mermaid-rules.md`.

## AI operating manual (`docs/ai/OPERATING-MANUAL.md`, optional) — v2

The repo-specific "how an agent should work *here*": a doc index (one-line purpose +
when-to-read per doc), the safe-inspection command set, the "do not document / do
not guess" rules, the update-trigger policy. **Forbidden:** duplicating the docs it
indexes — it is an *index* of pointers.

## Separation principle

README is for **humans** (quickstart); `AGENTS.md` is the **agent's** operating
context. Don't mix audiences — it bloats both (anti-pattern AP-13).
