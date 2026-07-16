<!-- Line counts marked (target) are estimates until the code exists.
     Task 9 measures them with `wc -l` and substitutes the real numbers. -->

# REFERENCE.md — 420 lines vs 1,300,000

A map from this repo's spine to [xai-org/grok-build](https://github.com/xai-org/grok-build),
xAI's production coding agent: ~1.3M lines of Rust, Apache 2.0, published
January 2026 as a periodic export from their internal monorepo.

Two data points, per subsystem: **miniagent (~420 lines, target) → grok-build (1.3M)**.

Each section answers three questions:

1. What does grok-build do here, with file paths?
2. What is the minimum that preserves the behavior?
3. What do their extra lines buy — and who is it for?

---

## The headline

**grok-build's 1.3M lines are not 1.3M lines of "agent."**

| Crate | Lines | What it is |
|---|---|---|
| `xai-grok-pager` | **414,627** | The TUI |
| `xai-grok-shell` | 335,843 | Agent runtime |
| `xai-grok-tools` | 112,275 | Tool implementations |
| `xai-grok-workspace` | 76,730 | Filesystem, VCS, execution, checkpoints |

The **interface is larger than the agent**. One settings modal
(`crates/codegen/xai-grok-pager/src/views/settings_modal.rs`) is 12,471 lines —
roughly thirty times this entire repository.

Subtract the TUI and most of what remains is MCP transports, sandboxing,
telemetry, config resolution, plugins, update machinery, session storage,
permissions, voice, and markdown rendering. The portion that answers *"how does
an agent work"* is a few thousand lines at most, and its irreducible core — the
loop — is about ten.

So the ratio isn't 420 : 1,300,000 for the same thing. It's three different things:

- **~420 lines** — the mechanism. What makes it an agent.
- **~thousands** — making it reliable. Goal verification, compaction, anchored editing, retries.
- **1.3M** — making it a *product*. Interface, integrations, distribution, enterprise.

Most of what a funded agent team builds is not intelligence, and not even agent
design. It's product.

---

## Sections

- [ ] **The loop** — *Task 7*
- [x] [**Tools: read, list, grep**](#tools-read-list-grep)
- [ ] **Tools: edit and write** — *Task 4*
- [ ] **Tools: bash and safety** — *Task 5*
- [ ] **Sessions and the stateless model** — *Task 6*
- [ ] **What we left out, and why** — *Task 9*

---

## Tools: read, list, grep

**Ours:** ~90 lines for three tools plus their JSON schemas.
**grok-build:** `xai-grok-tools` is 112,275 lines.

### What grok-build does

It doesn't implement them. `read_file`, `list_dir`, and `grep_files` under
`src/implementations/codex/` are **ported from openai/codex**; `read`, `glob`,
and `grep` under `src/implementations/opencode/` are **ported from sst/opencode**.
Both are attributed in `THIRD_PARTY_NOTICES.md` with Apache 2.0 §4(b) change
notices.

grok also ships *two* read tools and *three* edit variants
(`grok_build`, `grok_build_concise`, `grok_build_hashline`) behind config, plus
an `lsp` tool for code intelligence.

### The minimum

Three functions, ~90 lines. `read_file` returns line-numbered text; `list_dir`
marks files and dirs; `grep` returns `file:lineno:line`.

The one non-obvious decision is **line numbers in `read_file`**. They look
cosmetic and are not: they're what lets the model refer to a location in a later
turn without re-reading. grok's codex-derived `read_file` does the same.

### What the extra lines buy

Three things, none of them the tool logic:

1. **Variants under experiment.** Three toolsets exist simultaneously so xAI can
   A/B the *format* the model sees — concise vs. verbose vs. hash-anchored — and
   flip between them server-side.
2. **Scale and safety at the edges.** Binary detection, encoding, `.gitignore`
   respect, huge-file truncation, image handling, path normalization.
3. **A tool taxonomy.** `tool_taxonomy.rs` maps every tool onto a canonical
   vocabulary (`read_file` and `Read` both → `Read`) so tools from different
   harnesses and MCP servers can coexist in one UI.

### The finding

**xAI's tool layer is other people's code, and they say so.** The most
interesting thing about `xai-grok-tools` isn't in the tools — it's that a
frontier lab looked at the tool layer and decided it wasn't worth rebuilding.
The differentiator was somewhere else.

---

## Verified reference map

Every claim in this document points at a real path in `xai-org/grok-build`.

| Subsystem | Location | Note |
|---|---|---|
| Repo shape | `xai-grok-pager` / `xai-grok-shell` / `xai-grok-tools` / `xai-grok-workspace` | TUI / runtime / tools / host |
| System prompt | `crates/codegen/xai-grok-agent/templates/prompt.md` | **45 lines.** Plain Markdown with Jinja-style conditionals that inject live tool names |
| Safety doctrine | `<action_safety>` in `prompt.md` | Reversibility, blast radius, "one approval is not a blank check" |
| Goal subsystem | `xai-grok-shell/src/session/templates/goal_{planner,verifier,strategist,summarizer}_prompt.md` | Planner 239 lines, verifier 202 — four LLM roles decomposing one task |
| Tool ports | `xai-grok-tools/THIRD_PARTY_NOTICES.md` | `implementations/codex/` from **openai/codex**; `implementations/opencode/` from **sst/opencode** |
| Sessions | `docs/user-guide/17-sessions.md` | `~/.grok/sessions/<encoded-cwd>/<session-id>/` + `summary.json` |
| Compaction | `crates/common/xai-grok-compaction` | Its own crate |
| Anchored editing | `xai-grok-tools/src/implementations/grok_build_hashline/` | Three schemes + an 887-line benchmark with no LLM in it |
| Remote toolset flag | `xai-grok-shell/src/tools/config.rs` → `resolve_file_toolset()` | Server-side `/v1/settings` can flip users to hashline |
| MCP | `xai-grok-mcp/src/servers.rs` | 7,538 lines |
| Claude migration | `xai-grok-shell/src/claude_import.rs`, `xai-grok-workspace/src/foreign_sessions/claude.rs` | Imports Claude Code settings, MCP servers, permission rules, sessions |
| Project rules | `AGENTS.md` | Not a proprietary format |

---

## Three findings that don't fit in a section

**1. xAI's tools are ports.** `apply_patch`, `grep_files`, `list_dir`, `read_file`
come from openai/codex. `bash`, `edit`, `glob`, `grep`, `read`, `skill`,
`todowrite`, `write` come from sst/opencode. Both are attributed in-tree with
Apache §4(b) change notices. xAI did not consider the tool layer a
differentiator worth rebuilding.

**2. They built a defection ramp off Claude Code.** `/import-claude` reads Claude
Code's settings, MCP servers, and permission rules and rewrites them into
`.grok/config.toml`. `foreign_sessions/claude.rs` reads Claude Code *sessions*.
You do not build that unless your competitive theory is *the harness is not the
moat — the model is*. Publishing 1.3M lines under Apache 2.0 while refusing
external contributions fits the same theory exactly.

**3. Anchored editing is still an open question inside xAI.** Hashline ships
behind a server-side flag with three candidate schemes and a benchmark that
measures stale-detection precision and recall *separately* — because a false
"valid" corrupts your code while a false "stale" only costs a re-read. They also
price the fix in read-amplification. That's a team measuring a trade-off, not
one that has settled it.

---

*Reference source: [xai-org/grok-build](https://github.com/xai-org/grok-build) @ `b189869`, Apache 2.0.*
