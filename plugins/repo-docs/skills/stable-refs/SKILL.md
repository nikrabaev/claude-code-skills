---
name: stable-refs
description: >
  Convert volatile documentation references (line numbers, copied code snippets,
  vague mentions) into stable ones — path+symbol, route, table/entity, config-key
  name, command, or test name — and verify they still resolve. Use when reviewing
  or writing references in agent docs, when a doc cites line numbers, or when asked
  how to reference a piece of code so the doc will not rot.
---

# Stable references (path+symbol over line numbers)

**Core principle:** cite the most stable identifier that still locates the thing.
Line numbers are the highest-churn reference — one edit above and they are wrong.
Outdated code-element references are an empirically widespread doc problem.

## Stability ranking (most → least durable — prefer the highest that locates it)

1. **Module / package** — `src/billing/`, `@acme/auth`
2. **Path + exported symbol** — `` `processPayment()` in `src/billing/charge.ts` `` (survives line moves; breaks only on rename, a reviewable event)
3. **Route / API** — `POST /api/v1/orders`
4. **DB table / entity** — `` `orders` table ``, `Order` entity
5. **Event / topic / queue** — `orders.created`, `payments` queue
6. **Config key (NAME, never value)** — `MENV_PASSPHRASE`, `max_connections`
7. **Test name** — test `"refunds on dispute"`
8. **Command / script** — `bun test`, `npm run build`
9. **File path only** — `src/index.ts` (when the whole file is the unit)
10. **❌ Line number** — never.

Backtick symbols/paths/commands; prefer prose-embedded refs ("see `createOrder()` in
`src/api/orders.ts`") so the role is unambiguous.

## Workflow

### 1. Find volatile references

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/no_line_refs.py --root .   # line refs
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/dup_detect.py  --root .    # copied snippets
```

### 2. Rewrite each up the ranking

`see line N` → `` `processPayment()` in `src/billing/charge.ts` ``.
A copied function body → the public-contract reference + a pointer to the file.
Don't document trivially-discoverable detail (npm/git/pytest output) or a linter
rule that a config already owns — point to the config.

### 3. Verify the new references resolve

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/path_exists.py   --root .
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/symbol_exists.py --root .   # uses extract_symbols.sh
```

`path_exists` confirms paths; `symbol_exists` confirms `` `symbol()` in `file` ``
references exist in the symbol index. Fix any miss, then re-run. Show the output.
