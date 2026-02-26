"""API tests for GET/PATCH /auth/me (user profile, timezone)."""

import pytest


def test_get_me_returns_timezone(api_client, user_token):
    """GET /auth/me includes timezone field (null or string)."""
    r = api_client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "timezone" in data
    assert data["timezone"] is None or isinstance(data["timezone"], str)


def test_patch_me_timezone_200(api_client, user_token):
    """PATCH /auth/me with valid timezone updates and returns updated user."""
    # Use UTC - guaranteed in zoneinfo on all platforms (Windows, minimal installs)
    r = api_client.patch(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"timezone": "UTC"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["timezone"] == "UTC"
    assert "email" in data
    assert "id" in data

    # Verify persisted
    get_r = api_client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert get_r.status_code == 200
    assert get_r.json()["timezone"] == "UTC"


def test_patch_me_timezone_null(api_client, user_token):
    """PATCH /auth/me with null clears timezone."""
    api_client.patch(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"timezone": "UTC"},
    )
    r = api_client.patch(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"timezone": None},
    )
    assert r.status_code == 200
    assert r.json()["timezone"] is None


def test_patch_me_timezone_invalid_400(api_client, user_token):
    """PATCH /auth/me with invalid IANA timezone returns 400."""
    r = api_client.patch(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"timezone": "Invalid/Timezone"},
    )
    assert r.status_code == 400
    assert "Invalid timezone" in r.json().get("detail", "")


def test_patch_me_401_no_auth(api_client):
    """PATCH /auth/me returns 401 when not authenticated."""
    r = api_client.patch(
        "/api/auth/me",
        json={"timezone": "UTC"},
    )
    assert r.status_code == 401
