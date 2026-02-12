# Plan 001: Backend Foundation

## STOP: Read This Entire Document Before Making Any Changes

This plan establishes the new backend architecture: SQLite database, LLM provider interface, SSE streaming, and the new project structure. All subsequent plans depend on this foundation.

**Dependencies**: Plan 000 (Master Plan) read and understood
**Estimated effort**: 3-5 days

---

## Context & Rationale

The current backend has:
- 1,200-line `claude_service.py` with hardcoded Anthropic SDK
- Redis with silent failures and data loss on restart
- WebSocket handler (569 lines) with complex state management
- JWT admin auth system with hardcoded password
- No test structure

The new backend will have:
- Clean provider interface (~100 lines) supporting multiple AI models
- SQLite with WAL mode for persistent, queryable session storage
- SSE streaming with standard HTTP POST for input (~100 lines)
- No auth code (handled by Nginx Proxy Manager on the server)
- Clear separation: providers / services / api / models

---

## Strict Rules

### MUST DO
- [ ] Delete all v1 files that are fully replaced by this plan (see Phase 0)
- [ ] Create the new project structure BEFORE writing any code
- [ ] Use `aiosqlite` for async SQLite access (NOT synchronous sqlite3)
- [ ] Enable WAL mode on database initialization
- [ ] Use Python `ABC` for the provider interface (NOT LangChain, NOT LiteLLM)
- [ ] Use `pydantic-settings` for configuration (NOT raw os.getenv)
- [ ] Use `AsyncIterator[str]` as the return type for streaming
- [ ] Add `.env.example` with all required variables (NO actual keys)
- [ ] Run `ruff check` and `mypy` after every file change

