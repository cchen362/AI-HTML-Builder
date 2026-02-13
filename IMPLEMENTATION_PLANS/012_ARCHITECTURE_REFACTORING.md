# Implementation Plan 012: Architecture Refactoring

## Status: PENDING

---

## STOP - READ THIS FIRST

**DO NOT START** this implementation until:
- Plans 001-011 are FULLY complete (they are)
- You have read this ENTIRE document
- You understand this plan makes **zero behavior changes** — only cleanup, consolidation, and dead code removal

**DESTRUCTIVE ACTIONS PROHIBITED:**
- Do NOT delete any code that has active callers
- Do NOT change API behavior or response formats
- Do NOT modify the surgical editing engine (`editor.py`, `fuzzy_match.py`)
- Do NOT modify any test that tests real behavior (only delete tests for dead code)
- Do NOT change database schema

**WHY THIS REFACTORING IS NEEDED:**
Two independent review agents (UX + architecture) audited the entire codebase after 12 implementation plans. Findings:
- ~310 lines of dead code (rate_limiter, sse-starlette, unused types, deprecated interfaces)
- Export pipeline is 939 lines across 8 files for 4 export formats (over-abstracted registry pattern)
- Templates stored in 3 redundant places (backend JSON, backend API, frontend TS)
- `chat.py` is a 302-line monolith with 3 independent paths crammed into one generator
- Dev dependencies (ruff, mypy, pytest) shipped in production Docker image
- React Router loaded (45KB) for a single-route app

**DEPENDENCIES:**
- Plans 001-011 (all complete)
- No external dependencies

**ESTIMATED EFFORT:** 1-2 days

---

## Phase 1: Dead Code Deletion

### 1a. Backend — Delete rate_limiter module

**Files to DELETE entirely:**
- `backend/app/utils/rate_limiter.py` (27 lines)
- `backend/tests/test_rate_limiter.py` (51 lines)

**Evidence:** Zero imports in any backend file. Only imported by its own test file.

### 1b. Backend — Remove unused config fields

**File:** `backend/app/config.py`

Remove these 3 fields (0 callers each):
```python
rate_limit_requests: int = 30    # DELETE
rate_limit_window: int = 60      # DELETE
session_timeout_hours: int = 24  # DELETE
```

### 1c. Backend — Remove dead session cleanup method

**File:** `backend/app/services/session_service.py`

Delete the `cleanup_expired_sessions()` method — never called from any endpoint, scheduled task, or lifespan hook. Sessions accumulate but this is fine for 2-5 users; cleanup can be re-added when Plan 008 deploys.

### 1d. Backend — Remove sse-starlette dependency

**File:** `backend/requirements.txt`

Remove: `sse-starlette>=2.0.0`

**Evidence:** Zero imports anywhere. SSE is implemented manually via `_sse()` helper in `chat.py` with FastAPI's native `StreamingResponse`.

### 1e. Frontend — Remove deprecated Message type

**File:** `frontend/src/types/index.ts`

Delete the deprecated `Message` interface (0 importers):
```typescript
/**
 * @deprecated Use ChatMessage instead
 */
export interface Message {
  id: number;
  role: 'user' | 'assistant' | 'system';
  content: string;
}
```

### 1f. Frontend — Remove duplicate BuiltinTemplate type

**File:** `frontend/src/types/index.ts`

Delete the `BuiltinTemplate` interface — it's a duplicate of the one in `services/templateService.ts` with 0 importers from this location.

### 1g. Frontend — Remove unused getTemplateById function

**File:** `frontend/src/data/promptTemplates.ts`

Delete:
```typescript
export const getTemplateById = (id: string): PromptTemplate | undefined => {
  return promptTemplates.find(t => t.id === id);
};
```

Zero importers anywhere in the codebase.

### 1h. Frontend — Remove react-router-dom

**File:** `frontend/package.json`

Remove from dependencies:
- `react-router-dom`
- `@types/react-router-dom`

