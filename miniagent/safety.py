"""The confirmation gate.

Mirrors the <action_safety> section of grok-build's system prompt
(crates/codegen/xai-grok-agent/templates/prompt.md — 45 lines total). Its
principles:

  - Weigh each action by how easily it can be undone and how far its
    effects reach.
  - Local, reversible work is fine to do freely.
  - Confirming is cheap; a mistaken action is not.
  - One approval is not a blank check.

Note the asymmetry, because it is the finding: grok teaches safety to the
*model*, in prose, in the system prompt. We enforce it in *code*, at
dispatch. Prose generalizes to every tool and every situation the author
never imagined; code only catches what you enumerated. Ours is 35 lines and
catches exactly one thing.

Theirs also has a real sandbox behind it (xai-grok-sandbox) and a
permissions engine (xai-grok-workspace/src/permission/). Ours asks a
yes/no question.
"""

RISKY = {"bash"}


def confirm(tool_name: str, args: dict, auto: bool = False, input_fn=input) -> bool:
    """Return True to proceed. Only gates tools named in RISKY.

    RISKY is deliberately just {"bash"}. write and edit_file mutate files
    but land in a repo under version control, so they are recoverable; bash
    can do anything to anything. A gate that fires on every file write
    trains the user to hit 'y' reflexively, which makes this gate worth
    less. A gate that fires constantly is a gate nobody reads.
    """
    if auto or tool_name not in RISKY:
        return True
    print(f"\n  {tool_name}: {args.get('command', args)}")
    return input_fn("  allow? [y/N] ").strip().lower() == "y"
