---
name: generate-onboarding-doc
description: >
  Produce onboarding / local-dev docs — setup commands, a repo tour by directory, a
  "first change" walkthrough referencing real files, and a troubleshooting table —
  from the onboarding template, referencing real commands and files. Use when asked
  to document getting-started, setup, or the local development environment for a repo.
---

# Generate an onboarding doc (real commands, real files)

**Core principle:** reference, don't duplicate. The README owns the human quickstart;
`package.json`/scripts own the commands. This doc points to them and adds the repo
tour + first-change path an agent needs.

`${CLAUDE_PLUGIN_ROOT}` is the plugin root.

## Workflow

### 1. Inspect (read-only)

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/scan_repo.py      --root . --json   # stack + versions, dirs
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/extract_scripts.py --root . --json  # install/run/test commands
```

Read the README so you can point to it instead of repeating it. Note the real entry
points and a plausible "first change" file.

### 2. Draft from the template

Copy `${CLAUDE_PLUGIN_ROOT}/templates/onboarding.md.tmpl` (delete the HTML comment).
Honor every rule:

- **Commands referenced, not pasted** — "Full list: see `package.json` scripts". Give
  install/run/test + a single-test command.
- **Specific stack with versions** (e.g. "Bun ≥ 1.1, not Node"), from the scan.
- **Repo tour** = real directories and their purpose. **Stable refs only.**
- **First change** = a concrete starter task pointing at a real file, then the test
  command to confirm.
- **No secrets** — env **KEY NAMES only** (`MENV_PASSPHRASE`), never values; point to
  `.env.example` / the config file.
- Footer: `Source of truth: <setup scripts/config>. Update when: <setup/tooling change>.`

### 3. Run the gate — no "done" until it passes

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/run_gate.sh --root . docs/onboarding.md
```

Fix every FAIL (SKIP = tool absent). Show the gate output and the doc.

REQUIRED SUB-SKILL: superpowers:verification-before-completion.

## Common mistakes

- Re-typing the README quickstart → link to it; this doc is for what the README omits.
- Pasting the scripts block → `dup_detect` blocks it. Reference `package.json`.
- Printing an env-var **value** → names only, ever.
