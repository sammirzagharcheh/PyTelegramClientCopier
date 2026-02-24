"""API tests for transform CRUD endpoints."""


def test_list_transforms_200_empty(api_client, user_token):
    r = api_client.get(
        "/api/mappings/1/transforms",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert r.status_code == 200
    assert r.json() == []


def test_list_transforms_403_other_user(api_client, user_token):
    r = api_client.get(
        "/api/mappings/2/transforms",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert r.status_code == 403


def test_create_text_transform_201(api_client, user_token):
    r = api_client.post(
        "/api/mappings/1/transforms",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "rule_type": "text",
            "find_text": "Sam channel",
            "replace_text": "Tom channel",
            "priority": 10,
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["rule_type"] == "text"
    assert data["find_text"] == "Sam channel"
    assert data["replace_text"] == "Tom channel"
    assert data["enabled"] is True


def test_create_regex_transform_201(api_client, user_token):
    r = api_client.post(
        "/api/mappings/1/transforms",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "rule_type": "regex",
            "regex_pattern": "#\\d+",
            "replace_text": "#XXX",
            "regex_flags": "i",
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["rule_type"] == "regex"
    assert data["regex_pattern"] == "#\\d+"
    assert data["regex_flags"] == "i"


def test_create_regex_transform_invalid_pattern_400(api_client, user_token):
    r = api_client.post(
        "/api/mappings/1/transforms",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "rule_type": "regex",
            "regex_pattern": "(",
            "replace_text": "x",
        },
    )
    assert r.status_code == 400
    assert "Invalid regex pattern" in r.json()["detail"]


def test_create_emoji_requires_find_text(api_client, user_token):
    r = api_client.post(
        "/api/mappings/1/transforms",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "rule_type": "emoji",
            "replace_text": "STAR",
        },
    )
    assert r.status_code == 400
    assert "find_text is required" in r.json()["detail"]


def test_update_transform_200(api_client, user_token):
    create = api_client.post(
        "/api/mappings/1/transforms",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "rule_type": "text",
            "find_text": "Sam",
            "replace_text": "Tom",
        },
    )
    assert create.status_code == 201
    transform_id = create.json()["id"]

    r = api_client.patch(
        f"/api/mappings/1/transforms/{transform_id}",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"replace_text": "Tommy", "enabled": False, "priority": 5},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["replace_text"] == "Tommy"
    assert data["enabled"] is False
    assert data["priority"] == 5


def test_delete_transform_200(api_client, user_token):
    create = api_client.post(
        "/api/mappings/1/transforms",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "rule_type": "text",
            "find_text": "Sam",
            "replace_text": "Tom",
        },
    )
    assert create.status_code == 201
    transform_id = create.json()["id"]

    delete_resp = api_client.delete(
        f"/api/mappings/1/transforms/{transform_id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert delete_resp.status_code == 200
    assert delete_resp.json()["status"] == "ok"


def test_admin_can_manage_other_user_transforms(api_client, admin_token):
    create = api_client.post(
        "/api/mappings/1/transforms",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "rule_type": "text",
            "find_text": "A",
            "replace_text": "B",
        },
    )
    assert create.status_code == 201
    transform_id = create.json()["id"]

    list_resp = api_client.get(
        "/api/mappings/1/transforms",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert list_resp.status_code == 200
    assert any(item["id"] == transform_id for item in list_resp.json())
