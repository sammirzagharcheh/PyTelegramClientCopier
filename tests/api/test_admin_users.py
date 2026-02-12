"""API tests for PATCH /admin/users/{user_id} (admin edit user, incl. password)."""

import pytest


def test_patch_user_200(api_client, admin_token):
    """Admin can update user name, role, and status."""
    r = api_client.patch(
        "/api/admin/users/1",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "Updated User", "role": "user", "status": "active"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == 1
    assert data["email"] == "user@test.com"
    assert data["name"] == "Updated User"
    assert data["role"] == "user"
    assert data["status"] == "active"


def test_patch_user_status_inactive(api_client, admin_token):
    """Admin can set user status to inactive."""
    r = api_client.patch(
        "/api/admin/users/3",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"status": "inactive"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "inactive"


def test_patch_user_password_200(api_client, admin_token):
    """Admin can set new password for a user; new password works for login."""
    r = api_client.patch(
        "/api/admin/users/1",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"password": "admin_set_newpass"},
    )
    assert r.status_code == 200

    # New password works
    login_r = api_client.post(
        "/api/auth/login",
        json={"email": "user@test.com", "password": "admin_set_newpass"},
    )
    assert login_r.status_code == 200
    assert "access_token" in login_r.json()

    # Old password fails
    old_login = api_client.post(
        "/api/auth/login",
        json={"email": "user@test.com", "password": "pass"},
    )
    assert old_login.status_code == 401


def test_patch_user_partial(api_client, admin_token):
    """Admin can send partial update (only name)."""
    r = api_client.patch(
        "/api/admin/users/2",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "Admin Renamed"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Admin Renamed"
    assert data["email"] == "admin@test.com"
    assert data["role"] == "admin"


def test_patch_user_401_no_auth(api_client):
    """Returns 401 when not authenticated."""
    r = api_client.patch(
        "/api/admin/users/1",
        json={"name": "X"},
    )
    assert r.status_code == 401


def test_patch_user_403_user_role(api_client, user_token):
    """Regular user cannot PATCH other users (admin only)."""
    r = api_client.patch(
        "/api/admin/users/3",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"name": "Hacked"},
    )
    assert r.status_code == 403


def test_patch_user_404(api_client, admin_token):
    """Returns 404 when user does not exist."""
    r = api_client.patch(
        "/api/admin/users/999",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "X"},
    )
    assert r.status_code == 404
