import uuid
from datetime import datetime, timedelta

import structlog

from app.auth_database import get_auth_db

logger = structlog.get_logger()


class AuthService:
    # --- Password helpers ---

    @staticmethod
    def _hash_password(password: str) -> str:
        import bcrypt

        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    @staticmethod
    def _verify_password(password: str, password_hash: str) -> bool:
        import bcrypt

        return bcrypt.checkpw(password.encode(), password_hash.encode())

    @staticmethod
    def _generate_token() -> str:
        return uuid.uuid4().hex

    @staticmethod
    def _generate_invite_code() -> str:
        import secrets

        return secrets.token_urlsafe(6)[:8]

    # --- Auth session helper ---

    async def _create_auth_session(self, user_id: str) -> str:
        """Create an auth_session row. Returns the token string."""
        from app.config import settings

        token = self._generate_token()
        session_id = uuid.uuid4().hex
        expires = datetime.utcnow() + timedelta(
            days=settings.auth_session_expiry_days
        )
        db = await get_auth_db()
        await db.execute(
            "INSERT INTO auth_sessions (id, user_id, token, expires_at) VALUES (?, ?, ?, ?)",
            (session_id, user_id, token, expires.isoformat()),
        )
        await db.commit()
        return token

    @staticmethod
    def _user_dict(row: dict) -> dict:
        """Convert a user row to a safe dict (no password_hash)."""
        return {
            "id": row["id"],
            "username": row["username"],
            "display_name": row["display_name"],
            "is_admin": bool(row["is_admin"]),
        }

    # --- Public methods ---

    async def needs_setup(self) -> bool:
        """True if no users exist in auth.db."""
        db = await get_auth_db()
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        row = await cursor.fetchone()
        if row is None:
            return True
        return row[0] == 0

    async def setup_admin(
        self, username: str, password: str, display_name: str
    ) -> dict:
        """Create the first admin user. Only works when 0 users exist.
        Also generates and stores the initial invite code in settings table.
        Returns user dict."""
        if not await self.needs_setup():
            raise ValueError("Users already exist. Setup is complete.")

        user_id = uuid.uuid4().hex
        password_hash = self._hash_password(password)

        db = await get_auth_db()
        await db.execute(
            "INSERT INTO users (id, username, password_hash, display_name, is_admin) "
            "VALUES (?, ?, ?, ?, 1)",
            (user_id, username, password_hash, display_name),
        )

        # Generate initial invite code
        invite_code = self._generate_invite_code()
        await db.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES ('invite_code', ?)",
            (invite_code,),
        )
        await db.commit()

        # Assign orphaned sessions (from before auth existed) to the admin
        from app.database import get_db

        app_db = await get_db()
        await app_db.execute(
            "UPDATE sessions SET user_id = ? WHERE user_id IS NULL",
            (user_id,),
        )
        await app_db.commit()

        logger.info("Admin user created", username=username, user_id=user_id[:8])
        return self._user_dict(
            {
                "id": user_id,
                "username": username,
                "display_name": display_name,
                "is_admin": 1,
            }
        )

    async def register(
        self,
        username: str,
        password: str,
        display_name: str,
        invite_code: str,
    ) -> tuple[dict, str]:
        """Register a new (non-admin) user. Validates invite code.
        Returns (user_dict, session_token)."""
        # Validate invite code
        db = await get_auth_db()
        cursor = await db.execute(
            "SELECT value FROM settings WHERE key = 'invite_code'"
        )
        row = await cursor.fetchone()
        if not row or row["value"] != invite_code:
            raise ValueError("Invalid invite code")

        # Check username uniqueness
        cursor = await db.execute(
            "SELECT id FROM users WHERE username = ?", (username,)
        )
        if await cursor.fetchone():
            raise ValueError("Username already taken")

        user_id = uuid.uuid4().hex
        password_hash = self._hash_password(password)

        await db.execute(
            "INSERT INTO users (id, username, password_hash, display_name, is_admin) "
            "VALUES (?, ?, ?, ?, 0)",
            (user_id, username, password_hash, display_name),
        )
        await db.commit()

        token = await self._create_auth_session(user_id)
        logger.info("User registered", username=username, user_id=user_id[:8])
        return (
            self._user_dict(
                {
                    "id": user_id,
                    "username": username,
                    "display_name": display_name,
                    "is_admin": 0,
                }
            ),
            token,
        )

    async def login(self, username: str, password: str) -> tuple[dict, str]:
        """Validate credentials. Create auth_session. Return (user_dict, session_token)."""
        db = await get_auth_db()
        cursor = await db.execute(
            "SELECT id, username, password_hash, display_name, is_admin "
            "FROM users WHERE username = ?",
            (username,),
        )
        row = await cursor.fetchone()
        if not row:
            raise ValueError("Invalid username or password")

        if not self._verify_password(password, row["password_hash"]):
            raise ValueError("Invalid username or password")

        token = await self._create_auth_session(row["id"])
        logger.info("User logged in", username=username)
        return self._user_dict(dict(row)), token

    async def logout(self, token: str) -> None:
        """Delete the auth_session for this token."""
        db = await get_auth_db()
        await db.execute("DELETE FROM auth_sessions WHERE token = ?", (token,))
        await db.commit()

    async def validate_token(self, token: str) -> dict | None:
        """Look up token in auth_sessions. Check not expired. Return user dict or None."""
        db = await get_auth_db()
        cursor = await db.execute(
            "SELECT u.id, u.username, u.display_name, u.is_admin, a.expires_at, a.user_id "
            "FROM auth_sessions a "
            "JOIN users u ON u.id = a.user_id "
            "WHERE a.token = ?",
            (token,),
        )
        row = await cursor.fetchone()
        if not row:
            return None

        # Check expiry
        expires_at = datetime.fromisoformat(row["expires_at"])
        if expires_at < datetime.utcnow():
            # Expired — clean up this user's expired sessions
            await db.execute(
                "DELETE FROM auth_sessions WHERE user_id = ? AND expires_at < ?",
                (row["user_id"], datetime.utcnow().isoformat()),
            )
            await db.commit()
            return None

        return self._user_dict(dict(row))

    async def list_users(self) -> list[dict]:
        """List all users."""
        db = await get_auth_db()
        cursor = await db.execute(
            "SELECT id, username, display_name, is_admin, created_at FROM users "
            "ORDER BY created_at ASC"
        )
        rows = await cursor.fetchall()
        return [
            {
                "id": r["id"],
                "username": r["username"],
                "display_name": r["display_name"],
                "is_admin": bool(r["is_admin"]),
                "created_at": r["created_at"],
            }
            for r in rows
        ]

    async def delete_user(self, user_id: str) -> bool:
        """Delete user and their auth_sessions (CASCADE). Returns False if not found."""
        db = await get_auth_db()
        cursor = await db.execute("DELETE FROM users WHERE id = ?", (user_id,))
        await db.commit()
        return cursor.rowcount > 0  # type: ignore[return-value]

    async def get_invite_code(self) -> str:
        """Get current invite code from settings table."""
        db = await get_auth_db()
        cursor = await db.execute(
            "SELECT value FROM settings WHERE key = 'invite_code'"
        )
        row = await cursor.fetchone()
        if not row:
            return ""
        return row["value"]

    async def regenerate_invite_code(self) -> str:
        """Generate new invite code, store in settings, return it."""
        new_code = self._generate_invite_code()
        db = await get_auth_db()
        await db.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES ('invite_code', ?)",
            (new_code,),
        )
        await db.commit()
        logger.info("Invite code regenerated")
        return new_code


auth_service = AuthService()
