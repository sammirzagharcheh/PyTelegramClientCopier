"""API tests for filter CRUD endpoints."""

import pytest


def test_list_filters_200(api_client, user_token):
    r = api_client.get(
        "/api/mappings/1/filters",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_list_filters_404_mapping(api_client, user_token):
    r = api_client.get(
        "/api/mappings/999/filters",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert r.status_code == 404


def test_list_filters_403_other_user(api_client, user_token):
    r = api_client.get(
        "/api/mappings/2/filters",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert r.status_code == 403


def test_list_filters_401_no_auth(api_client):
    r = api_client.get("/api/mappings/1/filters")
    assert r.status_code == 401


def test_create_filter_201(api_client, user_token):
    r = api_client.post(
        "/api/mappings/1/filters",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"include_text": "announcement", "exclude_text": None, "media_types": None, "regex_pattern": None},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["include_text"] == "announcement"
    assert data["mapping_id"] == 1
    assert "id" in data


def test_create_filter_with_all_fields(api_client, user_token):
    r = api_client.post(
        "/api/mappings/1/filters",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "include_text": "order",
            "exclude_text": "spam",
            "media_types": "text,voice",
            "regex_pattern": r"#\d+",
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["include_text"] == "order"
    assert data["exclude_text"] == "spam"
    assert data["media_types"] == "text,voice"
    assert data["regex_pattern"] == r"#\d+"


def test_create_filter_404_mapping(api_client, user_token):
    r = api_client.post(
        "/api/mappings/999/filters",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"include_text": "x"},
    )
    assert r.status_code == 404


def test_create_filter_403_other_user(api_client, user_token):
    r = api_client.post(
        "/api/mappings/2/filters",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"include_text": "x"},
    )
    assert r.status_code == 403


def test_update_filter_200(api_client, user_token):
    create = api_client.post(
        "/api/mappings/1/filters",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"include_text": "old", "exclude_text": None, "media_types": None, "regex_pattern": None},
    )
    assert create.status_code == 201
    fid = create.json()["id"]

    r = api_client.patch(
        f"/api/mappings/1/filters/{fid}",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"include_text": "new"},
    )
    assert r.status_code == 200
    assert r.json()["include_text"] == "new"


def test_update_filter_404_filter(api_client, user_token):
    r = api_client.patch(
        "/api/mappings/1/filters/999",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"include_text": "x"},
    )
    assert r.status_code == 404


def test_update_filter_403_other_user(api_client, user_token):
    r = api_client.patch(
        "/api/mappings/2/filters/1",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"include_text": "x"},
    )
    assert r.status_code == 403


def test_delete_filter_200(api_client, user_token):
    create = api_client.post(
        "/api/mappings/1/filters",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"include_text": "todelete", "exclude_text": None, "media_types": None, "regex_pattern": None},
    )
    assert create.status_code == 201
    fid = create.json()["id"]

    r = api_client.delete(
        f"/api/mappings/1/filters/{fid}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert r.status_code == 200

    list_r = api_client.get(
        "/api/mappings/1/filters",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    ids = [f["id"] for f in list_r.json()]
    assert fid not in ids


def test_delete_filter_404(api_client, user_token):
    r = api_client.delete(
        "/api/mappings/1/filters/999",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert r.status_code == 404


def test_admin_can_access_any_mapping_filters(api_client, admin_token):
    r = api_client.get(
        "/api/mappings/1/filters",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
