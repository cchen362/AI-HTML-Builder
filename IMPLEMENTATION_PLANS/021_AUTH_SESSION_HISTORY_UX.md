# Implementation Plan 021: Auth, Session History & UX Polish

## Status: PHASE 1 COMPLETE — Phases 2-4 PENDING

---

## STOP — READ THIS FIRST

**DO NOT START** this implementation until:
- Plans 001–020a are FULLY complete (they are)
- You have read this ENTIRE document
- You understand the 4 phases and their dependencies

**This plan emerged from a UX workshop** (see `020_REVIEW_FINDINGS.md`). 19 UX/architecture items were reviewed; 10 were approved for implementation and organized into 4 sequential phases.

**PHASE DEPENDENCIES:**
- Phase 1 (Auth) MUST be done first — everything else depends on user identity
- Phase 2 (Sessions) depends on Phase 1
- Phase 3 (Version Diff) is independent of Phase 2
- Phase 4 (UX Polish) is independent of Phase 2 and Phase 3

**EACH PHASE = ONE SESSION/COMMIT.** Do not combine phases.

**DESTRUCTIVE ACTIONS PROHIBITED:**
- Do NOT change AI model routing, editing engine, or creation pipeline
- Do NOT change database schema beyond what this plan specifies
- Do NOT modify export pipeline logic (only UI feedback changes)
- Do NOT remove the 3-dot menu — add items to it

---

## Workshop Decisions Summary

| Item | Decision | What |
|------|----------|------|
| U1 | PROCEED | Auth + session persistence + session browser |
| U2 | DEFER | Regenerate/edit on messages |
| U3 | PROCEED | Before/After version toggle |
| U4 | DEFER | Undo / Ctrl+Z |
| U5 | DROP | Theme (personal preference) |
| U6 | DROP | Preview iframe (already interactive) |
| U7 | PROCEED | Better error messages |
| U8 | PROCEED | Export progress feedback |
| U9 | DROP | Mobile support |
| U10 | DROP | Keyboard shortcuts reference |
| U11 | PROCEED | ARCHITECT → BUILDER rename |
| U12 | DROP | Cancel button size |
| U13 | DROP | Template preview (useful as-is) |
| U14 | PROCEED | Smarter export filenames |
| U15 | PROCEED | Infographic PNG-only explanation |
| U16 | DEFER | Onboarding walkthrough |
| U17 | PROCEED (with U1) | No "+" button — use New Session + session browser |
| U18 | DROP | Search in chat history |
| U19 | PROCEED | Dead CSS cleanup |

### Key UX Decisions (Non-Negotiable)
1. **No "+" button in tab bar.** Sessions = projects. New docs within a session happen via chat. New projects = "New Session" in 3-dot menu.
2. **Session browser on login landing page** + "My Sessions" in 3-dot menu for mid-session access.
3. **"New Session"** stays in 3-dot menu. Same as today but old session is now preserved (not orphaned).
4. **Selecting a past session = full context switch.** Clear current tabs, load selected session's docs/chat/preview entirely.
5. **Auth via HTTP-only cookie**, NOT JWT. Separate `auth.db`, NOT same as `app.db`.
6. **Admin bootstrap + invite code** for self-registration. No CLI user management — admin panel in UI.

---

## Phase 1: Authentication Layer

### Overview
Add user authentication with a separate SQLite database. Admin creates account on first launch, generates invite code, shares with team. Users self-register with invite code. All API endpoints protected by HTTP-only cookie auth.

### 1.1 — New Dependency

**File: `backend/requirements.txt`**

Add after the `# Utilities` section:
```
# Authentication
bcrypt==4.3.0
```

**Why bcrypt and not passlib?** Direct bcrypt is lighter (one dependency vs three) and sufficient for our needs. `passlib` adds unnecessary wrapping.

**Dockerfile note:** `gcc` is already installed (Dockerfile line 21), so bcrypt's C extension compiles fine on `python:3.11-slim`.

### 1.2 — New Config Settings

**File: `backend/app/config.py`**

Add two settings to the `Settings` class:
```python
# Authentication
auth_database_path: str = "./data/auth.db"
auth_session_expiry_days: int = 30
```

### 1.3 — Auth Database Module

**New file: `backend/app/auth_database.py`**

Follow the EXACT same pattern as `backend/app/database.py`:
- Module-level `_db: aiosqlite.Connection | None = None`
- `async def get_auth_db() -> aiosqlite.Connection`
- `async def init_auth_db() -> None` — creates file, enables WAL + foreign keys, runs schema
- `async def close_auth_db() -> None`

**Schema (AUTH_SCHEMA constant):**
```sql
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
```

**No `_MIGRATIONS` list initially.** Clean schema, no legacy data.

### 1.4 — Auth Service

**New file: `backend/app/services/auth_service.py`**

Class `AuthService` with singleton `auth_service = AuthService()` at module level.

**Methods (implement ALL):**

```python
async def needs_setup(self) -> bool:
    """True if no users exist in auth.db."""
    # SELECT COUNT(*) FROM users → count == 0

async def setup_admin(self, username: str, password: str, display_name: str) -> dict:
    """Create the first admin user. Only works when 0 users exist.
    Also generates and stores the initial invite code in settings table.
    Returns user dict: {id, username, display_name, is_admin}.
    Raises ValueError if users already exist."""

async def register(self, username: str, password: str, display_name: str, invite_code: str) -> tuple[dict, str]:
    """Register a new (non-admin) user. Validates invite code.
    Returns (user_dict, session_token).
    Raises ValueError if invite code is invalid or username taken."""

async def login(self, username: str, password: str) -> tuple[dict, str]:
    """Validate credentials. Create auth_session. Return (user_dict, session_token).
    Raises ValueError if credentials invalid."""

async def logout(self, token: str) -> None:
    """Delete the auth_session for this token."""

async def validate_token(self, token: str) -> dict | None:
    """Look up token in auth_sessions. Check not expired. Return user dict or None.
    Also cleans up expired sessions for this user (opportunistic cleanup)."""

async def list_users(self) -> list[dict]:
    """List all users. Admin function."""

async def delete_user(self, user_id: str) -> bool:
    """Delete user and their auth_sessions. Returns False if not found."""

async def get_invite_code(self) -> str:
    """Get current invite code from settings table. Key: 'invite_code'."""

async def regenerate_invite_code(self) -> str:
    """Generate new 8-char alphanumeric code via secrets.token_urlsafe(6),
    store in settings, return it."""
```

