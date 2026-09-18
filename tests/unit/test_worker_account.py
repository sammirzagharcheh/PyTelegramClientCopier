"""User vs bot worker registry paths and CLI argv."""

from pathlib import Path

from app.telegram.worker_account import (
    bot_registry_path,
    build_run_worker_argv,
    is_bot_registry_path,
)


def test_bot_registry_path_shape():
    assert bot_registry_path(7) == "bot://7"
    assert is_bot_registry_path("bot://7") is True
    assert is_bot_registry_path("/tmp/user.session") is False
    assert is_bot_registry_path("") is False
    assert is_bot_registry_path(None) is False


def test_build_run_worker_argv_user_includes_session_not_token(tmp_path):
    session = tmp_path / "acct.session"
    session.write_text("x")
    argv = build_run_worker_argv(
        user_id=1,
        account_id=4,
        session_path=str(session),
        python_exe="python",
        project_root=tmp_path,
    )
    assert "--account-id" in argv
    assert "4" in argv
    assert str(session.resolve()) in argv
    joined = " ".join(argv)
    assert "bot_token" not in joined
    assert "123456:" not in joined


def test_build_run_worker_argv_bot_omits_token_and_session_file(tmp_path):
    token = "123456:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw"
    argv = build_run_worker_argv(
        user_id=2,
        account_id=9,
        session_path=bot_registry_path(9),
        python_exe="python",
        project_root=tmp_path,
    )
    joined = " ".join(argv)
    assert token not in joined
    assert "bot://" not in joined
    assert argv[-2:] == ["--account-id", "9"]
    assert "--account-id" in argv
    # No extra positional after user_id besides flags
    assert "run-worker" in argv
    user_id_idx = argv.index("2")
    assert argv[user_id_idx + 1] == "--account-id"
