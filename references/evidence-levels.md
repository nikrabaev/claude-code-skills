# Evidence levels & evidence-gating

Two related ideas: how the DESIGN tags the *strength* of a claim, and the rule that
every generated doc claim must be **evidence-gated**.

## Evidence legend (used in DESIGN.md)

- **[OFFICIAL]** — vendor / tool-maintainer docs.
- **[EMPIRICAL]** — research paper, benchmark, or measured result.
- **[EXPERT]** — respected practitioner / maintainer.
- **[OBSERVED]** — inferred from multiple real repos / tools.
- **[SYNTHESIS]** — reasoned recommendation where direct evidence is thin (logic, not
  an authority). Flag these inline so a reader knows they are not vendor-blessed.

## The evidence-gating rule (for generated docs)

Generation is **evidence-gated**: inspect the repo with read-only scripts first,
record what you saw, and write only what you verified. (BP-9)

- Every non-trivial claim traces to a **file, symbol, or command** actually inspected.
- An unknown becomes `> [!WARNING] NEEDS VERIFICATION`, never an invented fact.
- Hallucinated architecture is worse than none — it actively misleads the agent
  reading the doc. (AP-4)

## How the gate enforces it

- `path_exists.py` / `lychee` — referenced paths/links must resolve.
- `symbol_exists.py` (via `extract_symbols.sh`) — `` `symbol()` in `file` `` refs
  must exist in the symbol index.
- `drift_check.py` (advisory) — flags refs whose target disappeared and docs older
  than the code they cite.

If a claim can't pass these, it isn't evidence-backed — mark it NEEDS VERIFICATION or
cut it.