**Static helpers:**
```python
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
    import uuid
    return uuid.uuid4().hex

@staticmethod
def _generate_invite_code() -> str:
    import secrets
    return secrets.token_urlsafe(6)[:8]  # 8-char alphanumeric
```

**Auth session creation helper (used by login + register):**
```python
async def _create_auth_session(self, user_id: str) -> str:
    """Create an auth_session row. Returns the token string."""
    from datetime import datetime, timedelta
    from app.config import settings
    token = self._generate_token()
    session_id = uuid.uuid4().hex
    expires = datetime.utcnow() + timedelta(days=settings.auth_session_expiry_days)
    db = await get_auth_db()
    await db.execute(
        "INSERT INTO auth_sessions (id, user_id, token, expires_at) VALUES (?, ?, ?, ?)",
        (session_id, user_id, token, expires.isoformat()),
    )
    await db.commit()
    return token
```

### 1.5 — Auth Middleware

**New file: `backend/app/auth_middleware.py`**

```python
from fastapi import Request, HTTPException, Depends


async def get_current_user(request: Request) -> dict:
    """FastAPI dependency. Reads 'auth_token' cookie → validates → returns user dict.
    Raises HTTPException(401) if missing, invalid, or expired."""
    from app.services.auth_service import auth_service

    token = request.cookies.get("auth_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = await auth_service.validate_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Session expired or invalid")

    return user


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """FastAPI dependency. Requires user to be admin. Raises HTTPException(403)."""
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
```

### 1.6 — Auth API Endpoints

**New file: `backend/app/api/auth.py`**

**Pydantic request models:**
```python
class LoginRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6, max_length=200)

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6, max_length=200)
    display_name: str = Field(..., min_length=1, max_length=100)
    invite_code: str = Field(..., min_length=1)

class SetupRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6, max_length=200)
    display_name: str = Field(..., min_length=1, max_length=100)
```

**Cookie helper:**
```python
def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="auth_token",
        value=token,
        httponly=True,
        secure=True,       # HTTPS via Nginx Proxy Manager
        samesite="lax",
        max_age=30 * 24 * 3600,  # 30 days
        path="/",
    )

def _clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(key="auth_token", path="/")
```

**IMPORTANT for local dev:** When running on `localhost` (HTTP, not HTTPS), `secure=True` will prevent the cookie from being set. Add a conditional:
```python
import os
_IS_DEV = os.getenv("DEV_MODE", "").lower() in ("1", "true", "yes")

def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="auth_token",
        value=token,
        httponly=True,
        secure=not _IS_DEV,
        samesite="lax",
        max_age=30 * 24 * 3600,
        path="/",
    )
```

**Endpoints (all use lazy imports for testability):**

| Endpoint | Method | Auth | Body | Returns |
|----------|--------|------|------|---------|
| `/api/auth/needs-setup` | GET | None | — | `{needs_setup: bool}` |
| `/api/auth/setup` | POST | None | SetupRequest | `{user: {...}}` + cookie. 409 if users exist. |
| `/api/auth/login` | POST | None | LoginRequest | `{user: {...}}` + cookie. 401 on bad creds. |
| `/api/auth/register` | POST | None | RegisterRequest | `{user: {...}}` + cookie. 400 bad invite, 409 dup username. |
| `/api/auth/me` | GET | Cookie | — | `{user: {...}}` |
| `/api/auth/logout` | POST | Cookie | — | `{success: true}` + clear cookie |
| `/api/admin/users` | GET | Admin | — | `{users: [...]}` |
| `/api/admin/users/{user_id}` | DELETE | Admin | — | `{success: true}`. 404 not found. 400 can't delete self. |
| `/api/admin/invite-code` | GET | Admin | — | `{invite_code: "abc123xy"}` |
| `/api/admin/invite-code` | POST | Admin | — | `{invite_code: "new12345"}` (regenerate) |

### 1.7 — App DB Migration

**File: `backend/app/database.py`**

Add to `_MIGRATIONS` list:
```python
"ALTER TABLE sessions ADD COLUMN user_id TEXT",
```

Add to `SCHEMA` string (after the existing indexes):
```sql
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
```

### 1.8 — Wire Auth into Main App

**File: `backend/app/main.py`**

Changes:
1. **Import auth DB functions** at top:
   ```python
   from app.auth_database import init_auth_db, close_auth_db
   ```

2. **Initialize auth DB in lifespan** (add after `await init_db()`):
   ```python
   await init_auth_db()
   ```

3. **Register auth router** (add after other `include_router` calls):
   ```python
   from app.api import auth  # noqa: E402
   app.include_router(auth.router)
   ```

4. **Close auth DB in shutdown** (add before `await close_db()`):
   ```python
   await close_auth_db()
   ```

### 1.9 — Protect Existing Endpoints with Auth

**CRITICAL: Every existing API endpoint (except health + auth) must now require authentication.**

**File: `backend/app/api/sessions.py`**

Add imports at top:
```python
from fastapi import Depends
from app.auth_middleware import get_current_user
```

Add `user: dict = Depends(get_current_user)` parameter to EVERY endpoint function.

Add session ownership validation function:
```python
async def _require_session_ownership_by_user(session_id: str, user_id: str) -> None:
    """Raise 403 if the session doesn't belong to this user."""
    from app.database import get_db
    db = await get_db()
    cursor = await db.execute(
        "SELECT user_id FROM sessions WHERE id = ?", (session_id,)
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    if row["user_id"] and row["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
```

