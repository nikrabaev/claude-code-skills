# Empirical self-eval — does repo-docs beat baseline `/init`?

The open question (DESIGN §16 closing): *does a repo with repo-docs-generated
docs measurably improve Claude/Codex task success vs a baseline `/init`-style
CLAUDE.md?* The drift literature proves bad docs are a real, measurable problem;
no source yet measures the *uplift* of disciplined AI docs. Two tiers:

## Tier A — objective doc-quality delta (runnable now)

`scripts/eval_harness.py` measures two doc sets against a repo's real source and
reports the delta on objective properties:

- `score_docs` score, total bytes / Codex-cap fit, evidence density,
- % of path references that resolve, line-ref count, duplication findings.

```bash
python3 scripts/eval_harness.py --root /path/to/repo \
  --dir-a /tmp/repo-docs-out  --label-a repo-docs \
  --dir-b /tmp/baseline-init  --label-b init --json
```

`--dir-a` holds the repo-docs output (generated via the skills); `--dir-b` holds a
baseline `/init` CLAUDE.md. The harness is rigorous and needs no live agent loop.
Produce the two doc sets first (generate one, run `/init` for the other), then
compare. This is the concrete v3 deliverable.

## Tier B — task-success uplift (design + pilot)

The real north star: a fixed battery of repo-specific questions/tasks answered by
an agent given each doc set as context, scored for correctness.

- **Design:** N repo-specific tasks (e.g. "where is auth enforced?", "add a flag
  to subcommand X"); for each doc set, run the same agent with only that doc set
  as context; grade answers against a fixed key.
- **Conflict of interest:** the doc author scoring its own docs is biased. Mitigate
  with an **independent grader** (a fixed rubric / a separate model / a human) and a
  pre-registered answer key written before any run.
- **Scope:** a design + a *small pilot* (a handful of tasks on menv), not a full
  study — unless explicitly commissioned.
