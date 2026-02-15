import json as json_mod
import uuid

import structlog

from app.database import get_db

logger = structlog.get_logger()


class SessionService:
    """Manages sessions, documents, and versions in SQLite."""

    async def create_session(self, user_id: str | None = None) -> str:
        db = await get_db()
        session_id = str(uuid.uuid4())
        await db.execute(
            "INSERT INTO sessions (id, user_id) VALUES (?, ?)",
            (session_id, user_id),
        )
        await db.commit()
        logger.info("Session created", session_id=session_id[:8])
        return session_id

    async def get_or_create_session(
        self, session_id: str, user_id: str | None = None
    ) -> str:
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
        return await self.create_session(user_id=user_id)

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

    async def verify_document_ownership(
        self, document_id: str, session_id: str
    ) -> bool:
        """Check if a document belongs to a session."""
        db = await get_db()
        cursor = await db.execute(
            "SELECT 1 FROM documents WHERE id = ? AND session_id = ?",
            (document_id, session_id),
        )
        row = await cursor.fetchone()
        return row is not None

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
        visual_prompt: str = "",
    ) -> int:
        db = await get_db()
        # Get next version number
        cursor = await db.execute(
            "SELECT COALESCE(MAX(version), 0) + 1 as next_ver "
            "FROM document_versions WHERE document_id = ?",
            (document_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            raise RuntimeError(
                f"Failed to determine next version for document {document_id}"
            )
        version = row["next_ver"]
        await db.execute(
            """INSERT INTO document_versions
               (document_id, version, html_content, user_prompt, edit_summary,
                model_used, tokens_used, visual_prompt)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                document_id,
                version,
                html_content,
                user_prompt,
                edit_summary,
                model_used,
                tokens_used,
                visual_prompt,
            ),
        )
        await db.commit()
        logger.info(
            "Version saved", doc_id=document_id[:8], version=version
        )
        return version

    async def save_manual_edit(
        self, document_id: str, html_content: str
    ) -> int:
        """Save a manual HTML edit as a new version."""
        return await self.save_version(
            document_id=document_id,
            html_content=html_content,
            user_prompt="",
            edit_summary="Manual edit",
            model_used="manual",
            tokens_used=0,
        )

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
            """SELECT version, user_prompt, edit_summary, model_used,
                      tokens_used, created_at, visual_prompt
               FROM document_versions WHERE document_id = ? ORDER BY version DESC""",
            (document_id,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def restore_version(
        self, document_id: str, version: int
    ) -> int:
        """Restore an old version by saving its HTML as a new version."""
        old = await self.get_version(document_id, version)
        if not old:
            raise ValueError(f"Version {version} not found")
        return await self.save_version(
            document_id=document_id,
            html_content=old["html_content"],
            user_prompt="",
            edit_summary=f"Restored from version {version}",
            model_used="restore",
            tokens_used=0,
        )

    async def rename_document(
        self, document_id: str, new_title: str
    ) -> bool:
        """Rename a document. Returns True if found and renamed."""
        db = await get_db()
        cursor = await db.execute(
            "UPDATE documents SET title = ? WHERE id = ?",
            (new_title, document_id),
        )
        await db.commit()
        return cursor.rowcount > 0

    async def delete_document(
        self, session_id: str, document_id: str
    ) -> bool:
        """Delete a document. Activates another if this was active.
        Returns False if this is the last document (cannot delete)."""
        db = await get_db()

        # Count documents in session
        cursor = await db.execute(
            "SELECT COUNT(*) as cnt FROM documents WHERE session_id = ?",
            (session_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            raise RuntimeError(
                f"Failed to count documents for session {session_id}"
            )
        if row["cnt"] <= 1:
            return False

        # Check if document exists and is active
        cursor = await db.execute(
            "SELECT is_active FROM documents WHERE id = ? AND session_id = ?",
            (document_id, session_id),
        )
        doc_row = await cursor.fetchone()
        if not doc_row:
            return False

        was_active = bool(doc_row["is_active"])

        # Nullify document_id in chat_messages (no ON DELETE for this FK)
        await db.execute(
            "UPDATE chat_messages SET document_id = NULL WHERE document_id = ?",
            (document_id,),
        )

        # Delete document (CASCADE deletes versions)
        await db.execute(
            "DELETE FROM documents WHERE id = ? AND session_id = ?",
            (document_id, session_id),
        )

        # If deleted document was active, activate the most recent remaining
        if was_active:
            await db.execute(
                """UPDATE documents SET is_active = 1
                   WHERE id = (
                     SELECT id FROM documents
                     WHERE session_id = ? ORDER BY created_at DESC LIMIT 1
                   )""",
                (session_id,),
            )

        await db.commit()
        logger.info("Document deleted", doc_id=document_id[:8])
        return True

    async def get_user_sessions(
        self, user_id: str, limit: int = 20, offset: int = 0
    ) -> list[dict]:
        """Get all sessions for a user with summary info."""
        db = await get_db()
        cursor = await db.execute(
            """SELECT
                 s.id,
                 s.created_at,
                 s.last_active,
                 s.metadata,
                 COUNT(d.id) as doc_count,
                 (SELECT content FROM chat_messages
                  WHERE session_id = s.id AND role = 'user'
                  ORDER BY id ASC LIMIT 1) as first_message
               FROM sessions s
               LEFT JOIN documents d ON d.session_id = s.id
               WHERE s.user_id = ?
               GROUP BY s.id
               ORDER BY s.last_active DESC, s.id DESC
               LIMIT ? OFFSET ?""",
            (user_id, limit, offset),
        )
        rows = await cursor.fetchall()

        result = []
        for row in rows:
            r = dict(row)
            metadata = json_mod.loads(r.get("metadata") or "{}")
            title = metadata.get("title", "")
            if not title and r.get("first_message"):
                title = r["first_message"][:80]
            if not title:
                title = "Untitled Session"

            result.append(
                {
                    "id": r["id"],
                    "title": title,
                    "doc_count": r["doc_count"],
                    "first_message_preview": (r.get("first_message") or "")[:80],
                    "last_active": r["last_active"],
                    "created_at": r["created_at"],
                }
            )
        return result

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session. CASCADE handles documents/versions/messages."""
        db = await get_db()
        cursor = await db.execute(
            "DELETE FROM sessions WHERE id = ?", (session_id,)
        )
        await db.commit()
        return cursor.rowcount > 0

    async def update_session_title(
        self, session_id: str, title: str
    ) -> bool:
        """Update the title stored in session metadata JSON."""
        db = await get_db()
        cursor = await db.execute(
            "SELECT metadata FROM sessions WHERE id = ?", (session_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return False
        metadata = json_mod.loads(row["metadata"] or "{}")
        metadata["title"] = title
        await db.execute(
            "UPDATE sessions SET metadata = ? WHERE id = ?",
            (json_mod.dumps(metadata), session_id),
        )
        await db.commit()
        return True

    async def add_chat_message(
        self,
        session_id: str,
        role: str,
        content: str,
        document_id: str | None = None,
        message_type: str = "text",
        template_name: str | None = None,
        user_content: str | None = None,
    ) -> None:
        db = await get_db()
        await db.execute(
            """INSERT INTO chat_messages
               (session_id, document_id, role, content, message_type, template_name, user_content)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (session_id, document_id, role, content, message_type, template_name, user_content),
        )

        # Update last_active timestamp
        await db.execute(
            "UPDATE sessions SET last_active = CURRENT_TIMESTAMP WHERE id = ?",
            (session_id,),
        )

        # Auto-title: set session title from first user message
        if role == "user":
            cursor = await db.execute(
                "SELECT metadata FROM sessions WHERE id = ?", (session_id,)
            )
            meta_row = await cursor.fetchone()
            if meta_row:
                metadata = json_mod.loads(meta_row["metadata"] or "{}")
                if not metadata.get("title"):
                    # Prefer template_name, then user_content, then full content
                    if template_name:
                        auto_title = template_name
                    elif (
                        user_content
                        and user_content != "(template only)"
                    ):
                        auto_title = user_content[:80]
                    else:
                        auto_title = content[:80]
                    metadata["title"] = auto_title
                    await db.execute(
                        "UPDATE sessions SET metadata = ? WHERE id = ?",
                        (json_mod.dumps(metadata), session_id),
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



session_service = SessionService()
