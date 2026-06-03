# Pre-commit checklist (docs)

Before committing generated or edited docs, create a TodoWrite item for each box. No
"done" until the gate output is shown and clean.

## Run the gate

- [ ] `bash ${CLAUDE_PLUGIN_ROOT}/scripts/run_gate.sh --root .` — every FAIL fixed.
      (SKIP just means a tool isn't installed; note it, don't score it.)
- [ ] Showed the gate output. [verification-before-completion]

## Spot-check the blocking classes

- [ ] No line-number references (`no_line_refs.py`). [AP-1]
- [ ] Referenced paths/symbols resolve (`path_exists.py` / `symbol_exists.py`). [BP-3]
- [ ] No duplicated source-of-truth (`dup_detect.py`). [BP-2]
- [ ] `CLAUDE.md` chain **within its verbosity budget** (`size_check.py`). [BP-8]
- [ ] Mermaid (if any) passed `maid`; no `click`/interactive links. [BP-12 / AP-15]

## Judgment

- [ ] Unknowns marked `> [!WARNING] NEEDS VERIFICATION`, not invented. [BP-9]
- [ ] No volatile/temporary detail in an always-loaded file. [BP-11]
- [ ] (ADRs only) No edit to an accepted ADR's body — superseded instead. [§8]
- [ ] (Optional, advisory) Ran `drift_check.py` and triaged any stale findings.
