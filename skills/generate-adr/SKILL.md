---
name: generate-adr
description: >
  Create a new immutable Architecture Decision Record (Nygard/MADR) under
  /adr/NNNN-imperative-name.md and link supersessions — one decision per file,
  with status and date. Use when asked to record an architecture or technical
  decision, capture the rationale for a choice, or supersede a prior decision.
---

# Generate an ADR (immutable — supersede, don't edit)

**Core principle:** an ADR is a historical record. Once accepted, **you do not edit
its body.** To change a decision, write a NEW ADR that supersedes the old one. The
only permitted edit to a past ADR is flipping its **Status** line to point at the
superseding record.

`${CLAUDE_PLUGIN_ROOT}` is the plugin root.

## Workflow

### 1. Find the next number

```bash
ls adr/ docs/adr/ 2>/dev/null     # find the highest existing NNNN
```

ADRs live in `adr/` (or `docs/adr/`) as `NNNN-imperative-name.md`, zero-padded
(`0001`, `0002`, …). The next ADR is highest + 1.

### 2. Draft from the template

Copy `${CLAUDE_PLUGIN_ROOT}/templates/adr.md.tmpl` (delete the HTML comment). Fill:

- **One decision** — never bundle two. Title is imperative ("Use X for Y").
- **Status** (Proposed / Accepted / Superseded by …), **Date** (`YYYY-MM-DD`).
- **Context** (the forces — reference real modules with stable refs, no line numbers),
  **Decision** (active voice: "We will …"), **Options considered**, **Consequences**.

### 3. Superseding an existing decision

When this ADR replaces an older one:

1. Set the **new** ADR's `Supersedes:` to `ADR-KKKK`.
2. In the **old** ADR, change ONLY its `Status:` to `Superseded by [ADR-NNNN](NNNN-name.md)`.
   Touch nothing else in the old file.

This keeps reciprocal supersedes/superseded-by links and preserves history.

### 4. Run the gate

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/run_gate.sh --root . adr/NNNN-name.md
```

Show the gate output and the ADR. REQUIRED SUB-SKILL: superpowers:verification-before-completion.

## Red flags — STOP

- About to **edit the Context/Decision/Consequences of an accepted ADR** → STOP. Write
  a new superseding ADR instead. (Editing the Status line to mark supersession is the
  only allowed change.)
- Putting **two decisions** in one file → split them.
- "I'll just tweak the old one, it's basically the same decision" → no. New decision =
  new ADR.
