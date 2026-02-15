"""Tests for AuthService."""

import os

os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key-for-testing")

import pytest
from unittest.mock import patch


@pytest.fixture
async def auth_dbs(tmp_path):
    """Initialize both auth and app databases in temp dir."""
    auth_path = str(tmp_path / "auth.db")
    app_path = str(tmp_path / "app.db")

    # Patch settings at all import sites:
    # - app.config.settings: covers lazy imports in auth_service.py
    # - app.auth_database.settings: module-level import
    # - app.database.settings: module-level import
    with (
        patch("app.config.settings") as mock_cfg,
        patch("app.auth_database.settings") as mock_auth,
        patch("app.database.settings") as mock_db,
    ):
        for s in (mock_cfg, mock_auth, mock_db):
            s.auth_database_path = auth_path
            s.database_path = app_path
            s.auth_session_expiry_days = 30

        import app.auth_database as auth_db_mod
        import app.database as db_mod

        auth_db_mod._db = None
        db_mod._db = None

        await auth_db_mod.init_auth_db()
        await db_mod.init_db()

        from app.services.auth_service import AuthService

        service = AuthService()
        yield service

        await auth_db_mod.close_auth_db()
        await db_mod.close_db()


async def test_needs_setup_initially_true(auth_dbs):
    service = auth_dbs
    assert await service.needs_setup() is True


async def test_setup_admin_creates_user(auth_dbs):
    service = auth_dbs
    user = await service.setup_admin("admin", "secret123", "Admin User")
    assert user["username"] == "admin"
    assert user["display_name"] == "Admin User"
    assert user["is_admin"] is True
    assert "id" in user


async def test_needs_setup_false_after_admin(auth_dbs):
    service = auth_dbs
    await service.setup_admin("admin", "secret123", "Admin User")
    assert await service.needs_setup() is False


async def test_setup_admin_fails_if_already_done(auth_dbs):
    service = auth_dbs
    await service.setup_admin("admin", "secret123", "Admin")
    with pytest.raises(ValueError, match="already exist"):
        await service.setup_admin("admin2", "pass", "Admin2")


async def test_setup_admin_generates_invite_code(auth_dbs):
    service = auth_dbs
    await service.setup_admin("admin", "secret123", "Admin")
    code = await service.get_invite_code()
    assert len(code) > 0


async def test_login_success(auth_dbs):
    service = auth_dbs
    await service.setup_admin("admin", "pass123", "Admin")
    user, token = await service.login("admin", "pass123")
    assert user["username"] == "admin"
    assert len(token) > 0


async def test_login_wrong_password(auth_dbs):
    service = auth_dbs
    await service.setup_admin("admin", "pass123", "Admin")
    with pytest.raises(ValueError, match="Invalid"):
        await service.login("admin", "wrong")


async def test_login_wrong_username(auth_dbs):
    service = auth_dbs
    await service.setup_admin("admin", "pass123", "Admin")
    with pytest.raises(ValueError, match="Invalid"):
        await service.login("nobody", "pass123")


async def test_validate_token(auth_dbs):
    service = auth_dbs
    await service.setup_admin("admin", "pass123", "Admin")
    _, token = await service.login("admin", "pass123")
    user = await service.validate_token(token)
    assert user is not None
    assert user["username"] == "admin"


async def test_validate_token_invalid(auth_dbs):
    service = auth_dbs
    result = await service.validate_token("bogus-token")
    assert result is None


async def test_logout(auth_dbs):
    service = auth_dbs
    await service.setup_admin("admin", "pass123", "Admin")
    _, token = await service.login("admin", "pass123")
    await service.logout(token)
    assert await service.validate_token(token) is None


async def test_register_with_valid_code(auth_dbs):
    service = auth_dbs
    await service.setup_admin("admin", "pass", "Admin")
    code = await service.get_invite_code()
    user, token = await service.register("newuser", "pass", "New User", code)
    assert user["username"] == "newuser"
    assert user["is_admin"] is False
    assert len(token) > 0


async def test_register_with_invalid_code(auth_dbs):
    service = auth_dbs
    await service.setup_admin("admin", "pass", "Admin")
    with pytest.raises(ValueError, match="Invalid invite code"):
        await service.register("newuser", "pass", "New User", "wrong-code")


async def test_register_duplicate_username(auth_dbs):
    service = auth_dbs
    await service.setup_admin("admin", "pass", "Admin")
    code = await service.get_invite_code()
    await service.register("user1", "pass", "User1", code)
    with pytest.raises(ValueError, match="already taken"):
        await service.register("user1", "pass", "User1b", code)


async def test_list_users(auth_dbs):
    service = auth_dbs
    await service.setup_admin("admin", "pass", "Admin")
    code = await service.get_invite_code()
    await service.register("user1", "pass", "User1", code)
    users = await service.list_users()
    assert len(users) == 2
    usernames = {u["username"] for u in users}
    assert "admin" in usernames
    assert "user1" in usernames


async def test_delete_user(auth_dbs):
    service = auth_dbs
    await service.setup_admin("admin", "pass", "Admin")
    code = await service.get_invite_code()
    user, _ = await service.register("user1", "pass", "User1", code)
    assert await service.delete_user(user["id"]) is True
    users = await service.list_users()
    assert len(users) == 1


async def test_delete_nonexistent_user(auth_dbs):
    service = auth_dbs
    assert await service.delete_user("fake-id") is False


async def test_regenerate_invite_code(auth_dbs):
    service = auth_dbs
    await service.setup_admin("admin", "pass", "Admin")
    old_code = await service.get_invite_code()
    new_code = await service.regenerate_invite_code()
    assert new_code != old_code
    assert len(new_code) > 0
    # Old code should no longer work
    with pytest.raises(ValueError, match="Invalid invite code"):
        await service.register("user2", "pass", "U2", old_code)


async def test_password_hashing():
    """Password hashing should be one-way and verifiable."""
    from app.services.auth_service import AuthService

    h = AuthService._hash_password("test")
    assert h != "test"
    assert AuthService._verify_password("test", h) is True
    assert AuthService._verify_password("wrong", h) is False


async def test_orphaned_session_migration(auth_dbs):
    """setup_admin() should assign orphaned sessions to the admin."""
    service = auth_dbs

    # Create an orphaned session (no user_id)
    from app.database import get_db

    db = await get_db()
    await db.execute(
        "INSERT INTO sessions (id) VALUES (?)",
        ("orphan-session-1",),
    )
    await db.commit()

    user = await service.setup_admin("admin", "pass", "Admin")

    cursor = await db.execute(
        "SELECT user_id FROM sessions WHERE id = ?",
        ("orphan-session-1",),
    )
    row = await cursor.fetchone()
    assert row is not None
    assert row["user_id"] == user["id"]
