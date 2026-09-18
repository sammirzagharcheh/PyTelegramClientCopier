"""restart_workers_for_mapping includes bot accounts."""

from unittest.mock import MagicMock, patch

import pytest

from app.db.sqlite import get_sqlite, init_sqlite
from app.telegram.worker_account import bot_registry_path
from app.web.routers import workers


@pytest.mark.asyncio
async def test_restart_workers_for_mapping_spawns_bound_bot(tmp_path):
    import app.config as config

    config.settings.sqlite_path = str(tmp_path / "map-bot.db")
    await init_sqlite()
    db = await get_sqlite()
    await db.execute(
        "INSERT INTO users (id, email, role, status) VALUES (?, ?, ?, ?)",
        (1, "user@example.com", "user", "active"),
    )
    await db.execute(
        "INSERT INTO telegram_accounts (id, user_id, type, bot_token, status, name) VALUES (?, ?, ?, ?, ?, ?)",
        (5, 1, "bot", "123456:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw", "active", "Bot"),
    )
    await db.commit()

    workers._workers.clear()
    workers._worker_counter = 0
    fake_proc = MagicMock()
    fake_proc.pid = 777
    fake_proc.poll.return_value = None

    with patch("subprocess.Popen", return_value=fake_proc) as mock_popen:
        await workers.restart_workers_for_mapping(db, 1, 5)

    assert mock_popen.called
    cmd = mock_popen.call_args[0][0]
    assert "--account-id" in cmd
    assert "5" in cmd
    assert "123456:" not in " ".join(str(x) for x in cmd)
    # Registry uses sentinel, not empty session
    async with db.execute("SELECT session_path FROM worker_registry WHERE account_id = 5") as cur:
        row = await cur.fetchone()
    assert row[0] == bot_registry_path(5)
    await db.close()
