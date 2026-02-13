# Implementation Plan 016: Transformation Context + Document Ownership Validation

## Status: COMPLETE

**Phase 2 implementation notes (Feb 2026):**
- Deviated from original plan: used **path params** instead of query params for session_id
- All document endpoints moved from `/api/documents/{docId}/*` to `/api/sessions/{sid}/documents/{docId}/*`
- Export endpoint moved from `/api/export/{docId}/{format}` to `/api/sessions/{sid}/documents/{docId}/export/{format}`
- Frontend `getSessionId()` helper reads from sessionStorage — no component prop threading needed
- Added `_require_document_ownership()` helper in sessions.py, lazy import in export.py
- 270 tests total (269 pass + 1 pre-existing failure), ESLint + TypeScript + Vite build clean

**Phase 1 implementation notes (Feb 2026):**
- Added `_strip_base64_for_context()` in `chat.py` — strips base64 payloads but preserves `<img>` tags + alt text
- This was NOT in the original plan but identified during discussion: base64 images are pure noise to Gemini in text form, wasting tokens ($0.16/500KB image) and risking context overflow
- Token estimation fixed to include context HTML size (was off by ~1000x for transformation requests)
- 264 tests total (263 pass + 1 pre-existing failure), ruff/mypy clean on all modified files

---

## STOP - READ THIS FIRST

**DO NOT START** this implementation until:
- Plan 015 (Critical Bug Fixes) is FULLY complete (it is — deployed and live)
- You have read this ENTIRE document end-to-end
- You understand every file path, code change, and verification step

**STRICT RULES — FOLLOW EXACTLY:**
1. Implement phases IN ORDER (1 → 2 → 3). Do NOT skip phases or reorder.
2. Run verification after EACH phase before proceeding to the next.
3. Do NOT create files not listed in this plan. Do NOT delete files not listed in this plan.
4. Do NOT modify the surgical editing engine (`editor.py`, `fuzzy_match.py`) or database schema.
5. Do NOT add dependencies to `package.json` or `requirements.txt`.
6. Every test change must preserve ALL existing passing tests.

**CONTEXT:**

A user created slides about "Change Management", then asked "Turn this into a stakeholder brief". The router correctly classified this as CREATE (transformation intent), but `_handle_create()` sent Gemini ONLY the bare message with zero context about the existing document. Gemini hallucinated "Project Phoenix" content — completely made-up information unrelated to the user's slides.

Additionally, all `/api/documents/{id}/*` endpoints accept bare document IDs without checking session ownership. While UUIDs are unguessable and the server is on private Tailscale, this needs defense-in-depth.

**INVESTIGATION RESULTS:**
- NOT a cross-session data leak — all documents belong to the correct session
- Content is LLM hallucination caused by missing context, not data mixing
- `DocumentCreator.stream_create()` already accepts `template_content` param — it's just never wired up

**OPENROUTER ASSESSMENT:** Researched and rejected. No Google SDK compatibility (rewrite needed), 5.5% cost markup, +50-150ms latency. Keep direct Anthropic + Google API keys.

**DEPENDENCIES:**
- Plans 001-015 (all complete)

---

## Phase 1: Fix Transformation Context (Bug 1)

The critical fix. When route = "create" and existing HTML exists, pass it to the creator as context.

### Step 1.1: Update `_build_messages` wording in creator.py

**File:** `backend/app/services/creator.py`

**Current code (lines 135-158):**
```python
def _build_messages(
    self, user_message: str, template: str | None
) -> list[dict]:
    messages: list[dict] = []
    if template:
        messages.append(
            {
                "role": "user",
                "content": (
                    "Use this template as a starting point:\n\n"
                    + template
                ),
            }
        )
        messages.append(
            {
                "role": "assistant",
                "content": (
                    "I'll use this template as inspiration for the design."
                ),
            }
        )
    messages.append({"role": "user", "content": user_message})
    return messages
```

