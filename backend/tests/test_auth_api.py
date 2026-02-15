"""Tests for auth API endpoints."""

import os

os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key-for-testing")

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient


@pytest.fixture
def auth_client(tmp_path):
    """TestClient with real auth (no override) and temp databases."""
    auth_path = str(tmp_path / "auth.db")
    app_path = str(tmp_path / "app.db")

    # Patch settings at every import site:
    # - app.config.settings: covers lazy `from app.config import settings` in auth.py, auth_service.py
    # - app.auth_database.settings: module-level import
    # - app.database.settings: module-level import
    with (
        patch("app.config.settings") as mock_cfg_settings,
        patch("app.auth_database.settings") as mock_auth_settings,
        patch("app.database.settings") as mock_db_settings,
    ):
        for s in (mock_cfg_settings, mock_auth_settings, mock_db_settings):
            s.auth_database_path = auth_path
            s.database_path = app_path
            s.auth_session_expiry_days = 30
            s.dev_mode = True

        import app.auth_database as auth_db_mod
        import app.database as db_mod

        auth_db_mod._db = None
        db_mod._db = None

        import asyncio

        loop = asyncio.new_event_loop()
        loop.run_until_complete(auth_db_mod.init_auth_db())
        loop.run_until_complete(db_mod.init_db())

        from app.main import app
        from app.auth_middleware import get_current_user, require_admin

        # Remove the conftest overrides for this test module
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(require_admin, None)

        client = TestClient(app, raise_server_exceptions=False)
        yield client

        loop.run_until_complete(auth_db_mod.close_auth_db())
        loop.run_until_complete(db_mod.close_db())
        loop.close()


def test_needs_setup_initially(auth_client):
    resp = auth_client.get("/api/auth/needs-setup")
    assert resp.status_code == 200
    assert resp.json()["needs_setup"] is True


