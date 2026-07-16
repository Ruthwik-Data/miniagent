from miniagent.tools import read_file, list_dir, grep


def test_read_file_adds_line_numbers(tmp_path):
    f = tmp_path / "a.py"
    f.write_text("first\nsecond\n")
    assert read_file(str(f)) == "1\tfirst\n2\tsecond"


def test_read_file_honours_offset_and_limit(tmp_path):
    f = tmp_path / "a.py"
    f.write_text("one\ntwo\nthree\nfour\n")
    assert read_file(str(f), offset=1, limit=2) == "2\ttwo\n3\tthree"


def test_list_dir_marks_dirs_and_files(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "a.txt").write_text("x")
    assert list_dir(str(tmp_path)) == "f a.txt\nd sub"


def test_grep_reports_file_line_and_text(tmp_path):
    (tmp_path / "a.py").write_text("import os\nimport sys\n")
    out = grep("^import sys", str(tmp_path))
    assert out.endswith("a.py:2:import sys")


def test_grep_reports_no_matches_rather_than_empty(tmp_path):
    (tmp_path / "a.py").write_text("nothing here\n")
    assert grep("zzz", str(tmp_path)) == "no matches"