**File:** `frontend/src/App.tsx`

Remove Router import and wrappers:
```typescript
// DELETE this import
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'

// REPLACE this:
function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<ChatApp />} />
      </Routes>
    </Router>
  )
}

// WITH this:
function App() {
  return <ChatApp />
}
```

Then run `npm install` to update package-lock.json.

### Verification

```bash
cd backend && python -m pytest -v          # All tests pass (minus deleted rate_limiter tests)
cd backend && ruff check backend/          # Clean
cd backend && mypy backend/                # Clean (or same 2 pre-existing)
cd frontend && npm install                 # Update lockfile
cd frontend && npm run build               # Clean
cd frontend && npm run lint                # Clean
```

---

## Phase 2: Dependency Cleanup

### 2a. Split requirements.txt

**File:** `backend/requirements.txt` (rename to production-only)

Remove from `requirements.txt`:
- `sse-starlette>=2.0.0` (already dead from Phase 1)
- `ruff>=0.5.0`
- `mypy>=1.10.0`
- `pytest>=8.2.0`
- `pytest-asyncio>=0.23.0`

### 2b. Create requirements-dev.txt

**New file:** `backend/requirements-dev.txt`

```
-r requirements.txt
ruff>=0.5.0
mypy>=1.10.0
pytest>=8.2.0
pytest-asyncio>=0.23.0
```

### 2c. Update Dockerfile

**File:** `Dockerfile`

Ensure Stage 2 (Python runtime) uses `requirements.txt` only (no dev deps in production image). The Dockerfile likely already references `requirements.txt` so this may only need verification.

### Verification

```bash
cd backend && pip install -r requirements-dev.txt  # Still works for local dev
# Docker build verification deferred to Plan 008
```

---

## Phase 3: Template Consolidation

Templates are stored in 3 redundant places:
1. `backend/app/config/builtin_templates.json` (8 templates)
2. `backend/app/api/templates.py` (API serving that JSON)
3. `frontend/src/data/promptTemplates.ts` (identical data, used as fallback)

Since templates are static prompts with no server-side logic, consolidate to frontend-only.

### 3a. Delete backend template files

**Delete entirely:**
- `backend/app/config/builtin_templates.json`
- `backend/app/api/templates.py` (55 lines)
- `backend/tests/test_templates_api.py` (80 lines)

### 3b. Remove template router from main.py

**File:** `backend/app/main.py`

Remove the template router import and registration:
```python
# DELETE these lines
from app.api.templates import router as templates_router
app.include_router(templates_router)
```

### 3c. Simplify TemplateCards.tsx

**File:** `frontend/src/components/EmptyState/TemplateCards.tsx`

Remove API fetch + fallback pattern. Use `promptTemplates` from `data/promptTemplates.ts` directly.

### 3d. Delete templateService.ts

**File:** `frontend/src/services/templateService.ts`

Delete entirely — no more API calls needed. The `BuiltinTemplate` type (if still needed) can be imported from `promptTemplates.ts` or defined inline.

Update any files that import from `templateService.ts` to import from `promptTemplates.ts` instead.

### Verification

```bash
cd backend && python -m pytest -v          # Passes (template tests deleted)
cd backend && ruff check backend/          # Clean
cd frontend && npm run build               # Clean
# Verify: template cards still render in the empty state
```

---

## Phase 4: Export Pipeline Consolidation

**Current architecture (939 lines, 8 files):**
- `exporters/base.py` (107 lines) — 3 exception classes + 2 dataclasses + ABC
- `exporters/registry.py` (42 lines) — plugin registry pattern (overkill)
- `exporters/html_exporter.py` (44 lines) — literally `html.encode('utf-8')`
- `exporters/pdf_exporter.py` (73 lines) — Playwright PDF
- `exporters/png_exporter.py` (84 lines) — Playwright screenshot
- `exporters/pptx_exporter.py` (365 lines) — Claude code generation + sandbox
- `export_service.py` (74 lines) — orchestration via registry
- `api/export.py` (150 lines) — 4 copy-paste endpoints