**Change to:**
```python
def _build_messages(
    self, user_message: str, template: str | None
) -> list[dict]:
    messages: list[dict] = []
    if template:
        messages.append(
            {
                "role": "user",
                "content": (
                    "Here is the existing document to use as context "
                    "and source material:\n\n"
                    + template
                ),
            }
        )
        messages.append(
            {
                "role": "assistant",
                "content": (
                    "I have the existing document. I'll use its content "
                    "as source material for the new document."
                ),
            }
        )
    messages.append({"role": "user", "content": user_message})
    return messages
```

**Why:** The old wording ("template as inspiration") told the LLM to use the HTML as a design reference. The new wording ("source material") tells the LLM the HTML contains the user's actual content that must be preserved in the new format.

### Step 1.2: Wire `current_html` into `_handle_create`

**File:** `backend/app/api/chat.py`

**Change 1 — function signature (line 105):**

Current:
```python
async def _handle_create(
    session_service: Any,
    request: ChatRequest,
    session_id: str,
) -> AsyncIterator[dict]:
```

Change to:
```python
async def _handle_create(
    session_service: Any,
    request: ChatRequest,
    session_id: str,
    current_html: str | None = None,
) -> AsyncIterator[dict]:
```

**Change 2 — pass to stream_create (line 130):**

Current:
```python
    async for chunk in creator.stream_create(request.message):
```

Change to:
```python
    async for chunk in creator.stream_create(request.message, template_content=current_html):
```

**Change 3 — call site (lines 322-325):**

Current:
```python
            elif route == "create":
                handler = _handle_create(
                    session_service, request, session_id,
                )
```

Change to:
```python
            elif route == "create":
                handler = _handle_create(
                    session_service, request, session_id,
                    current_html=current_html,
                )
```

### Step 1.3: Update creator test assertion

**File:** `backend/tests/test_creator.py`

The test `test_create_with_template_context` (line 80) asserts:
```python
assert "template" in messages[0]["content"].lower()
```

**Change to:**
```python
assert "existing document" in messages[0]["content"].lower()
```

### Step 1.4: Add transformation context tests

**File:** `backend/tests/test_chat_create_image.py`

Add these tests AFTER the existing `test_create_route_fallback_to_claude` test (after line 141):

```python
@pytest.mark.asyncio
async def test_create_route_with_existing_html_passes_context(tmp_path):
    """When route=create and HTML exists (transformation), current_html is passed to creator."""
    from app.database import init_db, close_db
    from app.config import settings
    from app.services.session_service import session_service

    db_path = tmp_path / "test.db"
    with patch.object(settings, "database_path", str(db_path)):
        await init_db()

        try:
            # Create session with existing document
            sid = await session_service.create_session()
            doc_id = await session_service.create_document(sid, "Slides")
            await session_service.save_version(doc_id, SAMPLE_HTML)

            from app.api.chat import chat, ChatRequest

            mock_gemini = MagicMock()
            mock_gemini.model = "gemini-2.5-pro"

            captured_calls: list = []

            async def fake_stream(msg, template_content=None):
                captured_calls.append({"msg": msg, "template_content": template_content})
                yield SAMPLE_HTML

            mock_creator = MagicMock()
            mock_creator.stream_create = fake_stream

            with patch("app.providers.gemini_provider.GeminiProvider", return_value=mock_gemini), \
                 patch("app.providers.anthropic_provider.AnthropicProvider", return_value=MagicMock()), \
                 patch("app.services.creator.DocumentCreator", return_value=mock_creator), \
                 patch("app.services.creator.extract_html", return_value=SAMPLE_HTML), \
                 patch("app.services.router.classify_request", new_callable=AsyncMock, return_value="create"):

                request = ChatRequest(message="Turn this into a stakeholder brief")
                response = await chat(sid, request)

                body = ""
                async for chunk in response.body_iterator:
                    body += chunk

            # Verify template_content was passed (existing HTML as context)
            assert len(captured_calls) == 1
            assert captured_calls[0]["template_content"] is not None
            assert "<!DOCTYPE html>" in captured_calls[0]["template_content"]

        finally:
            await close_db()


@pytest.mark.asyncio
async def test_create_route_without_html_no_context(tmp_path):
    """When route=create and no HTML exists (fresh creation), template_content is None."""
    from app.database import init_db, close_db
    from app.config import settings

    db_path = tmp_path / "test.db"
    with patch.object(settings, "database_path", str(db_path)):
        await init_db()

        try:
            from app.api.chat import chat, ChatRequest

            mock_gemini = MagicMock()
            mock_gemini.model = "gemini-2.5-pro"

            captured_calls: list = []

            async def fake_stream(msg, template_content=None):
                captured_calls.append({"msg": msg, "template_content": template_content})
                yield SAMPLE_HTML

            mock_creator = MagicMock()
            mock_creator.stream_create = fake_stream

            with patch("app.providers.gemini_provider.GeminiProvider", return_value=mock_gemini), \
                 patch("app.providers.anthropic_provider.AnthropicProvider", return_value=MagicMock()), \
                 patch("app.services.creator.DocumentCreator", return_value=mock_creator), \
                 patch("app.services.creator.extract_html", return_value=SAMPLE_HTML):

                request = ChatRequest(message="Create a landing page")
                response = await chat("test-session-no-context", request)

                body = ""
                async for chunk in response.body_iterator:
                    body += chunk

            # Verify template_content is None (no existing doc)
            assert len(captured_calls) == 1
            assert captured_calls[0]["template_content"] is None

        finally:
            await close_db()
```

