from miniagent import sessions


def test_save_then_load_round_trips_messages(tmp_path):
    messages = [
        {"role": "system", "content": "you are an agent"},
        {"role": "user", "content": "hi"},
        {"role": "tool", "tool_call_id": "1", "content": "exit 0"},
    ]
    sessions.save("s1", messages, root=tmp_path)
    assert sessions.load("s1", root=tmp_path) == messages


def test_save_creates_the_session_directory(tmp_path):
    path = sessions.save("s1", [{"role": "user", "content": "x"}], root=tmp_path)
    assert path.exists()
    assert path.parent == tmp_path / ".miniagent" / "sessions"


def test_latest_returns_the_most_recently_written_session(tmp_path):
    sessions.save("older", [{"role": "user", "content": "1"}], root=tmp_path)
    sessions.save("newer", [{"role": "user", "content": "2"}], root=tmp_path)
    assert sessions.latest(root=tmp_path) == "newer"


def test_latest_returns_none_when_there_are_no_sessions(tmp_path):
    assert sessions.latest(root=tmp_path) is None


def test_new_id_is_unique():
    assert sessions.new_id() != sessions.new_id()
