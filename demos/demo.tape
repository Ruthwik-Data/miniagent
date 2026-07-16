# vhs tape — the README demo.  Run: cd demos && vhs demo.tape
#
# Nothing is staged. calc.py has a real bug, the test really fails, and the
# agent really fixes it. If a run fails, the GIF shows it failing.

Output demo.gif

Set Shell zsh
Set FontSize 16
Set Width 1150
Set Height 440
Set Padding 20
Set Theme "Catppuccin Mocha"
Set TypingSpeed 40ms

Hide
Type "cd /tmp/miniagent-demo"
Enter
Type "source setup.sh"
Enter
Type "clear"
Enter
Show

Type "cat calc.py"
Enter
Sleep 1200ms

Type "pytest -q 2>&1 | tail -3"
Enter
Sleep 2500ms

Type "miniagent 'the tests are failing, fix them' --auto"
Enter
Sleep 40s

Type "pytest -q 2>&1 | tail -2"
Enter
Sleep 3500ms