### Phase 1 Verification

```bash
cd backend && python -m pytest tests/test_creator.py tests/test_chat_create_image.py -v
```

All tests must pass (existing + 2 new). Zero failures before proceeding.

---

## Phase 2: Document Ownership Validation (Bug 2)

Add `session_id` as a required query parameter to all document-level endpoints. Validate that the document belongs to the session.

### Step 2.1: Add `verify_document_ownership()` to session service

**File:** `backend/app/services/session_service.py`

Add this method to the `SessionService` class, after `get_session_documents()` (after line 75):

```python
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
```

### Step 2.2: Update sessions.py endpoints

**File:** `backend/app/api/sessions.py`

**Change 1 — Add imports (line 1):**

Current:
```python
from fastapi import APIRouter, HTTPException
```

Change to:
```python
from fastapi import APIRouter, HTTPException, Query
```

**Change 2 — Add ownership helper (after imports, before `router = APIRouter()`):**

```python
async def _require_document_ownership(
    document_id: str, session_id: str
) -> None:
    """Raise 403 if the document doesn't belong to the session."""
    owns = await session_service.verify_document_ownership(
        document_id, session_id
    )
    if not owns:
        raise HTTPException(
            status_code=403,
            detail="Document does not belong to this session",
        )
```

**Change 3 — Update all 6 document endpoints to require `session_id`:**

Replace `get_versions` (lines 40-43):
```python
@router.get("/api/documents/{document_id}/versions")
async def get_versions(
    document_id: str,
    session_id: str = Query(..., description="Session ID for ownership check"),
):
    await _require_document_ownership(document_id, session_id)
    versions = await session_service.get_version_history(document_id)
    return {"versions": versions}
```

Replace `get_version` (lines 46-51):
```python
@router.get("/api/documents/{document_id}/versions/{version}")
async def get_version(
    document_id: str,
    version: int,
    session_id: str = Query(..., description="Session ID for ownership check"),
):
    await _require_document_ownership(document_id, session_id)
    ver = await session_service.get_version(document_id, version)
    if not ver:
        raise HTTPException(status_code=404, detail="Version not found")
    return ver
```

Replace `get_latest_html` (lines 54-57):
```python
@router.get("/api/documents/{document_id}/html")
async def get_latest_html(
    document_id: str,
    session_id: str = Query(..., description="Session ID for ownership check"),
):
    await _require_document_ownership(document_id, session_id)
    html = await session_service.get_latest_html(document_id)
    return {"html": html}
```