Call `_require_session_ownership_by_user(session_id, user["id"])` at the start of every endpoint that takes `session_id`.

For `create_session()`: pass `user["id"]` to the service:
```python
session_id = await session_service.create_session(user_id=user["id"])
```

**File: `backend/app/api/chat.py`**

Add `user: dict = Depends(get_current_user)` to the `chat()` endpoint. Add session ownership check. Pass `user["id"]` to session creation if session is auto-created.

**File: `backend/app/api/export.py`**

Add `user: dict = Depends(get_current_user)` to the export endpoint.

**File: `backend/app/api/upload.py`**

Add `user: dict = Depends(get_current_user)` to the upload endpoint.

**File: `backend/app/api/costs.py`**

Add `user: dict = Depends(require_admin)` to BOTH cost endpoints (admin-only — cost data is sensitive).

### 1.10 — Session Service Changes

**File: `backend/app/services/session_service.py`**

Modify `create_session()` to accept and store `user_id`:
```python
async def create_session(self, user_id: str | None = None) -> str:
    db = await get_db()
    session_id = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO sessions (id, user_id) VALUES (?, ?)",
        (session_id, user_id),
    )
    await db.commit()
    return session_id
```

### 1.11 — Orphaned Session Migration

**File: `backend/app/services/auth_service.py`**

In `setup_admin()`, after creating the admin user, assign all orphaned sessions:
```python
# Assign orphaned sessions (from before auth existed) to the admin
from app.database import get_db
app_db = await get_db()
await app_db.execute(
    "UPDATE sessions SET user_id = ? WHERE user_id IS NULL",
    (user_id,),
)
await app_db.commit()
```

### 1.12 — Frontend: Auth Context

**New file: `frontend/src/contexts/AuthContext.tsx`**

```typescript
interface User {
  id: string;
  username: string;
  display_name: string;
  is_admin: boolean;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  needsSetup: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string, displayName: string, inviteCode: string) => Promise<void>;
  setup: (username: string, password: string, displayName: string) => Promise<void>;
  logout: () => Promise<void>;
}
```

**On mount:**
1. `GET /api/auth/needs-setup` → if `needs_setup: true`, set `needsSetup = true`, stop
2. `GET /api/auth/me` → if 200, set user. If 401, set user = null.
3. Set `isLoading = false`

### 1.13 — Frontend: Auth Pages

**New files:**
- `frontend/src/components/Auth/LoginPage.tsx`
- `frontend/src/components/Auth/RegisterPage.tsx`
- `frontend/src/components/Auth/SetupPage.tsx`
- `frontend/src/components/Auth/AdminPanel.tsx`
- `frontend/src/components/Auth/Auth.css`

**LoginPage.tsx:**
- Form: username input, password input, "Sign In" button
- Error display for invalid credentials
- "Don't have an account? Sign Up" link → switches view to RegisterPage
- **Styling: Must match the Cyberpunk Amethyst theme** (dark surfaces, gold accents, mint text). Coordinate with user on exact design during implementation.

**RegisterPage.tsx:**
- Form: username, password, display name, invite code, "Create Account" button
- "Already have an account? Sign In" link → switches back to LoginPage
- Validation errors for bad invite code, duplicate username

**SetupPage.tsx:**
- Only shown when `needsSetup === true` (first time, 0 users)
- Form: username, password, display name, "Create Admin Account" button
- Welcome message: "Welcome to AI HTML Builder. Create your admin account to get started."

**AdminPanel.tsx:**
- Modal component, opened from 3-dot menu (admin only)
- Section 1: Invite code display + "Copy" button + "Regenerate" button
- Section 2: User list table with username, display name, "Remove" action button
- Cannot remove yourself (disable button for current user)
- Remove action uses ConfirmDialog (existing component)

### 1.14 — Frontend: App.tsx Auth Gate

**File: `frontend/src/App.tsx`**

Wrap the entire app with `AuthProvider`. Add render gate:
```tsx
<AuthProvider>
  <AuthGate />
</AuthProvider>

function AuthGate() {
  const { user, isLoading, needsSetup } = useAuth();

  if (isLoading) return <LoadingScreen />;  // Existing glyph loader
  if (needsSetup) return <SetupPage />;
  if (!user) return <LoginPage />;          // LoginPage manages its own Register toggle
  return <ChatApp user={user} />;           // Existing app content
}
```

### 1.15 — Frontend: API Functions

**File: `frontend/src/services/api.ts`**

Add auth API functions:
```typescript
// Auth (no session ID needed — cookie-based)
needsSetup: () => json('/api/auth/needs-setup'),
setup: (data: { username: string; password: string; display_name: string }) =>
  json('/api/auth/setup', { method: 'POST', headers: HEADERS, body: JSON.stringify(data) }),
login: (data: { username: string; password: string }) =>
  json('/api/auth/login', { method: 'POST', headers: HEADERS, body: JSON.stringify(data) }),
register: (data: { username: string; password: string; display_name: string; invite_code: string }) =>
  json('/api/auth/register', { method: 'POST', headers: HEADERS, body: JSON.stringify(data) }),
logout: () => json('/api/auth/logout', { method: 'POST' }),
getMe: () => json('/api/auth/me'),
// Admin
getUsers: () => json('/api/admin/users'),
deleteUser: (userId: string) => json(`/api/admin/users/${userId}`, { method: 'DELETE' }),
getInviteCode: () => json('/api/admin/invite-code'),
regenerateInviteCode: () => json('/api/admin/invite-code', { method: 'POST' }),
```

**IMPORTANT:** All fetch calls must include `credentials: 'same-origin'` (or `'include'`) to send cookies. Check if the existing `json()` helper already does this. If not, add it:
```typescript
const json = async (url: string, options?: RequestInit) => {
  const res = await fetch(url, { ...options, credentials: 'same-origin' });
  // ... existing error handling
};
```

### 1.16 — Frontend: useSSEChat Changes

**File: `frontend/src/hooks/useSSEChat.ts`**

