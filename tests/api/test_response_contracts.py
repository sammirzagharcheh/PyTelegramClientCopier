"""Lightweight API response-contract checks for frontend compatibility."""


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
