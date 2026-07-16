# vhs tape — the README demo.
# Records the agent fixing a genuinely failing test, end to end.
#
#   cd demos && vhs demo.tape
#
# Requires: a working provider key exported as OPENAI_API_KEY (or edit the
# --model flag below for any litellm provider).
#
# The setup is real: calc.py has a real bug, test_calc.py really fails, and
# the agent really fixes it. Nothing here is staged — if the run fails, the
# GIF shows it failing.

Output demo.gif

Set Shell zsh
Set FontSize 15
Set Width 1200
Set Height 760
Set Padding 22
Set Theme "Catppuccin Mocha"
Set TypingSpeed 45ms
Set PlaybackSpeed 1.0

# --- setup: a real bug in a real repo -------------------------------------
Hide
Type "cd $(mktemp -d)" Enter
Type "printf 'def add(a, b):\n    return a - b\n' > calc.py" Enter
Type "printf 'from calc import add\n\ndef test_add():\n    assert add(1, 2) == 3\n' > test_calc.py" Enter
Type "clear" Enter
Show

# --- the bug --------------------------------------------------------------
Type "cat calc.py"
Enter
Sleep 1.5s

Type "~/miniagent/.venv/bin/pytest -q 2>&1 | tail -3"
Enter
Sleep 3s

# --- hand it to the agent -------------------------------------------------
Type "miniagent 'the tests are failing, fix them' --auto"
Enter
Sleep 45s

# --- proof ----------------------------------------------------------------
Type "cat calc.py"
Enter
Sleep 2s

Type "~/miniagent/.venv/bin/pytest -q 2>&1 | tail -2"
Enter
Sleep 4s