- Remove all `sessionStorage.getItem('ai-html-builder-session-id')` and `sessionStorage.setItem(...)` calls
- Session ID is now managed purely in React state
- Session initialization moves to Phase 2 (home screen decides which session to load)
- For Phase 1: on mount, create a new session via `POST /api/sessions` (cookie handles auth)

### 1.17 — Frontend: 3-dot Menu Updates

**File: `frontend/src/components/ChatWindow/index.tsx`**

Add to the 3-dot dropdown menu:
- Username display (e.g., "Signed in as Chee") — non-clickable, muted text
- "Admin Settings" button (only visible when `user.is_admin === true`) → opens AdminPanel modal
- "Logout" button → calls `logout()` from AuthContext

### 1.18 — Frontend: Types

**File: `frontend/src/types/index.ts`**

Add:
```typescript
export interface User {
  id: string;
  username: string;
  display_name: string;
  is_admin: boolean;
}
```

### Phase 1 Tests

**New file: `backend/tests/test_auth_service.py`** (~30 tests):
- `test_needs_setup_initially_true`
- `test_setup_admin_creates_user_and_invite_code`
- `test_setup_admin_fails_when_users_exist`
- `test_register_with_valid_invite_code`
- `test_register_with_invalid_invite_code_fails`
- `test_register_duplicate_username_fails`
- `test_login_valid_credentials_returns_user_and_token`
- `test_login_invalid_password_raises`
- `test_login_nonexistent_user_raises`
- `test_validate_token_valid`
- `test_validate_token_expired_returns_none`
- `test_validate_token_nonexistent_returns_none`
- `test_logout_deletes_session`
- `test_list_users`
- `test_delete_user`
- `test_delete_nonexistent_user_returns_false`
- `test_get_invite_code`
- `test_regenerate_invite_code_changes_value`
- `test_password_hash_verify_roundtrip`
- `test_create_auth_session_sets_expiry`

**Test fixture:** Create a `tmp_path`-based auth.db for each test. Follow the pattern from `backend/tests/test_session_service.py`.

**New file: `backend/tests/test_auth_api.py`** (~20 tests):
- Test all endpoints via FastAPI TestClient
- Mock auth_service for unit isolation where appropriate
- Test cookie setting/clearing behavior
- Test 401 on protected routes without cookie
- Test 403 on admin routes with non-admin user

**New file: `backend/tests/test_auth_middleware.py`** (~5 tests):
- `test_get_current_user_valid_token`
- `test_get_current_user_no_cookie_raises_401`
- `test_get_current_user_invalid_token_raises_401`
- `test_require_admin_with_admin_passes`
- `test_require_admin_with_non_admin_raises_403`

### Phase 1 Verification
```bash
cd backend && pytest                    # All tests pass
cd backend && ruff check .              # Clean
cd backend && mypy .                    # Clean
cd frontend && npm run lint             # Clean
cd frontend && npm run build            # Succeeds
```

Manual test:
1. Start backend + frontend dev servers
2. Visit app → see Setup page (no users exist)
3. Create admin account → auto-login → see template cards
4. Open 3-dot menu → see "Admin Settings" → see invite code
5. Open incognito → see Login page → click "Sign Up" → register with invite code
6. Back to admin → send a chat message → verify chat still works through auth
7. Logout → see Login page → login again → verify cookie persists

---

## Phase 2: Session History & Home Screen

### 2.1 — Backend: Session List Endpoint

**File: `backend/app/api/sessions.py`**

Add new endpoint:
```python
@router.get("/api/sessions")
async def list_sessions(
    user: dict = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List all sessions for the authenticated user with summary info."""
    sessions = await session_service.get_user_sessions(
        user["id"], limit=limit, offset=offset
    )
    return {"sessions": sessions}
```

### 2.2 — Backend: Delete Session Endpoint

**File: `backend/app/api/sessions.py`**

```python
@router.delete("/api/sessions/{session_id}")
async def delete_session(
    session_id: str,
    user: dict = Depends(get_current_user),
):
    await _require_session_ownership_by_user(session_id, user["id"])
    success = await session_service.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True}
```

### 2.3 — Backend: Update Session Title Endpoint

**File: `backend/app/api/sessions.py`**

```python
class UpdateSessionRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)

@router.patch("/api/sessions/{session_id}")
async def update_session(
    session_id: str,
    body: UpdateSessionRequest,
    user: dict = Depends(get_current_user),
):
    await _require_session_ownership_by_user(session_id, user["id"])
    success = await session_service.update_session_title(session_id, body.title)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True}
```

### 2.4 — Backend: Session Service Additions

**File: `backend/app/services/session_service.py`**

**New method — `get_user_sessions()`:**
```python
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

    import json as json_mod
    result = []
    for row in rows:
        r = dict(row)
        metadata = json_mod.loads(r.get("metadata") or "{}")
        title = metadata.get("title", "")
        if not title and r.get("first_message"):
            title = r["first_message"][:80]
        if not title:
            title = "Untitled Session"

        result.append({
            "id": r["id"],
            "title": title,
            "doc_count": r["doc_count"],
            "first_message_preview": (r.get("first_message") or "")[:80],
            "last_active": r["last_active"],
            "created_at": r["created_at"],
        })
    return result
```

**IMPORTANT:** Use `s.id DESC` as tiebreaker in ORDER BY (SQLite `CURRENT_TIMESTAMP` has second-level precision — see MEMORY.md).

**New method — `delete_session()`:**
```python
async def delete_session(self, session_id: str) -> bool:
    db = await get_db()
    cursor = await db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    await db.commit()
    return cursor.rowcount > 0
```

**New method — `update_session_title()`:**
```python
async def update_session_title(self, session_id: str, title: str) -> bool:
    import json as json_mod
    db = await get_db()
    cursor = await db.execute("SELECT metadata FROM sessions WHERE id = ?", (session_id,))
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
```