**Target architecture (~400 lines, 5 files):**
- `exporters/base.py` (~40 lines) — 1 exception, 2 dataclasses
- `exporters/playwright_exporter.py` (~100 lines) — PDF + PNG combined
- `exporters/pptx_exporter.py` (~365 lines) — unchanged
- `export_service.py` (~50 lines) — dict-based dispatch
- `api/export.py` (~50 lines) — single parameterized endpoint

### 4a. Simplify base.py

**File:** `backend/app/services/exporters/base.py`

- Collapse `ExportError`, `UnsupportedFormatError`, `ExportGenerationError` into single `ExportError`
- Keep `ExportResult` and `ExportOptions` dataclasses
- Remove the `BaseExporter` ABC if no longer needed (exporters can just be functions or simple classes)

### 4b. Delete registry.py

**File:** `backend/app/services/exporters/registry.py`

Delete entirely. Replace with simple dict in `export_service.py`.

### 4c. Create playwright_exporter.py (merge PDF + PNG)

**New file:** `backend/app/services/exporters/playwright_exporter.py`

Merge `pdf_exporter.py` and `png_exporter.py`. They share identical page setup logic; only the final export call differs (`.pdf()` vs `.screenshot()`).

### 4d. Delete old exporter files

**Delete:**
- `backend/app/services/exporters/html_exporter.py` — inline into export_service
- `backend/app/services/exporters/pdf_exporter.py` — merged into playwright_exporter
- `backend/app/services/exporters/png_exporter.py` — merged into playwright_exporter
- `backend/app/services/exporters/registry.py` — replaced by simple dict

### 4e. Simplify export_service.py

**File:** `backend/app/services/export_service.py`

- Remove registry imports and initialization
- Add simple EXPORTERS dict
- Inline HTML export (just `html.encode('utf-8')`)
- Direct dispatch to exporter functions/classes

### 4f. Unify API endpoints

**File:** `backend/app/api/export.py`

Replace 4 copy-paste endpoints with single:
```python
@router.post("/api/export/{document_id}/{format_key}")
async def export_document(
    document_id: str,
    format_key: str,
    version: int | None = Query(None),
    title: str = Query("document"),
    # Format-specific optional params
    slide_width: int = Query(10),
    slide_height: float = Query(7.5),
    theme: str = Query("default"),
    page_format: str = Query("A4"),
    landscape: bool = Query(False),
    scale: float = Query(1.0),
    full_page: bool = Query(True),
    width: int | None = Query(None),
    height: int | None = Query(None),
) -> StreamingResponse:
```

Keep `list_formats` endpoint.

**Note:** Frontend `api.ts` already calls `POST /api/export/${documentId}/${format}` — no frontend changes needed.

### 4g. Update main.py

**File:** `backend/app/main.py`

Remove registry initialization from lifespan. Exporter setup now happens at import time via dict.

### 4h. Update tests

Update any export tests that import from deleted files:
- `test_export_base.py` — update exception class imports
- `test_export_html.py` — may need to test via export_service instead of direct importer
- `test_export_pdf.py` / `test_export_pptx.py` — update imports

### Verification

```bash
cd backend && python -m pytest tests/test_export*.py -v   # All export tests pass
cd backend && ruff check backend/                          # Clean
cd backend && mypy backend/                                # Clean
# Manual: export HTML, PPTX, PDF, PNG from a generated document
```

---

## Phase 5: chat.py Handler Extraction

**Current:** 302-line file with a single `event_stream()` async generator containing 3 independent paths (edit, create, image) with mixed SSE formatting.

### 5a. Extract edit handler

Create `async def _handle_edit(...)` generator that yields SSE dicts for the edit path.

### 5b. Extract create handler

