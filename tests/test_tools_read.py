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


def test_grep_never_searches_the_agents_own_session_store(tmp_path):
    # Found live: grep matched .miniagent/sessions/*.json — the transcript the
    # running loop was writing — and fed the conversation back into itself.
    # 142,984 tokens against a 128,000 limit in six turns.
    sessions = tmp_path / ".miniagent" / "sessions"
    sessions.mkdir(parents=True)
    (sessions / "s1.json").write_text('{"content": "findme"}\n')
    (tmp_path / "real.py").write_text("findme\n")

    out = grep("findme", str(tmp_path))

    assert "real.py" in out
    assert ".miniagent" not in out


def test_grep_skips_vcs_and_build_dirs(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "COMMIT_EDITMSG").write_text("needle\n")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "x.js").write_text("needle\n")
    (tmp_path / "src.py").write_text("needle\n")

    out = grep("needle", str(tmp_path))

    assert "src.py" in out
    assert ".git" not in out
    assert "node_modules" not in out