Replace `restore_version` (lines 60-66):
```python
@router.post("/api/documents/{document_id}/versions/{version}/restore")
async def restore_version(
    document_id: str,
    version: int,
    session_id: str = Query(..., description="Session ID for ownership check"),
):
    await _require_document_ownership(document_id, session_id)
    try:
        new_version = await session_service.restore_version(document_id, version)
        return {"version": new_version}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
```

Replace `rename_document` (lines 103-108):
```python
@router.patch("/api/documents/{document_id}")
async def rename_document(
    document_id: str,
    body: RenameRequest,
    session_id: str = Query(..., description="Session ID for ownership check"),
):
    await _require_document_ownership(document_id, session_id)
    success = await session_service.rename_document(document_id, body.title)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"success": True}
```

Replace `save_manual_edit` (lines 122-128):
```python
@router.post("/api/documents/{document_id}/manual-edit")
async def save_manual_edit(
    document_id: str,
    body: ManualEditRequest,
    session_id: str = Query(..., description="Session ID for ownership check"),
):
    await _require_document_ownership(document_id, session_id)
    version = await session_service.save_manual_edit(
        document_id, body.html_content
    )
    return {"version": version, "success": True}
```

### Step 2.3: Update export.py endpoint

**File:** `backend/app/api/export.py`

**Change 1 — Add session_id parameter to `export()` (after line 36, before `) -> StreamingResponse:`):**

Add `session_id` as the first query parameter (after `format_key` path param):

```python
@router.post("/api/export/{document_id}/{format_key}")
async def export(
    document_id: str,
    format_key: str,
    session_id: str = Query(..., description="Session ID for ownership check"),
    version: int | None = Query(None, description="Document version (None = latest)"),
    # ... rest of params unchanged
```

**Change 2 — Add ownership check at the top of the function body (before `try:` on line 39):**

```python
    from app.services.session_service import session_service
    owns = await session_service.verify_document_ownership(document_id, session_id)
    if not owns:
        raise HTTPException(status_code=403, detail="Document does not belong to this session")
```

### Step 2.4: Update frontend API service

**File:** `frontend/src/services/api.ts`

**Change 1 — Add `getSessionId()` helper (after line 11, before `export const api`):**

```typescript
const SESSION_KEY = 'ai-html-builder-session-id';

function getSessionId(): string {
  const sid = sessionStorage.getItem(SESSION_KEY);
  if (!sid) throw new Error('No active session');
  return sid;
}
```

**Change 2 — Update `getDocumentHtml` (lines 37-39):**

Current:
```typescript
  getDocumentHtml(docId: string): Promise<{ html: string }> {
    return json(`/api/documents/${docId}/html`);
  },
```

Change to:
```typescript
  getDocumentHtml(docId: string): Promise<{ html: string }> {
    return json(`/api/documents/${docId}/html?session_id=${getSessionId()}`);
  },
```

**Change 3 — Update `getVersions` (lines 42-44):**

Current:
```typescript
  getVersions(docId: string): Promise<{ versions: Version[] }> {
    return json(`/api/documents/${docId}/versions`);
  },
```

Change to:
```typescript
  getVersions(docId: string): Promise<{ versions: Version[] }> {
    return json(`/api/documents/${docId}/versions?session_id=${getSessionId()}`);
  },
```

**Change 4 — Update `getVersion` (lines 47-49):**

Current:
```typescript
  getVersion(docId: string, version: number): Promise<VersionDetail> {
    return json(`/api/documents/${docId}/versions/${version}`);
  },
```

Change to:
```typescript
  getVersion(docId: string, version: number): Promise<VersionDetail> {
    return json(`/api/documents/${docId}/versions/${version}?session_id=${getSessionId()}`);
  },
```

**Change 5 — Update `restoreVersion` (lines 102-106):**

