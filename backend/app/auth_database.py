import aiosqlite
from pathlib import Path
from app.config import settings
import structlog

logger = structlog.get_logger()

_db: aiosqlite.Connection | None = None


async def get_auth_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        raise RuntimeError("Auth database not initialized. Call init_auth_db() first.")
    return _db


async def init_auth_db() -> None:
    global _db
    db_path = Path(settings.auth_database_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    _db = await aiosqlite.connect(str(db_path))
    _db.row_factory = aiosqlite.Row

    await _db.execute("PRAGMA journal_mode=WAL")
    await _db.execute("PRAGMA foreign_keys=ON")

    await _db.executescript(AUTH_SCHEMA)
    await _db.commit()
    logger.info("Auth database initialized", path=str(db_path))


async def close_auth_db() -> None:
    global _db
    if _db:
        await _db.close()
        _db = None
        logger.info("Auth database closed")


AUTH_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    display_name TEXT NOT NULL,
    is_admin BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS auth_sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_token ON auth_sessions(token);
CREATE INDEX IF NOT EXISTS idx_auth_sessions_user ON auth_sessions(user_id);
"""
