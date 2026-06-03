# Spec: convert this repo into a Claude Code plugin marketplace

**Date:** 2026-06-03
**Status:** approved

## Goal

Convert the repository (git remote `nikrabaev/claude-code-skills`), which currently
ships a single Claude Code plugin (`repo-docs`) with all content at the repo root,
into a **plugin marketplace** that can host one or more plugins. Deliver a
`.claude-plugin/marketplace.json`, a proper multi-plugin directory structure, and a
README.

## Decisions

- **Marketplace name:** `claude-code-skills` (matches the repo; install reads
  `repo-docs@claude-code-skills`).
- **Layout:** move the existing plugin into `plugins/repo-docs/`. The repo root
  becomes the marketplace (catalog + README); each plugin gets its own folder.
- **Design docs:** move `docs/DESIGN.md` and `docs/plans/` into
  `plugins/repo-docs/docs/` so the plugin is self-contained. The repo-root `docs/`
  is then free for marketplace-level material (e.g. this spec).
- **No splitting:** `repo-docs` stays one cohesive plugin. The structure becomes
  multi-plugin-*ready*; no logic/code changes to skills or scripts.

## Target structure

```
claude-code-skills/                  # repo root = the marketplace
├── .claude-plugin/
│   └── marketplace.json             # NEW — marketplace catalog
├── README.md                        # NEW — marketplace landing page
├── docs/
│   └── superpowers/specs/           # this spec (marketplace-level docs)
├── plugins/
│   └── repo-docs/                   # existing plugin, moved intact
│       ├── .claude-plugin/plugin.json   # moved (authoritative version)
│       ├── README.md                    # NEW — per-plugin overview
│       ├── skills/ commands/ scripts/ templates/ references/ checklists/ examples/  # moved
│       └── docs/  (DESIGN.md, plans/)   # moved
├── .gitignore                       # stays at root
└── .idea/                           # stays (gitignored)
```

## Why the move is safe

Every skill/command invokes scripts via `${CLAUDE_PLUGIN_ROOT}/scripts/...`,
sub-skills are already namespaced (`repo-docs:docs-audit`), and `run_gate.sh`
resolves its sibling scripts via `$BASH_SOURCE`. Nothing references the repo *root*.
Moving the tree as a unit with `git mv` (preserving history) keeps every internal
relative path valid; `CLAUDE_PLUGIN_ROOT` resolves to `plugins/repo-docs/` once
installed.

## marketplace.json (shape)

Top-level: `$schema`, `name`, `owner {name,email}`, `description`, `plugins[]`.
The single plugin entry: `name: repo-docs`, `source: "./plugins/repo-docs"`
(explicit path, no `metadata.pluginRoot`), `description` mirrored from `plugin.json`,
`version: 0.1.0` (identical to `plugin.json`, which stays authoritative — avoids the
silent-override footgun), `author`, `homepage`, `repository`, `category`, `keywords`.
No `license` field (no LICENSE file exists; not claiming one).

## README (root)

What the marketplace is · plugins table (`repo-docs` → one-line + link) · install
(`/plugin marketplace add nikrabaev/claude-code-skills` →
`/plugin install repo-docs@claude-code-skills`) · local-dev testing
(`/plugin marketplace add ./`) · repo layout · "adding a new plugin" section.

## Verification

1. `python3 -m json.tool` on both manifests (valid JSON).
2. Run `plugins/repo-docs/scripts/tests/` from the new location — all pass
   (proves the move broke no script-to-script paths).
3. `git status` shows the moves as renames (history preserved).
```
