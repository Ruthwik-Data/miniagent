"""The six tools.

grok-build's equivalents are ports, not originals:

  - src/implementations/codex/    — apply_patch, grep_files, list_dir,
                                    read_file — from openai/codex
  - src/implementations/opencode/ — bash, edit, glob, grep, read, skill,
                                    todowrite, write — from sst/opencode

Both attributed in crates/codegen/xai-grok-tools/THIRD_PARTY_NOTICES.md with
Apache 2.0 sec.4(b) change notices. xAI did not consider the tool layer a
differentiator worth rebuilding — which is itself the finding.

The whole file is deterministic: no tool here knows an LLM exists. That is
what makes every one of them testable for free.
"""
import re
import subprocess
from pathlib import Path


def read_file(path: str, offset: int = 0, limit: int = 2000) -> str:
    """Read a file with 1-based line numbers.

    Line numbers are not cosmetic. They are what lets the model refer to a
    location in a later turn ("line 42") without re-reading the file.
    """
    lines = Path(path).read_text().splitlines()
    chunk = lines[offset : offset + limit]
    return "\n".join(f"{offset + i + 1}\t{line}" for i, line in enumerate(chunk))


def list_dir(path: str = ".") -> str:
    """List a directory. 'd name' for dirs, 'f name' for files."""
    entries = sorted(Path(path).iterdir(), key=lambda p: p.name)
    return "\n".join(f"{'d' if e.is_dir() else 'f'} {e.name}" for e in entries)


def grep(pattern: str, path: str = ".") -> str:
    """Regex search across files under path. Returns file:lineno:line per hit."""
    rx = re.compile(pattern)
    hits = []
    for f in sorted(Path(path).rglob("*")):
        if not f.is_file():
            continue
        try:
            text = f.read_text()
        except (UnicodeDecodeError, PermissionError, OSError):
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if rx.search(line):
                hits.append(f"{f}:{i}:{line}")
    return "\n".join(hits) if hits else "no matches"


def edit_file(path: str, old_string: str, new_string: str) -> str:
    """Replace old_string with new_string. Naive string match, deliberately.

    grok-build ships an alternative: hashline anchored editing, where every
    line carries a content hash so a stale anchor is *detected* rather than
    silently mismatched. Three candidate schemes — ContentOnly,
    ChunkFingerprint, CheckpointChain — live in
    src/implementations/grok_build_hashline/, benchmarked by an 887-line
    harness with no LLM in it, and gated behind a server-side flag
    (xai-grok-shell/src/tools/config.rs::resolve_file_toolset).

    We use the naive version on purpose. It fails when the model targets
    content it misremembers. That failure is the point — see REFERENCE.md.

    Note it never raises. "no match found" is a string the model reads and
    recovers from; that string IS the retry mechanism.
    """
    p = Path(path)
    try:
        text = p.read_text()
    except OSError as e:
        return f"error: cannot read {path}: {e}"

    count = text.count(old_string)
    if count == 0:
        return f"no match found for that string in {path}"
    if count > 1:
        return f"{count} matches found in {path}; old_string must be unique"

    p.write_text(text.replace(old_string, new_string))
    return f"edited {path}"


def write(path: str, content: str) -> str:
    """Create or overwrite a file. Creates parent directories as needed.

    Not gated by safety.confirm(). The reversibility test from grok's
    <action_safety> is what decides it: writes land in a repo under version
    control and are recoverable, while bash can do anything to anything.
    Gating writes would mean confirming every file the agent creates, which
    trains the user to hit 'y' reflexively and makes the bash gate worth
    less. A gate that fires constantly is a gate nobody reads.

    grok-build's equivalent is ported from sst/opencode.
    """
    p = Path(path)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    except OSError as e:
        return f"error: cannot write {path}: {e}"
    return f"wrote {len(content)} bytes to {path}"


def bash(command: str, cwd: str = ".") -> str:
    """Run a shell command. Returns exit code plus combined output.

    The only tool gated by safety.confirm(), because it is the only one
    that can do anything to anything.

    grok-build instead runs commands through xai-grok-sandbox with a
    permissions engine and configurable approval rules. We ask a yes/no
    question. The 120s timeout is the whole resource story here; theirs
    has background tasks, monitors, and kill_task.

    cwd is expanduser'd because models pass "~" and subprocess does not
    expand it — found by actually running this against a live model, which
    is also why grok-build has a normalization.rs. Path shapes the model
    emits are not the shapes the OS accepts.
    """
    try:
        r = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=Path(cwd).expanduser(),
            timeout=120,
        )
    except (FileNotFoundError, NotADirectoryError) as e:
        return f"error: bad cwd {cwd!r}: {e}"
    except subprocess.TimeoutExpired:
        return "error: command timed out after 120s"
    output = (r.stdout + r.stderr).strip()
    return f"exit {r.returncode}\n{output}" if output else f"exit {r.returncode}"


TOOLS = {
    "read_file": read_file,
    "list_dir": list_dir,
    "grep": grep,
    "edit_file": edit_file,
    "write": write,
    "bash": bash,
}

SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file from disk. Returns the contents with line numbers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file."},
                    "offset": {"type": "integer", "description": "0-based first line."},
                    "limit": {"type": "integer", "description": "Max lines to return."},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List the entries of a directory.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Directory path."}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "grep",
            "description": "Regex search across files. Returns file:lineno:line for each hit.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Python regex."},
                    "path": {"type": "string", "description": "Root to search under."},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": (
                "Replace a unique string in a file. old_string must appear "
                "exactly once and match the file's current contents exactly."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file."},
                    "old_string": {"type": "string", "description": "Exact text to replace."},
                    "new_string": {"type": "string", "description": "Replacement text."},
                },
                "required": ["path", "old_string", "new_string"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write",
            "description": (
                "Create a new file or overwrite an existing one with the given "
                "content. Creates parent directories as needed. Use edit_file "
                "to change part of an existing file."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file."},
                    "content": {"type": "string", "description": "Full file contents."},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": (
                "Run a shell command and return its exit code and output. "
                "Requires user confirmation unless --auto is set. Prefer the "
                "dedicated file tools for reading and editing."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The command to run."},
                    "cwd": {"type": "string", "description": "Working directory."},
                },
                "required": ["command"],
            },
        },
    },
]
