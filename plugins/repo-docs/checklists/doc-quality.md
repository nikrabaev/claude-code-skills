# Doc-quality checklist

A doc is **code** — it gets a gate. Create a TodoWrite item for each box below and
do not claim "done" until the automated gate output is shown and clean.

## Manual checklist (judgment calls)

- [ ] Every claim traces to a file / symbol / command actually inspected — no guessing. [BP-9]
- [ ] No line-number references anywhere. [AP-1]
- [ ] No duplicated source-of-truth (no pasted `package.json`/config/schema). [BP-2]
- [ ] AGENTS.md (whole root→cwd chain) under 32 KiB; each file within its tier budget. [BP-8 / AP-14]
- [ ] Boundaries section present with all three tiers (✅ Always / ⚠️ Ask first / 🚫 Never). [BP-5]
- [ ] Commands lead, with flags (including a single-test command). [BP-6]
- [ ] Stack named with versions, not vaguely described. [BP-7]
- [ ] Non-obvious code-style rules carry ✅/🚫 examples. [BP-13]
- [ ] Source-of-truth pointer + update triggers present (footer). [BP-10]
- [ ] No volatile/temporary detail in an always-loaded file. [BP-11]
- [ ] Mermaid (if any) validated, ≤ ~15–20 nodes, no `click`/interactive links. [BP-12 / AP-15]
- [ ] CLAUDE.md imports `@AGENTS.md` and adds NO duplicated facts. [file strategy]
- [ ] No `@`-imports in always-loaded files except CLAUDE.md's single `@AGENTS.md`. [AP-11]
- [ ] Human-facing content not mixed into agent files (README ≠ AGENTS.md). [BP-4]
- [ ] Unknowns marked `> [!WARNING] NEEDS VERIFICATION`, not invented. [BP-9]

## Automated gate

Run: `bash ${CLAUDE_PLUGIN_ROOT}/scripts/run_gate.sh --root .`

| Check | Script / tool | Blocks on |
|---|---|---|
| Markdown lint | `validate_markdown.sh` → markdownlint-cli2 | bad headings/lists/fences; in-doc anchor defects (MD051); link-defect rules |
| No line refs | `no_line_refs.py` | `path.ext:NNN`, `line NNN` |
| Dead path | `path_exists.py` (+ `check_links.sh` → lychee) | backticked path / link / local file path that does not exist |
| Symbol exists | `symbol_exists.py` (+ `extract_symbols.sh`) | `` `symbol()` in `file` `` reference with no definition |
| Mermaid valid | `validate_mermaid.sh` → maid | syntax error in flowchart/sequence/pie/class/state |
| SoT duplication | `dup_detect.py` | doc block that copied `package.json`/config |
| Size budget | `size_check.py` | over a tier target, or **over the Codex 32 KiB chain cap** |

**Policy:** errors (line refs, dead paths/symbols, broken links, invalid Mermaid,
duplicated source-of-truth, over 32 KiB) **block**. SKIP means the external tool
isn't installed — note it, don't score it. Warnings (near-cap, weak evidence)
report. Auto-repair only where safe (`maid --fix`, line-ref rewrite); otherwise
surface. **No "done" claim until the gate output is shown.**
