# claude-code-skills

A [Claude Code](https://code.claude.com/docs/en/overview) **plugin marketplace** —
a Git repo that catalogs installable plugins (skills, slash commands, scripts) so
you can add them to Claude Code with a couple of commands.

## Plugins

| Plugin | Description |
|---|---|
| [`repo-docs`](plugins/repo-docs) | Generate, audit, compress, and validate AI-facing repository documentation — the canonical `CLAUDE.md` — for Claude Code, with stable references, source-of-truth discipline, and a validation gate with a soft verbosity budget. 14 skills, 6 slash commands. |

## Install

In a Claude Code session, register this marketplace, then install a plugin:

```text
/plugin marketplace add nikrabaev/claude-code-skills
/plugin install repo-docs@claude-code-skills
```

- `nikrabaev/claude-code-skills` is the GitHub `owner/repo` shorthand.
- `repo-docs@claude-code-skills` is `<plugin-name>@<marketplace-name>`.

Browse and toggle installed plugins anytime with `/plugin`. Update the catalog with
`/plugin marketplace update claude-code-skills`.

## Local development / testing

To try changes before pushing, add the marketplace from a local path:

```text
/plugin marketplace add ./
/plugin install repo-docs@claude-code-skills
```

The `repo-docs` plugin's scripts have a self-contained test suite:

```bash
cd plugins/repo-docs
python3 -m pytest scripts/tests/        # or: for f in scripts/tests/test_*.py; do python3 "$f"; done
```

## Repository layout

```
claude-code-skills/
├── .claude-plugin/
│   └── marketplace.json      # the marketplace catalog (lists every plugin)
├── plugins/
│   └── repo-docs/            # one self-contained plugin
│       ├── .claude-plugin/
│       │   └── plugin.json   # plugin manifest (authoritative)
│       ├── skills/           # SKILL.md folders (auto-discovered)
│       ├── commands/         # slash commands (auto-discovered)
│       ├── scripts/          # validators/extractors + tests
│       ├── templates/  references/  checklists/  examples/
│       └── docs/             # the plugin's design docs
├── docs/                     # marketplace-level docs (design specs)
└── README.md
```

Each plugin lives in its own folder under `plugins/` and is referenced from
`.claude-plugin/marketplace.json` by a relative `source` path. Claude Code
auto-discovers a plugin's `skills/`, `commands/`, and `agents/` directories — the
`plugin.json` need only declare metadata.

## Adding a new plugin

1. Create `plugins/<your-plugin>/` with a `.claude-plugin/plugin.json` (at minimum a
   `name`) and the components you want (`skills/`, `commands/`, `agents/`, …).
2. Add an entry to the `plugins` array in
   [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json) with a
   `name` and a `source` of `"./plugins/<your-plugin>"`.
3. Test locally with `/plugin marketplace add ./`, then commit and push.

See the [official plugin docs](https://code.claude.com/docs/en/plugins) and
[plugin-marketplace docs](https://code.claude.com/docs/en/plugin-marketplaces) for
the full schema.
