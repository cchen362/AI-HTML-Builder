# Implementation Plan 011: Remove Custom Templates Feature

## Status: COMPLETE

---

## STOP - READ THIS FIRST

**DO NOT START** this implementation until:
- Plans 001-007, 009a, 009b are FULLY complete (they are)
- You have read this ENTIRE document
- You understand the distinction between **builtin templates** (8 starter prompts from JSON, KEEP) and **custom templates** (user-saved documents to SQLite, REMOVE)
- You understand the `action-group` layout in the viewer header (Plan 009b)

**DESTRUCTIVE ACTIONS PROHIBITED:**
- Do NOT delete builtin template routes (`GET /api/templates/builtin`, `GET /api/templates/builtin/{id}`)
- Do NOT delete `builtin_templates.json`
- Do NOT delete `fetchBuiltinTemplates()` from `templateService.ts`
- Do NOT delete `promptTemplates.ts` (hardcoded fallback data)
- Do NOT delete `PromptLibraryModal.tsx` (uses builtin templates only)
- Do NOT delete the `from-template` endpoint in `sessions.py` (generic, not custom-specific)
- Do NOT modify the chat, export, version history, or document management features

**WHY THIS FEATURE IS BEING REMOVED:**
- No login/auth mechanism exists — all custom templates stored as `created_by = "anonymous"`
- All users see and can delete all templates (no ownership isolation)
- For a corporate tool where some projects should have limited visibility, shared templates without auth is a privacy concern
- Auth (via Nginx Proxy Manager `X-Remote-User` header) is deferred to Plan 008
- Rather than ship a broken feature, remove it cleanly and re-introduce it properly when auth is in place

**DEPENDENCIES:**
- Plan 006: File Upload & Templates (introduced the feature)
- Plan 009a: Visual Foundation (CSS custom properties used by affected components)
- Plan 009b: Viewer Pane & UX Polish (action-group layout in viewer header)

**ESTIMATED EFFORT:** 0.5 days

---

## Impact Analysis

### Zero impact on other features

The custom template system is **completely isolated**:
- `templates` database table has **no foreign keys** to/from any other table
- Chat, editing, creation, export, version history, document tabs — **nothing touches** the templates table
- Builtin templates load from a static JSON file, not the database
- The `from-template` endpoint in `sessions.py` is generic (takes raw HTML, not a template ID)

### What stays

| Component | Why it stays |
|-----------|-------------|
| `GET /api/templates/builtin` | Serves the 8 starter prompt templates |
| `GET /api/templates/builtin/{id}` | Used by TemplateCards to fetch individual templates |
| `builtin_templates.json` | The 8 template definitions |
| `promptTemplates.ts` | Frontend fallback data for builtin templates |
| `fetchBuiltinTemplates()` in `templateService.ts` | Loads builtin templates from API |
| `PromptLibraryModal.tsx` | Uses builtin templates only (zero custom references) |
| `POST /api/sessions/{sid}/documents/from-template` | Generic endpoint, not custom-specific |

### What goes

| Component | Why it goes |
|-----------|-------------|
| `POST/GET/DELETE /api/templates/custom/*` routes | Custom CRUD with broken auth |
| `template_service.py` | Custom template service (SQLite CRUD + thumbnail gen) |
| `SaveTemplateModal` in `App.tsx` | "Save as Template" modal |
| "Save Template" button in viewer header | Triggers the modal |
| `handleSaveTemplate` / `handleSelectCustomTemplate` in `App.tsx` | Custom template callbacks |
| `onSelectCustomTemplate` prop chain | ChatWindow → MessageList → TemplateCards |
| "My Templates" section in `TemplateCards.tsx` | Renders user's custom templates |
| Custom functions in `templateService.ts` | `fetchCustomTemplates`, `createCustomTemplate`, etc. |
| `templates` table in `database.py` | Custom template storage |
| Custom template tests in `test_templates_api.py` | Tests for removed routes |

---

## Phase 1: Backend — Remove Custom Template Routes

### File: `backend/app/api/templates.py`

Delete the entire custom templates section (lines 58-124). Keep only:
- Imports (trim unused: remove `Header`, `Field`)
- `_TEMPLATES_PATH`, `_builtin_cache`, `_load_builtin_templates()`
- `get_builtin_templates()` route
- `get_builtin_template()` route

The file should look like this after the edit:

