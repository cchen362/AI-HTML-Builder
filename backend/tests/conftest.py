"""Shared test configuration.

Overrides auth dependency so all existing tests pass without
real authentication cookies.
"""

import os

# Ensure test env vars are set before any app import
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key-for-testing")

import pytest  # noqa: E402


_TEST_USER = {
    "id": "test-user-id",
    "username": "testuser",
    "display_name": "Test User",
    "is_admin": True,
}


@pytest.fixture(autouse=True)
def override_auth():
    """Override get_current_user and require_admin for all tests."""
    from app.main import app
    from app.auth_middleware import get_current_user, require_admin

    async def _fake_user() -> dict:
        return _TEST_USER

    async def _fake_admin() -> dict:
        return _TEST_USER

    app.dependency_overrides[get_current_user] = _fake_user
    app.dependency_overrides[require_admin] = _fake_admin
    yield
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(require_admin, None)