### MUST NOT DO
- [ ] Do NOT import anything from the old `services/claude_service.py`
- [ ] Do NOT use Redis anywhere in the new code
- [ ] Do NOT implement WebSocket endpoints
- [ ] Do NOT add JWT or any auth middleware
- [ ] Do NOT install LangChain, LiteLLM, or any LLM framework
- [ ] Do NOT create the surgical editing logic yet (that's Plan 002)
- [ ] Do NOT add Gemini providers yet (that's Plan 003)
- [ ] Do NOT delete `claude_service.py` or `artifact_manager.py` (needed as reference for Plan 002)

---

## Phase 0: Dead Code Cleanup

Before creating the new structure, delete all v1 files that are fully replaced by this plan. This ensures a clean foundation with zero technical debt.

### Files to Delete
- `backend/app/services/redis_service.py` → replaced by SQLite `database.py`
- `backend/app/services/memory_store.py` → Redis fallback, no longer needed
- `backend/app/services/analytics_service.py` → replaced by `cost_tracker.py`
- `backend/app/services/file_processor.py` → deprecated (returns 410)
- `backend/app/middleware/` (entire directory) → JWT auth removed, NPM handles auth
- `backend/app/api/admin/` (entire directory) → JWT admin system removed
- `backend/app/api/endpoints/upload.py` → deprecated endpoint
- `backend/app/api/websocket.py` → replaced by SSE `api/chat.py`
- `backend/app/models/analytics.py` → replaced by `cost_tracking` table
- `backend/app/core/` (entire directory) → `config.py` moves to `app/config.py`

### Files to KEEP (reference for later plans)
- `services/claude_service.py` → Plan 002 extracts surgical editing logic, then deletes
- `services/artifact_manager.py` → Plan 002 references version patterns, then deletes
- `models/session.py`, `models/schemas.py` → reference for data shapes, delete in Plan 002
- `api/endpoints/health.py`, `api/endpoints/export.py` → reference for response formats, delete in Plan 003
- `utils/logger.py`, `utils/sanitizer.py` → reference, delete in Plan 002

---

## Phase 1: Project Structure

### Step 1.1: Create New Directory Structure

Create the following structure inside `backend/`:

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── session.py
│   │   ├── chat.py
│   │   └── export.py
│   │
│   ├── providers/
│   │   ├── __init__.py
│   │   └── base.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── session_service.py
│   │   └── cost_tracker.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── chat.py
│   │   ├── sessions.py
│   │   ├── health.py
│   │   └── costs.py
│   │
│   └── utils/
│       ├── __init__.py
│       ├── fuzzy_match.py
│       ├── html_validator.py
│       └── rate_limiter.py
│
├── tests/
│   ├── __init__.py
│   ├── test_database.py
│   ├── test_session_service.py
│   └── test_rate_limiter.py
│
├── requirements.txt
├── .env.example
└── Dockerfile
```

### Step 1.2: New requirements.txt

```
# Core
fastapi>=0.111.0
uvicorn[standard]>=0.30.0
pydantic>=2.8.0
pydantic-settings>=2.3.0

# Database
aiosqlite>=0.20.0

# AI Providers
anthropic>=0.40.0
google-genai>=1.52.0

# Streaming
sse-starlette>=2.0.0

# Export
python-pptx>=1.0.0
playwright>=1.49.0

# File processing
python-docx>=1.1.0
PyPDF2>=3.0.0
openpyxl>=3.1.0

# Utilities
structlog>=24.4.0
python-multipart>=0.0.9

# Development
ruff>=0.5.0
mypy>=1.10.0
pytest>=8.2.0
pytest-asyncio>=0.23.0
```

### Step 1.3: .env.example

```bash
# Required: AI Provider API Keys
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...

# Optional: Override defaults
DATABASE_PATH=./data/app.db
LOG_LEVEL=info
RATE_LIMIT_REQUESTS=30
RATE_LIMIT_WINDOW=60
SESSION_TIMEOUT_HOURS=24
MAX_UPLOAD_SIZE_MB=50
```

---

## Phase 2: Configuration & Database

### Step 2.1: config.py

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # AI Providers
    anthropic_api_key: str
    google_api_key: str = ""

    # Database
    database_path: str = "./data/app.db"

    # Server
    log_level: str = "info"
    rate_limit_requests: int = 30
    rate_limit_window: int = 60  # seconds
    session_timeout_hours: int = 24
    max_upload_size_mb: int = 50

    # Models (configurable without code change)
    edit_model: str = "claude-sonnet-4-5-20250929"
    creation_model: str = "gemini-2.5-pro"
    image_model: str = "gemini-3-pro-image-preview"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
```

### Step 2.2: database.py

```python
import aiosqlite
import os
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

async def init_db():
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
    await _db.commit()
    logger.info("Database initialized", path=str(db_path))

async def close_db():
    global _db
    if _db:
        await _db.close()
        _db = None
        logger.info("Database closed")

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
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

CREATE TABLE IF NOT EXISTS templates (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    html_content TEXT NOT NULL,
    thumbnail_base64 TEXT,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_documents_session ON documents(session_id);
CREATE INDEX IF NOT EXISTS idx_versions_document ON document_versions(document_id);
CREATE INDEX IF NOT EXISTS idx_messages_session ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_cost_date ON cost_tracking(date);
"""
```

---

## Phase 3: Provider Interface

### Step 3.1: providers/base.py

```python
from abc import ABC, abstractmethod
from typing import AsyncIterator
from dataclasses import dataclass

@dataclass
class GenerationResult:
    """Result from an LLM generation call."""
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""

@dataclass
class ToolCall:
    """A tool call returned by the LLM."""
    name: str
    input: dict
    id: str = ""

@dataclass
class ToolResult:
    """Result from an LLM call that uses tools."""
    tool_calls: list[ToolCall]
    text: str = ""  # Any non-tool text in the response
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""

class LLMProvider(ABC):
    """Base interface for text/code generation providers."""

    @abstractmethod
    async def generate(
        self,
        system: str,
        messages: list[dict],
        max_tokens: int = 8000,
        temperature: float = 0.7,
    ) -> GenerationResult:
        """Generate a complete response."""
        ...

    @abstractmethod
    async def stream(
        self,
        system: str,
        messages: list[dict],
        max_tokens: int = 8000,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """Stream a response token by token."""
        ...

    @abstractmethod
    async def generate_with_tools(
        self,
        system: str | list[dict],
        messages: list[dict],
        tools: list[dict],
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> ToolResult:
        """Generate a response using tool definitions. Used for surgical editing."""
        ...


class ImageProvider(ABC):
    """Base interface for image generation providers."""

    @abstractmethod
    async def generate_image(
        self,
        prompt: str,
        resolution: str = "2k",  # "2k" or "4k"
    ) -> bytes:
        """Generate an image from a text prompt. Returns PNG bytes."""
        ...
```

### Step 3.2: providers/anthropic_provider.py (Skeleton)

```python
import anthropic
from typing import AsyncIterator
from app.providers.base import LLMProvider, GenerationResult, ToolResult, ToolCall
from app.config import settings
import structlog

logger = structlog.get_logger()

class AnthropicProvider(LLMProvider):
    """Claude Sonnet 4.5 provider for surgical editing and PPT export."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        key = api_key or settings.anthropic_api_key
        if not key or not key.startswith("sk-ant-"):
            raise ValueError("Valid Anthropic API key required (starts with sk-ant-)")
        self.client = anthropic.AsyncAnthropic(api_key=key)
        self.model = model or settings.edit_model

    async def generate(self, system, messages, max_tokens=8000, temperature=0.7):
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=messages,
        )
        return GenerationResult(
            text=response.content[0].text,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=self.model,
        )

    async def stream(self, system, messages, max_tokens=8000, temperature=0.7):
        async with self.client.messages.stream(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def generate_with_tools(self, system, messages, tools, max_tokens=4096, temperature=0.0):
        # Handle system as string or list of cache-controlled blocks
        system_param = system if isinstance(system, list) else system

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_param,
            tools=tools,
            messages=messages,
        )

        tool_calls = []
        text_parts = []

        for block in response.content:
            if block.type == "tool_use":
                tool_calls.append(ToolCall(
                    name=block.name,
                    input=block.input,
                    id=block.id,
                ))
            elif block.type == "text":
                text_parts.append(block.text)

        return ToolResult(
            tool_calls=tool_calls,
            text="\n".join(text_parts),
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=self.model,
        )
```

---

## Phase 4: Session Service

### Step 4.1: services/session_service.py

```python
import uuid
from datetime import datetime
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
            (session_id,)
        )
        await db.commit()
        logger.info("Session created", session_id=session_id[:8])
        return session_id

    async def get_or_create_session(self, session_id: str) -> str:
        db = await get_db()
        row = await db.execute_fetchone(
            "SELECT id FROM sessions WHERE id = ?", (session_id,)
        )
        if row:
            await db.execute(
                "UPDATE sessions SET last_active = CURRENT_TIMESTAMP WHERE id = ?",
                (session_id,)
            )
            await db.commit()
            return session_id
        return await self.create_session()

    async def create_document(self, session_id: str, title: str = "Untitled") -> str:
        db = await get_db()
        doc_id = str(uuid.uuid4())
        # Deactivate other documents in this session
        await db.execute(
            "UPDATE documents SET is_active = 0 WHERE session_id = ?",
            (session_id,)
        )
        await db.execute(
            "INSERT INTO documents (id, session_id, title, is_active) VALUES (?, ?, ?, 1)",
            (doc_id, session_id, title)
        )
        await db.commit()
        logger.info("Document created", doc_id=doc_id[:8], session_id=session_id[:8])
        return doc_id

    async def get_active_document(self, session_id: str) -> dict | None:
        db = await get_db()
        row = await db.execute_fetchone(
            "SELECT * FROM documents WHERE session_id = ? AND is_active = 1",
            (session_id,)
        )
        return dict(row) if row else None

    async def get_session_documents(self, session_id: str) -> list[dict]:
        db = await get_db()
        rows = await db.execute_fetchall(
            "SELECT * FROM documents WHERE session_id = ? ORDER BY created_at",
            (session_id,)
        )
        return [dict(r) for r in rows]

    async def switch_document(self, session_id: str, document_id: str) -> bool:
        db = await get_db()
        await db.execute(
            "UPDATE documents SET is_active = 0 WHERE session_id = ?",
            (session_id,)
        )
        result = await db.execute(
            "UPDATE documents SET is_active = 1 WHERE id = ? AND session_id = ?",
            (document_id, session_id)
        )
        await db.commit()
        return result.rowcount > 0

    async def save_version(
        self, document_id: str, html_content: str,
        user_prompt: str = "", edit_summary: str = "",
        model_used: str = "", tokens_used: int = 0
    ) -> int:
        db = await get_db()
        # Get next version number
        row = await db.execute_fetchone(
            "SELECT COALESCE(MAX(version), 0) + 1 as next_ver FROM document_versions WHERE document_id = ?",
            (document_id,)
        )
        version = row["next_ver"]
        await db.execute(
            """INSERT INTO document_versions
               (document_id, version, html_content, user_prompt, edit_summary, model_used, tokens_used)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (document_id, version, html_content, user_prompt, edit_summary, model_used, tokens_used)
        )
        await db.commit()
        logger.info("Version saved", doc_id=document_id[:8], version=version)
        return version

    async def get_latest_html(self, document_id: str) -> str | None:
        db = await get_db()
        row = await db.execute_fetchone(
            "SELECT html_content FROM document_versions WHERE document_id = ? ORDER BY version DESC LIMIT 1",
            (document_id,)
        )
        return row["html_content"] if row else None

    async def get_version(self, document_id: str, version: int) -> dict | None:
        db = await get_db()
        row = await db.execute_fetchone(
            "SELECT * FROM document_versions WHERE document_id = ? AND version = ?",
            (document_id, version)
        )
        return dict(row) if row else None

    async def get_version_history(self, document_id: str) -> list[dict]:
        db = await get_db()
        rows = await db.execute_fetchall(
            """SELECT version, user_prompt, edit_summary, model_used, tokens_used, created_at
               FROM document_versions WHERE document_id = ? ORDER BY version DESC""",
            (document_id,)
        )
        return [dict(r) for r in rows]

    async def add_chat_message(
        self, session_id: str, role: str, content: str,
        document_id: str | None = None, message_type: str = "text"
    ):
        db = await get_db()
        await db.execute(
            """INSERT INTO chat_messages (session_id, document_id, role, content, message_type)
               VALUES (?, ?, ?, ?, ?)""",
            (session_id, document_id, role, content, message_type)
        )
        await db.commit()

    async def get_chat_history(self, session_id: str, limit: int = 50) -> list[dict]:
        db = await get_db()
        rows = await db.execute_fetchall(
            """SELECT * FROM chat_messages WHERE session_id = ?
               ORDER BY created_at DESC LIMIT ?""",
            (session_id, limit)
        )
        return [dict(r) for r in reversed(rows)]

    async def cleanup_expired_sessions(self, timeout_hours: int = 24):
        db = await get_db()
        result = await db.execute(
            "DELETE FROM sessions WHERE last_active < datetime('now', ? || ' hours')",
            (f"-{timeout_hours}",)
        )
        await db.commit()
        if result.rowcount > 0:
            logger.info("Cleaned up expired sessions", count=result.rowcount)


session_service = SessionService()
```

---

## Phase 5: SSE Streaming & Chat API

### Step 5.1: api/chat.py

```python
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
import structlog

logger = structlog.get_logger()
router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    document_id: str | None = None  # If None, uses active document

@router.post("/api/chat/{session_id}")
async def chat(session_id: str, request: ChatRequest):
    """
    Process a chat message and stream the response via SSE.

    The response includes:
    - Token-by-token text streaming (for chat display)
    - Final event with HTML output and metadata
    """
    from app.services.session_service import session_service
    from app.services.router import model_router

    # Ensure session exists
    session_id = await session_service.get_or_create_session(session_id)

    # Save user message
    await session_service.add_chat_message(session_id, "user", request.message)

    async def event_stream():
        try:
            # Route to appropriate model/service
            result = model_router.route(request.message, session_id)

            # Stream response based on result type
            # (Implementation details in Plans 002 and 003)

            # Placeholder: yield events as SSE format
            yield f"data: {json.dumps({'type': 'status', 'content': 'Processing...'})}\n\n"

            # Final event
            yield f"data: {json.dumps({'type': 'done', 'content': 'Complete'})}\n\n"

        except Exception as e:
            logger.error("Chat error", error=str(e), session_id=session_id[:8])
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )
```

### Step 5.2: api/sessions.py

```python
from fastapi import APIRouter
from app.services.session_service import session_service

router = APIRouter()

@router.post("/api/sessions")
async def create_session():
    session_id = await session_service.create_session()
    return {"session_id": session_id}

@router.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    docs = await session_service.get_session_documents(session_id)
    active = await session_service.get_active_document(session_id)
    return {"session_id": session_id, "documents": docs, "active_document": active}

@router.get("/api/sessions/{session_id}/documents")
async def get_documents(session_id: str):
    docs = await session_service.get_session_documents(session_id)
    return {"documents": docs}

@router.post("/api/sessions/{session_id}/documents/{document_id}/switch")
async def switch_document(session_id: str, document_id: str):
    success = await session_service.switch_document(session_id, document_id)
    return {"success": success}

@router.get("/api/documents/{document_id}/versions")
async def get_versions(document_id: str):
    versions = await session_service.get_version_history(document_id)
    return {"versions": versions}

@router.get("/api/documents/{document_id}/versions/{version}")
async def get_version(document_id: str, version: int):
    ver = await session_service.get_version(document_id, version)
    if not ver:
        return {"error": "Version not found"}, 404
    return ver

@router.get("/api/documents/{document_id}/html")
async def get_latest_html(document_id: str):
    html = await session_service.get_latest_html(document_id)
    return {"html": html}

@router.get("/api/sessions/{session_id}/chat")
async def get_chat_history(session_id: str):
    messages = await session_service.get_chat_history(session_id)
    return {"messages": messages}
```

### Step 5.3: api/health.py

```python
from fastapi import APIRouter
from app.database import get_db

router = APIRouter()

@router.get("/api/health")
async def health():
    try:
        db = await get_db()
        await db.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": str(e)}
```

---

## Phase 6: Main Application

### Step 6.1: main.py

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import structlog

from app.config import settings
from app.database import init_db, close_db

structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(
        getattr(structlog, settings.log_level.upper(), structlog.INFO)
    ),
)
logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    logger.info("Application started")
    yield
    # Shutdown
    await close_db()
    logger.info("Application stopped")

app = FastAPI(title="AI HTML Builder", lifespan=lifespan)

# Import and register API routers
from app.api import chat, sessions, health, costs
app.include_router(chat.router)
app.include_router(sessions.router)
app.include_router(health.router)
app.include_router(costs.router)

# Serve static frontend files (built React app)
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

    @app.get("/{path:path}")
    async def serve_spa(path: str):
        """Serve the React SPA for all non-API routes."""
        file_path = static_dir / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(static_dir / "index.html")
```

---

## Phase 7: Utility Modules

### Step 7.1: utils/rate_limiter.py

```python
from collections import defaultdict
import time

class RateLimiter:
    def __init__(self, max_requests: int = 30, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self.requests: dict[str, list[float]] = defaultdict(list)

    def allow(self, key: str) -> bool:
        now = time.time()
        self.requests[key] = [
            t for t in self.requests[key] if now - t < self.window
        ]
        if len(self.requests[key]) >= self.max_requests:
            return False
        self.requests[key].append(now)
        return True

    def remaining(self, key: str) -> int:
        now = time.time()
        self.requests[key] = [
            t for t in self.requests[key] if now - t < self.window
        ]
        return max(0, self.max_requests - len(self.requests[key]))
```

### Step 7.2: utils/html_validator.py

```python
def validate_edit_result(original: str, modified: str) -> tuple[bool, str]:
    """Validate that edits didn't break the document structure."""
    if not modified or not modified.strip():
        return False, "Modified HTML is empty"

    # Check document didn't shrink dramatically
    if len(original) > 100:
        ratio = len(modified) / len(original)
        if ratio < 0.3:
            return False, f"Document shrank to {ratio:.0%} of original size"

    # Check critical structural elements preserved
    for tag in ["</head>", "</body>", "</html>"]:
        if tag in original.lower() and tag not in modified.lower():
            return False, f"Lost {tag} closing tag"

    # Check style and script tags preserved
    original_styles = original.lower().count("<style")
    modified_styles = modified.lower().count("<style")
    if modified_styles < original_styles:
        return False, f"Lost style tags: {original_styles} -> {modified_styles}"

    original_scripts = original.lower().count("<script")
    modified_scripts = modified.lower().count("<script")
    if modified_scripts < original_scripts:
        return False, f"Lost script tags: {original_scripts} -> {modified_scripts}"

    return True, "OK"
```

---

## Build Verification

After completing all phases, run:

```bash
# From backend/ directory
cd backend

# Install dependencies
pip install -r requirements.txt

# Lint check
ruff check app/

# Type check
mypy app/ --ignore-missing-imports

# Run tests
pytest tests/ -v

# Start the server (should start without errors)
uvicorn app.main:app --reload --port 8000

# Test health endpoint
curl http://localhost:8000/api/health
# Expected: {"status": "healthy", "database": "connected"}

# Test session creation
curl -X POST http://localhost:8000/api/sessions
# Expected: {"session_id": "uuid-here"}
```

---

## Testing Scenarios

| Test | Expected Result | Pass/Fail |
|------|----------------|-----------|
| `GET /api/health` returns healthy | `{"status": "healthy", "database": "connected"}` | [ ] |
| `POST /api/sessions` creates session | Returns UUID session_id | [ ] |
| `GET /api/sessions/{id}` returns session data | Returns documents list and active document | [ ] |
| SQLite file created at configured path | `data/app.db` exists after first request | [ ] |
| WAL mode enabled | `PRAGMA journal_mode` returns `wal` | [ ] |
| Server starts without Redis | No Redis error, no fallback needed | [ ] |
| Static files served for non-API routes | `GET /` returns index.html | [ ] |
| Rate limiter blocks after threshold | 31st request in 60s returns 429 | [ ] |

---

## Rollback Plan

If this phase fails:
1. The old backend code is untouched (new code is in new file structure)
2. `git checkout` the old code to restore
3. The old Redis + WebSocket system continues to work as-is

---

## Sign-off Checklist

- [ ] All files created per project structure
- [ ] `ruff check` passes with zero errors
- [ ] `mypy` passes with zero errors
- [ ] `pytest` passes all tests
- [ ] Server starts and health check returns healthy
- [ ] SQLite database created with correct schema
- [ ] Session CRUD operations work via API
- [ ] Version history operations work via API
- [ ] No references to Redis, WebSocket, or JWT anywhere in new code

---

## Implementation Notes (Post-Completion)

> **Status: COMPLETE** - All phases implemented and verified on February 12, 2026.
> 29/29 tests passing, ruff clean, mypy clean on all 14 new files.

### Deviations from Plan

The following changes were made during implementation. Future plans should reference the **actual code** rather than the code listings above when these differ.

#### 1. config.py - Pydantic v2 Configuration

**Plan used:** `class Config:` (deprecated in Pydantic v2)
**Actual:** `model_config = {}` dict with `"extra": "ignore"`. Added `# type: ignore[call-arg]` on `Settings()` instantiation for mypy compatibility with env var loading.

#### 2. aiosqlite API - Cursor Pattern

**Plan used:** `db.execute_fetchone()` and `db.execute_fetchall()` (these methods do NOT exist)
**Actual:** All queries use the correct pattern:
```python
cursor = await db.execute("SELECT ...", params)
row = await cursor.fetchone()  # or fetchall()
```
This affects `session_service.py` throughout. **Critical for Plan 002** - any new queries MUST use the cursor pattern.

#### 3. session_service.py - Ordering & Safety

- Added `id DESC` tiebreaker in `get_chat_history` ORDER BY clause (SQLite `CURRENT_TIMESTAMP` has only second-level precision)
- Added `assert row is not None` after COALESCE queries for mypy safety
- Changed `reversed(rows)` to `reversed(list(rows))` (aiosqlite Row objects need list conversion)
- `cleanup_expired_sessions` returns `int` count of deleted sessions (plan returned None)

#### 4. api/sessions.py - HTTPException

**Plan used:** `return {"error": "..."}, 404` (this does NOT work in FastAPI)
**Actual:** `raise HTTPException(status_code=404, detail="...")`. Future endpoints must use HTTPException.

#### 5. api/chat.py - Simplified Skeleton

**Plan imported:** `from app.services.router import model_router` (module doesn't exist yet)
**Actual:** Removed model_router import. Chat endpoint is a placeholder with SSE skeleton only. Plans 002-003 will implement the actual routing logic.

#### 6. main.py - Structlog Configuration

**Plan used:** `getattr(structlog, settings.log_level.upper(), structlog.INFO)` (structlog has no `INFO` constant)
**Actual:** Uses `logging` module constants via explicit `LOG_LEVELS` dict mapping. Added `# noqa: E402` on late imports. Added `str()` conversion for Path objects passed to StaticFiles/FileResponse.

#### 7. providers/base.py - Enhanced Dataclasses

- `ToolCall.input` uses `field(default_factory=dict)` (mutable default safety)
- `ToolResult.tool_calls` uses `field(default_factory=list)` (mutable default safety)
- Added `ImageResponse` dataclass (plan had `generate_image` returning raw `bytes`)
- `ImageProvider.generate_image()` returns `ImageResponse` not `bytes`

#### 8. providers/anthropic_provider.py - Type Ignores

Added `# type: ignore[arg-type]` and `# type: ignore[union-attr]` comments for Anthropic SDK strict typing. This is standard practice with their SDK and does not affect runtime behavior.

#### 9. Files Not in Original Plan

| File | Purpose |
|------|---------|
| `backend/pyproject.toml` | pytest-asyncio config (`asyncio_mode = "auto"`) |
| `backend/app/services/cost_tracker.py` | Full implementation (plan listed but had no code) |
| `backend/app/api/costs.py` | Full implementation (plan listed but had no code) |
| `backend/app/utils/fuzzy_match.py` | Stub with exact-match only (plan listed but had no code) |
| `backend/tests/test_database.py` | 7 tests for DB init, WAL, schema, indexes |
| `backend/tests/test_session_service.py` | 17 tests for all CRUD operations |
| `backend/tests/test_rate_limiter.py` | 6 tests for rate limiting logic |

#### 10. Additional Cleanup (Beyond Phase 0)

During verification, found and deleted additional dead artifacts:
- `backend/app/services/conversational_llm_service.py.backup` (dead backup)
- `backend/app/services/llm_service.py.backup` (dead backup)
- `backend/app/api/{endpoints}/` (empty stale directory with literal curly braces)
- `backend/app/api/middleware/` (empty directory)
- `backend/app/api/websocket/` (empty directory)
- All `__pycache__/` directories (stale bytecode from v1)

### Key Patterns for Future Plans

1. **aiosqlite queries**: Always use `cursor = await db.execute(); row = await cursor.fetchone()`
2. **Error responses**: Use `raise HTTPException(status_code=N, detail="...")` not tuple returns
3. **Mutable defaults**: Use `field(default_factory=...)` for list/dict dataclass fields
4. **SQLite ordering**: Always add `id` as tiebreaker when ordering by `CURRENT_TIMESTAMP`
5. **Anthropic SDK**: Add `# type: ignore[arg-type]` when passing `list[dict]` for messages/tools
6. **pytest-asyncio**: `asyncio_mode = "auto"` is configured in `pyproject.toml`
7. **Settings instantiation**: `Settings()  # type: ignore[call-arg]` is needed for mypy

---

*Created: February 12, 2026*
*Completed: February 12, 2026*
*Plan: 001 - Backend Foundation*
*Next: Plan 002 - Surgical Editing Engine*
