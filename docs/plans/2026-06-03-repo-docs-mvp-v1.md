# repo-docs Plugin (MVP + v1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `repo-docs` Claude Code plugin — a flat set of sibling skills + one orchestrator, plus slash commands, scripts, templates, checklists, and reference docs — that generates, maintains, and quality-controls AI-facing repo documentation (`AGENTS.md` canonical + thin `CLAUDE.md` importer) for Claude Code and OpenAI Codex.

**Architecture:** Progressive disclosure: a tiny always-loaded orchestrator routes by `description` to deep on-demand sub-skills (`REQUIRED SUB-SKILL:`, never `@path`). Generators are evidence-gated (inspect repo first via read-only scripts) and end by running a validation gate. The sole canonical artifact is `AGENTS.md`; `CLAUDE.md` is `@AGENTS.md` + a Claude-only block. Codex hard-caps the concatenated `AGENTS.md` chain at 32 KiB and silently truncates past it — `size_check` is the sharpest lever.

**Tech Stack:** Claude Code plugin (`.claude-plugin/plugin.json`, auto-discovered `skills/`, `commands/`). Scripts: Python 3 stdlib only (target 3.9). Shell wrappers around `markdownlint-cli2`, `@probelabs/maid`, `lychee`. Code extraction via `ctags`/`ripgrep`. `${CLAUDE_PLUGIN_ROOT}` for bundled paths.

**Source of truth:** `docs/DESIGN.md` (§7 folder structure, §9 stable refs, §10 Mermaid, §12 gate, §13 scripts, §14 skill drafts, §15 roadmap). This plan implements **MVP + v1** only.

---

## Verified constraints (do not get wrong)

1. **Codex 32 KiB cap.** `project_doc_max_bytes` default 32768; concatenated root→cwd `AGENTS.md` chain, blank-line-joined, closer-overrides, **empty files skipped, silently truncated past cap**. `size_check` sums the chain and warns BEFORE the cap.
2. **Progressive disclosure** — tiny always-loaded text, depth routed on demand (context rot).
3. **Stable refs only** — path+symbol, route, table, command, test name. NEVER line numbers.
4. **Reference, don't copy** source-of-truth (package.json/config/schema).
5. **Evidence-gated** — inspect first; mark unknowns `> [!WARNING] NEEDS VERIFICATION`, never guess.
6. **Mermaid** — validate with `maid`; ≤~15–20 nodes; quote labels; NO `click`/interactive links; lowercase `end` and leading o/x on edges break flowcharts.
7. **Tool boundaries** — markdownlint-cli2 = syntax/style + in-doc anchors (no network, no path existence); lychee = links + local file-path existence + fragments; Vale = prose only; ctags/ripgrep = symbol/path existence; maid validates only flowchart/sequence/pie/class/state.
8. **Refuted — do NOT reintroduce:** (a) SKILL.md 500-line limit is a TARGET not a gate; (b) a skill `description` must state WHAT + WHEN (third person, ≤1024 chars), not when-only.

---

## File structure (MVP + v1)

```
repo-docs/
├── .claude-plugin/plugin.json
├── commands/{docs-audit,docs-generate,docs-validate,docs-fix}.md
├── skills/
│   ├── repo-docs/SKILL.md                    # orchestrator/router
│   ├── generate-agent-instructions/SKILL.md  # MVP
│   ├── docs-audit/SKILL.md                    # MVP
│   ├── compress-docs/SKILL.md                 # v1
│   ├── stable-refs/SKILL.md                   # v1
│   └── source-of-truth-map/SKILL.md           # v1
├── scripts/
│   ├── scan_repo.py            extract_scripts.py   no_line_refs.py
│   ├── path_exists.py          size_check.py        symbol_exists.py   # v1
│   ├── dup_detect.py           # v1
│   ├── extract_symbols.sh      # v1
│   ├── validate_markdown.sh    validate_mermaid.sh  check_links.sh     # check_links v1
│   ├── run_gate.sh             # convenience composition of the gate
│   └── tests/test_*.py, test_shell_wrappers.sh
├── templates/{AGENTS.md.tmpl,CLAUDE.md.tmpl}
├── checklists/doc-quality.md
└── references/{doc-taxonomy,stable-references,mermaid-rules,codex-agents-md,agents-md-interop}.md
```

---

## Script conventions (all scripts obey)

