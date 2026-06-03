# Mermaid checklist

Create a TodoWrite item for each box. Never commit a diagram that has not passed
`maid`. Full rules: `references/mermaid-rules.md`.

## Before committing a diagram

- [ ] Diagram is one of the five `maid`-validated types: flowchart/`graph`,
      `sequenceDiagram`, `classDiagram`, `stateDiagram-v2`, `pie`. (Others pass
      through unvalidated — avoid them in committed docs.)
- [ ] Ran `validate_mermaid.sh --fix` then `validate_mermaid.sh` — clean. [BP-12]
- [ ] **≤ ~15–20 nodes**; labels ≤ ~40 chars. Split per subsystem/flow if larger.
- [ ] Labels containing `()[]{}:;,"#` are **quoted**: `A["process(payment)"]`. [AP-3]
- [ ] Flowchart arrows are `-->` (not `->`); sequence arrows `->>` / `-->>`.
- [ ] No bare `end` in a flowchart (capitalize: `End` / `END`).
- [ ] No leading `o`/`x` on an edge (`A---oB` makes an unintended circle/cross edge).
- [ ] Valid direction header: `TD` / `TB` / `BT` / `LR` / `RL`.
- [ ] **No `click` directives or interactive links** — GitHub's CSP blocks them; put
      links in prose. (maid will NOT catch this — check by hand.) [AP-15]
- [ ] Source under `maxTextSize` (50000) — a diagram that needs scrolling is a smell.

## Commands

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/validate_mermaid.sh --fix path/to/doc.md
bash ${CLAUDE_PLUGIN_ROOT}/scripts/validate_mermaid.sh path/to/doc.md
```
