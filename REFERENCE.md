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
- [x] [**Tools: edit and write**](#tools-edit-and-write)
- [x] [**Tools: bash and safety**](#tools-bash-and-safety)
- [x] [**Sessions and the stateless model**](#sessions-and-the-stateless-model)
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

## Tools: edit and write

**Ours:** ~60 lines. `edit_file` does a naive unique-string replace; `write`
creates or overwrites.
**grok-build:** three separate edit toolsets, one of them with a dedicated
887-line benchmark.

### What grok-build does

`search_replace` in the default toolset does what ours does. But xAI also built
**hashline**, an anchored editor where every line carries a short content hash,
so the model targets `a3f:  return a - b` instead of the bare text. A stale
anchor is then *detected* rather than silently mismatched.

There are **three candidate schemes**, and the docstrings say why:

| Scheme | Anchor | Trade-off |
|---|---|---|
| **A** `ContentOnly` | line hash | Simplest. Weakest freshness — edits above a line don't invalidate it |
| **B** `ChunkFingerprint` | line hash + fixed chunk fingerprint | Only anchors in the touched chunk invalidate. *"Recommended starting point"* |
| **C** `CheckpointChain` | line hash + nearest-checkpoint fingerprint | Strongest detection, most churn after edits |

`benchmark.rs` (887 lines) scores them in two phases — single-mutation
microbenchmarks and deterministic edit-trace simulation — across hash lengths
`[2,3]`, chunk sizes `[8,16,32]`, checkpoint intervals `[16,32,64]`.

### The minimum

`text.count(old_string)`: zero matches → error string; more than one → refuse as
ambiguous; exactly one → replace. Thirty lines.

**We use it on purpose.** It fails when the model targets content it
misremembers from three turns ago. That failure is the point.

### What the extra lines buy

Detection of a specific, silent failure — and they measured it rather than
assumed it.

The metric design is the part worth stealing. They keep **`false_valid`** (anchor
says fine, content changed → *your code gets corrupted*) separate from
**`false_stale`** (anchor says stale, content didn't change → *a wasted re-read*).
Both are "errors"; averaging them into one accuracy number would hide the only
distinction that matters. Then they price the fix in **read-amplification**:
Scheme A validates 1 line, B validates `chunk_size`, C validates back to the
checkpoint. Stronger detection literally costs more context.

And there is **no LLM anywhere in that benchmark.** They isolated the
deterministic substrate — given a file and a mutation, does the anchor correctly
report stale? — and measured that for free. (`tests/fakes.py` in this repo is the
same move, arrived at independently.)

### The finding

**Hashline ships behind a server-side flag** — `resolve_file_toolset()` checks
`/v1/settings` and can flip users to it remotely. Three schemes, a benchmark, and
a remote rollout switch means **xAI has not settled this question.** They're
running it on real traffic to find out.

Which makes naive string matching a defensible v1 rather than a naive one: it's
the baseline a frontier lab is still measuring against.

### Why `write` isn't gated

`write` overwrites files and `bash` is gated, so the asymmetry needs a reason.
It's grok's own reversibility test from `<action_safety>`: writes land in a repo
under version control and are recoverable; `bash` can do anything to anything.
Gating writes would mean confirming every file the agent creates — which trains
you to hit `y` reflexively and makes the `bash` gate worth less. **A gate that
fires constantly is a gate nobody reads.**

---

## Tools: bash and safety

**Ours:** ~20 lines of `bash`, ~35 lines of gate.
**grok-build:** `xai-grok-sandbox`, a permissions engine, and a 45-line system
prompt that teaches the concept.

### What grok-build does

Two completely different mechanisms, and the interesting one isn't the code.

**In code:** `xai-grok-sandbox` sandboxes execution. `xai-grok-workspace/src/permission/`
holds a rules engine with pattern matching, filters, and actions. `/always-approve`
persists decisions. Background execution runs through `scheduler`, `monitor`, and
`kill_task`.

**In prose:** the `<action_safety>` section of `templates/prompt.md` — plain
English, addressed to the model:

> *Weigh each action by how easily it can be undone and how far its effects
> reach... Confirming is cheap; a mistaken action is not... One approval is not a
> blank check.*

It then enumerates categories: destructive (`rm -rf`, dropping tables),
irreversible (force-push, `git reset --hard`), and *visible to others* (pushing,
commenting on PRs, sending messages).

### The minimum

`RISKY = {"bash"}` and a `y/N` prompt. Thirty-five lines.

### What the extra lines buy

**Generalization.** This is the real finding, and it surprised me.

Our gate is code, so it catches exactly what we enumerated: the string `"bash"`.
It cannot tell `ls` from `rm -rf /` — both get the same prompt, and a prompt that
fires on `ls` is one you learn to dismiss.

Grok's primary safety mechanism is *prose in a prompt*, which generalizes to
situations the author never imagined. The model reads "weigh reversibility and
blast radius" and applies it to a tool that didn't exist when the sentence was
written. **You cannot write that in a rules engine** — which is presumably why
they have both, with the sandbox as the floor under the judgment rather than a
replacement for it.

That inverts the intuition. The instinct is that real safety is enforced in code
and prompts are soft. But the enumerable part is the *cheap* part; the part that
scales is the paragraph.

### The finding

**The most sophisticated safety machinery in a 1.3M-line agent is 15 lines of
English.** Everything else is the floor beneath it.

---

## Sessions and the stateless model

**Ours:** ~40 lines. `json.dump(messages)`.
**grok-build:** a session store, `summary.json` metadata, rewind snapshots,
nested subagent sessions, and `xai-grok-compaction` as its own crate.

### The fact everything else follows from

**The model is stateless.** It remembers nothing between calls.

Every turn resends the entire transcript: system prompt, every message, every
tool call, every result. Turn 10 resends turns 1–9. The "memory" you experience
talking to an agent is an illusion produced by replaying the whole conversation
each time, at full cost, on every turn.

So persisting a session is writing a list of dicts to disk:

```python
path.write_text(json.dumps(messages, indent=2))
```

The part that sounds hardest — giving an agent memory — is one line, because
**the context window is the state.** There is nowhere else for state to live.

### What grok-build does

Sessions save automatically, per working directory, under
`~/.grok/sessions/<encoded-cwd>/<session-id>/` with a `summary.json` holding
title, timestamps, model id, and message counts. You can **resume**, **rewind**
(file snapshots per turn), or **compact**. Subagent sessions nest inside their
parent.

### What the extra lines buy

Everything downstream of that one fact:

- **Rewind** needs file snapshots, because replaying the transcript restores the
  model's state but not your disk. Statelessness cuts both ways.
- **Compaction** exists because the transcript grows and every turn resends all
  of it. Around turn 30 you hit the context limit — not gradually, but as a wall.
  That's a whole crate (`xai-grok-compaction`) whose entire job is deciding what
  to forget.
- **`summary.json`** exists because a directory of `<uuid>.json` is unusable once
  you have forty of them.

### The finding

**Compaction is not an optimization — it's a consequence.** The moment you accept
that the model is stateless and the transcript is the memory, you have also
accepted that memory grows without bound and must eventually be thrown away on
purpose. Every agent that runs longer than ~30 turns has a compaction strategy,
whether it chose one or not.

Ours is: warn, and let the user start a new session. That *is* a strategy. It's
just the cheapest one.

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
