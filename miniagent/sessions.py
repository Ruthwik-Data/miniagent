"""Session persistence: json.dump(messages).

That is the whole thing, and it is the most important fact in this repo.

The model is stateless. It remembers nothing between calls. Every turn
resends the entire transcript — system prompt, every message, every tool
call, every result. The "memory" you experience talking to an agent is an
illusion produced by replaying the whole conversation each time.

So persisting a session is writing a list of dicts to disk. The part that
sounds hardest — giving an agent memory — is forty lines, because **the
context window IS the state**. There is nowhere else for state to live.

grok-build: "Grok saves every conversation to disk automatically... You can
resume, rewind, or compact it." (docs/user-guide/17-sessions.md). Theirs
live under ~/.grok/sessions/<encoded-cwd>/<session-id>/ with a summary.json
of metadata, grouped by working directory, plus file snapshots for rewind
and nested subagent sessions. Ours is the same idea minus all of that.

The consequence is the next lesson: transcripts grow, every turn resends
everything, and the context limit arrives. That is why xai-grok-compaction
is its own crate. We warn; they compact.
"""
import json
import os
import time
from datetime import datetime
from pathlib import Path


def session_dir(root: Path | None = None) -> Path:
    """Where sessions live. Defaults to .miniagent/sessions under cwd.

    Per-directory, like grok's encoded-cwd grouping: the transcript that
    matters is the one from this repo, not the last one you ran anywhere.
    """
    return (Path(root) if root else Path.cwd()) / ".miniagent" / "sessions"


def new_id() -> str:
    """Sortable timestamp plus random suffix. grok uses UUIDv7."""
    return f"{datetime.now():%Y%m%d-%H%M%S}-{os.urandom(2).hex()}"


def save(session_id: str, messages: list[dict], root: Path | None = None) -> Path:
    """Write the transcript. This is the entire memory system."""
    d = session_dir(root)
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{session_id}.json"
    path.write_text(json.dumps(messages, indent=2))
    os.utime(path, (time.time(), time.time()))
    return path


def load(session_id: str, root: Path | None = None) -> list[dict]:
    """Read a transcript back. Resuming is this, and nothing else."""
    return json.loads((session_dir(root) / f"{session_id}.json").read_text())


def latest(root: Path | None = None) -> str | None:
    """Most recently written session id for this directory, or None."""
    d = session_dir(root)
    if not d.exists():
        return None
    files = sorted(d.glob("*.json"), key=lambda p: p.stat().st_mtime)
    return files[-1].stem if files else None