- **Python 3 stdlib only**, target 3.9.6 (no `match`, no `X | Y` runtime unions; `from __future__ import annotations` if annotating).
- Each Python script exposes **importable pure functions** + a `main(argv=None) -> int`; the `if __name__ == "__main__":` guard calls `sys.exit(main())`. Tests import the functions directly.
- CLI: `--root DIR` (default cwd), positional paths/globs where relevant, `--json` for machine-readable output, `--help`.
- **Exit codes:** `0` clean/pass · `1` violations found · `2` usage/internal error or required external tool missing (skip, not fail).
- Validators print a human summary to stdout and (with `--json`) a JSON object to stdout.
- Tests live in `scripts/tests/test_<name>.py`, use `unittest`, build fixtures in `tempfile.mkdtemp()`, and add the scripts dir to `sys.path` via `os.path.dirname(os.path.dirname(__file__))`.
- Run all: `python3 -m unittest discover -s scripts/tests -p 'test_*.py'` from repo root.

### Shared index contract (extract_symbols.sh ↔ symbol_exists.py)
`extract_symbols.sh` emits a JSON **array** to stdout: `[{"symbol": "<name>", "kind": "<function|class|method|const|...>", "file": "<relpath-from-root>"}, ...]`. `symbol_exists.py` consumes exactly this shape (via `--index FILE` or by invoking the script).

---

## The validation gate (the spine, §12)

Order (skip steps whose tool is absent, reporting the skip):
`validate_markdown` → `no_line_refs` → `path_exists` → `symbol_exists` → `check_links` → `validate_mermaid` (if diagrams) → `dup_detect` → `size_check`.
(`score_docs` is v3 — out of scope here.) **Errors block** (line refs, dead paths/symbols, broken links, invalid Mermaid, SoT duplication, over-32-KiB). **Warnings report** (size target, drift suspicion). No "done" claim until gate output is shown. `run_gate.sh` composes these.

---

# Phase 1 — Scripts (TDD, parallelizable)

The 8 Python scripts have no shared state (the one contract — the symbol index — is fixed above) and are built by parallel agents. Each agent: write tests first → run to fail → implement → run to pass → report. Below is the contract + the concrete test cases each must satisfy.

### Task 1: `scan_repo.py` (MVP)
**Files:** Create `scripts/scan_repo.py`; Test `scripts/tests/test_scan_repo.py`.
**Contract:** `scan_repo.py [--root DIR] [--json]` → JSON object:
`{"root", "languages": {<lang>: <file_count>}, "top_dirs": [...], "manifests": [{"type","path"}], "stack": [{"name","version","source"}], "monorepo_packages": [...], "entry_points": [...]}`.
**Algorithm:** Walk tree skipping a built-in ignore set (`.git node_modules dist build .venv venv __pycache__ vendor target .next coverage`). Map file extensions → languages (`.py`→python, `.ts/.tsx`→typescript, `.js/.jsx`→javascript, `.go`→go, `.rs`→rust, `.rb`→ruby, `.java`→java, `.sh`→shell). Detect manifests by filename (`package.json pyproject.toml setup.py Cargo.toml go.mod Gemfile pom.xml requirements.txt Makefile justfile Taskfile.yml`). Parse versions: package.json deps+devDeps; pyproject `[project] dependencies`/`[tool.poetry.dependencies]` (regex, best-effort); Cargo.toml `[dependencies]`; go.mod `require`. Monorepo: package.json `workspaces`, `pnpm-workspace.yaml`, `lerna.json`, top-level `packages/*` dirs → list package dirs. Entry points: package.json `main`/`bin`, plus existing common files (`src/index.ts main.py src/main.rs cmd/`). Cap walk depth (e.g. 8) on huge trees.
**Test cases:** (a) fixture with `package.json` deps `{"react":"^18.2.0"}` → `stack` contains name=react version normalized `18.2.0` (or `^18.2.0`) source=package.json. (b) fixture dirs `src/`, `tests/` → `top_dirs` includes both. (c) `.py` files → `languages.python >= count`. (d) package.json with `workspaces: ["packages/*"]` + `packages/a`,`packages/b` → `monorepo_packages` has a,b. (e) `--json` emits parseable JSON; default emits human summary. **Limits:** heuristic stack detection; depth-capped.

