import pytest
from pathlib import Path
from unittest.mock import patch


@pytest.fixture
async def temp_db(tmp_path):
    """Create a temporary database for testing."""
    db_path = str(tmp_path / "test.db")

    with (
        patch("app.config.settings") as mock_settings,
        patch("app.database.settings") as mock_db_settings,
    ):
        mock_settings.database_path = db_path
        mock_db_settings.database_path = db_path

        import app.database as db_module

        # Reset module state
        db_module._db = None

        await db_module.init_db()
        yield db_module
        await db_module.close_db()


@pytest.mark.asyncio
async def test_init_db_creates_file(tmp_path):
    """Database file should be created on init."""
    db_path = str(tmp_path / "data" / "test.db")

    with (
        patch("app.config.settings") as mock_settings,
        patch("app.database.settings") as mock_db_settings,
    ):
        mock_settings.database_path = db_path
        mock_db_settings.database_path = db_path

        import app.database as db_module

        db_module._db = None
        await db_module.init_db()

        assert Path(db_path).exists()
        await db_module.close_db()


@pytest.mark.asyncio
async def test_wal_mode_enabled(temp_db):
    """WAL journal mode should be enabled."""
    db = await temp_db.get_db()
    cursor = await db.execute("PRAGMA journal_mode")
    row = await cursor.fetchone()
    assert row[0] == "wal"


@pytest.mark.asyncio
async def test_foreign_keys_enabled(temp_db):
    """Foreign keys should be enabled."""
    db = await temp_db.get_db()
    cursor = await db.execute("PRAGMA foreign_keys")
    row = await cursor.fetchone()
    assert row[0] == 1


@pytest.mark.asyncio
async def test_tables_created(temp_db):
    """All expected tables should exist."""
    db = await temp_db.get_db()
    cursor = await db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    rows = await cursor.fetchall()
    table_names = {row[0] for row in rows}

    expected = {
        "sessions",
        "documents",
        "document_versions",
        "chat_messages",
        "cost_tracking",
    }
    assert expected.issubset(table_names)


@pytest.mark.asyncio
async def test_indexes_created(temp_db):
    """All expected indexes should exist."""
    db = await temp_db.get_db()
    cursor = await db.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
    )
    rows = await cursor.fetchall()
    index_names = {row[0] for row in rows}

    expected = {
        "idx_documents_session",
        "idx_versions_document",
        "idx_messages_session",
        "idx_cost_date",
    }
    assert expected.issubset(index_names)


@pytest.mark.asyncio
async def test_get_db_before_init_raises():
    """get_db should raise if called before init_db."""
    import app.database as db_module

    db_module._db = None
    with pytest.raises(RuntimeError, match="Database not initialized"):
        await db_module.get_db()


@pytest.mark.asyncio
async def test_close_db_idempotent(temp_db):
    """close_db should be safe to call multiple times."""
    await temp_db.close_db()
    await temp_db.close_db()  # Should not raise
