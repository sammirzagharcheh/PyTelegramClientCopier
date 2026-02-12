"""API tests for POST /auth/change-password (user self-change)."""

import pytest


def test_change_password_200(api_client, user_token):
    """Authenticated user can change password with correct current password."""
    r = api_client.post(
        "/api/auth/change-password",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"current_password": "pass", "new_password": "newpass123"},
    )
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}

    # Verify new password works by logging in
    login_r = api_client.post(
        "/api/auth/login",
        json={"email": "user@test.com", "password": "newpass123"},
    )
    assert login_r.status_code == 200
    assert "access_token" in login_r.json()

    # Old password should fail
    old_login = api_client.post(
        "/api/auth/login",
        json={"email": "user@test.com", "password": "pass"},
    )
    assert old_login.status_code == 401


def test_change_password_400_wrong_current(api_client, user_token):
    """Returns 400 when current password is incorrect."""
    r = api_client.post(
        "/api/auth/change-password",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"current_password": "wrong", "new_password": "newpass123"},
    )
    assert r.status_code == 400
    assert "incorrect" in r.json().get("detail", "").lower()


def test_change_password_401_no_auth(api_client):
    """Returns 401 when not authenticated."""
    r = api_client.post(
        "/api/auth/change-password",
        json={"current_password": "pass", "new_password": "newpass123"},
    )
    assert r.status_code == 401


def test_change_password_admin_can_use_own(api_client, admin_token):
    """Admin can change their own password via self-change endpoint."""
    r = api_client.post(
        "/api/auth/change-password",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"current_password": "pass", "new_password": "adminnew"},
    )
    assert r.status_code == 200

    login_r = api_client.post(
        "/api/auth/login",
        json={"email": "admin@test.com", "password": "adminnew"},
    )
    assert login_r.status_code == 200
