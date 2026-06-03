# AGENTS.md interop matrix (Appendix A)

Why generating one excellent `AGENTS.md` is enough: it is read — natively or via the
open agents.md standard — by far more than Codex. This is the evidence behind
"out-of-scope generators (Cursor/Windsurf/Copilot/…) are unnecessary." Verified in
the research gap-closure pass.

| Tool | Reads `AGENTS.md`? | Notes |
|---|---|---|
| **OpenAI Codex** | ✅ native, canonical | root→cwd concat, closer-overrides, 32 KiB cap |
| **Claude Code** | ⚠️ not natively (early 2026) | gets it via `CLAUDE.md`'s `@AGENTS.md` import |
| **Cursor** | ✅ | plain-markdown `AGENTS.md` alternative to `.cursor/rules` |
| **Windsurf** | ✅ | root = always-on, subdir = glob `<dir>/**` |
| **Amp (Sourcegraph)** | ✅ canonical | `AGENTS.md` > `AGENT.md` > `CLAUDE.md` fallback |
| **JetBrains Junie** | ✅ | `.junie/AGENTS.md` or `AGENTS.md` |
| **Google Jules** | ✅ native | auto-reads root `AGENTS.md` |
| **Gemini CLI** | ⚙️ opt-in | default `GEMINI.md`; add `AGENTS.md` to `context.fileName` |
| **Cline** | ✅ (Nov 2025) | workspace-root + nested subdirs |
| **OpenHands** | ✅ recommended | root `AGENTS.md` always-on |
| **Roo Code** | ✅ (frozen) | reads `AGENTS.md`; project archived 2026-05-15 |
| **Continue** | ❓ unverified | no shipped auto-load confirmed |
| **Aider** | ❌ not auto | load via `--read`; `CONVENTIONS.md` is its idiom |
| **Amazon Q Developer** | ❌ | uses `.amazonq/rules/*.md` |
| **Replit** | ❌ not native | uses `replit.md` |

**Takeaway.** A single well-formed `AGENTS.md` covers Codex (the target) plus ~10
other agents for free; `CLAUDE.md`'s `@AGENTS.md` import covers Claude Code. Only
Aider, Amazon Q, and Replit use a different idiom — out of scope, and each is a thin
future add-on if ever needed.

## The file strategy this enables

`AGENTS.md` is the single source of truth. `CLAUDE.md` carries one line of
substance — `@AGENTS.md` — plus a short Claude-only block. Codex reads `AGENTS.md`
and ignores `CLAUDE.md`; Claude Code reads `CLAUDE.md` and pulls in `AGENTS.md` via
the import. One source of truth, two (plus ~10) readers, **zero duplicated facts to
drift apart.**
