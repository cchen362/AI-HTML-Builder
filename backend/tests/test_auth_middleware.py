"""Tests for auth middleware (get_current_user, require_admin)."""

import os

os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key-for-testing")

from unittest.mock import patch, AsyncMock
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from app.auth_middleware import get_current_user, require_admin


def _make_test_app():
    """Create a minimal FastAPI app with endpoints that use auth deps."""
    test_app = FastAPI()

    @test_app.get("/test-user")
    async def get_user(user: dict = Depends(get_current_user)):
        return user

    @test_app.get("/test-admin")
    async def get_admin(user: dict = Depends(require_admin)):
        return user

    return test_app


def test_no_cookie_returns_401():
    app = _make_test_app()
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/test-user")
    assert resp.status_code == 401


def test_invalid_token_returns_401():
    app = _make_test_app()
    client = TestClient(app, raise_server_exceptions=False)
    client.cookies.set("auth_token", "fake-token")
    with patch(
        "app.services.auth_service.auth_service.validate_token",
        new_callable=AsyncMock,
        return_value=None,
    ):
        resp = client.get("/test-user")
    assert resp.status_code == 401


def test_valid_token_returns_user():
    app = _make_test_app()
    client = TestClient(app, raise_server_exceptions=False)
    client.cookies.set("auth_token", "good-token")
    user_data = {
        "id": "u1",
        "username": "test",
        "display_name": "Test",
        "is_admin": False,
    }
    with patch(
        "app.services.auth_service.auth_service.validate_token",
        new_callable=AsyncMock,
        return_value=user_data,
    ):
        resp = client.get("/test-user")
    assert resp.status_code == 200
    assert resp.json()["username"] == "test"


def test_non_admin_returns_403():
    app = _make_test_app()
    client = TestClient(app, raise_server_exceptions=False)
    client.cookies.set("auth_token", "good-token")
    user_data = {
        "id": "u1",
        "username": "test",
        "display_name": "Test",
        "is_admin": False,
    }
    with patch(
        "app.services.auth_service.auth_service.validate_token",
        new_callable=AsyncMock,
        return_value=user_data,
    ):
        resp = client.get("/test-admin")
    assert resp.status_code == 403


def test_admin_passes():
    app = _make_test_app()
    client = TestClient(app, raise_server_exceptions=False)
    client.cookies.set("auth_token", "good-token")
    user_data = {
        "id": "u1",
        "username": "admin",
        "display_name": "Admin",
        "is_admin": True,
    }
    with patch(
        "app.services.auth_service.auth_service.validate_token",
        new_callable=AsyncMock,
        return_value=user_data,
    ):
        resp = client.get("/test-admin")
    assert resp.status_code == 200
    assert resp.json()["username"] == "admin"
