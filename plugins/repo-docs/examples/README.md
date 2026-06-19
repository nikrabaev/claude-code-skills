# Examples

Annotated reference outputs.

- `good/` — docs that pass the full gate, with notes on *why* they work.
- `bad/` — docs that exhibit the anti-patterns (AP-1…AP-16), each annotated with
  the problem and the fix.

`good/menv-CLAUDE.md` is a real `generate-agent-instructions` output for the menv
repo (Bun + Ink/React TUI), produced during dogfooding. It passes the gate against
menv's actual source (paths and symbols resolve, no line refs, no duplicated
source-of-truth, 2.4 KiB — comfortably within the verbosity budget).