```python
"""Templates API: builtin template management."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException

router = APIRouter()
logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Builtin templates (loaded from JSON, cached in memory)
# ---------------------------------------------------------------------------

_TEMPLATES_PATH = Path(__file__).parent.parent / "config" / "builtin_templates.json"
_builtin_cache: list[dict[str, Any]] | None = None


def _load_builtin_templates() -> list[dict[str, Any]]:
    global _builtin_cache  # noqa: PLW0603
    if _builtin_cache is not None:
        return _builtin_cache
    try:
        with open(_TEMPLATES_PATH, encoding="utf-8") as f:
            data = json.load(f)
        _builtin_cache = data["templates"]
        logger.info("Loaded builtin templates", count=len(_builtin_cache))
        return _builtin_cache  # type: ignore[return-value]
    except Exception as e:
        logger.error("Failed to load builtin templates", error=str(e))
        return []


@router.get("/api/templates/builtin")
async def get_builtin_templates() -> dict:
    """Get all builtin starter prompt templates."""
    templates = _load_builtin_templates()
    return {"templates": templates, "count": len(templates)}


@router.get("/api/templates/builtin/{template_id}")
async def get_builtin_template(template_id: str) -> dict:
    """Get a specific builtin template by ID."""
    templates = _load_builtin_templates()
    template = next((t for t in templates if t["id"] == template_id), None)
    if not template:
        raise HTTPException(
            status_code=404, detail=f"Template '{template_id}' not found"
        )
    return template
```

### Verification
- `ruff check backend/app/api/templates.py`
- `mypy backend/app/api/templates.py`

---

## Phase 2: Backend — Remove Template Service

### File: `backend/app/services/template_service.py`

**Delete this file entirely.** It is used exclusively by the custom template routes.

Verify no other file imports from it:
- `api/templates.py` — will no longer import it (Phase 1)
- No other backend file imports `template_service`

### Verification
- `ruff check backend/app/` — no import errors
- `mypy backend/app/` — no missing module errors

---

## Phase 3: Backend — Remove Database Table

### File: `backend/app/database.py`

Remove the `templates` table creation and its index from the `init_db()` function.

Find and delete:
```sql
CREATE TABLE IF NOT EXISTS templates (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    html_content TEXT NOT NULL,
    thumbnail_base64 TEXT,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

And:
```sql
CREATE INDEX IF NOT EXISTS idx_templates_created_by ON templates(created_by);
```

**NOTE:** Existing databases on deployed instances will still have the `templates` table. This is harmless — SQLite `CREATE TABLE IF NOT EXISTS` was used, so removing it from code just means the table won't be created on fresh installs. Existing data sits inert. No migration needed for 2-5 users on a private server.

### Verification
- `ruff check backend/app/database.py`
- `mypy backend/app/database.py`

---

## Phase 4: Backend — Update Tests

### File: `backend/tests/test_templates_api.py`

Delete the custom template tests. Keep only the builtin template tests.

Delete these tests (they test custom template CRUD):
- `test_create_custom_template`
- `test_create_template_with_remote_user`
- Any test with "custom" in the name
- Any test that calls `POST /api/templates/custom`, `GET /api/templates/custom`, or `DELETE /api/templates/custom/{id}`

Keep these tests (they test builtin templates):
- `test_get_builtin_templates`
- `test_get_builtin_template_by_id`
- `test_get_builtin_template_not_found`
- `test_builtin_templates_have_all_ids`
- `test_builtin_templates_use_unified_placeholders`

Also remove any imports that were only needed for custom tests (e.g., `template_service` imports).

### Verification
- `pytest backend/tests/test_templates_api.py -v` — all remaining tests pass
- `pytest backend/tests/ -v` — full suite passes

---

## Phase 5: Frontend — Remove Save Template Modal and Button from App.tsx

### File: `frontend/src/App.tsx`

#### 5a. Remove imports (lines 10-11)

Delete:
```typescript
import { createCustomTemplate } from './services/templateService'
import { getCustomTemplate } from './services/templateService'
```

#### 5b. Delete `SaveTemplateModal` component (lines 16-82)

Delete the entire `SaveTemplateModal` component definition.

#### 5c. Remove `handleSaveTemplate` prop from `HtmlViewer`

In the `HtmlViewer` component props interface, remove:
```typescript
handleSaveTemplate: () => void;
```

In the `HtmlViewer` component body, remove the "Save Template" button (lines 172-179):
```tsx
<button
  className="save-template-btn"
  onClick={handleSaveTemplate}
  disabled={!currentHtml}
  title="Save current document as a reusable template"
