# CI workflow for AI docs

A doc is **code** — it gets CI. `templates/github-workflow-docs.yml` is a copyable
GitHub Actions workflow that runs the same gate the generators run, on every PR (and
push to `main`) that touches docs. Drop it into the TARGET repo at
`.github/workflows/docs.yml`.

## What each step checks (and its boundary)

| Step | Tool | Catches | Does NOT catch |
|---|---|---|---|
| Markdown lint | `markdownlint-cli2` | heading/list/fence defects, in-doc anchors (MD051), link-defect rules | network, whether a path exists |
| Mermaid validate | `@probelabs/maid` | syntax errors in flowchart/sequence/pie/class/state | other diagram types; `click`/CSP issues |
| Link & path check | `lychee` (offline) | dead links, dead local file paths, bad fragments | external flakiness (run a nightly full check separately) |
| AGENTS.md < 32 KiB | inline Python | the Codex hard cap (silent truncation past it) | token count (it measures bytes) |

The tools are wired to **what they actually do** (DESIGN §12): markdownlint never
checks the network or path existence — `lychee` does; `maid` only deeply validates
five diagram types. Don't expect one tool to do another's job.

## Drift is advisory, not a blocker

`drift_check.py` is intentionally **advisory** — sources change faster than docs, and
git mtime is a heuristic (mtime ≠ semantic staleness). Wire it as a separate,
non-blocking step (`continue-on-error: true`) so a stale-doc warning reports without
failing the build:

```yaml
      - name: Docs drift (advisory)
        continue-on-error: true
        run: python3 path/to/repo-docs/scripts/drift_check.py --root . docs/ AGENTS.md
```

Add `--strict` only if a team decides drift should block a merge.

## Notes

- The `lychee` offline mode validates internal links + local paths without network;
  schedule a full (online) run nightly if you want external-URL coverage.
- If the target repo ships its own `.markdownlint*` config, `markdownlint-cli2` uses
  it (the plugin's relaxed config only applies when run via `validate_markdown.sh`).
