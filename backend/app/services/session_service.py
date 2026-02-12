import uuid
from app.database import get_db
import structlog

logger = structlog.get_logger()


class SessionService:
    """Manages sessions, documents, and versions in SQLite."""

    async def create_session(self) -> str:
        db = await get_db()
        session_id = str(uuid.uuid4())
        await db.execute(
            "INSERT INTO sessions (id) VALUES (?)",
            (session_id,),
        )
        await db.commit()
        logger.info("Session created", session_id=session_id[:8])
        return session_id

    async def get_or_create_session(self, session_id: str) -> str:
        db = await get_db()
        cursor = await db.execute(
            "SELECT id FROM sessions WHERE id = ?", (session_id,)
        )
        row = await cursor.fetchone()
        if row:
            await db.execute(
                "UPDATE sessions SET last_active = CURRENT_TIMESTAMP WHERE id = ?",
                (session_id,),
            )
            await db.commit()
            return session_id
        return await self.create_session()

    async def create_document(
        self, session_id: str, title: str = "Untitled"
    ) -> str:
        db = await get_db()
        doc_id = str(uuid.uuid4())
        # Deactivate other documents in this session
        await db.execute(
            "UPDATE documents SET is_active = 0 WHERE session_id = ?",
            (session_id,),
        )
        await db.execute(
            "INSERT INTO documents (id, session_id, title, is_active) VALUES (?, ?, ?, 1)",
            (doc_id, session_id, title),
        )
        await db.commit()
        logger.info(
            "Document created",
            doc_id=doc_id[:8],
            session_id=session_id[:8],
        )
        return doc_id

    async def get_active_document(self, session_id: str) -> dict | None:
        db = await get_db()
        cursor = await db.execute(
            "SELECT * FROM documents WHERE session_id = ? AND is_active = 1",
            (session_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_session_documents(self, session_id: str) -> list[dict]:
        db = await get_db()
        cursor = await db.execute(
            "SELECT * FROM documents WHERE session_id = ? ORDER BY created_at",
            (session_id,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def switch_document(
        self, session_id: str, document_id: str
    ) -> bool:
        db = await get_db()
        await db.execute(
            "UPDATE documents SET is_active = 0 WHERE session_id = ?",
            (session_id,),
        )
        cursor = await db.execute(
            "UPDATE documents SET is_active = 1 WHERE id = ? AND session_id = ?",
            (document_id, session_id),
        )
        await db.commit()
        return cursor.rowcount > 0

    async def save_version(
        self,
        document_id: str,
        html_content: str,
        user_prompt: str = "",
        edit_summary: str = "",
        model_used: str = "",
        tokens_used: int = 0,
    ) -> int:
        db = await get_db()
        # Get next version number
        cursor = await db.execute(
            "SELECT COALESCE(MAX(version), 0) + 1 as next_ver "
            "FROM document_versions WHERE document_id = ?",
            (document_id,),
        )
        row = await cursor.fetchone()
        assert row is not None  # COALESCE guarantees a result
        version = row["next_ver"]
        await db.execute(
            """INSERT INTO document_versions
               (document_id, version, html_content, user_prompt, edit_summary, model_used, tokens_used)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                document_id,
                version,
                html_content,
                user_prompt,
                edit_summary,
                model_used,
                tokens_used,
            ),
        )
        await db.commit()
        logger.info(
            "Version saved", doc_id=document_id[:8], version=version
        )
        return version

    async def get_latest_html(self, document_id: str) -> str | None:
        db = await get_db()
        cursor = await db.execute(
            "SELECT html_content FROM document_versions "
            "WHERE document_id = ? ORDER BY version DESC LIMIT 1",
            (document_id,),
        )
        row = await cursor.fetchone()
        return row["html_content"] if row else None

    async def get_version(
        self, document_id: str, version: int
    ) -> dict | None:
        db = await get_db()
        cursor = await db.execute(
            "SELECT * FROM document_versions WHERE document_id = ? AND version = ?",
            (document_id, version),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_version_history(self, document_id: str) -> list[dict]:
        db = await get_db()
        cursor = await db.execute(
            """SELECT version, user_prompt, edit_summary, model_used, tokens_used, created_at
               FROM document_versions WHERE document_id = ? ORDER BY version DESC""",
            (document_id,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def add_chat_message(
        self,
        session_id: str,
        role: str,
        content: str,
        document_id: str | None = None,
        message_type: str = "text",
    ) -> None:
        db = await get_db()
        await db.execute(
            """INSERT INTO chat_messages (session_id, document_id, role, content, message_type)
               VALUES (?, ?, ?, ?, ?)""",
            (session_id, document_id, role, content, message_type),
        )
        await db.commit()

    async def get_chat_history(
        self, session_id: str, limit: int = 50
    ) -> list[dict]:
        db = await get_db()
        cursor = await db.execute(
            """SELECT * FROM chat_messages WHERE session_id = ?
               ORDER BY created_at DESC, id DESC LIMIT ?""",
            (session_id, limit),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in reversed(list(rows))]

    async def cleanup_expired_sessions(self, timeout_hours: int = 24) -> int:
        db = await get_db()
        cursor = await db.execute(
            "DELETE FROM sessions WHERE last_active < datetime('now', ? || ' hours')",
            (f"-{timeout_hours}",),
        )
        await db.commit()
        deleted = cursor.rowcount
        if deleted > 0:
            logger.info("Cleaned up expired sessions", count=deleted)
        return deleted


session_service = SessionService()