>
  Save Template
</button>
```

**After removal, the `action-group--secondary` div will contain only the "Full Screen" button.** Since it's a single button, the action-group wrapper with separator is no longer visually necessary. Replace:

```tsx
<div className="action-group action-group--secondary">
  <button
    className="fullscreen-btn"
    onClick={handleFullScreen}
    disabled={!currentHtml}
    title="Open in new tab"
  >
    Full Screen
  </button>
</div>
```

With just the button directly inside `viewer-actions` (no secondary action-group wrapper):

```tsx
<button
  className="fullscreen-btn"
  onClick={handleFullScreen}
  disabled={!currentHtml}
  title="Open in new tab"
>
  Full Screen
</button>
```

The resulting `viewer-actions` div should contain:
```tsx
<div className="viewer-actions">
  <div className="action-group action-group--primary">
    <button className={`history-btn${historyOpen ? ' active' : ''}`} ...>History</button>
    <ExportDropdown ... />
  </div>
  <button className="fullscreen-btn" ...>Full Screen</button>
</div>
```

#### 5d. Remove state and callbacks in `ChatApp`

Delete from state declarations:
```typescript
const [saveModalOpen, setSaveModalOpen] = useState(false)
const [isSavingTemplate, setIsSavingTemplate] = useState(false)
```

Delete `handleSaveTemplate` callback (lines 347-358).

Delete `handleSelectCustomTemplate` callback (lines 360-370).

#### 5e. Remove prop passing

Remove from `ChatWindow` props:
```typescript
onSelectCustomTemplate={handleSelectCustomTemplate}
```

Remove from `HtmlViewer` props:
```typescript
handleSaveTemplate={() => setSaveModalOpen(true)}
```

Delete the `<SaveTemplateModal ... />` render (lines 417-422).

### Verification
- `npx tsc --noEmit` from frontend directory
- `npx vite build` from frontend directory

---

## Phase 6: Frontend — Remove Custom Template Props from Component Chain

### File: `frontend/src/components/ChatWindow/index.tsx`

Remove from `ChatWindowProps` interface:
```typescript
onSelectCustomTemplate?: (templateId: string, templateName: string) => void;
```

Remove from destructured props:
```typescript
onSelectCustomTemplate,
```

Remove from `MessageList` props:
```typescript
onSelectCustomTemplate={onSelectCustomTemplate}
```

### File: `frontend/src/components/ChatWindow/MessageList.tsx`

Remove `onSelectCustomTemplate` from props interface and destructuring.

Remove from `TemplateCards` props:
```typescript
onSelectCustomTemplate={onSelectCustomTemplate}
```

### File: `frontend/src/components/EmptyState/TemplateCards.tsx`

#### 6a. Remove custom template interface and props

Remove from `TemplateCardsProps`:
```typescript
onSelectCustomTemplate?: (htmlContent: string, templateName: string) => void;
```

Remove from destructured props:
```typescript
onSelectCustomTemplate,
```

#### 6b. Remove custom template state and effects

Delete:
```typescript
const [customTemplates, setCustomTemplates] = useState<CustomTemplate[]>([]);
```

Delete the custom template fetch from the `useEffect` (lines 44-48):
```typescript
fetchCustomTemplates()
  .then(setCustomTemplates)
  .catch(() => {
    // No custom templates available
  });
```

#### 6c. Delete `handleDeleteCustom` function (lines 51-59)

#### 6d. Delete "My Templates" render block (lines 63-99)

Delete the entire `{customTemplates.length > 0 && (...)}` block.

#### 6e. Update imports (line 3)

```typescript
// BEFORE
import { fetchBuiltinTemplates, fetchCustomTemplates, deleteCustomTemplate } from '../../services/templateService';
import type { BuiltinTemplate, CustomTemplate } from '../../services/templateService';

