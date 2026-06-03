# Doc-quality scoring rubric (`score_docs.py`)

`score_docs.py` rates a doc 0–100 across six dimensions. It is an **advisory
proxy**, never the sole gate (DESIGN §13 #16, §12): it reports a score, it does
not block. The blocking gate (`run_gate.sh`) decides pass/fail; the score guides
*improvement*.

## Dimensions

| Dimension | Weight | Measures | 1.0 means |
|---|---|---|---|
| `size_fit` | 0.15 | bytes vs the budget (target 12 KiB → Codex 32 KiB cap) | at/under the 12 KiB target |
| `evidence` | 0.30 | fraction of substantive lines bearing a backticked ref or `NEEDS VERIFICATION` | every claim is evidence-gated |
| `ref_stability` | 0.15 | absence of line-number references | no `path.ext:NNN` / `line NNN` |
| `examples` | 0.15 | presence of ✅/🚫 examples, fenced snippets, "e.g." | concrete examples throughout |
| `boundaries` | 0.15 | a Boundaries/Contracts section with ✅/⚠️/🚫 tiers | all three tiers present |
| `drift` | 0.10 | dead paths/symbols + doc-vs-code mtime (needs `--root`) | nothing stale |

Final score = `round(100 · Σ(weightᵢ·scoreᵢ) / Σ(weightᵢ))` over **applicable**
dimensions. `drift` is excluded (weights renormalized) when no `--root` is given —
an unmeasurable dimension is dropped, never scored 0.

HTML comments (`<!-- … -->`) are invisible to any reader/agent, so the "rendered"
dimensions (`evidence`, `examples`, `boundaries`) score the comment-stripped text;
`size_fit` (Codex loads the raw bytes), `ref_stability`, and `drift` use the raw
text to mirror the gate's exact checks.

## Threshold & calibration

- Default threshold: **70** (`--threshold N`). The v3 quality bar is "every
  generated doc scores above threshold."
- The weights are **`[SYNTHESIS]` — reasoned, not vendor-blessed.** They are
  calibrated so the annotated good example (`examples/good/menv-AGENTS.md`) scores
  high (≈88) and the annotated bad example (`examples/bad/AGENTS.md`) scores low
  (≈40). Tune them for your repo with `--weights "evidence=0.4,size_fit=0.1,..."`.

## Use

`score_docs.py [--root DIR] [docs...] [--json] [--strict] [--threshold N] [--weights ...]`.
Advisory: exit 0 even below threshold; `--strict` exits 1 if any doc is below it.
In `run_gate.sh` it runs as a non-blocking advisory step. See
`references/evidence-levels.md` for the evidence-gating rule the `evidence`
dimension rewards.