Current:
```typescript
  restoreVersion(docId: string, version: number): Promise<{ version: number }> {
    return json(`/api/documents/${docId}/versions/${version}/restore`, {
      method: 'POST',
    });
  },
```

Change to:
```typescript
  restoreVersion(docId: string, version: number): Promise<{ version: number }> {
    return json(`/api/documents/${docId}/versions/${version}/restore?session_id=${getSessionId()}`, {
      method: 'POST',
    });
  },
```

**Change 6 — Update `renameDocument` (lines 109-115):**

Current:
```typescript
  renameDocument(docId: string, title: string): Promise<{ success: boolean }> {
    return json(`/api/documents/${docId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title }),
    });
  },
```

Change to:
```typescript
  renameDocument(docId: string, title: string): Promise<{ success: boolean }> {
    return json(`/api/documents/${docId}?session_id=${getSessionId()}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title }),
    });
  },
```

**Change 7 — Update `saveManualEdit` (lines 125-131):**

Current:
```typescript
  saveManualEdit(documentId: string, htmlContent: string): Promise<{ version: number; success: boolean }> {
    return json(`/api/documents/${documentId}/manual-edit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ html_content: htmlContent }),
    });
  },
```

Change to:
```typescript
  saveManualEdit(documentId: string, htmlContent: string): Promise<{ version: number; success: boolean }> {
    return json(`/api/documents/${documentId}/manual-edit?session_id=${getSessionId()}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ html_content: htmlContent }),
    });
  },
```

**Change 8 — Update `exportDocument` (lines 134-167):**

Current (line 139-144):
```typescript
    const params = new URLSearchParams();
    if (title) params.set('title', title);

    const res = await fetch(
      `${BASE}/api/export/${documentId}/${format}?${params.toString()}`,
      { method: 'POST' },
    );
```

Change to:
```typescript
    const params = new URLSearchParams();
    params.set('session_id', getSessionId());
    if (title) params.set('title', title);

    const res = await fetch(
      `${BASE}/api/export/${documentId}/${format}?${params.toString()}`,
      { method: 'POST' },
    );
```

### Phase 2 Verification

```bash
cd backend && python -m pytest tests/test_document_management.py tests/test_export_api.py tests/test_session_service.py -v
```

**IMPORTANT:** Existing tests in `test_document_management.py` and `test_export_api.py` will FAIL because endpoints now require `session_id` query parameter. These are fixed in Phase 3.

---

## Phase 3: Update Tests

### Step 3.1: Add ownership tests to `test_session_service.py`

**File:** `backend/tests/test_session_service.py`

Add after the last test (after line 206):

```python
@pytest.mark.asyncio
async def test_verify_ownership_correct_session(db_and_service):
    service = db_and_service
    sid = await service.create_session()
    doc_id = await service.create_document(sid, "Test")
    assert await service.verify_document_ownership(doc_id, sid) is True


@pytest.mark.asyncio
async def test_verify_ownership_wrong_session(db_and_service):
    service = db_and_service
    sid1 = await service.create_session()
    sid2 = await service.create_session()
    doc_id = await service.create_document(sid1, "Test")
    assert await service.verify_document_ownership(doc_id, sid2) is False


@pytest.mark.asyncio
async def test_verify_ownership_nonexistent_doc(db_and_service):
    service = db_and_service
    sid = await service.create_session()
    assert await service.verify_document_ownership("nonexistent", sid) is False
```

### Step 3.2: Update `test_document_management.py`

**File:** `backend/tests/test_document_management.py`

**Change 1 — Update mock fixture (lines 18-22) to include `verify_document_ownership`:**

Current:
```python
@pytest.fixture()
def mock_session_service():
    mock_svc = AsyncMock()
    with patch("app.api.sessions.session_service", mock_svc):
        yield mock_svc
```

Change to:
```python
@pytest.fixture()
def mock_session_service():
    mock_svc = AsyncMock()
    mock_svc.verify_document_ownership.return_value = True
    with patch("app.api.sessions.session_service", mock_svc):
        yield mock_svc
```

**Change 2 — Update all API calls in rename/delete tests to pass `session_id`:**

In `test_rename_document_success` (line 39-41):
```python
    resp = client.patch(
        "/api/documents/doc-123",
        json={"title": "New Title"},
        params={"session_id": "sess-1"},
    )
```

In `test_rename_document_not_found` (line 54-56):
```python
    resp = client.patch(
        "/api/documents/doc-999",
        json={"title": "New Title"},
        params={"session_id": "sess-1"},
    )
```

In `test_rename_document_empty_title_rejected` (line 64-66):
```python
    resp = client.patch(
        "/api/documents/doc-123",
        json={"title": ""},
        params={"session_id": "sess-1"},
    )
```

**Change 3 — Add 403 tests (after `test_rename_document_empty_title_rejected`):**

```python
def test_rename_document_wrong_session(
    client: TestClient, mock_session_service: AsyncMock
) -> None:
    mock_session_service.verify_document_ownership.return_value = False
    resp = client.patch(
        "/api/documents/doc-123",
        json={"title": "New Title"},
        params={"session_id": "wrong-session"},
    )
    assert resp.status_code == 403


def test_get_html_wrong_session(
    client: TestClient, mock_session_service: AsyncMock
) -> None:
    mock_session_service.verify_document_ownership.return_value = False
    resp = client.get(
        "/api/documents/doc-123/html",
        params={"session_id": "wrong-session"},
    )
    assert resp.status_code == 403


def test_get_html_missing_session_returns_422(
    client: TestClient, mock_session_service: AsyncMock
) -> None:
    """Missing required session_id query param returns 422."""
    resp = client.get("/api/documents/doc-123/html")
    assert resp.status_code == 422
```

### Step 3.3: Update `test_export_api.py`

**File:** `backend/tests/test_export_api.py`

**Change 1 — Update mock fixture to include ownership mock:**

Add after line 26 (inside `mock_export_fns` fixture, before `yield`):

Actually, export.py does a lazy import of `session_service`. We need to also mock it. Update the fixture:

Current (lines 13-26):
```python
@pytest.fixture
def mock_export_fns():
    """Patch export functions at the API module level."""
    with (
        patch("app.api.export.export_document", new_callable=AsyncMock) as mock_export,
        patch("app.api.export.list_available_formats") as mock_formats,
    ):
        mock_formats.return_value = {
            "html": "HTML",
            "pdf": "PDF",
            "pptx": "PowerPoint",
            "png": "PNG",
        }
        yield mock_export, mock_formats
```

Change to:
```python
@pytest.fixture
def mock_export_fns():
    """Patch export functions at the API module level."""
    mock_svc = AsyncMock()
    mock_svc.verify_document_ownership.return_value = True
    with (
        patch("app.api.export.export_document", new_callable=AsyncMock) as mock_export,
        patch("app.api.export.list_available_formats") as mock_formats,
        patch("app.api.export.session_service", mock_svc),
    ):
        mock_formats.return_value = {
            "html": "HTML",
            "pdf": "PDF",
            "pptx": "PowerPoint",
            "png": "PNG",
        }
        yield mock_export, mock_formats
```

**WAIT — export.py uses a lazy import (`from app.services.session_service import session_service` inside the function body). We need to patch at the source module instead.**

Change to:
```python
@pytest.fixture
def mock_export_fns():
    """Patch export functions at the API module level."""
    mock_svc = AsyncMock()
    mock_svc.verify_document_ownership.return_value = True
    with (
        patch("app.api.export.export_document", new_callable=AsyncMock) as mock_export,
        patch("app.api.export.list_available_formats") as mock_formats,
        patch("app.services.session_service.session_service", mock_svc),
    ):
        mock_formats.return_value = {
            "html": "HTML",
            "pdf": "PDF",
            "pptx": "PowerPoint",
            "png": "PNG",
        }
        yield mock_export, mock_formats
```

**NOTE:** The exact patch target depends on how the import is written in `export.py`. After Step 2.3, the import in export.py is `from app.services.session_service import session_service`. So the lazy import resolves at call time. The safest approach is to patch it where it gets imported inside the function. Since the function body has a lazy import, we must patch at the session_service module level. If tests fail, try `patch("app.services.session_service.SessionService.verify_document_ownership", new_callable=AsyncMock, return_value=True)` instead.

**Change 2 — Add `session_id` to all export test calls:**

In `test_export_html_returns_200` (line 63):
```python
    resp = client.post("/api/export/doc-123/html", params={"title": "test", "session_id": "sess-1"})
```

In `test_export_html_with_version` (line 72):
```python
    resp = client.post("/api/export/doc-123/html", params={"version": 2, "session_id": "sess-1"})
```

In `test_export_pdf_returns_200` (line 85):
```python
    resp = client.post("/api/export/doc-123/pdf", params={"session_id": "sess-1"})
```

In `test_export_returns_400_on_export_error` (line 97):
```python
    resp = client.post("/api/export/doc-123/html", params={"session_id": "sess-1"})
```

In `test_export_returns_500_on_unexpected_error` (line 105):
```python
    resp = client.post("/api/export/doc-123/html", params={"session_id": "sess-1"})
```

In `test_content_disposition_has_filename` (line 132):
```python
    resp = client.post("/api/export/doc-123/html", params={"title": "myfile", "session_id": "sess-1"})
```

### Phase 3 Verification

```bash
cd backend && python -m pytest -v
```

**ALL tests must pass.** Check the count matches expected (previous count + 5 new tests).

Then run:
```bash
cd backend && ruff check . && mypy .
cd frontend && npm run lint && npm run build
```

All clean, zero errors.

---

## Files Modified (Summary)

| File | Change Type | Phase |
|------|-----------|-------|
| `backend/app/services/creator.py` | Edit `_build_messages` wording | 1 |
| `backend/app/api/chat.py` | Add `current_html` param to `_handle_create` | 1 |
| `backend/app/services/session_service.py` | Add `verify_document_ownership()` | 2 |
| `backend/app/api/sessions.py` | Add ownership helper + `session_id` to 6 endpoints | 2 |
| `backend/app/api/export.py` | Add `session_id` + ownership check to export | 2 |
| `frontend/src/services/api.ts` | Add `getSessionId()` + pass `session_id` to 7 methods | 2 |
| `backend/tests/test_creator.py` | Update assertion wording | 3 |
| `backend/tests/test_chat_create_image.py` | Add 2 transformation context tests | 3 |
| `backend/tests/test_session_service.py` | Add 3 ownership verification tests | 3 |
| `backend/tests/test_document_management.py` | Update for `session_id` param + add 3 tests | 3 |
| `backend/tests/test_export_api.py` | Update for `session_id` param | 3 |

**Total:** 11 files modified, 0 files created, 0 files deleted.

---

## Final Verification

1. `cd backend && python -m pytest -v` — all tests pass
2. `cd backend && ruff check . && mypy .` — clean
3. `cd frontend && npm run lint && npm run build` — clean
4. **Live test after deploy:** Create slides → "Turn this into a stakeholder brief" → verify the brief contains the SAME content as the slides (not hallucinated content)
5. **Live test after deploy:** Open browser dev tools → `GET /api/documents/{doc_id}/html` without `session_id` → expect 422. With wrong `session_id` → expect 403

---

## Post-Implementation: Update CLAUDE.md

Add to the plan table:
```
| 016 | Transformation Context + Ownership Validation | COMPLETE |
```

Add to Known Issues → Resolved Issues:
```
- ~~"Turn this into X" creates document with hallucinated content~~ — **RESOLVED in Plan 016** (existing HTML passed as context to creator)
- ~~Document endpoints accessible without session validation~~ — **RESOLVED in Plan 016** (session_id query param required)
```