**Modify `add_chat_message()`** — add AFTER the existing INSERT:
```python
# Update last_active timestamp
await db.execute(
    "UPDATE sessions SET last_active = CURRENT_TIMESTAMP WHERE id = ?",
    (session_id,),
)

# Auto-title: set session title from first user message
if role == "user":
    import json as json_mod
    cursor2 = await db.execute(
        "SELECT metadata FROM sessions WHERE id = ?", (session_id,)
    )
    meta_row = await cursor2.fetchone()
    if meta_row:
        metadata = json_mod.loads(meta_row["metadata"] or "{}")
        if not metadata.get("title"):
            metadata["title"] = content[:80]
            await db.execute(
                "UPDATE sessions SET metadata = ? WHERE id = ?",
                (json_mod.dumps(metadata), session_id),
            )
```

### 2.5 — Backend: Extend Cleanup to 30 Days

**File: `backend/app/main.py`**

Change line 69 from:
```python
"DELETE FROM sessions WHERE last_active < datetime('now', '-7 days')"
```
To:
```python
"DELETE FROM sessions WHERE last_active < datetime('now', '-30 days')"
```

### 2.6 — Frontend: Home Screen Component

**New file: `frontend/src/components/HomeScreen/HomeScreen.tsx`**
**New file: `frontend/src/components/HomeScreen/HomeScreen.css`**

**Layout:**
```
┌─────────────────────────────────────────────────────┐
│  Welcome back, {display_name}                       │
│                                                     │
│  ── Pick up where you left off ─────────────────    │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐│
│  │ Session title │ │ Session title │ │ Session title ││
│  │ 3 docs · 2h  │ │ 1 doc · yday │ │ 1 doc · 3d   ││
│  └──────────────┘ └──────────────┘ └──────────────┘│
│  [View all sessions →]                              │
│                                                     │
│  ── Or start something new ─────────────────────    │
│  [Template Card] [Template Card] [Template Card]    │
│  [Template Card] [Template Card] [Template Card]    │
│                                                     │
│  [Type your prompt here...]                 [Send]  │
└─────────────────────────────────────────────────────┘
```

- "Pick up where you left off" section only shown when user has past sessions
- Show up to 3 most recent sessions
- "View all sessions →" opens `MySessionsModal`
- "Or start something new" section uses existing `TemplateCards` component
- Chat input at bottom for freeform new session
- First-time user (no sessions) sees only the template cards + input

**Props:**
```typescript
interface HomeScreenProps {
  user: User;
  recentSessions: SessionSummary[];
  onSelectSession: (sessionId: string) => void;
  onSelectTemplate: (template: PromptTemplate) => void;
  onSendMessage: (message: string) => void;
  onViewAllSessions: () => void;
}
```

**New file: `frontend/src/components/HomeScreen/SessionCard.tsx`**

```typescript
interface SessionCardProps {
  session: SessionSummary;
  onClick: () => void;
}
// Shows: title, doc count, relative time (e.g., "2 hours ago")
// Styled distinctly from template cards (different accent, no icon)
```

### 2.7 — Frontend: My Sessions Modal

**New file: `frontend/src/components/HomeScreen/MySessionsModal.tsx`**
**New file: `frontend/src/components/HomeScreen/MySessionsModal.css`**

- Full paginated session list
- Each row: title, doc count, relative time, delete button
- Click row → `onSelectSession(sessionId)` → context switch
- Delete button → ConfirmDialog (existing component) → `DELETE /api/sessions/{sid}`
- "Load more" at bottom for pagination
- Close button (×) and Escape key to close

### 2.8 — Frontend: Session Switching in useSSEChat

**File: `frontend/src/hooks/useSSEChat.ts`**

Add `loadSession()` function:
```typescript
const loadSession = useCallback(async (targetSessionId: string) => {
    // Clear ALL current state
    setMessages([]);
    setDocuments([]);
    setActiveDocument(null);
    setCurrentHtml('');
    setStreamingContent('');
    setCurrentStatus('');
    setIsStreaming(false);
    setError(null);

    // Load the target session
    setSessionId(targetSessionId);

    const session = await api.getSession(targetSessionId);
    setDocuments(session.documents);

    const active = session.documents.find((d: Document) => d.is_active) || session.documents[0];
    setActiveDocument(active || null);

    if (active) {
        const { html } = await api.getDocumentHtml(active.id);
        setCurrentHtml(html);
    }

    const { messages: history } = await api.getChatHistory(targetSessionId);
    setMessages(history);
}, []);
```

Add `showHomeScreen` state:
```typescript
const [showHomeScreen, setShowHomeScreen] = useState(true);
```

Modify initialization (remove sessionStorage):
- On mount: set `showHomeScreen = true` (home screen decides what to do)
- When user selects a session from home screen: call `loadSession(id)`, set `showHomeScreen = false`
- When user sends first message from home screen: create session, send message, set `showHomeScreen = false`
- "New Session": create new session, clear state, set `showHomeScreen = true`

Export `loadSession`, `showHomeScreen`, `setShowHomeScreen` from the hook.

### 2.9 — Frontend: Menu Updates

**File: `frontend/src/components/ChatWindow/index.tsx`**

Add "My Sessions" to the 3-dot dropdown:
```jsx
<button onClick={() => { setMenuOpen(false); setMySessionsOpen(true); }}>
    My Sessions
</button>
```

The `MySessionsModal` is rendered at the ChatWindow level, triggered by `mySessionsOpen` state.

### 2.10 — Frontend: API Functions

**File: `frontend/src/services/api.ts`**

```typescript
listSessions: (limit?: number, offset?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    if (offset) params.set('offset', String(offset));
    return json(`/api/sessions?${params.toString()}`);
},
deleteSession: (sessionId: string) =>
    json(`/api/sessions/${sessionId}`, { method: 'DELETE' }),
updateSessionTitle: (sessionId: string, title: string) =>
    json(`/api/sessions/${sessionId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title }),
    }),
