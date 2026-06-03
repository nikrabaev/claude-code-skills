# Examples

Annotated reference outputs.

- `good/` — docs that pass the full gate, with notes on *why* they work.
- `bad/` — docs that exhibit the anti-patterns (AP-1…AP-15), each annotated with
  the problem and the fix.

`good/menv-AGENTS.md` is a real `generate-agent-instructions` output for the menv
repo (Bun + Ink/React TUI), produced during dogfooding. It passes the gate against
menv's actual source (paths and symbols resolve, no line refs, no duplicated
source-of-truth, 2.4 KiB — well under the 32 KiB Codex cap).
