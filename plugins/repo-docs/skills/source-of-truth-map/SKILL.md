---
name: source-of-truth-map
description: >
  Map which file canonically owns each fact in a repo (commands, versions, schema,
  config, routes) so docs reference the owner instead of duplicating it — and flag
  doc blocks that have copied a source-of-truth file. Use when removing duplication,
  deciding where a fact belongs, or when docs and config have drifted out of sync.
---

# Source-of-truth map (reference, don't copy)

**Core principle:** every fact has one canonical home. Docs point to it; they never
hold a second copy that can silently diverge. Copied source-of-truth is the doc
anti-pattern with the clearest measured cost.

## Common owners

| Fact | Canonical owner (reference this) |
|---|---|
| Build/test/lint commands | `package.json` scripts, `Makefile`, `justfile`, `Taskfile.yml` |
| Dependency versions | lockfile + manifest (`package.json`, `Cargo.toml`, `go.mod`, `pyproject.toml`) |
| Lint/format rules | the linter/formatter config (`.eslintrc`, `ruff.toml`, `.prettierrc`, …) |
| DB schema | migrations / `schema.prisma` / ORM models |
| HTTP routes | the router/handler source |
| Env/config keys | `.env.example`, config schema (name only — never the value) |
| TS/build config | `tsconfig.json`, build config |

## Workflow

### 1. Inventory the owners

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/scan_repo.py       --root . --json
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/extract_scripts.py --root . --json
```

Build the map of fact → owning file from the scan (manifests, configs, schema).

### 2. Detect duplication in the docs

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/dup_detect.py --root .
```

Each finding is a doc block that copied an owner (e.g. pasted `package.json`
scripts). For each: replace the copy with a one-line reference to the owner
("Build/test: see `package.json` scripts").

### 3. Decide where a *new* fact belongs

- Already owned by a source-of-truth file → reference it; don't restate it.
- Volatile implementation detail → omit; document the public contract instead.
- Needed on every task and has no canonical home (a convention, a guardrail) →
  put it in `AGENTS.md`.
- Deep/low-frequency → a `docs/` sub-doc with a pointer.

### 4. Verify

Re-run `dup_detect.py` (and the full gate if you edited docs) until clean; show the
output. Hand any line-number or copied-snippet cleanup to
REQUIRED SUB-SKILL: repo-docs:stable-refs.