```

### 2.11 — Frontend: App.tsx Home Screen Integration

**File: `frontend/src/App.tsx`**

When `showHomeScreen === true`, render `HomeScreen` instead of the SplitPane layout. The `HomeScreen` component receives callbacks for session selection, template selection, and new message sending.

### 2.12 — Frontend: Types

**File: `frontend/src/types/index.ts`**

```typescript
export interface SessionSummary {
  id: string;
  title: string;
  doc_count: number;
  first_message_preview: string;
  last_active: string;
  created_at: string;
}
```

### Phase 2 Tests

**New file: `backend/tests/test_session_list.py`** (~10 tests):
- `test_get_user_sessions_empty`
- `test_get_user_sessions_returns_summary`
- `test_get_user_sessions_pagination`
- `test_get_user_sessions_only_own_sessions`
- `test_delete_session_cascades`
- `test_delete_nonexistent_session`
- `test_update_session_title`
- `test_auto_title_from_first_message`
- `test_last_active_updated_on_chat_message`
- `test_session_list_ordered_by_last_active`

### Phase 2 Verification
```bash
cd backend && pytest
cd frontend && npm run lint && npm run build
```

Manual test:
1. Login → see Home Screen with "Start something new" (no past sessions)
2. Select a template → create a document → send a few messages
3. 3-dot menu → "New Session" → see Home Screen with 1 past session in "Pick up where you left off"
4. Create another session → "New Session" → see 2 past sessions
5. Click a past session → full context switch (all docs, chat, preview restore)
6. 3-dot → "My Sessions" → see full list modal → delete a session
7. Verify deleted session disappears from list

---

## Phase 3: Version Diff (Before/After Toggle)

### 3.1 — VersionTimeline.tsx Changes

**File: `frontend/src/components/VersionHistory/VersionTimeline.tsx`**

**Add state:**
```typescript
const [diffMode, setDiffMode] = useState<'before' | 'after'>('after');
const [beforeHtml, setBeforeHtml] = useState<string | null>(null);
```

**Modify `handleVersionClick()`** — after the existing `setSelectedVersion(ver.version)` and `onVersionPreview(detail.html_content)`, add:
```typescript
// Pre-fetch previous version for Before/After toggle
if (ver.version > 1 && documentId) {
    try {
        const prevDetail = await api.getVersion(documentId, ver.version - 1);
        setBeforeHtml(prevDetail.html_content);
    } catch {
        setBeforeHtml(null);
    }
} else {
    setBeforeHtml(null);
}
setDiffMode('after');
```

**Modify the preview bar** (lines 106-122) — add Before/After toggle buttons:
```tsx
{selectedVersion !== null && (
    <div className="version-preview-bar">
        <span>Viewing v{selectedVersion}</span>
        <div className="version-preview-actions">
            {/* Before/After toggle */}
            <div className="version-diff-toggle">
                <button
                    className={`diff-toggle-btn${diffMode === 'before' ? ' active' : ''}`}
                    onClick={() => {
                        setDiffMode('before');
                        if (beforeHtml) onVersionPreview(beforeHtml);
                    }}
                    disabled={!beforeHtml || selectedVersion <= 1}
                    title={selectedVersion <= 1 ? 'No previous version' : `Show v${selectedVersion - 1}`}
                    type="button"
                >
                    ◀ Before
                </button>
                <button
                    className={`diff-toggle-btn${diffMode === 'after' ? ' active' : ''}`}
                    onClick={async () => {
                        setDiffMode('after');
                        if (documentId && selectedVersion) {
                            const detail = await api.getVersion(documentId, selectedVersion);
                            onVersionPreview(detail.html_content);
                        }
                    }}
                    type="button"
                >
                    After ▶
                </button>
            </div>

            {/* Existing buttons */}
            <button
                className="restore-version-btn"
                onClick={() => setRestoreConfirm(true)}
                type="button"
            >
                Restore this version
            </button>
            <button className="back-to-current-btn" onClick={handleBackToCurrent} type="button">
                Back to current
            </button>
        </div>
    </div>
)}
```

**Reset diff state on panel close or document change** — in the existing `useEffect` (lines 32-62), add:
```typescript
setDiffMode('after');
setBeforeHtml(null);
```

### 3.2 — Keyboard Navigation

Add a `useEffect` in `VersionTimeline.tsx`:
```typescript
useEffect(() => {
    if (selectedVersion === null) return;

    const handleKeyDown = (e: KeyboardEvent) => {
        if (e.key === 'ArrowLeft' && beforeHtml && selectedVersion > 1) {
            e.preventDefault();
            setDiffMode('before');
            onVersionPreview(beforeHtml);
        } else if (e.key === 'ArrowRight' && documentId && selectedVersion) {
            e.preventDefault();
            setDiffMode('after');
            api.getVersion(documentId, selectedVersion).then(detail => {
                onVersionPreview(detail.html_content);
            });
        }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
}, [selectedVersion, beforeHtml, documentId, onVersionPreview]);
```

### 3.3 — CSS

**File: `frontend/src/components/VersionHistory/VersionTimeline.css`**

Add:
```css
.version-diff-toggle {
    display: flex;
    border: 1px solid var(--border-default);
    border-radius: var(--radius-sm);
    overflow: hidden;
}

.diff-toggle-btn {
    padding: 0.2rem 0.6rem;
    font-family: var(--font-mono);
    font-size: var(--fs-xs);
    letter-spacing: var(--tracking-wide);
    background: transparent;
    border: none;
    color: var(--text-secondary);
    cursor: pointer;
    transition: all var(--duration-fast);
}

.diff-toggle-btn + .diff-toggle-btn {
    border-left: 1px solid var(--border-default);
}

.diff-toggle-btn.active {
    background: var(--accent-primary-muted);
    color: var(--accent-primary);
}

.diff-toggle-btn:disabled {
    color: var(--text-tertiary);
    cursor: not-allowed;
    opacity: 0.5;
}
```

### Phase 3 Verification

No backend changes → no backend tests needed.

Manual test:
1. Create a document → edit it 3 times (3 versions)
2. Open History panel → click v3 → see Before/After toggle
3. Click "Before" → preview shows v2
4. Click "After" → preview shows v3
5. Arrow keys: Left = Before, Right = After
6. Click v1 → "Before" button is disabled (no v0)
7. "Back to current" → toggle disappears

---

## Phase 4: UX Polish

All items in this phase are independent. Implement in any order.

### U7 — Better Error Messages

**New file: `frontend/src/utils/errorUtils.ts`**
```typescript
const STATUS_MESSAGES: Record<number, string> = {
    400: 'The request was invalid. Please check your input.',
    401: 'Your session has expired. Please log in again.',
    403: "You don't have permission to do that.",
    404: "This resource wasn't found. It may have been deleted.",
    413: 'File too large.',
    429: 'Too many requests. Please wait a moment and try again.',
    500: 'Something went wrong on the server. Try again in a moment.',
    502: 'Server is temporarily unavailable. Try again shortly.',
    503: 'Server is temporarily unavailable. Try again shortly.',
};

export function humanizeError(error: unknown): string {
    if (error instanceof TypeError && error.message.includes('fetch')) {
        return 'Server connection lost. Check your network and try again.';
    }
    if (error instanceof Error) {
        const match = error.message.match(/^(\d{3})\s/);
        if (match) {
            const code = parseInt(match[1], 10);
            return STATUS_MESSAGES[code] || `Server error (${code}). Please try again.`;
        }
        return error.message;
    }
    return 'An unexpected error occurred. Please try again.';
}
```

**New files: `frontend/src/components/Toast/Toast.tsx`** + `Toast.css`
- Auto-dismiss (4s default), positioned fixed bottom-right
- Types: `error` (red), `success` (green), `warning` (yellow)
- Slide-up + fade-in entry animation
- ToastProvider context for global `showToast(message, type)` access

**Modified: `frontend/src/hooks/useSSEChat.ts`**
- Fix `refreshDocuments()` catch: show warning toast instead of silent swallow
- Replace raw error messages with `humanizeError()` where applicable

### U8 — Export Progress Feedback

**File: `frontend/src/components/Export/ExportDropdown.tsx`**

Add `successFormat` state. Modify `handleExport()`:
```typescript
const [successFormat, setSuccessFormat] = useState<ExportFormat | null>(null);

const handleExport = async (format: ExportFormat) => {
    if (!documentId || loadingFormat) return;
    setLoadingFormat(format);
    setExportError(null);
    setSuccessFormat(null);
    try {
        await api.exportDocument(documentId, format, documentTitle);
        setSuccessFormat(format);
        setTimeout(() => {
            setSuccessFormat(null);
            setOpen(false);
        }, 2000);
    } catch (err) {
        setExportError(humanizeError(err));
    } finally {
        setLoadingFormat(null);
    }
};
```

Button rendering pattern (apply to each format):
```tsx
{loadingFormat === 'pdf' ? (
    <span className="export-loading"><span className="export-spinner" /> Exporting PDF...</span>
) : successFormat === 'pdf' ? (
    <span className="export-success">PDF downloaded!</span>
) : (
    'PDF'
)}
```

**File: `frontend/src/components/Export/ExportDropdown.css`**

Add:
```css
.export-spinner {
    display: inline-block;
    width: 14px;
    height: 14px;
    border: 2px solid var(--border-default);
    border-top-color: var(--accent-primary);
    border-radius: 50%;
    animation: spin 0.6s linear infinite;
    vertical-align: middle;
    margin-right: 0.4rem;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}

.export-success {
    color: var(--signal-success);
}
```

### U11 — Rename ARCHITECT → BUILDER

**File: `frontend/src/components/ChatWindow/MessageList.tsx`**

Two string replacements:
- Line 60: `'ARCHITECT'` → `'BUILDER'`
- Line 94: `ARCHITECT` → `BUILDER`

### U14 — Smarter Export Filenames

**File: `backend/app/utils/export_utils.py`**

Replace `sanitize_title()`:
```python
def sanitize_title(title: str) -> str:
    """Sanitize document title for use in filenames."""
    safe = "".join(
        c if c.isalnum() or c in (" ", "-", "_") else "_"
        for c in title
    ).strip()

    # Replace spaces with hyphens for cleaner filenames
    safe = safe.replace(" ", "-")

    # Collapse multiple hyphens/underscores
    while "--" in safe:
        safe = safe.replace("--", "-")
    while "__" in safe:
        safe = safe.replace("__", "_")

    # Truncate to 60 chars at word boundary
    if len(safe) > 60:
        truncated = safe[:60]
        last_sep = max(truncated.rfind("-"), truncated.rfind("_"))
        if last_sep > 30:
            truncated = truncated[:last_sep]
        safe = truncated

    # Strip trailing separators
    safe = safe.strip("-_")

    return safe or "document"
```

Add tests to existing export test file for the improved function.

### U15 — Infographic PNG-Only Explanation

**File: `frontend/src/components/Export/ExportDropdown.tsx`**

After the PNG button (line 124, before the closing `</div>` of the menu), add:
```tsx
{isInfographic && (
    <div className="export-infographic-hint">
        Infographics can only be exported as PNG
    </div>
)}
```

**File: `frontend/src/components/Export/ExportDropdown.css`**

Add:
```css
.export-infographic-hint {
    color: var(--text-tertiary);
    font-size: var(--fs-xs);
    padding: 0.5rem 1rem;
    border-top: 1px solid var(--border-subtle);
    font-style: italic;
}
```

### U19 — Dead CSS Cleanup

**File: `frontend/src/theme.css`**

Remove three unused `@keyframes` blocks (lines ~116-129):
- `@keyframes conduit-sweep`
- `@keyframes conduit-pulse`
- `@keyframes status-beacon`

**Verify first:** Search entire frontend for references to these animation names. Expected: 0 references.

### Phase 4 Verification
```bash
cd backend && pytest                    # sanitize_title tests pass
cd frontend && npm run lint && npm run build
```

Manual test:
1. Export a PDF → see spinner + "Exporting PDF..." → "PDF downloaded!" for 2s
2. Export an infographic → only PNG shown + "Infographics can only be exported as PNG"
3. Check exported filename is clean and truncated (not the full chat message)
4. AI messages now labeled "BUILDER" (not "ARCHITECT")
5. Stop backend → try chatting → see "Server connection lost" message
6. Verify no CSS regressions from dead animation removal

---

## Deployment Notes

### New Dependencies
- `bcrypt==4.3.0` — C extension, `gcc` already in Dockerfile line 21

### New Environment Variables (all optional, have defaults)
```bash
AUTH_DATABASE_PATH=./data/auth.db       # Default: ./data/auth.db
AUTH_SESSION_EXPIRY_DAYS=30             # Default: 30
DEV_MODE=false                          # Set to "true" for local dev (disables secure cookie)
```

### Docker
- No Dockerfile changes needed
- `auth.db` created in `/app/data/` (same volume mount as `app.db`)
- Both DBs backed up by existing cron job (add `auth.db` to `deploy.sh` backup)

### Cookie Behavior
- **Production** (HTTPS via NPM): `secure=True, samesite=lax, httponly=True` — works
- **Development** (HTTP via Vite proxy): `secure=False` when `DEV_MODE=true` — works because Vite proxy makes `/api` same-origin

### Existing Data Migration
- On first admin setup, `setup_admin()` assigns all existing orphaned sessions (`user_id IS NULL`) to the admin user
- No data loss — all existing sessions become the admin's sessions

### Deploy Script Update
**File: `deploy.sh`** — add `auth.db` backup:
```bash
if [ -f data/auth.db ]; then
    cp data/auth.db "backups/auth_${TIMESTAMP}.db"
fi
```

---

## Complete File Inventory

### New Backend Files (8)
| File | Lines (est.) | Purpose |
|------|-------------|---------|
| `backend/app/auth_database.py` | ~50 | Auth SQLite init/close/get |
| `backend/app/services/auth_service.py` | ~180 | Auth business logic |
| `backend/app/auth_middleware.py` | ~25 | FastAPI auth dependencies |
| `backend/app/api/auth.py` | ~150 | Auth REST endpoints |
| `backend/tests/test_auth_service.py` | ~250 | Auth service tests |
| `backend/tests/test_auth_api.py` | ~200 | Auth API integration tests |
| `backend/tests/test_auth_middleware.py` | ~60 | Middleware tests |
| `backend/tests/test_session_list.py` | ~120 | Session list/delete tests |

### New Frontend Files (~14)
| File | Purpose |
|------|---------|
| `frontend/src/contexts/AuthContext.tsx` | Auth state provider |
| `frontend/src/components/Auth/LoginPage.tsx` | Login form |
| `frontend/src/components/Auth/RegisterPage.tsx` | Registration form |
| `frontend/src/components/Auth/SetupPage.tsx` | First-time admin setup |
| `frontend/src/components/Auth/AdminPanel.tsx` | User/invite management modal |
| `frontend/src/components/Auth/Auth.css` | Auth page styles |
| `frontend/src/components/HomeScreen/HomeScreen.tsx` | Landing page |
| `frontend/src/components/HomeScreen/HomeScreen.css` | Landing page styles |
| `frontend/src/components/HomeScreen/SessionCard.tsx` | Session summary card |
| `frontend/src/components/HomeScreen/MySessionsModal.tsx` | Full session list modal |
| `frontend/src/components/HomeScreen/MySessionsModal.css` | Modal styles |
| `frontend/src/utils/errorUtils.ts` | Error humanization |
| `frontend/src/components/Toast/Toast.tsx` | Toast notifications |
| `frontend/src/components/Toast/Toast.css` | Toast styles |

### Modified Backend Files (9)
| File | Changes |
|------|---------|
| `backend/requirements.txt` | + `bcrypt==4.3.0` |
| `backend/app/config.py` | + `auth_database_path`, `auth_session_expiry_days` |
| `backend/app/database.py` | + `user_id` migration + index in SCHEMA |
| `backend/app/main.py` | + auth DB lifecycle, auth router, 30-day cleanup |
| `backend/app/services/session_service.py` | + `user_id`, `get_user_sessions`, `delete_session`, `update_session_title`, auto-title, `last_active` |
| `backend/app/api/sessions.py` | + auth deps, ownership check, list/delete/update endpoints |
| `backend/app/api/chat.py` | + auth dep, user_id passthrough |
| `backend/app/api/export.py` | + auth dep |
| `backend/app/api/upload.py` | + auth dep |
| `backend/app/api/costs.py` | + `require_admin` dep |
| `backend/app/utils/export_utils.py` | Improved `sanitize_title()` |

### Modified Frontend Files (10)
| File | Changes |
|------|---------|
| `frontend/src/App.tsx` | AuthProvider wrapper, home screen routing |
| `frontend/src/hooks/useSSEChat.ts` | Remove sessionStorage, add `loadSession`, `showHomeScreen`, fix error handling |
| `frontend/src/services/api.ts` | Auth + session list API calls, `credentials: 'same-origin'` |
| `frontend/src/types/index.ts` | + `User`, `SessionSummary` |
| `frontend/src/components/ChatWindow/index.tsx` | Menu: My Sessions, Logout, Admin Settings |
| `frontend/src/components/ChatWindow/MessageList.tsx` | ARCHITECT → BUILDER (2 occurrences) |
| `frontend/src/components/VersionHistory/VersionTimeline.tsx` | Before/After toggle + keyboard nav |
| `frontend/src/components/VersionHistory/VersionTimeline.css` | Diff toggle styles |
| `frontend/src/components/Export/ExportDropdown.tsx` | Spinner, success, infographic hint |
| `frontend/src/components/Export/ExportDropdown.css` | Spinner + success + hint styles |
| `frontend/src/theme.css` | Remove 3 dead `@keyframes` (~13 lines) |
