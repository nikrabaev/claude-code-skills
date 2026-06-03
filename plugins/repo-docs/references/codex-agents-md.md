# Codex AGENTS.md loading semantics (Appendix B)

The constraints the generator MUST honor. Verified [OFFICIAL, 3-0] (OpenAI Codex
AGENTS.md guide + config reference + issue openai/codex#7138).

## Concatenation

Codex joins `AGENTS.md` files from the **Git root down to the working directory**,
**blank-line-joined**. **Files closer to cwd override earlier ones** (they appear
later in the assembled prompt).

→ Put repo-wide rules in the root `AGENTS.md`; put package-specific overrides in
nested `packages/<x>/AGENTS.md`. Nearest wins.

## Scopes

- Global `~/.codex/AGENTS.md` + the project chain.
- Nested-subdirectory overrides within the project.
- An `AGENTS.override.md` precedence layer.

(The MVP/v1 generator targets the project chain; global and `override` scopes are a
later add-on.)

## The hard cap — the sharpest enforcement lever

- `project_doc_max_bytes`, **default 32768 (32 KiB)**.
- Codex **skips empty files**.
- Codex **stops adding files once the limit is reached** — anything past it is
  **SILENTLY TRUNCATED**. There is no error, no warning. The agent simply never
  sees the dropped tail, even though it is "in" the file.

→ The generator must keep the **summed root→cwd chain** under 32 KiB and **warn
before** the cap, because the failure mode is invisible. This is exactly what
`scripts/size_check.py` does: it sums the chain (skipping empty files,
blank-line-joined, measured in **bytes**) and exits non-zero at/above the cap, with
a near-cap warning at 90%.

## Generator implications

- Budget the **whole tree**, not each file in isolation.
- Prefer one tight root file + small nested overrides.
- Never let generated boilerplate push the chain over budget — every byte in an
  always-loaded file is paid on every task, and the tail past 32 KiB is lost.

## Why this matters more than the Claude side

Claude Code keeps the always-loaded layer (`CLAUDE.md`) small and pushes depth into
skills loaded on demand — over-loading degrades reliability ("context rot") but
nothing is silently dropped. Codex's 32 KiB cap is a *hard byte budget with silent
truncation*, so it is the binding constraint the generator sizes against.