def test_setup_admin(auth_client):
    resp = auth_client.post("/api/auth/setup", json={
        "username": "admin",
        "password": "secret123",
        "display_name": "Admin",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["user"]["username"] == "admin"
    assert data["user"]["is_admin"] is True
    # Cookie should be set
    assert "auth_token" in resp.cookies


def test_setup_twice_fails(auth_client):
    auth_client.post("/api/auth/setup", json={
        "username": "admin",
        "password": "secret",
        "display_name": "Admin",
    })
    resp = auth_client.post("/api/auth/setup", json={
        "username": "admin2",
        "password": "secret",
        "display_name": "Admin2",
    })
    assert resp.status_code == 409


def test_login_success(auth_client):
    auth_client.post("/api/auth/setup", json={
        "username": "admin",
        "password": "pass123",
        "display_name": "Admin",
    })
    resp = auth_client.post("/api/auth/login", json={
        "username": "admin",
        "password": "pass123",
    })
    assert resp.status_code == 200
    assert "auth_token" in resp.cookies
    assert resp.json()["user"]["username"] == "admin"


def test_login_wrong_password(auth_client):
    auth_client.post("/api/auth/setup", json={
        "username": "admin",
        "password": "pass123",
        "display_name": "Admin",
    })
    resp = auth_client.post("/api/auth/login", json={
        "username": "admin",
        "password": "wrong123",
    })
    assert resp.status_code == 401


def test_me_with_cookie(auth_client):
    auth_client.post("/api/auth/setup", json={
        "username": "admin",
        "password": "pass123",
        "display_name": "Admin",
    })
    # The cookie from setup should let us access /me
    resp = auth_client.get("/api/auth/me")
    assert resp.status_code == 200
    assert resp.json()["user"]["username"] == "admin"


def test_me_without_cookie(auth_client):
    # Clear any cookies
    auth_client.cookies.clear()
    resp = auth_client.get("/api/auth/me")
    assert resp.status_code == 401


def test_logout(auth_client):
    auth_client.post("/api/auth/setup", json={
        "username": "admin",
        "password": "pass123",
        "display_name": "Admin",
    })
    # Logged in from setup
    resp = auth_client.post("/api/auth/logout")
    assert resp.status_code == 200
    # Cookie should be cleared (max_age=0)
    # After logout, /me should fail
    auth_client.cookies.clear()
    resp = auth_client.get("/api/auth/me")
    assert resp.status_code == 401


def test_register_with_invite_code(auth_client):
    auth_client.post("/api/auth/setup", json={
        "username": "admin",
        "password": "pass123",
        "display_name": "Admin",
    })
    # Get invite code via admin endpoint
    code_resp = auth_client.get("/api/admin/invite-code")
    assert code_resp.status_code == 200
    code = code_resp.json()["invite_code"]

    # Clear admin cookies for registration
    auth_client.cookies.clear()

    resp = auth_client.post("/api/auth/register", json={
        "username": "user1",
        "password": "pass123",
        "display_name": "User One",
        "invite_code": code,
    })
    assert resp.status_code == 200
    assert resp.json()["user"]["username"] == "user1"
    assert resp.json()["user"]["is_admin"] is False
    assert "auth_token" in resp.cookies


def test_register_with_bad_invite_code(auth_client):
    auth_client.post("/api/auth/setup", json={
        "username": "admin",
        "password": "pass123",
        "display_name": "Admin",
    })
    auth_client.cookies.clear()

    resp = auth_client.post("/api/auth/register", json={
        "username": "user1",
        "password": "pass123",
        "display_name": "User One",
        "invite_code": "bad-code",
    })
    assert resp.status_code == 400


def test_protected_endpoint_without_auth(auth_client):
    auth_client.cookies.clear()
    resp = auth_client.post("/api/sessions")
    assert resp.status_code == 401


def test_admin_endpoint_with_non_admin(auth_client):
    auth_client.post("/api/auth/setup", json={
        "username": "admin",
        "password": "pass123",
        "display_name": "Admin",
    })
    code_resp = auth_client.get("/api/admin/invite-code")
    code = code_resp.json()["invite_code"]

    auth_client.cookies.clear()
    auth_client.post("/api/auth/register", json={
        "username": "user1",
        "password": "pass123",
        "display_name": "User One",
        "invite_code": code,
    })
    # Now logged in as non-admin user1
    resp = auth_client.get("/api/costs")
    assert resp.status_code == 403


def test_admin_users_list(auth_client):
    auth_client.post("/api/auth/setup", json={
        "username": "admin",
        "password": "pass123",
        "display_name": "Admin",
    })
    resp = auth_client.get("/api/admin/users")
    assert resp.status_code == 200
    users = resp.json()["users"]
    assert len(users) == 1
    assert users[0]["username"] == "admin"


def test_admin_regenerate_invite_code(auth_client):
    auth_client.post("/api/auth/setup", json={
        "username": "admin",
        "password": "pass123",
        "display_name": "Admin",
    })
    code1 = auth_client.get("/api/admin/invite-code").json()["invite_code"]
    code2 = auth_client.post("/api/admin/invite-code").json()["invite_code"]
    assert code1 != code2


def test_admin_delete_user(auth_client):
    auth_client.post("/api/auth/setup", json={
        "username": "admin",
        "password": "pass123",
        "display_name": "Admin",
    })
    code = auth_client.get("/api/admin/invite-code").json()["invite_code"]
    auth_client.cookies.clear()
    reg_resp = auth_client.post("/api/auth/register", json={
        "username": "user1",
        "password": "pass123",
        "display_name": "User1",
        "invite_code": code,
    })
    user_id = reg_resp.json()["user"]["id"]

    # Log back in as admin
    auth_client.cookies.clear()
    auth_client.post("/api/auth/login", json={
        "username": "admin",
        "password": "pass123",
    })

    resp = auth_client.delete(f"/api/admin/users/{user_id}")
    assert resp.status_code == 200

    # Verify user is gone
    users = auth_client.get("/api/admin/users").json()["users"]
    assert len(users) == 1