// AFTER
import { fetchBuiltinTemplates } from '../../services/templateService';
import type { BuiltinTemplate } from '../../services/templateService';
```

### Verification
- `npx tsc --noEmit`
- `npx vite build`

---

## Phase 7: Frontend — Trim templateService.ts

### File: `frontend/src/services/templateService.ts`

Keep only `fetchBuiltinTemplates()` and the `BuiltinTemplate` type.

Delete:
- `CustomTemplate` interface/type
- `fetchCustomTemplates()` function
- `getCustomTemplate()` function
- `createCustomTemplate()` function
- `deleteCustomTemplate()` function

### Verification
- `npx tsc --noEmit`
- `npx vite build`

---

## Phase 8: CSS Cleanup

### File: `frontend/src/App.css`

Delete custom template CSS:

1. Remove `.save-template-btn` from the `.history-btn, .save-template-btn` selector group (keep `.history-btn` standalone)
2. Remove `.save-template-btn:hover:not(:disabled)` from its combined selector (keep `.history-btn:hover`)
3. Remove `.save-template-btn:disabled` from its combined selector (keep `.history-btn:disabled`)
4. Delete the entire "Save Template Modal" CSS block:
   - `.save-template-overlay`
   - `.save-template-modal`
   - `.save-template-modal h3`
   - `.form-field`
   - `.form-field label`
   - `.form-field input, .form-field textarea`
   - `.modal-actions`
   - `.save-btn`
5. Delete `.action-group--secondary` CSS (no longer used — only had Save Template + Full Screen, now Full Screen is standalone):
   - `.action-group--secondary`
   - `.action-group--secondary button`
   - `.action-group--secondary button:hover:not(:disabled)`

### File: `frontend/src/components/EmptyState/TemplateCards.css`

Remove any CSS classes that are custom-template-only:
- `.custom-templates-grid` (if it exists)
- `.custom-template-card` (if it exists)
- `.custom-template-thumb` (if it exists)
- `.delete-template-btn` (if it exists)

### Verification
- `npx vite build` — no CSS errors
- Visual check: viewer header layout looks correct with History, Export, Full Screen buttons

---

## Phase 9: Update Documentation

### File: `CLAUDE.md`

1. **API Endpoints section**: Remove the custom template endpoints:
   - `POST /api/templates/custom`
   - `GET /api/templates/custom`
   - `GET /api/templates/custom/{id}`
   - `DELETE /api/templates/custom/{id}`

2. **Project Structure**: Remove `services/template_service.py` from the backend tree

3. **Database section**: Remove `templates` table from the table list

4. **Known Issues**: Add a note: "Custom templates removed (no auth mechanism). Will be re-introduced when Plan 008 adds Nginx Proxy Manager authentication."

### File: `IMPLEMENTATION_PLANS/README.md`

Add Plan 011 to the table:
```
| 011 | Remove Custom Templates | COMPLETE | 006 | Remove custom template feature (no auth) |
```

### Verification
- Read through all updated docs to ensure consistency

---

## Phase 10: Final Verification

```bash
# Backend
cd backend
ruff check .
mypy .
pytest -v

# Frontend
cd frontend
npx tsc --noEmit
npx vite build
```

**Expected results:**
- ruff: clean
- mypy: clean
- pytest: ~235+ tests passing (removed ~10 custom template tests), 1 pre-existing failure
- TypeScript: clean
- Vite build: clean

---

## Summary of Changes

| File | Action | Details |
|------|--------|---------|
| `api/templates.py` | Trim | Remove 4 custom routes, keep 2 builtin routes |
| `services/template_service.py` | **Delete** | Entire file removed |
| `database.py` | Trim | Remove `templates` table + index |
| `test_templates_api.py` | Trim | Remove ~7 custom tests, keep 5 builtin tests |
| `App.tsx` | Trim | Remove SaveTemplateModal, button, callbacks, state, props |
| `App.css` | Trim | Remove save-template CSS, modal CSS, secondary action-group |
| `ChatWindow/index.tsx` | Trim | Remove `onSelectCustomTemplate` prop |
| `MessageList.tsx` | Trim | Remove `onSelectCustomTemplate` prop |
| `TemplateCards.tsx` | Trim | Remove custom fetch, render, delete handler |
| `TemplateCards.css` | Trim | Remove custom template card styles |
| `templateService.ts` | Trim | Remove 4 custom functions + CustomTemplate type |
| `CLAUDE.md` | Update | Remove custom template references |
| `README.md` (plans) | Update | Add Plan 011 entry |

**Deleted files: 1** (`template_service.py`)
**New files: 0**
**Net lines removed: ~300+**

---

## Re-introduction Path

When Plan 008 implements Nginx Proxy Manager authentication:
1. NPM injects `X-Remote-User` header for all authenticated requests
2. Re-add `templates` table with `created_by` column
3. Re-add custom template routes (same pattern as before, but now `created_by` is a real username)
4. Template ownership and visibility will be properly scoped per user
5. The builtin template system remains unchanged throughout
