"""API tests for /api/stats/dashboard and /api/admin/stats/dashboard."""

from __future__ import annotations

import pytest


def test_stats_dashboard_200_schema(api_client, user_token):
    """User stats endpoint returns 200 and expected schema (works without MongoDB)."""
    r = api_client.get(
        "/api/stats/dashboard",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "messages_last_7d" in data
    assert "messages_prev_7d" in data
    assert "messages_by_day" in data
    assert "status_breakdown" in data
    assert "account_status" in data
    assert "mappings_total" in data
    assert "mappings_enabled" in data
    assert "accounts_total" in data
    assert isinstance(data["messages_last_7d"], int)
    assert isinstance(data["messages_prev_7d"], int)
    assert isinstance(data["messages_by_day"], list)
    assert len(data["messages_by_day"]) == 7
    for day in data["messages_by_day"]:
        assert "date" in day
        assert "count" in day
        assert isinstance(day["count"], int)
    assert isinstance(data["status_breakdown"], list)
    assert isinstance(data["account_status"], dict)
    assert data["mappings_total"] == 1  # seeded: user 1 has 1 mapping
    assert data["mappings_enabled"] == 1


def test_stats_dashboard_401_no_auth(api_client):
    """Stats endpoint returns 401 when not authenticated."""
    r = api_client.get("/api/stats/dashboard")
    assert r.status_code == 401


def test_admin_stats_dashboard_200_schema(api_client, admin_token):
    """Admin stats endpoint returns 200 and expected schema."""
    r = api_client.get(
        "/api/admin/stats/dashboard",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "users_total" in data
    assert "mappings_total" in data
    assert "mappings_enabled" in data
    assert "workers_count" in data
    assert "active_accounts" in data
    assert "messages_last_7d" in data
    assert "messages_prev_7d" in data
    assert "messages_by_day" in data
    assert "status_breakdown" in data
    assert "top_mappings" in data
    assert "worker_log_levels" in data
    assert isinstance(data["messages_by_day"], list)
    assert len(data["messages_by_day"]) == 7
    assert isinstance(data["top_mappings"], list)
    assert isinstance(data["worker_log_levels"], list)
    assert data["users_total"] == 3  # seeded users
    assert data["mappings_total"] == 2  # seeded mappings


def test_admin_stats_dashboard_401_no_auth(api_client):
    """Admin stats endpoint returns 401 when not authenticated."""
    r = api_client.get("/api/admin/stats/dashboard")
    assert r.status_code == 401


def test_admin_stats_dashboard_403_user_role(api_client, user_token):
    """Regular user cannot access admin stats."""
    r = api_client.get(
        "/api/admin/stats/dashboard",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert r.status_code == 403