### Task 2: `extract_scripts.py` (MVP)
**Files:** Create `scripts/extract_scripts.py`; Test `scripts/tests/test_extract_scripts.py`.
**Contract:** `extract_scripts.py [--root DIR] [--json]` → JSON **array** `[{"source","name","command"}]`.
**Algorithm:** package.json `scripts` (JSON parse → name/command). Makefile targets: lines matching `^([A-Za-z0-9_.-]+):(?!=)` excluding `.PHONY`/pattern rules; command = first recipe line if present. justfile recipes: `^([a-z0-9_-]+)(\s.*)?:` → name. Taskfile.yml: light regex for keys under `tasks:` (2-space indented `^  (\w[\w-]*):`). Dedup by (source,name).
**Test cases:** (a) package.json `{"scripts":{"test":"jest","build":"tsc"}}` → two entries with correct command. (b) Makefile with `build:` and `test:` targets → entries source=Makefile. (c) no manifests → empty array, exit 0. (d) `.PHONY:` line not emitted as a target. **Limits:** doesn't resolve aliased commands.

### Task 3: `no_line_refs.py` (MVP)
**Files:** Create `scripts/no_line_refs.py`; Test `scripts/tests/test_no_line_refs.py`.
**Contract:** `no_line_refs.py [--root DIR] [paths/globs...] [--json]` (default: all `*.md` under root). Detects line-number refs; exit 1 if any.
**Algorithm:** Strip fenced code blocks (``` and `~~~`, matched pairs) before scanning — they're examples, not refs. Patterns: (1) `(?<![:\w])([\w./-]+\.[A-Za-z][\w]*):(\d+)\b` — filename-with-extension + `:NNN`. (2) `\bline\s+\d+\b` (case-insensitive). **Exclusions:** skip a match if the colon-number is part of a URL (`https?://...` on the same token) or a `host:port` where left side has no path separator AND no real file extension (e.g. `localhost:3000`, `example.com:8080` → exclude via an allowlist of common TLDs/`localhost` OR require the extension to be a known code/file ext). Skip `::` scope (pattern 1 requires a single `:` not preceded by `:`). Report `{file, line_no_in_doc, match}`.
**Test cases:** (a) `src/app.ts:412` → flagged. (b) `see line 42` → flagged. (c) `localhost:3000` → NOT flagged. (d) `https://ex.com:8080/p` → NOT flagged. (e) ```` ```\nsrc/x.ts:9\n``` ```` (fenced) → NOT flagged. (f) `std::vector` → NOT flagged. (g) clean doc → exit 0. **Limits:** needs allowlist for legit colon-number tokens.

### Task 4: `path_exists.py` (MVP)
**Files:** Create `scripts/path_exists.py`; Test `scripts/tests/test_path_exists.py`.
**Contract:** `path_exists.py [--root DIR] [paths/globs...] [--json]` (default `*.md`). Backticked path-like tokens must exist relative to root; exit 1 on dead paths.
**Algorithm:** Extract inline-code spans (`` `...` ``). A token is "path-like" if: no spaces, not a URL, and (contains `/` OR matches `^[\w.-]+\.[A-Za-z0-9]+$` a filename with extension). Exclude symbol-calls (`endswith("()")` or contains `(`), exclude command-ish (contains space — already excluded), exclude env-var-ish (`^[A-Z_]+$`), exclude globs (`*`). Strip trailing punctuation `.,;:` and a trailing `/`. Resolve against root; a directory or file counts as existing. Report dead ones.
**Test cases:** (a) `` `src/exists.ts` `` (file created) → pass. (b) `` `src/missing.ts` `` → flagged. (c) `` `https://x.com/y` `` → skipped. (d) `` `processPayment()` `` → skipped. (e) `` `src/` `` dir exists → pass. (f) `` `MENV_PASSPHRASE` `` → skipped (env-var). **Limits:** paths only; complements lychee.

### Task 5: `size_check.py` (MVP)
**Files:** Create `scripts/size_check.py`; Test `scripts/tests/test_size_check.py`.
**Contract:** `size_check.py [--root DIR] [--cwd SUBDIR] [--cap 32768] [--warn-ratio 0.9] [--json]`. Computes the Codex chain size; exit 1 if `>= cap`, warn (exit 0) if `>= cap*warn_ratio`.
**Algorithm:** Chain = `AGENTS.md` at `root` and at every ancestor dir from `root` down to `root/<cwd>` inclusive (root→cwd order). Skip missing/empty files (Codex skips empty). Join existing files with one blank line (`\n\n`) — match Codex concatenation — and measure **bytes** of the joined result (`len(joined.encode("utf-8"))`). Also report each file's individual byte size (tier-budget warnings: warn if a single always-loaded file exceeds a soft target, configurable `--file-target`, default report-only). Output `{chain_files, chain_bytes, cap, over_cap: bool, near_cap: bool, files:[{path,bytes}]}`.
**Test cases:** (a) single small `AGENTS.md` (100 bytes) → over_cap False, exit 0. (b) construct chain `root/AGENTS.md` + `root/sub/AGENTS.md` whose joined bytes ≥ 32768 (`--cwd sub`) → over_cap True, exit 1. (c) joined bytes between 0.9·cap and cap → near_cap True, exit 0, warning printed. (d) empty `AGENTS.md` skipped (contributes 0, not counted as a file). **Limits:** counts bytes not tokens; chain root approximated by `--root` (no git discovery required).

### Task 6: `symbol_exists.py` (v1)
**Files:** Create `scripts/symbol_exists.py`; Test `scripts/tests/test_symbol_exists.py`.
**Contract:** `symbol_exists.py [--root DIR] [--index INDEX.json] [paths/globs...] [--json]`. If `--index` omitted, attempt to build it by invoking `scripts/extract_symbols.sh --root DIR` (degrade to exit 2 with a skip message if that fails). Index shape per the shared contract. Exit 1 if a referenced symbol is missing.
**Algorithm:** Only validate **explicit** stable refs to avoid false positives: match the pattern `` `<symbol>(...)?` `` followed (within the same sentence/line) by `` in `<file>` `` — i.e. the documented convention "`createOrder()` in `src/api/orders.ts`". For each `(symbol, file)` pair, check the index contains an entry whose `symbol` matches (strip trailing `()`) AND whose `file` endswith the referenced file (or basename match). Report misses. Ignore bare `` `symbol()` `` without an `in `file`` clause (too noisy).
**Test cases:** (a) index `[{"symbol":"processPayment","kind":"function","file":"src/billing/charge.ts"}]`, doc says ``` `processPayment()` in `src/billing/charge.ts` ``` → pass. (b) doc says ``` `notReal()` in `src/billing/charge.ts` ``` → flagged. (c) doc says ``` `processPayment()` in `src/wrong.ts` ``` → flagged (file mismatch). (d) bare ``` `helper()` ``` with no `in `file`` → ignored. **Limits:** index language coverage; basename matching.

### Task 7: `dup_detect.py` (v1)
**Files:** Create `scripts/dup_detect.py`; Test `scripts/tests/test_dup_detect.py`.
**Contract:** `dup_detect.py [--root DIR] [paths/globs...] [--threshold 0.7] [--json]`. Flags doc blocks that duplicate source-of-truth; exit 1 if duplication found.
**Algorithm:** Primary check — package.json `scripts`: build the set of `"<name>": "<command>"` / `<name> <command>` strings; for each fenced code block in a doc, if it contains ≥3 (or ≥50%) of those script entries verbatim → flag "pasted package.json scripts". Generic check — for each fenced block, compute token-set Jaccard vs the content of each manifest/config file (`package.json`, `tsconfig.json`, `*.config.*`); if `>= threshold` → flag. Report `{file, kind, source, similarity}`.
**Test cases:** (a) doc fenced block containing the verbatim `"scripts"` entries from a fixture package.json → flagged. (b) doc that says "Build commands: see `package.json` scripts" (no paste) → NOT flagged. (c) unrelated prose → NOT flagged. **Limits:** tune threshold to avoid flagging legit short examples.

### Task 8: `extract_symbols.sh` (v1)
**Files:** Create `scripts/extract_symbols.sh`; Test `scripts/tests/test_shell_wrappers.sh` (covers this + the three validator wrappers).
**Contract:** `extract_symbols.sh [--root DIR] [--no-ctags]` → JSON array `[{"symbol","kind","file"}]` to stdout (shared contract).
**Algorithm:** Prefer Universal Ctags: detect via `ctags --version | grep -qi 'universal ctags'`; if present and not `--no-ctags`, run `ctags -R --output-format=json -f - <root>` and map fields (`name`→symbol, `kind`→kind, `path`→file relpath). Else **ripgrep fallback** (`rg`): match `export\s+(async\s+)?function\s+(\w+)`, `export\s+const\s+(\w+)`, `^\s*def\s+(\w+)`, `^\s*class\s+(\w+)`, `^\s*(?:pub\s+)?fn\s+(\w+)`, `func\s+(\w+)` with `--no-heading --line-number`? No — emit no line numbers; capture file + symbol + kind. If neither tool present → emit `[]` + stderr note, exit 0. Emit valid JSON (use `python3 -c` for safe JSON encoding from the shell to avoid escaping bugs).
**Test cases (in test_shell_wrappers.sh):** fixture `src/a.ts` with `export function processPayment(){}` → fallback output (`--no-ctags`) JSON contains symbol `processPayment` kind `function` file ending `src/a.ts`. **Limits:** language coverage; dynamic exports missed.

---

# Phase 2 — Shell validator wrappers + gate (after Phase 1 CLIs are final)

### Task 9: `validate_markdown.sh` (MVP)
**Files:** Create `scripts/validate_markdown.sh`.
`set -euo pipefail`. Usage `validate_markdown.sh [paths...]` (default `.`). If `node`/`npx` missing → print install hint, exit 2. Run `npx -y markdownlint-cli2 "$@"`. Pass through exit code. Comment header states boundary: **syntax/style + in-doc anchors only; no network, no path existence.**

### Task 10: `validate_mermaid.sh` (MVP)
**Files:** Create `scripts/validate_mermaid.sh`.
Usage `validate_mermaid.sh [--fix] [paths...]` (default `.`). npx-missing → exit 2 + hint. Run `npx -y @probelabs/maid --format json [--fix] "$@"`. Boundary comment: **validates flowchart/sequence/pie/class/state only; others pass through unvalidated.**

### Task 11: `check_links.sh` (v1)
**Files:** Create `scripts/check_links.sh`.
Usage `check_links.sh [--offline] [paths...]` (default `.`). Detect `lychee` on PATH (it is a Rust binary, NOT npx) → missing: print `brew install lychee` / `cargo install lychee` hint, exit 2. Run `lychee [--offline] --include-fragments "$@"`. Boundary comment: **links + local file-path existence + fragments.**

### Task 12: `run_gate.sh` (convenience)
**Files:** Create `scripts/run_gate.sh`.
Usage `run_gate.sh [--root DIR] [paths...]`. Runs the gate in order, each step skipping (not failing) if its external tool is absent, but **failing** on a real violation. Tracks an `errors` counter; prints a final PASS/FAIL summary; exit 1 if any blocking check failed. Order: validate_markdown → no_line_refs → path_exists → symbol_exists → check_links → validate_mermaid → dup_detect → size_check.

---

# Phase 3 — Plugin manifest, skills, templates, checklists, references, commands

### Task 13: `.claude-plugin/plugin.json`
Minimal-plus: `name` (required) `repo-docs`, `version` `0.1.0`, `description`, `keywords`. Skills/commands auto-discovered — do not enumerate.

### Task 14: Orchestrator `skills/repo-docs/SKILL.md` (MVP)
Per §14 draft. Frontmatter `name: repo-docs`, `description` = what (manage AI-facing repo docs for Claude Code + Codex: AGENTS.md + thin CLAUDE.md, audit, compress, stable-refs) + when (create/audit/fix/validate AGENTS.md/CLAUDE.md). Body < 200 words: "Route, don't do." Decision table mapping intents → `REQUIRED SUB-SKILL:` for the **six skills that exist in MVP+v1** (generate-agent-instructions, docs-audit, compress-docs, source-of-truth-map, stable-refs). Intents for not-yet-built skills (architecture, onboarding, adr, mermaid, drift) → note "not yet available (v2)". Non-negotiables list (1–6). Never `@path` force-load.

### Task 15: `skills/generate-agent-instructions/SKILL.md` (MVP)
What+when description (§14). Body: evidence-gated workflow — (1) run `${CLAUDE_PLUGIN_ROOT}/scripts/scan_repo.py` + `extract_scripts.py`; (2) draft `AGENTS.md` from `templates/AGENTS.md.tmpl` — six high-signal sections (commands+flags first, structure, code-style ✅/🚫 examples, testing, git/PR, ✅/⚠️/🚫 Boundaries) + source-of-truth pointer + update triggers; reference don't copy; stable refs; mark unknowns NEEDS VERIFICATION; (3) write `CLAUDE.md` from `templates/CLAUDE.md.tmpl` (`@AGENTS.md` + Claude-only block); (4) run the gate (`run_gate.sh`) incl. `size_check` (< 32 KiB); (5) show gate output, no "done" until it passes. REQUIRED BACKGROUND markers as needed. Points to `checklists/doc-quality.md`.

### Task 16: `skills/docs-audit/SKILL.md` (MVP)
What+when. Body: read-only audit of existing AGENTS.md/CLAUDE.md/docs against the durability principles + anti-patterns; run the gate scripts in audit mode; emit a prioritized findings report (issue → BP/AP tag → fix). No file writes.

### Task 17–19: v1 skills `compress-docs`, `stable-refs`, `source-of-truth-map`
Each: what+when description per §14; concise body (< 500 words) implementing the relevant scripts + principles. `compress-docs` → route detail to sub-docs, cut filler/dup, enforce 32 KiB (`size_check`, `dup_detect`). `stable-refs` → convert volatile refs to stable (§9 ranking), run `no_line_refs`/`symbol_exists`. `source-of-truth-map` → map which file owns each fact, run `dup_detect`.

### Task 20: Templates
`templates/AGENTS.md.tmpl` per §14 (commands-first, ✅/🚫 examples, ✅/⚠️/🚫 Boundaries, `Source of truth:`/`Update when:` footer). `templates/CLAUDE.md.tmpl` = `@AGENTS.md` + "Claude Code specifics" block.

### Task 21: `checklists/doc-quality.md`
The §12 manual checklist, TodoWrite-driven (one `- [ ]` per item), each tagged BP/AP, plus the automated-gate table mapping check → script → fails-on.

### Task 22: `references/` deep docs (v1)
`doc-taxonomy.md` (§8), `stable-references.md` (§9), `mermaid-rules.md` (§10), `codex-agents-md.md` (Appendix B), `agents-md-interop.md` (Appendix A). Condensed from DESIGN.md, self-contained.

### Task 23: Slash commands (thin, v1)
`commands/docs-audit.md`, `docs-generate.md`, `docs-validate.md`, `docs-fix.md` — each 5–15 lines, frontmatter `description` (+ `argument-hint` where useful), body invokes the orchestrator with a preset intent + `$ARGUMENTS`.

---

# Phase 4 — Verification & dogfood

### Task 24: Run all tests + the gate on a sample
- `python3 -m unittest discover -s scripts/tests -p 'test_*.py'` → all pass (show output).
- `bash scripts/tests/test_shell_wrappers.sh` → pass.
- Build a tiny sample repo with a deliberately-bad doc (line ref, dead path, oversized AGENTS.md, pasted scripts, broken Mermaid) and show `run_gate.sh` blocking on each.

### Task 25: Dogfood on the menv repo
- Run `scan_repo.py`/`extract_scripts.py` against `/Users/nikrabaev/Work/personal/menv`.
- Follow `generate-agent-instructions` to produce an `AGENTS.md` (commands-first, Boundaries, SoT pointer, < 32 KiB) + `CLAUDE.md` importer **in a scratch dir** (do not modify menv).
- Run the gate; confirm it passes and `size_check` reports < 32 KiB. Show output.

### Task 26: Code review + finalize
- REQUIRED SUB-SKILL: superpowers:requesting-code-review.
- Address findings; commit on a branch.

---

## Self-review notes
- **Spec coverage:** every MVP+v1 manifest item maps to a task (orchestrator T14; generate-agent-instructions T15; docs-audit T16; templates T20; checklist T21; scripts T1–T12; commands T23; v1 skills T17–19; v1 scripts T6–8,T11; references T22). v2/v3 items (architecture/onboarding/adr/mermaid/drift skills, extract_routes/schema/events, drift_check, score_docs) intentionally excluded.
- **Refuted claims:** descriptions are what+when (not when-only); no hard 500-line gate anywhere.
- **Type consistency:** symbol index shape fixed once (extract_symbols.sh ↔ symbol_exists.py). Exit-code convention uniform (0/1/2). `--root`/`--json` uniform.
