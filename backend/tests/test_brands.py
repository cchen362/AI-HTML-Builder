"""Tests for brand profile CRUD and LLM injection."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from httpx import ASGITransport, AsyncClient
from app.main import app
from app.api.chat import _resolve_brand_spec


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
async def auth_db(tmp_path):
    """Initialize a temporary auth database for brand tests."""
    from app.auth_database import init_auth_db, close_auth_db, get_auth_db

    db_path = tmp_path / "auth.db"
    with patch("app.auth_database.settings", MagicMock(auth_database_path=str(db_path))):
        await init_auth_db()
        yield await get_auth_db()
        await close_auth_db()


@pytest.fixture
async def client(auth_db):
    """Async test client with auth DB ready."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# CRUD Tests
# ---------------------------------------------------------------------------

async def test_list_brands_empty(client):
    resp = await client.get("/api/brands")
    assert resp.status_code == 200
    assert resp.json() == {"brands": []}


async def test_create_brand(client):
    resp = await client.post("/api/brands", json={
        "name": "Acme Corp",
        "spec_text": "Primary: #006FCF, Dark: #003478",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Acme Corp"
    assert data["accent_color"] == "#006FCF"
    assert len(data["id"]) == 12


async def test_create_brand_no_hex(client):
    resp = await client.post("/api/brands", json={
        "name": "Simple",
        "spec_text": "Use blue and white colors, clean sans-serif fonts",
    })
    assert resp.status_code == 201
    assert resp.json()["accent_color"] == "#64748B"  # default slate


async def test_create_and_list(client):
    await client.post("/api/brands", json={
        "name": "Brand A",
        "spec_text": "Colors: #FF0000",
    })
    await client.post("/api/brands", json={
        "name": "Brand B",
        "spec_text": "Colors: #00FF00",
    })

    resp = await client.get("/api/brands")
    brands = resp.json()["brands"]
    assert len(brands) == 2
    assert brands[0]["name"] == "Brand A"
    assert brands[1]["name"] == "Brand B"


async def test_list_excludes_spec_text(client):
    await client.post("/api/brands", json={
        "name": "Test",
        "spec_text": "This should not appear in list",
    })
    resp = await client.get("/api/brands")
    brand = resp.json()["brands"][0]
    assert "spec_text" not in brand
    assert set(brand.keys()) == {"id", "name", "accent_color"}


async def test_delete_brand(client):
    create_resp = await client.post("/api/brands", json={
        "name": "Temporary",
        "spec_text": "Will be deleted",
    })
    brand_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/brands/{brand_id}")
    assert del_resp.status_code == 200
    assert del_resp.json() == {"deleted": True}

    list_resp = await client.get("/api/brands")
    assert len(list_resp.json()["brands"]) == 0


async def test_delete_nonexistent(client):
    resp = await client.delete("/api/brands/doesnotexist")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Validation Tests
# ---------------------------------------------------------------------------

async def test_create_empty_name(client):
    resp = await client.post("/api/brands", json={
        "name": "  ",
        "spec_text": "Some spec",
    })
    assert resp.status_code == 400
    assert "name" in resp.json()["detail"].lower()


async def test_create_empty_spec(client):
    resp = await client.post("/api/brands", json={
        "name": "Valid Name",
        "spec_text": "   ",
    })
    assert resp.status_code == 400
    assert "spec" in resp.json()["detail"].lower()


async def test_create_name_too_long(client):
    resp = await client.post("/api/brands", json={
        "name": "A" * 51,
        "spec_text": "Some spec",
    })
    assert resp.status_code == 400
    assert "50" in resp.json()["detail"]


async def test_create_spec_too_long(client):
    resp = await client.post("/api/brands", json={
        "name": "Test",
        "spec_text": "A" * 5001,
    })
    assert resp.status_code == 400
    assert "5000" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Auth Tests
# ---------------------------------------------------------------------------

async def test_non_admin_can_list(auth_db):
    """Non-admin users can list brands (GET /api/brands)."""
    from app.auth_middleware import get_current_user

    non_admin = {"id": "user-2", "username": "regular", "display_name": "Regular", "is_admin": False}

    async def _non_admin():
        return non_admin

    app.dependency_overrides[get_current_user] = _non_admin

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/api/brands")
        assert resp.status_code == 200
    finally:
        # Restore conftest override
        async def _admin():
            return {"id": "test-user-id", "username": "testuser", "display_name": "Test User", "is_admin": True}
        app.dependency_overrides[get_current_user] = _admin


async def test_non_admin_cannot_create(auth_db):
    """Non-admin users cannot create brands (POST /api/brands)."""
    from app.auth_middleware import get_current_user, require_admin

    non_admin = {"id": "user-2", "username": "regular", "display_name": "Regular", "is_admin": False}

    async def _non_admin():
        return non_admin

    app.dependency_overrides[get_current_user] = _non_admin
    app.dependency_overrides[require_admin] = require_admin  # Use REAL require_admin

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/api/brands", json={
                "name": "Forbidden",
                "spec_text": "Should fail",
            })
        assert resp.status_code == 403
    finally:
        async def _admin():
            return {"id": "test-user-id", "username": "testuser", "display_name": "Test User", "is_admin": True}
        app.dependency_overrides[get_current_user] = _admin
        app.dependency_overrides[require_admin] = _admin


