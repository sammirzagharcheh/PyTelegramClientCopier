"""Lightweight API response-contract checks for frontend compatibility."""

from unittest.mock import AsyncMock, patch


def test_login_response_contract(api_client):
    r = api_client.post(
        "/api/auth/login",
        json={"email": "user@test.com", "password": "pass"},
    )
    assert r.status_code == 200
    data = r.json()
    assert set(data.keys()) == {"access_token", "refresh_token", "token_type"}
    assert data["token_type"] == "bearer"


def test_mappings_pagination_contract(api_client, user_token):
    r = api_client.get(
        "/api/mappings",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert set(data.keys()) == {"items", "total", "page", "page_size", "total_pages"}
    assert isinstance(data["items"], list)


def test_workers_list_contract(api_client, user_token):
    r = api_client.get(
        "/api/workers",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list)
    for w in items:
        assert {
            "id",
            "user_id",
            "account_id",
            "session_path",
            "pid",
            "running",
            "started_at",
        }.issubset(w.keys())


def test_message_logs_response_contract(api_client, user_token):
    def mock_aggregate(pipeline):
        has_count = any(
            isinstance(s, dict) and s.get("$count") == "total"
            for s in pipeline
        )
        if has_count:
            async def count_gen():
                yield {"total": 0}
            return count_gen()
        async def list_gen():
            if False:
                yield
        return list_gen()

    mock_coll = AsyncMock()
    mock_coll.aggregate = mock_aggregate
    mock_coll.count_documents = AsyncMock(return_value=0)
    mock_db = AsyncMock()
    mock_db.message_logs = mock_coll

    with patch("app.web.routers.message_logs.get_mongo_db", return_value=mock_db):
        r = api_client.get(
            "/api/message-logs",
            headers={"Authorization": f"Bearer {user_token}"},
        )
    assert r.status_code == 200
    data = r.json()
    assert set(data.keys()) == {"items", "total", "page", "page_size", "total_pages"}
    assert isinstance(data["items"], list)


def test_schedule_response_contract(api_client, user_token):
    r = api_client.get(
        "/api/users/me/schedule",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert r.status_code == 200
    data = r.json()
    schedule_fields = {
        "mon_start_utc", "mon_end_utc", "tue_start_utc", "tue_end_utc",
        "wed_start_utc", "wed_end_utc", "thu_start_utc", "thu_end_utc",
        "fri_start_utc", "fri_end_utc", "sat_start_utc", "sat_end_utc",
        "sun_start_utc", "sun_end_utc",
    }
    assert schedule_fields.issubset(data.keys())
