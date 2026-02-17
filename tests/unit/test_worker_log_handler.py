"""Unit tests for MongoWorkerLogHandler."""

from unittest.mock import MagicMock, patch

from app.worker_log_handler import MongoWorkerLogHandler


def test_emit_prints_to_stderr_on_mongodb_failure():
    """When MongoDB insert_one raises, emit prints error to stderr instead of failing silently."""
    handler = MongoWorkerLogHandler(user_id=1, account_id=2)
    record = MagicMock()
    record.levelname = "INFO"
    record.getMessage.return_value = "test message"

    with patch("pymongo.MongoClient") as mock_client:
        mock_db = MagicMock()
        mock_client.return_value.__getitem__.return_value = mock_db
        mock_db.worker_logs.insert_one.side_effect = Exception("Connection refused")

        with patch("sys.stderr") as mock_stderr:
            handler.emit(record)
            mock_stderr.write.assert_called()
            call_args = "".join(c.args[0] for c in mock_stderr.write.call_args_list)
            assert "MongoWorkerLogHandler" in call_args
            assert "Connection refused" in call_args or "Failed" in call_args
