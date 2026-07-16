from miniagent.tools import edit_file, write


def test_edit_file_replaces_a_unique_string(tmp_path):
    f = tmp_path / "calc.py"
    f.write_text("def add(a, b):\n    return a - b\n")
    result = edit_file(str(f), "return a - b", "return a + b")
    assert result == f"edited {f}"
    assert f.read_text() == "def add(a, b):\n    return a + b\n"


def test_edit_file_reports_no_match_as_a_string(tmp_path):
    f = tmp_path / "calc.py"
    f.write_text("def add(a, b):\n    return a + b\n")
    result = edit_file(str(f), "return a * b", "return a + b")
    assert "no match" in result
    assert f.read_text() == "def add(a, b):\n    return a + b\n"


def test_edit_file_refuses_ambiguous_matches(tmp_path):
    f = tmp_path / "d.py"
    f.write_text("x = 1\nx = 1\n")
    result = edit_file(str(f), "x = 1", "x = 2")
    assert "2 matches" in result
    assert f.read_text() == "x = 1\nx = 1\n"


def test_edit_file_missing_file_returns_a_string(tmp_path):
    result = edit_file(str(tmp_path / "nope.py"), "a", "b")
    assert "error" in result.lower()


def test_write_creates_a_new_file(tmp_path):
    f = tmp_path / "new.py"
    result = write(str(f), "print('hi')\n")
    assert "wrote" in result
    assert f.read_text() == "print('hi')\n"


def test_write_creates_missing_parent_directories(tmp_path):
    f = tmp_path / "a" / "b" / "new.py"
    write(str(f), "x = 1\n")
    assert f.read_text() == "x = 1\n"


def test_write_overwrites_an_existing_file(tmp_path):
    f = tmp_path / "old.py"
    f.write_text("old content\n")
    write(str(f), "new content\n")
    assert f.read_text() == "new content\n"
