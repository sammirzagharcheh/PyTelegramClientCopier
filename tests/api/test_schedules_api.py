"""API tests for schedule endpoints."""

import pytest


def test_get_user_schedule_200(api_client, user_token):
    r = api_client.get("/api/users/me/schedule", headers={"Authorization": f"Bearer {user_token}"})
    assert r.status_code == 200
    data = r.json()
    assert "mon_start_utc" in data
    assert "sun_end_utc" in data


def test_get_user_schedule_401_no_auth(api_client):
    r = api_client.get("/api/users/me/schedule")
    assert r.status_code == 401


def test_patch_user_schedule_200(api_client, user_token):
    r = api_client.patch(
        "/api/users/me/schedule",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "mon_start_utc": "09:00",
            "mon_end_utc": "17:00",
            "tue_start_utc": "09:00",
            "tue_end_utc": "17:00",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["mon_start_utc"] == "09:00"
    assert data["mon_end_utc"] == "17:00"


def test_patch_user_schedule_422_invalid_time_format(api_client, user_token):
    r = api_client.patch(
        "/api/users/me/schedule",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"mon_start_utc": "9:00"},
    )
    assert r.status_code == 422
    details = r.json().get("detail", [])
    assert any("UTC HH:MM" in str(item) for item in details)


def test_get_mapping_schedule_200(api_client, user_token):
    r = api_client.get("/api/mappings/1/schedule", headers={"Authorization": f"Bearer {user_token}"})
    assert r.status_code == 200
    data = r.json()
    assert "mon_start_utc" in data


def test_get_mapping_schedule_404(api_client, user_token):
    r = api_client.get("/api/mappings/999/schedule", headers={"Authorization": f"Bearer {user_token}"})
    assert r.status_code == 404


def test_get_mapping_schedule_403_other_user(api_client, user_token):
    r = api_client.get("/api/mappings/2/schedule", headers={"Authorization": f"Bearer {user_token}"})
    assert r.status_code == 403


def test_put_mapping_schedule_200(api_client, user_token):
    r = api_client.put(
        "/api/mappings/1/schedule",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"mon_start_utc": "10:00", "mon_end_utc": "18:00"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["mon_start_utc"] == "10:00"
    assert data["mon_end_utc"] == "18:00"


def test_put_mapping_schedule_422_invalid_time_format(api_client, user_token):
    r = api_client.put(
        "/api/mappings/1/schedule",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"mon_end_utc": "24:00"},
    )
    assert r.status_code == 422
    details = r.json().get("detail", [])
    assert any("UTC HH:MM" in str(item) for item in details)


def test_delete_mapping_schedule_200(api_client, user_token):
    r = api_client.delete("/api/mappings/1/schedule", headers={"Authorization": f"Bearer {user_token}"})
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_bulk_apply_schedule_200(api_client, user_token):
    api_client.patch(
        "/api/users/me/schedule",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"mon_start_utc": "09:00", "mon_end_utc": "17:00"},
    )
    r = api_client.post(
        "/api/mappings/schedule/bulk-apply",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "updated" in data


def test_admin_can_manage_other_user_mapping_schedule(api_client, admin_token):
    """Admin can GET, PUT, and DELETE schedule for mapping owned by another user (mapping 1 = user 1)."""
    # GET - admin can read
    r = api_client.get(
        "/api/mappings/1/schedule",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "mon_start_utc" in data

    # PUT - admin can update
    r = api_client.put(
        "/api/mappings/1/schedule",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"mon_start_utc": "08:00", "mon_end_utc": "18:00"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["mon_start_utc"] == "08:00"
    assert data["mon_end_utc"] == "18:00"

    # DELETE - admin can switch to default
    r = api_client.delete(
        "/api/mappings/1/schedule",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
