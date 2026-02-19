import aiosqlite
from pathlib import Path
from app.config import settings
import structlog

logger = structlog.get_logger()

_db: aiosqlite.Connection | None = None


async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _db


async def init_db() -> None:
    global _db
    db_path = Path(settings.database_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    _db = await aiosqlite.connect(str(db_path))
    _db.row_factory = aiosqlite.Row

    # Enable WAL mode for concurrent read/write
    await _db.execute("PRAGMA journal_mode=WAL")
    await _db.execute("PRAGMA foreign_keys=ON")

    # Create tables
    await _db.executescript(SCHEMA)

    # Migrations (safe to re-run — ADD COLUMN raises "duplicate column" if exists)
    for migration in _MIGRATIONS:
        try:
            await _db.execute(migration)
        except Exception as e:
            if "duplicate column" not in str(e).lower():
                raise

    await _db.commit()

    # Backfill doc_type for existing infographic documents
    await _backfill_doc_types()

    logger.info("Database initialized", path=str(db_path))


async def close_db() -> None:
    global _db
    if _db:
        await _db.close()
        _db = None
        logger.info("Database closed")


SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    title TEXT DEFAULT 'Untitled',
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS document_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    html_content TEXT NOT NULL,
    user_prompt TEXT,
    edit_summary TEXT,
    model_used TEXT,
    tokens_used INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(document_id, version)
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    document_id TEXT REFERENCES documents(id),
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    message_type TEXT DEFAULT 'text',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cost_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    model TEXT NOT NULL,
    request_count INTEGER DEFAULT 0,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    images_generated INTEGER DEFAULT 0,
    estimated_cost_usd REAL DEFAULT 0,
    UNIQUE(date, model)
);

CREATE INDEX IF NOT EXISTS idx_documents_session ON documents(session_id);
CREATE INDEX IF NOT EXISTS idx_versions_document ON document_versions(document_id);
CREATE INDEX IF NOT EXISTS idx_messages_session ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_cost_date ON cost_tracking(date);
"""

# Schema migrations — each runs inside a try/except so re-runs are safe.
# SQLite raises an error if ADD COLUMN targets an existing column.
# Index creation after ALTER TABLE must also be in migrations (not SCHEMA)
# because SCHEMA runs via executescript before migrations, and existing DBs
# won't have the new column yet when the index tries to reference it.
_MIGRATIONS = [
    "ALTER TABLE document_versions ADD COLUMN visual_prompt TEXT",
    "ALTER TABLE chat_messages ADD COLUMN template_name TEXT",
    "ALTER TABLE chat_messages ADD COLUMN user_content TEXT",
    "ALTER TABLE sessions ADD COLUMN user_id TEXT",
    "CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)",
    "ALTER TABLE documents ADD COLUMN doc_type TEXT DEFAULT 'document'",
]


async def _backfill_doc_types() -> None:
    """Detect existing infographic documents and set doc_type accordingly.

    Idempotent: only updates documents that still have the default
    'document' type and whose latest HTML matches infographic structure.
    """
    from app.utils.html_validator import is_infographic_html

    if _db is None:
        return

    cursor = await _db.execute(
        """SELECT d.id, dv.html_content
           FROM documents d
           JOIN document_versions dv ON dv.document_id = d.id
           WHERE d.doc_type = 'document'
             AND dv.version = (
                 SELECT MAX(version) FROM document_versions
                 WHERE document_id = d.id
             )"""
    )
    rows = await cursor.fetchall()

    updated = 0
    for row in rows:
        if is_infographic_html(row["html_content"]):
            await _db.execute(
                "UPDATE documents SET doc_type = 'infographic' WHERE id = ?",
                (row["id"],),
            )
            updated += 1

    if updated > 0:
        await _db.commit()
        logger.info("Backfilled doc_type for infographic documents", count=updated)