Create `async def _handle_create(...)` generator that yields SSE dicts for the create path.

### 5c. Extract image handler

Create `async def _handle_image(...)` generator that yields SSE dicts for the image path.

### 5d. Simplify main chat() function

Main function becomes:
1. Session setup (~20 lines)
2. Route classification
3. Dispatch to handler
4. Wrap handler output with `_sse()` helper

### 5e. Standardize SSE formatting

Replace all inline `f"data: {json.dumps(...)}\n\n"` patterns with `_sse()` helper calls.

### Verification

```bash
cd backend && python -m pytest tests/test_chat*.py tests/test_editor.py -v  # All pass
cd backend && ruff check backend/app/api/chat.py                            # Clean
cd backend && mypy backend/app/api/chat.py                                  # Clean
```

---

## Phase 6: Documentation Update

### 6a. Update CLAUDE.md

- Remove references to deleted files (`rate_limiter.py`, `registry.py`, `html_exporter.py`, etc.)
- Update export architecture description
- Update template system description (frontend-only)
- Add Plan 012 to the plan table
- Add Plan 013 to the plan table (PENDING status)

### 6b. Update IMPLEMENTATION_PLANS/README.md

Add Plan 012 and 013 rows to the table.

### 6c. Update MEMORY.md

Add Plan 012 status and technical notes.

---

## Final Verification

```bash
# Backend
cd backend
python -m pytest -v                    # 210+ tests pass
ruff check backend/                    # Clean
mypy backend/                          # Clean (or same 2 pre-existing)

# Frontend
cd frontend
npm run build                          # Clean
npm run lint                           # Clean

# Manual smoke test
# 1. Create a new document via chat
# 2. Edit the document via chat (surgical edit)
# 3. Generate an image
# 4. Export as HTML, PPTX, PDF, PNG
# 5. Version history works
# 6. Template cards still render
```

---

## Summary of Changes

| File | Action | Details |
|------|--------|---------|
| `utils/rate_limiter.py` | **Delete** | Dead code (0 callers) |
| `tests/test_rate_limiter.py` | **Delete** | Tests for dead code |
| `config.py` | Trim | Remove 3 unused fields |
| `session_service.py` | Trim | Remove `cleanup_expired_sessions()` |
| `requirements.txt` | Trim | Remove sse-starlette, move dev deps |
| `requirements-dev.txt` | **Create** | Dev-only dependencies |
| `config/builtin_templates.json` | **Delete** | Redundant (frontend has same data) |
| `api/templates.py` | **Delete** | Served deleted JSON file |
| `tests/test_templates_api.py` | **Delete** | Tests for deleted API |
| `main.py` | Trim | Remove template router, registry init |
| `exporters/registry.py` | **Delete** | Over-abstracted plugin pattern |
| `exporters/html_exporter.py` | **Delete** | Inline (it's `html.encode()`) |
| `exporters/pdf_exporter.py` | **Delete** | Merged into playwright_exporter |
| `exporters/png_exporter.py` | **Delete** | Merged into playwright_exporter |
| `exporters/base.py` | Trim | 3 exceptions → 1 |
| `exporters/playwright_exporter.py` | **Create** | Merged PDF + PNG |
| `export_service.py` | Rewrite | Dict-based dispatch, inline HTML |
| `api/export.py` | Rewrite | 4 endpoints → 1 parameterized |
| `api/chat.py` | Refactor | 3 extracted handlers + dispatcher |
| `types/index.ts` | Trim | Remove deprecated Message, duplicate BuiltinTemplate |
| `promptTemplates.ts` | Trim | Remove unused getTemplateById |
| `package.json` | Trim | Remove react-router-dom |
| `App.tsx` | Trim | Remove Router wrappers |
| `TemplateCards.tsx` | Simplify | Remove API fetch, use data directly |
| `templateService.ts` | **Delete** | No more template API |

**Files deleted: 10** | **Files created: 2** | **Net lines removed: ~500+**
