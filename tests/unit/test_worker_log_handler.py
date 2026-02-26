"""Unit tests for MongoWorkerLogHandler and test_mongo_connection."""

from unittest.mock import MagicMock, patch

from app.worker_log_handler import MongoWorkerLogHandler, test_mongo_connection as check_mongo_connection


def test_test_mongo_connection_success():
    """test_mongo_connection returns (None, db_name) when write/delete succeeds."""
    with (
        patch("app.worker_log_handler._resolve_mongo_uri", return_value="mongodb://localhost:27017"),
        patch("app.worker_log_handler._resolve_mongo_db", return_value="test_db"),
        patch("pymongo.MongoClient") as mock_client,
    ):
        mock_db = MagicMock()
        mock_client.return_value.__getitem__.return_value = mock_db

        err, db_name = check_mongo_connection()

        assert err is None
        assert db_name == "test_db"
        mock_db.worker_logs.insert_one.assert_called_once()
        mock_db.worker_logs.delete_one.assert_called_once()


def test_test_mongo_connection_failure():
    """test_mongo_connection returns (error_str, db_name) when MongoDB fails."""
    with (
        patch("app.worker_log_handler._resolve_mongo_uri", return_value="mongodb://localhost:27017"),
        patch("app.worker_log_handler._resolve_mongo_db", return_value="test_db"),
        patch("pymongo.MongoClient") as mock_client,
    ):
        mock_db = MagicMock()
        mock_client.return_value.__getitem__.return_value = mock_db
        mock_db.worker_logs.insert_one.side_effect = Exception("Connection refused")

        err, db_name = check_mongo_connection()

        assert err == "Connection refused"
        assert db_name == "test_db"


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
