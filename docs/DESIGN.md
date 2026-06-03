# Blueprint: an AI repository-documentation mega-skill for Claude Code + Codex

**A research-backed design for `repo-docs` — a Superpowers-style Claude Code skill that generates, maintains, and quality-controls AI-facing repository documentation, targeting Claude Code and OpenAI Codex.**

> **Scope (v2, narrowed).** The skill *ships* as a Claude Code skill (root entry skill + sub-skills + slash commands + scripts + templates + checklists + validators). It *emits* exactly two agent-instruction artifacts: **`AGENTS.md`** (canonical; read by Codex and ~25 other tools) and **`CLAUDE.md`** (a thin `@AGENTS.md` importer + Claude-Code-specific pointers). It also produces durable Markdown docs (architecture, onboarding, local-dev, deployment, troubleshooting, ADRs) and validated Mermaid. Generators for Cursor / Windsurf / Copilot / Continue / etc. are **out of scope** — but because those tools also read `AGENTS.md` (see Appendix A), a good `AGENTS.md` travels to them for free.
>
> **File strategy (decided):** `AGENTS.md` is the single source of truth; `CLAUDE.md` is `@AGENTS.md` + a short Claude-only section. Codex ignores `CLAUDE.md`; Claude Code doesn't natively auto-load `AGENTS.md` — so this pairing gives both agents the same always-on context with **zero duplication and no cross-file drift.**

## Evidence legend

Every major recommendation is tagged:

- **[OFFICIAL]** — vendor/tool maintainer docs.
- **[EMPIRICAL]** — research paper, benchmark, or measured result.
- **[EXPERT]** — respected practitioner / maintainer.
- **[OBSERVED]** — inferred from multiple real repos/tools.
- **[SYNTHESIS]** — reasoned recommendation where direct evidence is thin (my logic, not an authority).

Claims marked **(verified N-0)** survived adversarial verification during research (vote shown). Two original research claims were **refuted** and are called out where relevant. This v2 integrates a second, gap-closure research pass that verified Mermaid rendering/validation, doc-tooling capabilities, Codex semantics, and the empirical doc-drift literature — so several v1 `[SYNTHESIS]` items are now `[OFFICIAL]` or `[EMPIRICAL]`.

---

## 1. Executive summary

**Thesis (confirmed by research).** Build the skill the way Anthropic and Superpowers build skills: a **short, always-loaded entry point** whose frontmatter `description` drives routing, plus **deep, on-demand sub-skills** that cost almost nothing until invoked. Apply the *same* principle to the docs the skill produces. Both rest on one empirically established fact: **long-context degradation ("context rot") is real across every frontier model**, and feeding an agent only the relevant ~300 tokens beats feeding it 113k tokens that merely *contain* the answer (Chroma, July 2025; independently replicated EMNLP 2025; restated by Anthropic). **[EMPIRICAL, verified 3-0]**

