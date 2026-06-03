<!--
  ANNOTATED BAD EXAMPLE. This file intentionally violates the rules so you can see
  what the gate catches. Each problem is tagged [AP-n] with the fix. Do NOT ship a
  file like this — every block below is an anti-pattern.
-->
# Our App

A modern, scalable TypeScript application using a microservices architecture.
<!-- [AP-4] hallucinated architecture: "microservices" with no evidence. If the
     repo is a monolith this actively misleads the agent. Fix: only claim what you
     inspected; mark unknowns "> [!WARNING] NEEDS VERIFICATION". -->
<!-- [AP-7] vague: "modern, scalable" is unactionable. Fix: name the stack +
     versions (e.g. "Bun runtime; Ink 5 + React 18 TUI"). -->

## Build

```
"dev": "vite",
"build": "tsc && vite build",
"test": "vitest",
"lint": "eslint ."
```
<!-- [AP-6] duplicated source-of-truth: the package.json scripts are pasted here
     and will drift. dup_detect flags this. Fix: "Build/test: see package.json
     scripts." -->

The auth flow is implemented at src/auth/session.ts:412.
<!-- [AP-1] line-number reference: wrong after one edit above it. no_line_refs
     flags this. Fix: `validateSession()` in `src/auth/session.ts`. -->

See the design notes in `docs/architecture-v2-DRAFT.md`.
<!-- dead path: that file doesn't exist. path_exists / lychee flag it. -->

We are currently mid-migration to the v2 API; for now use the old client.
<!-- [AP-9] volatile/temporary detail in an always-loaded file. Fix: omit from
     durable docs, or keep as a dated note outside AGENTS.md. -->

<!-- [AP-2/AP-14] MISSING: no Boundaries section (✅/⚠️/🚫). The single
     highest-signal section is absent — "Never commit secrets" especially.
     Also MISSING: a source-of-truth pointer + update triggers footer. -->