# ---------------------------------------------------------------------------
# Brand Resolution Tests
# ---------------------------------------------------------------------------

async def test_resolve_brand_spec_found(auth_db):
    """_resolve_brand_spec returns spec text for valid brand ID."""
    from app.auth_database import get_auth_db

    db = await get_auth_db()
    await db.execute(
        "INSERT INTO brand_profiles (id, name, accent_color, spec_text) VALUES (?, ?, ?, ?)",
        ("test123", "Test", "#FF0000", "Primary: #FF0000\nFont: Helvetica"),
    )
    await db.commit()

    result = await _resolve_brand_spec("test123")
    assert result == "Primary: #FF0000\nFont: Helvetica"


async def test_resolve_brand_spec_missing(auth_db):
    """_resolve_brand_spec returns None for unknown brand ID."""
    result = await _resolve_brand_spec("nonexistent")
    assert result is None


async def test_resolve_brand_spec_none():
    """_resolve_brand_spec returns None when brand_id is None."""
    result = await _resolve_brand_spec(None)
    assert result is None


# ---------------------------------------------------------------------------
# LLM Injection Tests
# ---------------------------------------------------------------------------

async def test_creator_brand_injection():
    """Creator appends brand guidelines to system prompt when brand_spec provided."""
    from app.services.creator import DocumentCreator, CREATION_SYSTEM_PROMPT

    mock_provider = MagicMock()

    captured_system = []

    async def fake_stream(system, messages, **kwargs):
        captured_system.append(system)
        yield "<!DOCTYPE html><html><body>test</body></html>"

    mock_provider.stream = fake_stream
    creator = DocumentCreator(mock_provider)

    async for _ in creator.stream_create("test", brand_spec="Colors: #FF0000"):
        pass

    assert len(captured_system) == 1
    assert "BRAND GUIDELINES" in captured_system[0]
    assert "Colors: #FF0000" in captured_system[0]
    assert captured_system[0].startswith(CREATION_SYSTEM_PROMPT)


async def test_creator_no_brand():
    """Creator uses default system prompt when no brand_spec."""
    from app.services.creator import DocumentCreator, CREATION_SYSTEM_PROMPT

    mock_provider = MagicMock()

    captured_system = []

    async def fake_stream(system, messages, **kwargs):
        captured_system.append(system)
        yield "<!DOCTYPE html><html><body>test</body></html>"

    mock_provider.stream = fake_stream
    creator = DocumentCreator(mock_provider)

    async for _ in creator.stream_create("test"):
        pass

    assert captured_system[0] == CREATION_SYSTEM_PROMPT


async def test_editor_brand_injection():
    """Editor appends brand block to system prompt when brand_spec provided."""
    from app.services.editor import SurgicalEditor, EDIT_SYSTEM_PROMPT

    mock_provider = MagicMock()
    mock_provider.generate_with_tools = AsyncMock(return_value=MagicMock(
        tool_calls=[],
        text="No changes needed",
        input_tokens=100,
        output_tokens=50,
        model="test-model",
    ))

    editor = SurgicalEditor(mock_provider)
    await editor.edit("<html><body>test</body></html>", "make it blue", brand_spec="Primary: #003478")

    call_kwargs = mock_provider.generate_with_tools.call_args
    system_blocks = call_kwargs.kwargs.get("system") or call_kwargs[1].get("system")

    assert len(system_blocks) == 2  # Original + brand block
    assert system_blocks[0] == EDIT_SYSTEM_PROMPT[0]
    assert "BRAND GUIDELINES" in system_blocks[1]["text"]
    assert "Primary: #003478" in system_blocks[1]["text"]


async def test_editor_no_brand():
    """Editor uses default system prompt when no brand_spec."""
    from app.services.editor import SurgicalEditor, EDIT_SYSTEM_PROMPT

    mock_provider = MagicMock()
    mock_provider.generate_with_tools = AsyncMock(return_value=MagicMock(
        tool_calls=[],
        text="No changes needed",
        input_tokens=100,
        output_tokens=50,
        model="test-model",
    ))

    editor = SurgicalEditor(mock_provider)
    await editor.edit("<html><body>test</body></html>", "make it blue")

    call_kwargs = mock_provider.generate_with_tools.call_args
    system_blocks = call_kwargs.kwargs.get("system") or call_kwargs[1].get("system")

    assert len(system_blocks) == 1
    assert system_blocks == EDIT_SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# ChatRequest with brand_id
# ---------------------------------------------------------------------------

async def test_chat_request_accepts_brand_id():
    """ChatRequest model accepts brand_id field."""
    from app.api.chat import ChatRequest

    req = ChatRequest(message="test", brand_id="abc123")
    assert req.brand_id == "abc123"

    req_none = ChatRequest(message="test")
    assert req_none.brand_id is None
