# menv — agent guide

Bun-runtime TypeScript CLI: an age-encrypted environment-variable vault with an Ink + React terminal UI (Ink 5, React 18). Reads/writes TOML (`smol-toml`) and YAML.

## Commands

- Run (dev): `bun run src/index.ts`  (package alias: `bun menv`)
- Build a standalone binary: `bun build --compile --outfile menv src/index.ts`
- Test (all): `bun test`
- Test one file: `bun test tests/ui/editTarget.test.ts`
- Test by name: `bun test -t "editLabel"`
- (Full command list: see `package.json` scripts — not duplicated here.)

## Project structure

- `src/index.ts` — entry point; parses `Bun.argv` and dispatches subcommands.
- `src/cli/` — one module per subcommand (init, generate, set, get, list, wire, …).
- `src/core/` — shared domain types and model (`src/core/types.ts`).
- `src/crypto/` — age encryption and key backends (keychain, passphrase, 1Password).
- `src/store/` — repo model load/save plus the in-memory store (`createStore()` in `src/store/store.ts`).
- `src/io/` — on-disk vault and backup I/O.
- `src/ui/` — Ink/React components (`src/ui/components/`).
- `tests/` — `bun:test` specs mirroring `src/`.

## Code style

- TypeScript strict mode (`tsconfig.json`); ESM only (`"type": "module"`).
- Imports keep explicit `.ts` extensions — ✅ `import { createStore } from "./store/store.ts"`  🚫 omit the extension.
- Named exports — ✅ `export function runSet()`  🚫 `export default`.
- Ink UI is built from React function components.

## Testing

- Framework: `bun:test` (`import { expect, test } from "bun:test"`); Ink components via `ink-testing-library`.
- Test names are descriptive sentences; filter with `bun test -t "<name>"`.

## Git / PR workflow

> [!WARNING] NEEDS VERIFICATION
> No branch/commit/PR conventions were found in the repo during inspection. Confirm with the maintainer and fill this in (or point to a CONTRIBUTING doc).

## Boundaries

- ✅ Always: run `bun test` before declaring done; keep `.ts` extensions on imports.
- ⚠️ Ask first: changes to crypto or key backends (`src/crypto/`), the on-disk vault format (`src/io/`, `src/store/`), or dependency bumps.
- 🚫 Never: commit secrets, the age identity key, or decrypted values; reference line numbers; duplicate `package.json` / `tsconfig.json`.

---
Source of truth: `package.json`, `tsconfig.json`, `src/`. Update when: commands or stack change, a new subcommand or key backend lands, or the vault format changes.
