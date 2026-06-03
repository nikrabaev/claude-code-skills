# Pre-generation checklist

Before writing ANY generated doc, create a TodoWrite item for each box. Generation is
evidence-gated — inspect first, never guess. (BP-9)

## Inspect before you write

- [ ] Ran the read-only scanners for this doc type:
      `scan_repo.py` (always); `extract_scripts.py` (commands/onboarding);
      `extract_symbols.sh` (architecture/refs); `extract_routes.py` /
      `extract_schema.py` / `extract_events.py` (architecture/request-flow/domain).
- [ ] Read the top-level entry point(s) and one or two representative source files to
      confirm the stack — did not infer it from filenames alone.

## Know what you're writing

- [ ] Identified the doc type in `references/doc-taxonomy.md` and its allowed /
      forbidden content, length target, and source-of-truth.
- [ ] Know which file(s) **own** each fact so the doc references instead of copies.
- [ ] Have concrete evidence (a path / symbol / command you saw) for every planned
      claim. Anything without evidence will be marked
      `> [!WARNING] NEEDS VERIFICATION`, not invented.

## Budget

- [ ] Picked the size target for this doc type; for `CLAUDE.md`, the whole root→cwd
      chain must stay **within the verbosity budget** (`size_check.py`).