**Why Claude Code + Codex is a clean target.** The two converge on the same discipline from opposite directions:
- **Claude Code** keeps the always-loaded layer (`CLAUDE.md`) small and pushes depth into **skills** that load on demand — "a skill's body loads only when used, so long reference material costs almost nothing." **[OFFICIAL, verified 3-0]**
- **Codex** enforces a **hard 32 KiB cap** on the concatenated `AGENTS.md` chain (`project_doc_max_bytes`, default 32768), **skips empty files, stops at the limit, and silently truncates** anything over it (issue openai/codex#7138). It concatenates files from git root down to cwd, blank-line-joined, with closer files overriding earlier ones. **[OFFICIAL, verified 3-0]**

So both agents *punish* a bloated always-loaded file — Codex literally drops bytes past 32 KiB without telling you. The skill's prime directive writes itself: **keep `AGENTS.md` small and durable; route everything else.**

**The drift-proof file design (your decision).** `AGENTS.md` is canonical. `CLAUDE.md` is one line of substance — `@AGENTS.md` — plus a short Claude-only block (skill/command pointers). Codex reads `AGENTS.md` and ignores `CLAUDE.md`; Claude Code reads `CLAUDE.md` and pulls in `AGENTS.md` via the import. One source of truth, two readers, no duplicated facts to drift apart. **[SYNTHESIS built on two OFFICIAL mechanisms: Claude `@`-import + Codex AGENTS.md-only loading]**

**Seven durable design principles** (priority order):
1. **Progressive disclosure** — small always-loaded layer, deep optional layer. **[OFFICIAL + EMPIRICAL]**
2. **Reference, don't copy** — point to source-of-truth files; copies go stale. **[OFFICIAL — Cursor verbatim; EMPIRICAL — drift literature]**
3. **Stable references over volatile detail** — path+symbol, route, table, command, test name; never line numbers. **[EMPIRICAL — outdated code-element references are widespread, arXiv:2212.01479]**
4. **Validate every claim against the repo** — "do not guess"; mark unknowns explicitly. **[SYNTHESIS + EXPERT]**
5. **Separate human-facing from AI-facing docs** — README is for humans; `AGENTS.md` is the agent's place. **[OFFICIAL — agents.md]**
6. **Budget by load frequency / hard caps** — the more often a file loads, the tighter; never exceed Codex's 32 KiB. **[OFFICIAL + EXPERT]**
7. **Make docs self-maintaining** — every durable doc carries update triggers + a source-of-truth pointer, so drift is detectable. **[SYNTHESIS; problem is EMPIRICAL — ICSE 2019 taxonomy]**

**What the skill does.** (a) **Audits** existing AI docs against these principles and scores them; (b) **generates** the `AGENTS.md`/`CLAUDE.md` pair + durable docs per a strict taxonomy with allowed/forbidden content per type; (c) **validates** outputs automatically — no line refs, no broken links, no dead paths, no broken Mermaid, no duplicated source-of-truth, every claim evidence-backed, **AGENTS.md under 32 KiB**; (d) **repairs/compresses** bad existing docs. Generation is **evidence-gated**: inspect the repo with read-only commands first, record findings, and refuse to write claims it couldn't verify (emitting a `NEEDS VERIFICATION` marker instead).

**Evidence health.** The architecture, the Codex/Claude semantics, the Mermaid rules, the validator tooling, and the doc-drift problem are now all **verified (OFFICIAL or EMPIRICAL)**. Remaining `[SYNTHESIS]`: specific size *targets* for durable docs, the exact doc taxonomy boundaries, and the doc-quality score weighting — these are reasoned, not authoritative, and are flagged inline.

---

## 2. Landscape map

Scoped to what matters for a **Claude Code + Codex** skill. "Influence" = should it shape `repo-docs`?

### 2a. The two target formats

| Format | What it is | Good for | Constraints to respect | Influence |
|---|---|---|---|---|
| **`CLAUDE.md`** (Claude Code) [OFFICIAL] | Always-loaded project memory; supports `@path` imports; `/init` bootstraps it. | The Claude-Code always-on layer. | `@`-imports force-load (fine for the canonical `AGENTS.md`; dangerous for big reference files). [EXPERT] | **High** — emitted as a thin `@AGENTS.md` importer. |
| **`AGENTS.md`** (Codex + open standard) [OFFICIAL] | Codex concatenates root→cwd, blank-line-joined, closer-overrides; global `~/.codex/AGENTS.md`; `AGENTS.override.md` layer; **hard 32 KiB cap, silent truncation past it**. Also the open agents.md standard read by ~25 tools. [verified 3-0] | One canonical agent doc both Codex and (via import) Claude read — and most other agents too. | **32 KiB concatenated cap**; nested files override; over-cap tail dropped silently → must warn before the cap. | **Very high** — the canonical artifact and the skill's center of gravity. |

### 2b. Claude Code skill substrate (how the skill is built)

| Item | What it is | Influence |
|---|---|---|
| **Agent Skills** [OFFICIAL] | Folders of instructions + scripts + resources; three-level progressive disclosure (metadata always-loaded ~100 tokens; SKILL.md body on trigger; bundled files on demand). Description drives selection among 100+ skills (what + when, third person, ≤1024 chars). 500-line SKILL.md is a **target, not a hard limit** (the "hard 500-line" claim was **refuted 1-2**). [verified] | **Foundational.** |
| **Superpowers** (obra/superpowers) [EXPERT] | Canonical structural model: composable skills in a **flat searchable namespace** (not a nested tree), SKILL.md per skill, auto-activation under a "1% rule," word budgets (getting-started <150 words, frequently-loaded <200, others <500), `REQUIRED SUB-SKILL:` markers, explicit anti-`@`-syntax warning ("@ force-loads 200k+ context before you need it"). [verified 3-0] | **Very high** — the structural template; adapt "flat namespace," not a literal root+children tree. |
| **`/init`** [OFFICIAL] | Bootstraps `CLAUDE.md` by scanning the repo. | **High (the baseline to beat)** — no stable-ref discipline, no size budget, no validation; `repo-docs` post-processes its output. |

### 2c. Empirical foundation, diagram & validation tooling

| Item | What it is | Influence |
|---|---|---|
| **Context-rot research** (Chroma; EMNLP 2025 arXiv:2510.05381; Lost-in-the-Middle arXiv:2307.03172; Anthropic) [EMPIRICAL] | Accuracy degrades with input length even at 100% retrieval; mid-context info used worst. [verified 3-0] | **The justification** for routed/minimal context. |
| **Doc-drift research** (Tan/Wagner/Treude arXiv:2212.01479; Aghajani et al. ICSE 2019) [EMPIRICAL] | 3,000+ GitHub projects mostly contain ≥1 outdated code-element reference; outdated/incomplete/inconsistent are the leading doc-issue categories (878-artifact taxonomy). [verified] | **High** — empirical grounding for stable-refs + drift detection. |
| **`maid`** (`@probelabs/maid`, v0.0.29, TypeScript) [OFFICIAL tool] | Mermaid **validator** without a browser. Actively validates flowchart/sequence/pie/class/state; other types pass through unvalidated. `--fix`, `--format json`, `--strict`, exit 0/1, pre-commit + GH Actions, MCP/SDK modes, "render guarantee." [verified] | **High** — the Mermaid gate. |
| **`@mermaid-js/mermaid-cli` (`mmdc`, v11.15.0)** + **`mermaid.parse()`** [OFFICIAL tool] | Render-based validation (no `--validate`; validate by rendering); Puppeteer/Chromium (heavy). `mermaid.parse(text, {suppressErrors})` returns `{diagramType}`/false/throws. [verified] | **Medium** — optional render-accurate check. |
| **`markdownlint-cli2`** [OFFICIAL tool] | Markdown syntax/style; **no network, no path-existence**; MD051 checks in-doc anchors, MD011/034/039/042/052/053/054/059 cover link defects. [verified] | **High** — base lint gate. |
| **`lychee`** (Rust, v0.24.2) [OFFICIAL tool] | Checks URLs, email (opt-in), **local file-path existence**, and fragments (`--include-fragments` none/anchor-only/text-only/full); `--offline`, `--root-dir`, `--base-url`, `--exclude(-path)`. [verified] | **High** — link + dead-path gate. |
| **`tree-sitter tags` / `universal-ctags` / `ripgrep`** [OFFICIAL tools] | Symbol-definition indexes (`@definition.*`/`@reference.*`, `queries/tags.scm`) and fast gitignore-aware search — the primitives for **symbol-existence** checks and the Tan-et-al. stale-reference technique. [verified] | **High** — stable-ref extraction + drift detection. |
| **`Vale`** [OFFICIAL tool] | Prose linter, 11 extension points; operates only on document text — **cannot verify codebase symbols**; rule files must end `.yml`. [verified] | **Medium** — encode "no line numbers," banned hedge words as regex rules. |

**Net read:** the formats agree on the principles but enforce nothing; `/init` generates but with no discipline; the validators exist but aren't wired into a generation workflow. `repo-docs`'s unique value is to **fuse evidence-gated generation + the durability principles + automated validation into one routed workflow, sized for Codex's hard cap.**

---

## 3. Authority map

### Major AI companies / official tools
- **Anthropic — Agent Skills + context-engineering docs/blogs.** Three-level progressive disclosure; "skill body loads only when used"; description drives selection; SKILL.md <500 lines is a target. **[OFFICIAL, verified 3-0]**
- **OpenAI — Codex `AGENTS.md` guide + config reference + issue #7138.** Root→cwd concatenation, closer-overrides, global + project scope, `AGENTS.override.md`, **32 KiB cap with silent truncation**. The strongest cross-vendor evidence for a hard byte budget. **[OFFICIAL, verified 3-0]**
- **agents.md (open standard, Linux Foundation / Agentic AI Foundation).** `AGENTS.md` ≠ README; root + nested nearest-wins; 60k+ projects; adopters include Codex, Cursor, Jules, Amp, Factory, JetBrains Junie. **[OFFICIAL]**
- **GitHub — "lessons from 2,500+ AGENTS.md repos."** Near-empirical: lead with commands+flags; six high-signal sections; ✅/⚠️/🚫 boundaries; "Never commit secrets" highest-value; specificity-with-versions beats verbosity. **[OBSERVED-empirical]**

### Researchers / empirical sources
- **Chroma "Context Rot" + EMNLP 2025 (arXiv:2510.05381) + Lost-in-the-Middle (arXiv:2307.03172) + Anthropic.** Length-degradation; the routed-context backbone. **[EMPIRICAL, verified 3-0]** (Chroma COI mitigated by independent replication.)
- **Tan, Wagner & Treude — "Detecting Outdated Code Element References" (arXiv:2212.01479).** 3,000+ projects; most carry ≥1 outdated code-element reference; detects references that survive after all source instances are deleted. **[EMPIRICAL]** — directly grounds stable-refs + the drift script.
- **Aghajani et al. — "Software Documentation Issues Unveiled" (ICSE 2019).** 878 artifacts; taxonomy where outdated/incomplete/inconsistent lead. **[EMPIRICAL]** — grounds doc-drift as measurable.

### OSS maintainers / tooling / examples
- **obra/Superpowers** — structural template, word budgets, `REQUIRED SUB-SKILL:`. **[EXPERT, verified 3-0]**
- **probelabs/maid** — AI-era Mermaid validator. **[OFFICIAL tool, verified]**
- **joelparkerhenderson/architecture-decision-record** — ADR templates (Nygard/MADR), immutability/supersede. **[OBSERVED]**
- **lycheeverse/lychee, DavidAnson/markdownlint(-cli2), tree-sitter, universal-ctags, BurntSushi/ripgrep, errata-ai/Vale** — the validator stack, capabilities verified. **[OFFICIAL tools, verified]**
- **humanlayer.dev "Writing a good CLAUDE.md"** — CLAUDE.md anti-patterns. **[EXPERT, blog]**

**Disagreement preserved — "big always-loaded file" vs "small routed skills":** resolved asymmetrically. Context cost/reliability → routed wins (context rot is empirical + Codex truncates at 32 KiB). Retrieval certainty → always-loaded wins (a fact in `AGENTS.md` is guaranteed present; a sub-skill fact loads only if routing fires on a good `description`). Maintainability → routed wins (small files rot locally). **Resolution:** put the facts an agent needs on *every* task (commands, hard guardrails, where things live) in `AGENTS.md`; route the rest to skills/sub-docs. The dividing question is *frequency of need*, not *importance*.

---

## 4. Best-practices catalog

Each: problem · why · good · bad · manual · automatic · where it lives · evidence.

### BP-1 — Progressive disclosure (small always-loaded, deep on-demand)
Problem: bloated instruction files degrade reliability and (for Codex) get truncated. Why: context rot + the 32 KiB cap. **[OFFICIAL+EMPIRICAL]** Good: 30–60-line `AGENTS.md` (commands, guardrails, "where things live," pointers) + deep docs/skills loaded on demand. Bad: a 1,200-line `AGENTS.md` (Codex silently drops the tail). Manual: "is this needed on *every* task?" Automatic: `size-check` warns vs 32 KiB and the per-tier target; `audit` flags oversized always-loaded files. Where: orchestrator + `compress-docs` + `size-check` script.

### BP-2 — Reference, don't copy
Problem: duplicated source-of-truth goes stale silently. Why: "keeps rules short and prevents staleness as code changes" [OFFICIAL — Cursor]; outdated references are empirically widespread [EMPIRICAL — arXiv:2212.01479]. Good: "Build commands: see `package.json` scripts"; "Auth flow in `src/auth/`, see `login()` in `src/auth/session.ts`." Bad: pasting the npm-scripts list or a function body. Manual: "does a source-of-truth file already own this?" Automatic: `dup-detect` flags doc blocks matching `package.json`/config/source. Where: `source-of-truth-map` sub-skill + `dup-detect` + checklist. **[OFFICIAL + EMPIRICAL]**

### BP-3 — Stable references instead of line numbers
Problem: `src/app.ts:412` is wrong after one edit above it. Why: line numbers are the highest-churn reference; outdated code-element references persist in docs across history. **[EMPIRICAL — arXiv:2212.01479]** Good: `` `processPayment()` in `src/billing/charge.ts` ``; `POST /api/v1/orders`; `` `orders` table ``; test `"refunds on dispute"`. Bad: "see line 412." Manual: ban line numbers in review. Automatic: `no-line-refs` regex gate fails CI; `drift-check` uses a symbol index (tree-sitter/ctags) to flag references whose target no longer exists. Where: `stable-refs` sub-skill + `no-line-refs`/`drift-check` scripts. See §9.

### BP-4 — Separate human-facing from AI-facing docs
Problem: mixing audiences bloats both. Why: "README is for humans; AGENTS.md complements with the context agents need." [OFFICIAL — agents.md] Good: README = quickstart; `AGENTS.md` = agent operating context. Bad: README with a 200-line "instructions for AI" appendix. Where: taxonomy (§8) + `docs-audit`. **[OFFICIAL]**

### BP-5 — Boundaries with explicit tiers (✅ Always / ⚠️ Ask first / 🚫 Never)
Problem: agents take destructive/out-of-scope actions. Why: in 2,500-repo data, boundary-setting correlated most with success; "Never commit secrets" was highest-value. **[OBSERVED-empirical]** Good: a "Boundaries" section with the three tiers + 5–10 specific rules. Bad: no guardrails. Where: `AGENTS.md` template + checklist.

### BP-6 — Lead with executable commands (with flags)
Problem: agents waste turns rediscovering build/test commands. Why: "put executable commands in an early section … include flags." **[OBSERVED-empirical]** Good: `` Test: `bun test` · single: `bun test tests/ui/scopes.test.ts` ``. Bad: "run the tests." Automatic: `extract-scripts` proposes them from `package.json`/`Makefile`/`justfile`. Where: `AGENTS.md` template + `extract-scripts`.

### BP-7 — Specificity with versions over vague description
Problem: "React project" gives nothing actionable. Why: specific stack-with-versions beats vague descriptions. **[OBSERVED-empirical]** Good: "Bun runtime (not Node); Ink+React TUI; age-encrypted vault." Bad: "a TypeScript app." Automatic: extract from lockfiles/manifests. Where: template + `scan-repo`.

### BP-8 — Budget by load frequency AND respect hard caps
Problem: every always-loaded token is paid on every task; Codex drops bytes past 32 KiB. Why: Superpowers budgets (<150/<200/<500 words) [EXPERT] + Codex 32 KiB cap [OFFICIAL]. Good: tiered budgets; `AGENTS.md` well under 32 KiB (target ≤ ~1–2 pages). Bad: uniform "keep it short" with no numbers. Automatic: `size-check` warns per tier and at the Codex cap. Where: writing standards + `size-check`. **[OFFICIAL + EXPERT]**

### BP-9 — Evidence-gated generation ("do not guess")
Problem: agents invent architecture from partial evidence. Why: hallucinated docs are worse than none — they mislead. **[SYNTHESIS]** Good: every non-trivial claim traces to a file/command actually inspected; unknowns get `> [!WARNING] NEEDS VERIFICATION`. Bad: "uses a microservices architecture" with no evidence. Automatic: `claim-evidence` requires a path/symbol/command near architectural claims; `path-exists`/`symbol-exists` verify them. Where: core workflow + `docs-audit`/`docs-quality-review` + scripts.

### BP-10 — Update triggers + source-of-truth pointer in every durable doc
Problem: docs drift because nothing says when to revisit. Why: drift is the dominant long-term failure and is empirically measurable. **[EMPIRICAL problem; SYNTHESIS mechanism]** Good: footer — `Source of truth: src/billing/. Update when: new payment provider or charge-flow change.` Bad: undated doc, no ownership. Automatic: template scaffolds it; `drift-review` cross-checks doc mtime vs referenced-path git mtime and dead refs. Where: all templates + `docs-drift-review`.

### BP-11 — Confidence + stability tiering of facts
Problem: volatile detail documented as stable architecture rots fast. Why: a fact's lifetime should match where it's written. **[SYNTHESIS]** Good: stable (public contracts, module boundaries) → durable docs; semi-stable (conventions) → `AGENTS.md`; volatile (current refactor) → omit or dated note. Bad: "we're mid-migration to v2" in permanent `AGENTS.md`. Automatic: lint for volatility markers ("currently," "for now," "TODO," dates) in always-loaded files. Where: writing standards + `docs-audit`.

### BP-12 — Diagram discipline (small, validated Mermaid)
Problem: broken/oversized Mermaid that doesn't render. Why: GitHub renders nothing on a syntax error; Mermaid fails past `maxTextSize` 50000; `strict` security blocks `click`. **[OFFICIAL, verified]** Good: ≤~15–20 nodes, quoted labels, validated with `maid`. Bad: 60-node graph, unquoted special chars, `click` links (silently inert on GitHub). Automatic: `maid` in pre-commit/CI. Where: `mermaid-diagrams` sub-skill + `validate-mermaid`. See §10.

### BP-13 — Provide good *and* bad examples
Problem: rules without examples are interpreted inconsistently. Why: real code examples beat abstract explanation. **[OBSERVED-empirical]** Good: "Named exports only — `export function x()` ✅, `export default` 🚫." Bad: "follow good code style." Where: templates + checklist.

---

## 5. Anti-pattern catalog

| # | Anti-pattern | Example | Why harmful | Skill response | Evidence |
|---|---|---|---|---|---|
| AP-1 | **Line-number references** | "see line 412" | Wrong after any edit above; outdated code-element refs persist in docs across history | Detect `no-line-refs` gate; repair → path+symbol; `drift-check` via symbol index | **[EMPIRICAL — arXiv:2212.01479]** |
| AP-2 | **Oversized always-loaded file** | 1,200-line `AGENTS.md` | Context rot; **Codex silently truncates past 32 KiB** | Prevent budget gate; detect `size-check` (warns at 32 KiB); repair `compress-docs` | **[EMPIRICAL + OFFICIAL]** |
| AP-3 | **Broken Mermaid** | unquoted `()`/`[]`, `->` vs `-->`, lowercase `end` | Renders blank on GitHub = negative value | Detect/repair `maid --fix` gate | **[OFFICIAL, verified]** |
| AP-4 | **Hallucinated architecture** | "event-bus microservices" in a monolith | Actively misleads the agent | Prevent evidence-gating + `NEEDS VERIFICATION`; detect `claim-evidence`/`path-exists` | **[SYNTHESIS]** |
| AP-5 | **Stale docs** | doc describes deleted module | Agent follows obsolete map | Prevent update-trigger footers; detect `drift-review` (mtime + dead paths + dead symbols) | **[EMPIRICAL — ICSE 2019]** |
| AP-6 | **Duplicated source-of-truth** | npm scripts pasted into `AGENTS.md` | Copies diverge; doc lies | Prevent reference-don't-copy; detect `dup-detect` | **[OFFICIAL + EMPIRICAL]** |
| AP-7 | **Vague rules** | "write clean code" | Unactionable; can't comply/verify | Prevent require example + verifiable criterion; detect hedge-word lint (Vale) | **[OBSERVED-empirical]** |
| AP-8 | **Conflicting rules** | "tabs" + "spaces" | Agent picks arbitrarily | Detect `conflict-scan`; repair consolidate | **[SYNTHESIS]** |
| AP-9 | **Over-specific temporary detail** | "mid-migration to v2" in permanent file | False fast; embeds assumptions as rules | Prevent stability tiering; detect volatility-marker lint | **[SYNTHESIS]** |
| AP-10 | **Missing validation** | no CI on AI docs | Drift ships unnoticed | Prevent ship the gate + CI snippet | **[SYNTHESIS]** |
| AP-11 | **`@`-import / force-load bloat** | `@docs/huge.md` in `AGENTS.md` | Force-loads 200k+ tokens early | Prevent reserve `@` for the canonical `AGENTS.md` only; detect `@`-in-always-loaded lint | **[EXPERT]** |
| AP-12 | **Over-constraining future agents** | rigid scripts forbidding judgment | Breaks when reality differs | Prevent "principles + examples, not rigid scripts"; detect audit heuristic | **[SYNTHESIS]** |
| AP-13 | **Mixed human/AI docs** | README with AI appendix | Wrong audience; both bloat | Prevent separation taxonomy; detect audit | **[OFFICIAL]** |
| AP-14 | **Codex silent truncation** | 40 KiB `AGENTS.md` vs 32 KiB cap | Tail dropped; agent misses rules it "has" | Detect `size-check` warns before the cap; repair compress/route | **[OFFICIAL — #7138]** |
| AP-15 | **Mermaid `click`/interactive links on GitHub** | clickable nodes linking to URLs | Blocked by GitHub CSP (renders in sandboxed iframe); links silently inert | Detect lint for `click`/`<a>` in committed Mermaid; repair remove or move to prose link | **[OBSERVED, verified]** |

---

## 6. Good and bad examples

> Short quotes only; summaries otherwise.

**Good — Codex `AGENTS.md` guide.** Documents concatenation, closer-overrides, and the **32 KiB cap**. *Lesson:* size and cascade-awareness are first-class; the generator must budget the whole root→cwd chain. *Caveat:* `AGENTS.override.md` and global scope add layers the simple generator can skip initially. **[OFFICIAL]**

**Good — agents.md spec.** Human/agent separation; nested nearest-wins; high-signal section list. *Lesson:* adopt the taxonomy and "separate from README." *Caveat:* "no required schema" → quality still depends on the author; the skill adds the discipline. **[OFFICIAL]**

**Good — GitHub "2,500-repo" analysis.** Six-section structure + ✅/⚠️/🚫 boundaries. *Lesson:* base the `AGENTS.md` template on it. *Caveat:* Copilot-corpus selection bias. **[OBSERVED-empirical]**

**Good — Superpowers `writing-skills/SKILL.md`.** Word budgets, `REQUIRED SUB-SKILL:`, `@`-syntax warning. *Lesson:* copy the budget discipline. *Caveat:* single-maintainer; flat namespace. **[EXPERT]**

**Good — joelparkerhenderson/ADR repo.** Nygard/MADR templates + immutability/supersede. *Lesson:* the ADR sub-skill template. **[OBSERVED]**

**Bad (pattern) — default `/init` output, unrefined.** No stable-ref discipline, no size budget, no validation. *Lesson:* `repo-docs` post-processes `/init` through audit + compress + validate. **[OBSERVED]**

**Bad (pattern) — accreted monolith `AGENTS.md`.** Grows to hundreds of lines; for Codex the tail past 32 KiB is silently dropped. *Lesson:* `compress-docs` exists for this. **[EXPERT + OFFICIAL]**

**Bad (pattern) — LLM-generated Mermaid that doesn't render.** `maid` exists because AI diagrams routinely break (unquoted labels, `->`, lowercase `end`). *Lesson:* never commit a diagram that hasn't passed `maid`. **[OFFICIAL tool]**

---

## 7. Recommended mega-skill architecture

**Structural decision:** a Claude Code **plugin = a flat set of sibling skills** + one **orchestrator** (matching Superpowers' real flat namespace, not a nested tree). "Sub-skill" = a sibling skill the orchestrator routes to via its `description`. Editor-rules generators (Cursor/Windsurf/Copilot) are **removed** at this scope.

### 7a. Folder structure
```
repo-docs/
├── .claude-plugin/plugin.json
├── commands/
│   ├── docs-audit.md
│   ├── docs-generate.md
│   ├── docs-validate.md
│   └── docs-fix.md
├── skills/
│   ├── repo-docs/SKILL.md                 # ORCHESTRATOR / router
│   ├── docs-audit/SKILL.md
│   ├── generate-agent-instructions/SKILL.md   # AGENTS.md (canonical) + CLAUDE.md (importer), Codex-cap-aware
│   ├── generate-architecture-doc/SKILL.md
│   ├── generate-onboarding-doc/SKILL.md
│   ├── generate-adr/SKILL.md
│   ├── mermaid-diagrams/SKILL.md
│   ├── docs-drift-review/SKILL.md
│   ├── compress-docs/SKILL.md
│   ├── source-of-truth-map/SKILL.md
│   ├── stable-refs/SKILL.md
│   ├── docs-quality-review/SKILL.md
│   └── refactor-bad-docs/SKILL.md
├── scripts/
│   ├── scan_repo.py
│   ├── extract_scripts.py
│   ├── extract_symbols.sh                  # tree-sitter/ctags/ripgrep
│   ├── extract_routes.py
│   ├── extract_schema.py
│   ├── extract_events.py
│   ├── validate_markdown.sh                # markdownlint-cli2
│   ├── validate_mermaid.sh                 # maid
│   ├── check_links.sh                      # lychee
│   ├── no_line_refs.py
│   ├── path_exists.py
│   ├── symbol_exists.py                    # uses extract_symbols index
│   ├── dup_detect.py
│   ├── size_check.py                       # tier budgets + Codex 32 KiB
│   ├── drift_check.py
│   └── score_docs.py
├── templates/
│   ├── AGENTS.md.tmpl
│   ├── CLAUDE.md.tmpl                       # @AGENTS.md + Claude-only block
│   ├── architecture-overview.md.tmpl
│   ├── onboarding.md.tmpl
│   ├── adr.md.tmpl
│   └── ai-operating-manual.md.tmpl
├── checklists/
│   ├── pre-generation.md
│   ├── doc-quality.md
│   ├── mermaid.md
│   └── pre-commit.md
├── references/
│   ├── doc-taxonomy.md                      # §8
│   ├── stable-references.md                 # §9
│   ├── mermaid-rules.md                     # §10 (verified)
│   ├── verbosity-budgets.md                 # §11 (incl. Codex 32 KiB)
│   ├── codex-agents-md.md                   # Appendix B
│   ├── agents-md-interop.md                 # Appendix A
│   └── evidence-levels.md
└── examples/
    ├── good/  (annotated)
    └── bad/   (annotated with the fix)
```

### 7b. Orchestrator `skills/repo-docs/SKILL.md`
Small (<200-word body). Classifies the request and routes via `REQUIRED SUB-SKILL:`; never does the work itself. `description` = *what* (manage AI-facing repo docs for Claude Code + Codex) + *when* (create/audit/fix `AGENTS.md`/`CLAUDE.md`, architecture/onboarding docs, ADRs, diagrams).

### 7c. Slash commands (thin)
`/docs-audit`, `/docs-generate <type>`, `/docs-validate`, `/docs-fix` — each a 5–15-line file invoking the orchestrator with a preset intent.

### 7d. Validation workflow (the spine)
Every generator ends by running the **gate** (§12): `validate_markdown` → `no_line_refs` → `path_exists` → `symbol_exists` → `check_links` → `validate_mermaid` (if diagrams) → `dup_detect` → `size_check` → `score_docs`. **No "done" until the gate passes** (`verification-before-completion`). Safe auto-repairs (`maid --fix`, line-ref rewrite) applied; otherwise surfaced.

### 7e. Routing/activation
Orchestrator `description` is the only always-loaded text; everything else loads on demand. Each sibling skill has a sharp third-person *what+when* `description`. Use `REQUIRED SUB-SKILL:`, **never `@path`** force-loads (the canonical `AGENTS.md` is the one sanctioned `@`-import, and only inside `CLAUDE.md`). Generators inspect the repo (read-only) before writing.

---

## 8. Documentation taxonomy

For each: purpose · audience · allowed · forbidden · length · freshness · update triggers · source-of-truth · stable-ref examples · checklist. Lengths are **[SYNTHESIS]** unless a vendor number is cited.

### `AGENTS.md` (canonical, Codex + interop)
- **Purpose:** the small set of facts any agent needs on *every* task here. **Audience:** Codex (direct), Claude (via import), ~25 other tools (Appendix A).
- **Allowed:** the six high-signal sections (commands+flags, testing, structure, code-style *examples*, git workflow, **✅/⚠️/🚫 boundaries**), pointers to deep docs. **Forbidden:** architecture essays, volatile state, duplicated `package.json`/config, line numbers.
- **Length:** target ≤ ~1–2 pages; **must keep the whole root→cwd concatenated chain < 32 KiB** (Codex hard cap, silent truncation). **Freshness:** high — co-edit with code. **Triggers:** command/stack/version change, new guardrail, structural move.
- **SoT:** reference, never copy; nested per-package files for monorepos (nearest wins). **Stable refs:** §9. **Checklist:** < 32 KiB, Boundaries present, commands first, examples present, no line refs, every claim cited.

### `CLAUDE.md` (thin importer)
- **Purpose:** give Claude Code the same always-on context + Claude-only pointers. **Audience:** Claude Code only (Codex ignores it).
- **Allowed:** `@AGENTS.md` import; a short "Claude Code specifics" block (which skills/`/commands` exist, where deep docs live). **Forbidden:** any fact that duplicates `AGENTS.md` (put it in `AGENTS.md`); large `@`-imports of reference files.
- **Length:** tiny (≤ ~15 lines + the import). **Freshness:** changes only when Claude-specific tooling changes. **Triggers:** new skill/command. **Checklist:** imports `AGENTS.md`, no duplicated facts, no heavy `@`-imports.

### Architecture overview (`docs/architecture.md`)
- **Purpose:** durable mental model — components, boundaries, data flow. **Audience:** humans + agents. **Allowed:** stable structure, public contracts, *one* small validated Mermaid. **Forbidden:** implementation minutiae, line refs, volatile detail, invented components.
- **Length:** ~1–3 pages. **Freshness:** medium. **Triggers:** new top-level component, boundary change. **SoT:** module dirs + public interfaces. **Stable refs:** module paths + exported symbols. **Checklist:** evidence-gated, diagram validated, ≤20 nodes.

### Request-flow docs
- Trace one representative request: ordered hops by route + handler symbol + queue/topic; one sequence diagram. **Forbidden:** every branch, line refs. **Length:** ~1 page. **Triggers:** route/handler/queue rename. **Stable refs:** `POST /api/orders` → `createOrder()` in `src/api/orders.ts` → `orders.created` topic.

### Domain-model docs
- Entities, relationships, invariants, table/collection names. **Forbidden:** full schemas (reference migrations), volatile columns. **Stable refs:** `orders` table; `Order` in `src/domain/order.ts`. **Triggers:** new entity / relationship change.

### Onboarding doc
- Setup commands, repo tour by directory, a "first change" walkthrough referencing real files. **Forbidden:** duplicating README quickstart, line refs. **Length:** ~1–2 pages. **Triggers:** setup/tooling change.

### Local-dev / Deployment / Troubleshooting docs
- **Local-dev:** run/test/debug locally; commands + ports + env *key names*. **Deployment:** pipeline stages, environments, where config lives (reference, not secrets). **Troubleshooting:** symptom → cause → fix table, each tied to a command. **Forbidden everywhere:** secrets, line refs, copied config. **Triggers:** infra/script change.

### ADRs (`/adr/NNNN-imperative-name.md`)
- Capture *why* a significant decision was made. **Structure:** Nygard (Context/Decision/Consequences) or MADR (+ options & pros/cons). **Allowed:** one decision, context, rationale, consequences, status, date. **Forbidden:** editing past ADRs (supersede instead), multiple decisions per file. **Length:** ≤1 page. **Freshness:** immutable — **supersede, don't edit**. [OBSERVED] **Checklist:** single decision, status, date, supersedes/superseded-by links.

### Mermaid diagrams (embedded)
- ≤~15–20 nodes, quoted labels, validated with `maid`, no `click`/interactive links (GitHub CSP). **Forbidden:** unvalidated diagrams, >1 screen, decorative diagrams. **Checklist:** passes `maid`, node count, renders on GitHub. See §10.

### AI operating manual (`docs/ai/OPERATING-MANUAL.md`, optional)
- The repo-specific "how an agent should work *here*": a doc index (one-line purpose + when-to-read per doc), the safe-inspection command set, the "do not document / do not guess" rules, the update-trigger policy. **Forbidden:** duplicating the docs it indexes. **Length:** ~1 page. **SoT:** it's an *index* — its job is pointers. The skill's signature artifact for making a repo legible to both Claude and Codex.

---

## 9. Stable reference strategy

**Principle [EMPIRICAL grounding — arXiv:2212.01479]:** reference the most stable identifier that still locates the thing. Stability ranking (most → least durable):

1. **Module / package** — `src/billing/`, `@acme/auth`.
2. **Path + exported symbol** — `` `processPayment()` in `src/billing/charge.ts` `` (survives line moves; breaks only on rename — a reviewable event).
3. **Route / API** — `POST /api/v1/orders`.
4. **DB table / schema object** — `` `orders` table ``, `Order` entity.
5. **Event / topic / queue** — `orders.created`, `payments` queue.
6. **Config key** — `MENV_PASSPHRASE`, `project_doc_max_bytes` — name, never value.
7. **Test name** — test `"refunds on dispute"`.
8. **Command / script** — `bun test`, `npm run build`.
9. **File path only** — `src/index.ts` (when the whole file is the unit).
10. **❌ Line number** — never.

**Conventions:** backtick symbols/paths/commands; prefer prose-embedded refs ("see `createOrder()` in `src/api/orders.ts`") so the role is clear. `no_line_refs` must not mistake `host:port` or `::` for `:line`.

**When NOT to document code detail:**
- It's already the source of truth (scripts, lockfile versions, schema) → reference it. [OFFICIAL]
- It's volatile implementation (a private helper's body) → omit; document the **public contract**.
- The agent discovers it trivially (`npm`/`git`/`pytest`) → don't waste budget. [OFFICIAL — Cursor]
- It's temporary state ("mid-migration") → omit from durable docs.
- It would duplicate a linter/formatter rule → point to the config. [OFFICIAL]

---

## 10. Mermaid strategy

> Now **verified** (gap-closure pass). Tooling and core limits are OFFICIAL; node-count *targets* are [SYNTHESIS].

**Diagram types (safest — `maid` actively validates these):** `flowchart`/`graph`, `sequenceDiagram`, `classDiagram`, `stateDiagram-v2`, `pie`. Other types `maid` passes through **unvalidated** — avoid them in committed docs unless render-tested. **[OFFICIAL, verified]**

**Rendering constraints (verified):**
- **GitHub:** ` ```mermaid ` fenced blocks render in Issues/Discussions/PRs/wikis/Markdown. Version is **not officially documented** — check with a ` ```mermaid ` block containing `info`. **`click` directives and interactive links are blocked by GitHub's CSP** (diagrams render in a sandboxed `viewscreen.githubusercontent.com` iframe); relative links break. So: **no clickable nodes in committed diagrams.** **[OFFICIAL + OBSERVED, verified]**
- **GitLab:** docs say "supports Mermaid version 10" (the bundled lib has since moved to 11.4.1 — docs lag code). **Self-managed GitLab with a `Cross-Origin-Resource-Policy` header of `same-site`/`same-origin` makes Mermaid silently fail** → use `cross-origin`. **[OFFICIAL, verified]**
- **Mermaid core:** **`maxTextSize` default 50000** (diagram source beyond it fails). **`securityLevel` default `strict`** — HTML in labels is encoded and **`click` is disabled** by default. Current `mermaid`/`mmdc` version 11.15.0. **[OFFICIAL, verified]**

**Syntax / escaping rules (verified pitfalls):**
- Arrows: `-->` (flowchart), `->>`/`-->>` (sequence). **Never `->` in a flowchart** (`maid` flags it; `--fix` rewrites it).
- **Quote labels with troublesome characters** (`()[]{}:;,"#`): `A["process(payment)"]`. Or use HTML entities (base-10, e.g. `#` → `#35;`). The single most common AI failure.
- **The word `end` breaks flowcharts** unless capitalized (`End`/`END`).
- **A leading `o` or `x` on an edge** creates an unintended circle/cross edge (`A---oB`); add a space or capitalize (`A--- oB`, `A---OB`).
- Valid flowchart directions: `TD`/`TB`/`BT`/`LR`/`RL`. Always start with a diagram header.

**Label length / size [SYNTHESIS]:** labels ≤ ~40 chars; **diagram ≤ ~15–20 nodes**. Beyond that, split per subsystem/flow. A diagram that needs scrolling is a smell.

**Validation commands (verified):**
```bash
# Fast, no browser — the default gate (exit 1 on error; warnings don't fail):
npx -y @probelabs/maid docs/                 # validate every diagram in a dir
npx -y @probelabs/maid README.md             # validate fenced mermaid in a file
npx -y @probelabs/maid diagram.mmd --fix      # safe auto-fixes (-> to -->, quote labels, etc.)
npx -y @probelabs/maid docs/ --format json    # machine-readable for the gate
npx -y @probelabs/maid diagram.mmd --strict   # require quoted labels (FL-STRICT-LABEL-QUOTES-REQUIRED)
# Optional render-accurate deep check (heavy, Chromium):
npx -p @mermaid-js/mermaid-cli mmdc -i diagram.mmd -o /tmp/out.svg
```
`maid` catches: invalid arrows, unclosed brackets / mismatched shapes, invalid directions, missing headers, malformed class/subgraph syntax; warns on undelimited link text. **Render guarantee:** "when Maid says it's valid, your diagram will render" (for the five validated types). **[OFFICIAL, verified]**

**Good example (renders):**
```mermaid
flowchart LR
  client["Client"] --> api["API: createOrder()"]
  api --> queue["orders.created"]
  queue --> worker["Order worker"]
```
**Risky example (silently fails on GitHub):**
```
graph LR
  A(create order(v2)) -> B[save]      %% unquoted parens; '->' not '-->'
  click A "https://x" _blank          %% click blocked by GitHub CSP
```

**Automatic validation:** the `mermaid-diagrams` skill pipes generated diagrams through `maid --fix` then re-validates; pre-commit runs `maid` on changed Markdown; CI runs `maid docs/`. Never commit an unvalidated diagram.

---

## 11. Verbosity and compression strategy

**Hard ceilings (must respect when emitting):**
- **Codex: 32 KiB** on the concatenated `AGENTS.md` chain (`project_doc_max_bytes`, default 32768), **silent truncation past it**. The single non-negotiable cap. **[OFFICIAL, verified]**

**Authoring targets (Superpowers) [EXPERT]:** getting-started/always-loaded **<150–200 words**; on-demand skills **<500 words**; split reference material **>~100 lines** into separate files. For `AGENTS.md`: aim ≤ ~1–2 pages, comfortably under 32 KiB. 500-line SKILL.md is a **strong target, not a hard gate** ("hard 500-line" claim **refuted 1-2**).

**Links vs duplication:** if a fact has a source-of-truth file, reference it — never inline a copy. Inline only facts with no canonical home. **[OFFICIAL + EMPIRICAL]**

**When to move material to sub-docs:** a section exceeds its tier budget; needed on <50% of tasks; deep reference (API tables, schema, troubleshooting matrices). Move it and leave a one-line pointer with a *when-to-read* hint.

**Dense-but-useful writing:** one idea per bullet; imperative voice; concrete nouns; ✅/🚫 examples for non-obvious rules; tables for "X → do Y"; cut hedge words ("generally," "try to," "consider").

**Two failure poles:** *Filler test* — "would the agent behave identically if this line were deleted?" If yes, delete it. *Under-spec test* — "can the agent verify it complied?" If no, add a concrete criterion/example. A good line is one the agent *cannot already infer* and *can act on/verify*.

**Summary/detail layering:** every domain gets a one-line summary in `AGENTS.md` (or the operating-manual index) and a detail doc loaded on demand. The summary *is* the routing description — same pattern as skill metadata → body. **[OFFICIAL pattern, applied to docs]**

---

## 12. Validation and quality gates

A doc is **code**; it gets CI. Runs after every generation and in pre-commit/CI.

**Manual checklist (`checklists/doc-quality.md`, TodoWrite-driven):**
- [ ] Every claim traces to a file/symbol/command actually inspected (no guessing). [BP-9]
- [ ] No line-number references. [AP-1]
- [ ] No duplicated source-of-truth. [BP-2]
- [ ] `AGENTS.md` (whole chain) under 32 KiB; each file within its tier budget. [BP-8/AP-14]
- [ ] Boundaries section present (✅/⚠️/🚫). [BP-5]
- [ ] Non-obvious rules have ✅/🚫 examples. [BP-13]
- [ ] Update trigger + source-of-truth pointer present. [BP-10]
- [ ] No volatile/temporary detail in a durable file. [BP-11]
- [ ] Mermaid validated, ≤ node cap, no `click`. [BP-12/AP-15]
- [ ] `CLAUDE.md` imports `AGENTS.md` and adds no duplicated facts.
- [ ] Human-facing content not mixed into agent files. [BP-4]
- [ ] Unknowns marked `> [!WARNING] NEEDS VERIFICATION`, not invented. [BP-9]

**Automated checks (the gate; tool capabilities verified):**
| Check | Tool/script | Fails on |
|---|---|---|
| Markdown lint | `markdownlint-cli2` | bad headings/lists/fences; in-doc anchor defects (MD051); link defects (MD011/034/039/042/052/053/054/059) |
| No line refs | `no_line_refs.py` | `path:NNN`, "line NNN" (bespoke — no tool does this) |
| Dead path / link | `lychee` | dead **local file paths** + dead links (`--include-fragments` for anchors) |
| Symbol exists | `symbol_exists.py` (tree-sitter/ctags index) | doc references a symbol with no definition in source |
| Mermaid valid | `maid` | any diagram syntax error in the 5 validated types |
| SoT duplication | `dup_detect.py` | doc block fuzzy-matches `package.json`/config/source |
| Claim has evidence | `score_docs.py` heuristic | architectural claim with no nearby path/symbol/command ref |
| Size budget | `size_check.py` | over tier target or **over Codex 32 KiB** |
| Drift | `drift_check.py` | doc older than referenced code; dead referenced paths/symbols (Tan-et-al. technique) |
| `@`-force-load | lint | `@path` in an always-loaded file other than `CLAUDE.md`'s single `@AGENTS.md` |

**Tooling boundaries to respect (verified):** `markdownlint-cli2` does **not** check the network or whether a file path exists — use `lychee` for that. `Vale` cannot verify codebase symbols — use the symbol index. `maid` only deeply validates 5 diagram types. Wire each tool to what it actually does.

**Gate policy:** errors (line refs, broken links, dead paths/symbols, invalid Mermaid, over 32 KiB) **block**; warnings (size target, weak evidence, drift suspicion) **report**. Auto-repair where safe (`maid --fix`, line-ref rewrite); else surface. No "done" claim until the gate output is shown.

---

## 13. Scripts and tools

Recommended language: **Python 3 stdlib** for portable scanners/validators; **shell wrappers** around `markdownlint-cli2`, `lychee`, `maid`; **`ripgrep`/`tree-sitter`/`ctags`** for code extraction. Each: purpose · in · out · lang · algorithm · limits.

1. **`scan_repo.py`** — repo map (langs, top dirs, manifests, entry points, monorepo packages, stack+versions from lockfiles). JSON out. Walk tree (respect `.gitignore`); detect manifests; parse versions. *Limits:* heuristic stack detection; cap depth on huge monorepos.
2. **`extract_scripts.py`** — canonical command list from `package.json`/`Makefile`/`justfile`/`taskfile`. *Limits:* doesn't resolve aliased commands.
3. **`extract_symbols.sh`** — exported/public symbols (no line numbers) via `tree-sitter tags`/`ctags`; fallback `ripgrep`. Out: `{symbol, kind, file}`. Builds the index `symbol_exists.py`/`drift_check.py` consume. *Limits:* language coverage; dynamic exports missed.
4. **`extract_routes.py`** — HTTP routes `{method, path, handler-symbol, file}`, framework-aware regex. *Limits:* dynamically-registered routes missed.
5. **`extract_schema.py`** — tables/entities from migrations/ORM/`schema.prisma`/SQL. *Limits:* raw-SQL-in-strings missed.
6. **`extract_events.py`** — queues/topics/events via `ripgrep` for publish/subscribe/emit. *Limits:* string-built names missed; noisy.
7. **`validate_markdown.sh`** — wraps `markdownlint-cli2`. *Limits:* style/syntax + in-doc anchors only; no network, no path existence.
8. **`validate_mermaid.sh`** — wraps `maid` (`--format json`, optional `--fix`). *Limits:* validates 5 types; others pass through.
9. **`no_line_refs.py`** — regex `(?:[\w./-]+\.\w+):\d+\b` and `\bline\s+\d+\b`, excluding fenced code and `host:port`/`::`. *Limits:* needs an allowlist for legit colon-number tokens.
10. **`path_exists.py`** — backticked path-like tokens resolve in git-tracked files. (Complements `lychee` for prose-embedded paths.) *Limits:* paths only.
11. **`symbol_exists.py`** — doc-referenced `symbol in file` pairs exist in the `extract_symbols` index. *Limits:* index language coverage.
12. **`check_links.sh`** — wraps `lychee` (internal+paths always; external optional/`--offline` in pre-commit, full in nightly). *Limits:* external flakiness.
13. **`dup_detect.py`** — normalized shingling / token-set similarity of doc blocks vs `package.json`/config/source; threshold flag. *Limits:* tune to avoid flagging legit examples.
14. **`size_check.py`** — per-file tier budgets **and the Codex 32 KiB chain limit** (sum root→cwd `AGENTS.md`). *Limits:* counts bytes, not tokens.
15. **`drift_check.py`** — references whose target path/symbol no longer exists (Tan-et-al.), or doc older than its referenced code (git mtime). *Limits:* mtime ≠ semantic staleness → advisory.
16. **`score_docs.py`** — 0–100 rubric (size-fit, evidence density, ref stability, example coverage, boundary presence, drift) + report. *Limits:* heuristic proxy; calibrate weights; never the sole gate.

---

## 14. Skill implementation draft

### Orchestrator — `skills/repo-docs/SKILL.md`
```markdown
---
name: repo-docs
description: >
  Generate, audit, fix, and validate AI-facing repository documentation for
  Claude Code and OpenAI Codex — the canonical AGENTS.md plus a thin CLAUDE.md
  importer, architecture/onboarding docs, ADRs, and validated Mermaid diagrams.
  Use when the user asks to create, improve, audit, compress, de-duplicate, or
  validate documentation meant for AI coding agents, or to set up AGENTS.md /
  CLAUDE.md for a repo.
---

# Managing AI-facing repository documentation (Claude Code + Codex)

Route, don't do. Classify the request and delegate.

## Decision table
| User intent | REQUIRED SUB-SKILL |
|---|---|
| "audit / review our AI docs" | REQUIRED SUB-SKILL: docs-audit |
| "create/improve AGENTS.md or CLAUDE.md" | REQUIRED SUB-SKILL: generate-agent-instructions |
| "architecture overview/diagram" | REQUIRED SUB-SKILL: generate-architecture-doc |
| "onboarding/dev setup docs" | REQUIRED SUB-SKILL: generate-onboarding-doc |
| "record a decision / ADR" | REQUIRED SUB-SKILL: generate-adr |
| "make/fix a Mermaid diagram" | REQUIRED SUB-SKILL: mermaid-diagrams |
| "are our docs stale?" | REQUIRED SUB-SKILL: docs-drift-review |
| "docs too long / compress" | REQUIRED SUB-SKILL: compress-docs |
| "what owns this fact?" | REQUIRED SUB-SKILL: source-of-truth-map |
| "how should we reference X?" | REQUIRED SUB-SKILL: stable-refs |
| "score/quality-check a doc" | REQUIRED SUB-SKILL: docs-quality-review |
| "these docs are bad, fix them" | REQUIRED SUB-SKILL: refactor-bad-docs |

## Non-negotiables (every sub-skill obeys)
1. Inspect before you write (scripts/scan_repo.py + extractors). Do NOT guess.
2. AGENTS.md is canonical; CLAUDE.md is `@AGENTS.md` + Claude-only pointers.
3. Keep the AGENTS.md chain under 32 KiB (Codex truncates silently past it).
4. Reference, never copy source-of-truth. No line numbers.
5. Mark unknowns `> [!WARNING] NEEDS VERIFICATION`.
6. Run the quality gate (checklists/doc-quality.md) before claiming done.
```

### Sub-skill descriptions (what+when, third person)
- **docs-audit** — "Audit a repo's existing AI-facing docs against durability principles and emit a scored report with prioritized fixes. Use when asked to review/assess/grade existing AGENTS.md/CLAUDE.md/architecture docs."
- **generate-agent-instructions** — "Generate the canonical AGENTS.md (six high-signal sections + ✅/⚠️/🚫 boundaries, under Codex's 32 KiB cap) and a thin CLAUDE.md that imports it. Use when asked to create/improve Claude Code or Codex project instructions."
- **generate-architecture-doc** — "Produce an evidence-gated architecture overview with at most one validated Mermaid diagram. Use when asked to document system design/architecture for agents."
- **generate-onboarding-doc** — "Produce onboarding/local-dev docs referencing real commands and files. Use when asked to document setup/getting-started."
- **generate-adr** — "Create a new ADR (Nygard/MADR) and link supersessions; never edit past ADRs. Use when asked to record an architecture decision."
- **mermaid-diagrams** — "Generate, fix, and validate Mermaid (maid) within size/syntax limits, no click links. Use when a diagram is requested or one fails to render."
- **docs-drift-review** — "Detect stale docs via path/symbol existence and git-mtime drift. Use when asked whether docs are out of date."
- **compress-docs** — "Compress oversized/always-loaded docs by routing detail to sub-docs and removing filler/duplication; enforce the 32 KiB cap. Use when a doc is bloated or over cap."
- **source-of-truth-map** — "Map which file owns each fact so docs reference instead of duplicate. Use when removing duplication or deciding where a fact belongs."
- **stable-refs** — "Convert volatile references (line numbers, copied snippets) into stable ones (path+symbol, route, table, command, test). Use when reviewing or writing references."
- **docs-quality-review** — "Score a doc (size, evidence, ref stability, examples, boundaries, drift) and report. Use when asked to quality-check a doc."
- **refactor-bad-docs** — "Diagnose and rewrite low-quality docs: split monoliths, fix refs, de-duplicate, add evidence/boundaries. Use when asked to fix bad existing docs."

### Templates (key pair)

`AGENTS.md.tmpl` (abbreviated):
```markdown
# <Project> — agent guide
<one-line: concrete stack + versions>          <!-- BP-7 -->

## Commands                                     <!-- BP-6, lead with these -->
- Install: `<cmd>`   Test: `<cmd>` (single: `<cmd>`)   Build: `<cmd>`

## Project structure
- `src/...` — <role>   (reference, don't inline trees)

## Code style
- <rule> — ✅ `<good>`  🚫 `<bad>`              <!-- BP-13 -->

## Testing
- Framework: <name>; run one test: `<cmd>`

## Git / PR workflow
- <branch/commit conventions>

## Boundaries                                   <!-- BP-5, highest-signal -->
✅ Always: run tests before "done"
⚠️ Ask first: schema migrations, dependency bumps
🚫 Never: commit secrets; reference line numbers; duplicate config

---
Source of truth: <dirs/files>. Update when: <triggers>.   <!-- BP-10 -->
```

`CLAUDE.md.tmpl` (the whole file):
```markdown
@AGENTS.md

## Claude Code specifics
- Skills: <which repo-docs skills apply here, if any>
- Deep docs: architecture → `docs/architecture.md`; onboarding → `docs/onboarding.md`
- (Everything an agent needs on every task lives in AGENTS.md above.)
```

### Example prompt → output
- *Prompt:* "Set up AGENTS.md and CLAUDE.md for this repo." → orchestrator routes to `generate-agent-instructions` → runs `scan_repo.py` + `extract_scripts.py` → drafts a ≤2-page `AGENTS.md` (commands first, Boundaries, pointers; references `package.json`) + a 4-line `CLAUDE.md` (`@AGENTS.md` + skill pointers) → runs the gate incl. `size_check` (confirms < 32 KiB) → reports the gate output + both files.

### Recommended scripts
All of §13; MVP = `scan_repo`, `extract_scripts`, `no_line_refs`, `path_exists`, `validate_markdown`, `validate_mermaid`, `size_check`.

---

## 15. Prioritized implementation roadmap

### MVP — "stop the bleeding" (entirely on verified evidence)
- **Build:** orchestrator; `generate-agent-instructions` (AGENTS.md canonical + CLAUDE.md importer, 32 KiB-aware); `docs-audit`; scripts `scan_repo`, `extract_scripts`, `no_line_refs`, `path_exists`, `validate_markdown`, `validate_mermaid` (wrap `maid`), `size_check`; `doc-quality.md` checklist; the two templates.
- **Postpone:** architecture/onboarding/ADR generators, drift, scoring.
- **Quality bar:** generated pair passes the gate (no line refs, no dead paths, valid Mermaid, **AGENTS.md < 32 KiB**, Boundaries present, every claim evidence-backed, CLAUDE.md imports AGENTS.md). Evidence-gated generation enforced.

### v1 — "useful"
- **Build:** `compress-docs`; `stable-refs`; `source-of-truth-map`; `check_links` (lychee); `dup_detect`; `extract_symbols` + `symbol_exists`. Slash commands. `references/` deep docs (taxonomy, stable-refs, mermaid-rules, codex-agents-md, agents-md-interop).
- **Quality bar:** no duplicated source-of-truth (`dup_detect` clean); all internal links + local paths resolve; symbol references exist.

### v2 — "advanced"
- **Build:** `generate-architecture-doc` + `mermaid-diagrams` (full §10 discipline); `generate-onboarding-doc`; `generate-adr` (Nygard/MADR + supersede); `docs-drift-review` + `drift_check` (Tan-et-al. technique); `extract_routes`/`extract_schema`/`extract_events`; the **AI operating manual** generator; CI workflow snippet.
- **Quality bar:** architecture docs evidence-gated with ≤1 validated diagram; ADRs immutable; drift review runs in CI; operating manual indexes (never duplicates) the doc set.

### v3 — "state of the art"
- **Build:** `score_docs` with calibrated rubric; `refactor-bad-docs` end-to-end; `docs-quality-review`; `conflict-scan`; optional `AGENTS.override.md`/global-scope handling for Codex; an **empirical self-eval** — does a repo with `repo-docs`-generated docs measurably improve Claude/Codex task success vs baseline `/init`?
- **Quality bar:** every generated doc scores above threshold; refactor produces measurably smaller, higher-evidence docs; ideally an eval shows agent-reliability improvement (the open empirical question — see §16 closing).

---

## 16. Source list

**Primary / official (target formats + skill substrate):**
- Anthropic — Agent Skills: https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills — progressive disclosure. [verified 3-0]
- Anthropic — Effective context engineering: https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents — context rot. [verified 3-0]
- Claude Code skills: https://code.claude.com/docs/en/skills · best-practices: https://docs.claude.com/en/docs/agents-and-tools/agent-skills/best-practices — description-driven routing; 500-line is a target (hard-limit claim refuted 1-2).
- OpenAI Codex — AGENTS.md: https://developers.openai.com/codex/guides/agents-md · config: https://developers.openai.com/codex/config-reference · #7138: https://github.com/openai/codex/issues/7138 — concatenation/override/**32 KiB cap + silent truncation**. [verified 3-0]
- agents.md: https://agents.md/ — open standard, human/agent separation, nested nearest-wins, adopters. [OFFICIAL]
- GitHub — "lessons from 2,500+ AGENTS.md repos": https://github.blog/ai-and-ml/github-copilot/how-to-write-a-great-agents-md-lessons-from-over-2500-repositories/ — six sections, ✅/⚠️/🚫 boundaries. [OBSERVED-empirical]

**Empirical:**
- Chroma "Context Rot": https://research.trychroma.com/context-rot · EMNLP 2025: https://arxiv.org/abs/2510.05381 · Lost-in-the-Middle: https://arxiv.org/abs/2307.03172. [verified 3-0]
- Tan, Wagner & Treude — outdated code-element references: https://arxiv.org/abs/2212.01479 — 3,000+ projects; the stale-reference grounding. [EMPIRICAL]
- Aghajani et al. — "Software Documentation Issues Unveiled" (ICSE 2019): https://2019.icse-conferences.org/details/icse-2019-Technical-Papers/49/Software-Documentation-Issues-Unveiled — 878-artifact taxonomy; doc-drift grounding. [EMPIRICAL]

**Expert practice / tooling (verified capabilities):**
- obra/Superpowers: https://github.com/obra/superpowers · writing-skills: https://github.com/obra/superpowers/blob/main/skills/writing-skills/SKILL.md — flat namespace, word budgets, `REQUIRED SUB-SKILL:`. [verified 3-0]
- probelabs/maid: https://github.com/probelabs/maid (npm `@probelabs/maid`) — Mermaid validator; `--fix`, `--format json`, `--strict`, exit 0/1, pre-commit/CI. [verified]
- @mermaid-js/mermaid-cli (`mmdc`): https://github.com/mermaid-js/mermaid-cli · `mermaid.parse()`: https://mermaid.js.org/config/usage.html · `maxTextSize`/`securityLevel`: https://mermaid.js.org/config/schema-docs/config.html · flowchart escaping: https://mermaid.js.org/syntax/flowchart.html. [verified]
- GitHub Mermaid: https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-diagrams · GitLab Mermaid: https://docs.gitlab.com/user/markdown/ — rendering surfaces, CSP `click` block, CORP silent-fail. [verified]
- lychee: https://github.com/lycheeverse/lychee — links + local-path existence + fragments. [verified]
- markdownlint(-cli2): https://github.com/DavidAnson/markdownlint-cli2 · rules: https://github.com/DavidAnson/markdownlint/blob/main/doc/Rules.md — MD051 etc.; no network/path-existence. [verified]
- tree-sitter tags: https://tree-sitter.github.io/tree-sitter/4-code-navigation.html · universal-ctags · ripgrep: https://github.com/BurntSushi/ripgrep · Vale: https://vale.sh/docs/styles. [verified]
- joelparkerhenderson/ADR: https://github.com/joelparkerhenderson/architecture-decision-record — Nygard/MADR, supersede-don't-edit. [OBSERVED]
- humanlayer.dev — "Writing a good CLAUDE.md": https://www.humanlayer.dev/blog/writing-a-good-claude-md. [EXPERT, blog]

**Tools to wrap (build-time deps):** `@probelabs/maid`, `markdownlint-cli2`, `lychee`, `@mermaid-js/mermaid-cli` (optional), `ripgrep`, `tree-sitter`/`universal-ctags`, `Vale` (optional).

---

## Appendix A — `AGENTS.md` interop matrix (why the canonical choice travels)

Verified in the gap-closure pass: a single well-formed `AGENTS.md` is read (natively or via the open standard) by far more than Codex. This is the evidence behind "out-of-scope generators are unnecessary."

| Tool | Reads `AGENTS.md`? | Notes | Evidence |
|---|---|---|---|
| **OpenAI Codex** | ✅ native, canonical | root→cwd concat, closer-overrides, 32 KiB cap | [OFFICIAL, verified] |
| **Claude Code** | ⚠️ not natively (early 2026) | gets it via `CLAUDE.md`'s `@AGENTS.md` import | [OFFICIAL, verified] |
| **Cursor** | ✅ | plain-markdown `AGENTS.md` alternative to `.cursor/rules` | [OFFICIAL, verified] |
| **Windsurf (Cognition)** | ✅ | root = always-on, subdir = glob `<dir>/**`; same Rules engine | [OFFICIAL, verified] |
| **Amp (Sourcegraph)** | ✅ canonical | `AGENTS.md` > `AGENT.md` > `CLAUDE.md` fallback | [OFFICIAL, verified] |
| **JetBrains Junie** | ✅ | `.junie/AGENTS.md` or `AGENTS.md`; legacy `.junie/guidelines.md` | [OFFICIAL, verified] |
| **Google Jules** | ✅ native | auto-reads root `AGENTS.md` | [OFFICIAL, verified] |
| **Gemini CLI** | ⚙️ opt-in | default `GEMINI.md`; add `AGENTS.md` to `context.fileName` | [OFFICIAL, verified] |
| **Cline** | ✅ (Nov 2025) | workspace-root + nested subdirs (gated on root file) | [OFFICIAL, verified] |
| **OpenHands** | ✅ recommended | root `AGENTS.md` always-on; also adopted a SKILL.md model | [OFFICIAL, verified] |
| **Roo Code** | ✅ (frozen) | reads `AGENTS.md`; **project discontinued, archived 2026-05-15** | [OFFICIAL, verified] |
| **Continue** | ❓ unverified | feature request #6716 closed but no shipped auto-load confirmed | [verified: UNVERIFIED] |
| **Aider** | ❌ not auto | load explicitly via `--read`; `CONVENTIONS.md` is its idiom | [OFFICIAL, verified] |
| **Amazon Q Developer** | ❌ not supported | uses `.amazonq/rules/*.md`; AGENTS.md request #2712 open | [OFFICIAL, verified] |
| **Replit** | ❌ not native | uses `replit.md`; AGENTS.md manual-only | [OFFICIAL, verified] |
| **Sourcegraph Cody** | n/a | Cody Free/Pro discontinued 2025-07-23; **Amp is the successor** (uses AGENTS.md) | [OFFICIAL, verified] |

**Takeaway:** generating one excellent `AGENTS.md` covers Codex (target) + ~10 other agents for free; `CLAUDE.md`'s import covers Claude Code. Only Aider, Amazon Q, and Replit use a different idiom — out of scope, and each is a thin future add-on if ever needed.

## Appendix B — Codex `AGENTS.md` loading semantics (the constraints the generator must honor)

Verified [OFFICIAL, 3-0]:
- **Concatenation:** Codex joins `AGENTS.md` from the Git root **down to cwd** with blank lines; **files closer to cwd override earlier ones** (they appear later in the prompt). → Put repo-wide rules at root; put package-specific overrides in nested files.
- **Scopes:** global `~/.codex/AGENTS.md` + project; nested-subdirectory override within project; an `AGENTS.override.md` precedence layer.
- **Hard cap:** `project_doc_max_bytes`, **default 32768 (32 KiB)**. Codex **skips empty files** and **stops adding files once the limit is reached** — anything past it is **silently truncated** (issue #7138). → The generator must keep the *summed* chain under 32 KiB and **warn before** the cap, because failure is invisible.
- **Generator implications:** budget the whole tree, not each file in isolation; prefer one tight root file + small nested overrides; never let generated boilerplate push the chain over budget.

---

### Closing note on uncertainty (carried from verification)
- **Now verified (OFFICIAL/EMPIRICAL):** the skill architecture, Claude Code + Codex semantics (incl. the 32 KiB cap), context-rot, the doc-drift problem, Mermaid rendering/validation, and the validator-tool capabilities.
- **Still [SYNTHESIS] (reasoned, not authoritative):** specific size *targets* for durable docs, the exact taxonomy boundaries, the AGENTS.md-canonical/CLAUDE.md-importer *sync strategy* (built on two official mechanisms but not itself vendor-blessed), and the doc-quality score weights. Flagged inline; revisit if vendors publish guidance.
- **Refuted, kept for transparency:** (1) SKILL.md 500-line "hard limit" is a target (1-2); (2) a skill description should state **what + when**, not when-only (1-2).
- **Open empirical question (v3 north star):** does `repo-docs`-generated documentation *measurably* improve Claude/Codex task success vs baseline `/init`? The drift literature proves bad docs are a real, measurable problem; no source yet measures the *uplift* of disciplined AI docs on agent reliability. That eval is worth running once the skill exists.
```