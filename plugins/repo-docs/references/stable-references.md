# Stable reference strategy

**Principle** (empirically grounded — outdated code-element references are
widespread, arXiv:2212.01479): reference the most stable identifier that still
locates the thing.

## Stability ranking (most → least durable)

1. **Module / package** — `src/billing/`, `@acme/auth`
2. **Path + exported symbol** — `` `processPayment()` in `src/billing/charge.ts` ``
   (survives line moves; breaks only on rename — a reviewable event)
3. **Route / API** — `POST /api/v1/orders`
4. **DB table / schema object** — `` `orders` table ``, `Order` entity
5. **Event / topic / queue** — `orders.created`, `payments` queue
6. **Config key** — `MENV_PASSPHRASE`, `max_connections` (name, **never value**)
7. **Test name** — test `"refunds on dispute"`
8. **Command / script** — `bun test`, `npm run build`
9. **File path only** — `src/index.ts` (when the whole file is the unit)
10. **❌ Line number** — never.

## Conventions

- Backtick symbols / paths / commands.
- Prefer prose-embedded refs ("see `createOrder()` in `src/api/orders.ts`") so the
  role is unambiguous.
- The `no_line_refs` check must not mistake `host:port` or `::` for `:line` — it
  only flags a colon-number whose left side ends in a known code/file extension.

## When NOT to document code detail

- It's already the source of truth (scripts, lockfile versions, schema) → reference
  it; don't restate it.
- It's volatile implementation (a private helper's body) → omit; document the
  **public contract**.
- The agent discovers it trivially (`npm` / `git` / `pytest` output) → don't waste
  budget.
- It's temporary state ("mid-migration") → omit from durable docs.
- It would duplicate a linter/formatter rule → point to the config.

## How the plugin enforces this

- `no_line_refs.py` — fails on `path.ext:NNN` and `line NNN` (block).
- `path_exists.py` — backticked path tokens must resolve (block).
- `symbol_exists.py` (+ `extract_symbols.sh`) — `` `symbol()` in `file` ``
  references must exist in the symbol index (block).
- `dup_detect.py` — flags copied source-of-truth that should have been a reference.
