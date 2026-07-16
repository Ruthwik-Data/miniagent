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


TOOLS = {
    "read_file": read_file,
    "list_dir": list_dir,
    "grep": grep,
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
]
