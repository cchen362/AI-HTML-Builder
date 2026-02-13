# Implementation Plan 009b: Viewer Pane & UX Polish

## Status: COMPLETE

All 7 phases implemented and verified (February 2026):
- 14 new backend tests (5 restore + 9 document management), all passing
- Ruff clean, mypy clean, TypeScript clean, Vite build clean
- Backend files created: `tests/test_restore_version.py`, `tests/test_document_management.py`
- Backend files modified: `services/session_service.py` (+restore_version, +rename_document, +delete_document), `api/sessions.py` (+3 endpoints)
- Frontend files modified: `App.tsx` (skeleton, restore, rename/delete, cancel, action groups), `App.css` (skeleton+action-group CSS), `CodeMirrorViewer.tsx` (data-theme MutationObserver), `ChatInput.tsx` (cancel btn+drag-drop), `ChatInput.css` (cancel+drop CSS), `ChatWindow/index.tsx` (onCancelRequest prop), `VersionTimeline.tsx` (restore btn), `VersionTimeline.css` (restore styles), `DocumentTabs.tsx` (rename+delete rewrite), `DocumentTabs.css` (close+rename styles), `api.ts` (+3 methods)
- 009a known issue resolved: `CodeMirrorViewer.tsx` now uses `MutationObserver` on `data-theme` attribute instead of `matchMedia`

---

## STOP - READ THIS FIRST

**DO NOT START** this implementation until:
- Plan 007 (Template Optimization) is FULLY complete and tested
- **Plan 009a (Visual Foundation) is FULLY complete and tested** — this plan depends on the CSS custom property system and theme architecture established in 009a
- You have read this ENTIRE document
- You understand the export API already exists at `backend/app/api/export.py` (Plan 005)
- You understand that `cancelRequest()` already exists in `useSSEChat.ts` but has no UI
- You understand the SQLite schema has `ON DELETE CASCADE` on `documents → document_versions`

**DESTRUCTIVE ACTIONS PROHIBITED:**
- Do NOT modify any backend export logic (`api/export.py`, `services/export_service.py`, `services/exporters/*`)
- Do NOT modify the SSE streaming logic in `api/chat.py`
- Do NOT modify the routing logic in `services/router.py`
- Do NOT modify `EDIT_SYSTEM_PROMPT` or `CREATION_SYSTEM_PROMPT`
- Do NOT add new npm dependencies — use native browser APIs only

**DEPENDENCIES:**
- Plan 005: Export pipeline (backend exporters fully tested — 193 tests)
- Plan 006: File upload system (upload service, template service)
- Plan 007: Template optimization (placeholder handling)
- **Plan 009a: Visual Foundation** — provides CSS custom properties (`theme.css`), theme toggle, font system, and animation keyframes. ALL CSS in this plan MUST use `var(--*)` tokens from `theme.css`. Zero hardcoded hex colors, font-family strings, or shadow values.

**KNOWN ISSUE FROM 009a (must fix in this plan):**
- `CodeMirrorViewer.tsx` still uses `window.matchMedia('(prefers-color-scheme: dark)')` for CodeMirror dark/light theme. Must be updated to read `document.documentElement.getAttribute('data-theme')` and listen for attribute changes (via `MutationObserver` or the ThemeToggle's `storage` event) instead of `matchMedia`.

**CSS ARCHITECTURE NOTE (from Plan 009a):**
- All colors: `var(--surface-*)`, `var(--text-*)`, `var(--accent-*)`, `var(--signal-*)`, `var(--border-*)`
- All fonts: `var(--font-display)`, `var(--font-body)`, `var(--font-mono)`
- All radii: `var(--radius-*)`
- All shadows: `var(--shadow-*)`
- All transitions: `var(--duration-*)` and `var(--ease-*)`
- Dark mode is default (`:root`). Light mode overrides via `[data-theme="light"]` ONLY.

**ESTIMATED EFFORT:** 2-3 days

---

## Context & Rationale

### Current State
Plans 001-007 rebuilt the entire backend: SQLite, SSE streaming, tool-based editing, Gemini creation, image generation, export pipeline, file upload, and templates. The frontend was partially rebuilt but the viewer pane and UX polish were not prioritized.

### Problems Found

#### Problem 1: PPTX/PDF/PNG Export Shows "Coming Soon" (CRITICAL)
The backend fully implements all export formats (Plan 005, 193 tests passing). The frontend `ExportDropdown.tsx` shows PowerPoint and PDF as disabled with "(Coming soon)" labels. **PPT export is the primary corporate use case** — users need to generate stakeholder decks.

**Current code in `ExportDropdown.tsx` (lines 45-50):**
```typescript
<button className="export-dropdown-item export-dropdown-item--disabled" disabled>
  PowerPoint <span className="coming-soon">(Coming soon)</span>
</button>
<button className="export-dropdown-item export-dropdown-item--disabled" disabled>
  PDF <span className="coming-soon">(Coming soon)</span>
</button>
```

**Backend API endpoints (already working in `backend/app/api/export.py`):**
- `POST /api/export/{document_id}/html` — downloads .html
- `POST /api/export/{document_id}/pptx?title=...` — downloads .pptx
- `POST /api/export/{document_id}/pdf?title=...&page_format=A4` — downloads .pdf
- `POST /api/export/{document_id}/png?title=...&full_page=true` — downloads .png

#### Problem 2: No Loading Feedback in Viewer
The viewer shows a static "No content yet" placeholder for the entire 10-30 second generation time. Users think the tool is broken. No skeleton, no progress, no status text in the viewer pane.

**Current code in `App.tsx` (lines 172-176):**
```typescript
{!displayHtml ? (
  <div className="placeholder">
    <h3>No content yet</h3>
    <p>Send a message to generate HTML content</p>
  </div>
) : ...}
```

#### Problem 3: No Version Restore
`VersionTimeline.tsx` lets users preview old versions but has no restore/rollback button. The only workaround is manually copying HTML source. No backend endpoint exists for restore.

#### Problem 4: No Document Management
`DocumentTabs.tsx` shows tab buttons but has no close (X) button and no rename capability. Document titles are auto-generated from the first 50 chars of the user prompt and can never be changed.

#### Problem 5: No Cancel Button
`useSSEChat.ts` has `cancelRequest()` (line 279) that calls `abortRef.current?.abort()`, but no UI element exposes this to users. During streaming, the send button shows loading dots with no way to stop.

#### Problem 6: Viewer Header Button Clutter
7 interactive elements in one row: `[Preview] [Code] [History] [Save Template] [Full Screen] [Export ▼]` with no visual grouping, no hierarchy, and equal visual weight.

#### Problem 7: No Drag-and-Drop Upload
File upload requires clicking "Attach File" button. No drag-and-drop zone. `ChatInput.tsx` has `handleFileSelect` and `validateFileClient` that can be reused for drop events.

---

## Strict Rules — Check Before Each Commit

### Export Rules
- [ ] Frontend calls `POST /api/export/{docId}/{format}` — NOT client-side blob download for PPTX/PDF/PNG
- [ ] HTML export can remain client-side (it's just the current HTML string)
- [ ] Export loading state is per-format (user can't click same format twice)
- [ ] Export errors show a dismissible toast/banner — NOT an alert()
- [ ] All export buttons disabled when no active document (no `documentId`)

### Backend Rules
- [ ] `restore_version` creates a NEW version (does not overwrite existing versions)
- [ ] `delete_document` checks that at least 1 document remains in session
- [ ] `delete_document` sets another document as active if deleting the active one
- [ ] `rename_document` validates title is non-empty and <= 200 chars
- [ ] `chat_messages.document_id` FK needs `SET NULL` handling on document delete (current schema has no ON DELETE action for this FK)

### Frontend Rules
- [ ] Cancel button only shows when `isProcessing === true`
- [ ] Drag-and-drop reuses existing `validateFileClient()` and `uploadFile()` functions
- [ ] Version restore shows confirmation dialog before executing
- [ ] Document delete shows confirmation dialog before executing
- [ ] Inline rename: Enter saves, Escape cancels, blur saves
- [ ] All new UI elements use CSS variables from `theme.css` — NO `@media (prefers-color-scheme: dark)`, use `[data-theme="light"]` overrides ONLY if semantic variables are insufficient

### Testing Rules
- [ ] New backend endpoints have unit tests (restore, rename, delete)
- [ ] Existing 244/245 tests still pass (1 pre-existing failure: `test_init_db_creates_file`)
- [ ] Frontend builds without TypeScript errors
- [ ] Frontend builds without Vite errors
- [ ] Ruff clean on modified backend files
- [ ] Mypy clean on modified backend files

---

## Phase 1: Export Wiring (P0 — PRIMARY USE CASE) — COMPLETE

> **Status:** Implemented exactly as documented. Zero discrepancies.
> **Files modified:** `api.ts` (+exportDocument), `ExportDropdown.tsx` (full rewrite), `ExportDropdown.css` (full rewrite), `App.tsx` (+documentTitle prop to HtmlViewer)
> **Verification:** TypeScript clean, Vite build clean.

### Objective
Wire up the frontend export dropdown to call the already-implemented backend export APIs for PPTX, PDF, and PNG.

### 1.1 Add Export API Method

**File:** `frontend/src/services/api.ts`

**Add to the `api` object (after `createFromTemplate`):**

```typescript
  /** Download a document export in the specified format. */
  async exportDocument(
    documentId: string,
    format: 'html' | 'pptx' | 'pdf' | 'png',
    title?: string,
  ): Promise<void> {
    const params = new URLSearchParams();
    if (title) params.set('title', title);

    const res = await fetch(
      `${BASE}/api/export/${documentId}/${format}?${params.toString()}`,
      { method: 'POST' },
    );

    if (!res.ok) {
      const errorData = await res.json().catch(() => null);
      throw new Error(errorData?.detail || `Export failed: ${res.status}`);
    }

    // Extract filename from Content-Disposition header
    const disposition = res.headers.get('Content-Disposition');
    const filenameMatch = disposition?.match(/filename="(.+)"/);
    const filename = filenameMatch?.[1] || `export.${format}`;

    // Download the blob
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  },
```

### 1.2 Update ExportDropdown Component

**File:** `frontend/src/components/Export/ExportDropdown.tsx`

**Replace entire file with:**

```typescript
import { useState, useRef, useEffect } from 'react';
import { api } from '../../services/api';
import './ExportDropdown.css';

interface ExportDropdownProps {
  onExportHtml: () => void;
  disabled?: boolean;
  documentId: string | null;
  documentTitle?: string;
}

type ExportFormat = 'pptx' | 'pdf' | 'png';

const ExportDropdown: React.FC<ExportDropdownProps> = ({
  onExportHtml,
  disabled = false,
  documentId,
  documentTitle,
}) => {
  const [open, setOpen] = useState(false);
  const [loadingFormat, setLoadingFormat] = useState<ExportFormat | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const ref = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  // Auto-dismiss error after 5 seconds
  useEffect(() => {
    if (!exportError) return;
    const timer = setTimeout(() => setExportError(null), 5000);
    return () => clearTimeout(timer);
  }, [exportError]);

  const handleExport = async (format: ExportFormat) => {
    if (!documentId || loadingFormat) return;
    setLoadingFormat(format);
    setExportError(null);
    try {
      await api.exportDocument(documentId, format, documentTitle);
      setOpen(false);
    } catch (err) {
      setExportError(err instanceof Error ? err.message : 'Export failed');
    } finally {
      setLoadingFormat(null);
    }
  };

  return (
    <div className="export-dropdown" ref={ref}>
      <button
        className="export-btn"
        onClick={() => setOpen((v) => !v)}
        disabled={disabled}
      >
        Export
      </button>
      {open && (
        <div className="export-dropdown-menu">
          {exportError && (
            <div className="export-error">
              <span>{exportError}</span>
              <button type="button" onClick={() => setExportError(null)}>&times;</button>
            </div>
          )}
          <button
            className="export-dropdown-item"
            onClick={() => {
              onExportHtml();
              setOpen(false);
            }}
          >
            HTML
          </button>
          <button
            className="export-dropdown-item"
            onClick={() => handleExport('pptx')}
            disabled={!documentId || loadingFormat === 'pptx'}
          >
            {loadingFormat === 'pptx' ? (
              <span className="export-loading">Exporting...</span>
            ) : (
              'PowerPoint'
            )}
          </button>
          <button
            className="export-dropdown-item"
            onClick={() => handleExport('pdf')}
            disabled={!documentId || loadingFormat === 'pdf'}
          >
            {loadingFormat === 'pdf' ? (
              <span className="export-loading">Exporting...</span>
            ) : (
              'PDF'
            )}
          </button>
          <button
            className="export-dropdown-item"
            onClick={() => handleExport('png')}
            disabled={!documentId || loadingFormat === 'png'}
          >
            {loadingFormat === 'png' ? (
              <span className="export-loading">Exporting...</span>
            ) : (
              'Image (PNG)'
            )}
          </button>
        </div>
      )}
    </div>
  );
};

export default ExportDropdown;
```

### 1.3 Update ExportDropdown CSS

**File:** `frontend/src/components/Export/ExportDropdown.css`

**Add these rules (keep existing rules, append):**

```css
.export-error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 12px;
  background: #fff0f0;
  border-bottom: 1px solid #ffcdd2;
  color: #c62828;
  font-size: 0.8rem;
}

.export-error button {
  background: none;
  border: none;
  color: #c62828;
  cursor: pointer;
  font-size: 1rem;
  padding: 0 4px;
}

.export-loading {
  color: #666;
  font-style: italic;
}

/* Remove old disabled/coming-soon styles */
.export-dropdown-item:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* NOTE (Plan 009a): Replace all hardcoded colors above with CSS variables:
   .export-error { background: var(--signal-error-muted); border-color: var(--signal-error); color: var(--signal-error); }
   .export-loading { color: var(--text-secondary); }
   Dark/light mode is handled automatically via theme.css variables. */
```

**Remove these CSS classes if they exist:** `.export-dropdown-item--disabled`, `.coming-soon`

### 1.4 Wire Up in App.tsx

**File:** `frontend/src/App.tsx`

**In the HtmlViewer component, change the ExportDropdown usage (line 166):**

Current:
```typescript
<ExportDropdown onExportHtml={handleExport} disabled={!currentHtml} />
```

Replace with:
```typescript
<ExportDropdown
  onExportHtml={handleExport}
  disabled={!currentHtml}
  documentId={activeDocumentId}
  documentTitle={activeDocument?.title}
/>
```

**Note:** The HtmlViewer props type doesn't currently have `activeDocument` — we'll need to pass it through. But since `activeDocumentId` is already a prop, and the ExportDropdown only needs the ID and a title string, we can add `documentTitle` as an optional prop to HtmlViewer or pass it alongside `activeDocumentId`. Simplest: add `documentTitle?: string` to HtmlViewer's props.

### Build Verification (Phase 1)
```bash
cd frontend && npx tsc --noEmit
cd frontend && npm run build
```

---

## Phase 2: Loading Skeleton in Viewer (P0)

### Objective
Show a pulsing skeleton and status text in the viewer while HTML is being generated.

### 2.1 Update HtmlViewer Props and Rendering

**File:** `frontend/src/App.tsx`

**Add `isStreaming` and `currentStatus` to HtmlViewer's props interface:**
```typescript
isStreaming: boolean;
currentStatus: string;
```

**Replace the empty-state placeholder block (lines 172-176):**

Current:
```typescript
{!displayHtml ? (
  <div className="placeholder">
    <h3>No content yet</h3>
    <p>Send a message to generate HTML content</p>
  </div>
) : viewMode === 'preview' ? (
```

Replace with:
```typescript
{!displayHtml ? (
  isStreaming ? (
    <div className="viewer-loading">
      <div className="loading-skeleton">
        <div className="skeleton-bar skeleton-header" />
        <div className="skeleton-bar skeleton-subheader" />
        <div className="skeleton-bar skeleton-line" />
        <div className="skeleton-bar skeleton-line" />
        <div className="skeleton-bar skeleton-line short" />
        <div className="skeleton-bar skeleton-line" />
        <div className="skeleton-bar skeleton-line" />
        <div className="skeleton-bar skeleton-line short" />
      </div>
      {currentStatus && <p className="loading-status">{currentStatus}</p>}
    </div>
  ) : (
    <div className="placeholder">
      <h3>No content yet</h3>
      <p>Send a message to generate HTML content</p>
    </div>
  )
) : viewMode === 'preview' ? (
```

**In ChatApp, pass the new props to HtmlViewer:**
```typescript
<HtmlViewer
  ...existing props...
  isStreaming={isStreaming}
  currentStatus={currentStatus}
/>
```

### 2.2 Add Skeleton CSS

**File:** `frontend/src/App.css`

**Add these rules:**

```css
/* Loading skeleton */
.viewer-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 2rem;
}

.loading-skeleton {
  width: 80%;
  max-width: 600px;
}

.skeleton-bar {
  height: 16px;
  background: linear-gradient(90deg, #e0e0e0 25%, #f0f0f0 50%, #e0e0e0 75%);
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.5s ease-in-out infinite;
  border-radius: 4px;
  margin-bottom: 12px;
}

.skeleton-header {
  height: 28px;
  width: 60%;
  margin-bottom: 16px;
}

.skeleton-subheader {
  height: 20px;
  width: 40%;
  margin-bottom: 24px;
}

.skeleton-line.short {
  width: 75%;
}

@keyframes skeleton-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.loading-status {
  margin-top: 1.5rem;
  color: #666;
  font-size: 0.9rem;
  animation: fade-pulse 2s ease-in-out infinite;
}

@keyframes fade-pulse {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; }
}

/* NOTE (Plan 009a): Replace hardcoded colors above with CSS variables:
   .skeleton-bar { background: linear-gradient(90deg, var(--surface-highlight) 25%, var(--surface-overlay) 50%, var(--surface-highlight) 75%); }
   .loading-status { color: var(--text-secondary); }
   Dark/light handled automatically via theme.css. No @media dark mode block needed. */
```

### Build Verification (Phase 2)
```bash
cd frontend && npx tsc --noEmit
cd frontend && npm run build
```

---

## Phase 3: Version Restore (P0)

### Objective
Allow users to restore a previous version by creating a new version from its HTML content.

### 3.1 Add Backend `restore_version` Method

**File:** `backend/app/services/session_service.py`

**Add method to SessionService class (after `get_version_history`):**

```python
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
```

### 3.2 Add Backend Restore Endpoint

**File:** `backend/app/api/sessions.py`

**Add endpoint (after `get_latest_html`):**

```python
@router.post("/api/documents/{document_id}/versions/{version}/restore")
async def restore_version(document_id: str, version: int):
    try:
        new_version = await session_service.restore_version(document_id, version)
        return {"version": new_version}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
```

### 3.3 Add Frontend API Method

**File:** `frontend/src/services/api.ts`

**Add to the `api` object:**

```typescript
  /** Restore a historical version (creates a new version from old HTML). */
  restoreVersion(docId: string, version: number): Promise<{ version: number }> {
    return json(`/api/documents/${docId}/versions/${version}/restore`, {
      method: 'POST',
    });
  },
```

### 3.4 Add Restore Button to VersionTimeline

**File:** `frontend/src/components/VersionHistory/VersionTimeline.tsx`

**Add `onRestoreVersion` to props interface:**
```typescript
interface VersionTimelineProps {
  documentId: string | null;
  onVersionPreview: (html: string) => void;
  onBackToCurrent: () => void;
  onRestoreVersion: (version: number) => void;
  isOpen: boolean;
  onToggle: () => void;
}
```

**In the preview bar (lines 102-109), add restore button next to "Back to current":**

Current:
```typescript
{selectedVersion !== null && (
  <div className="version-preview-bar">
    <span>Viewing v{selectedVersion}</span>
    <button className="back-to-current-btn" onClick={handleBackToCurrent} type="button">
      Back to current
    </button>
  </div>
)}
```

Replace with:
```typescript
{selectedVersion !== null && (
  <div className="version-preview-bar">
    <span>Viewing v{selectedVersion}</span>
    <div className="version-preview-actions">
      <button
        className="restore-version-btn"
        onClick={() => {
          if (window.confirm(`Restore version ${selectedVersion}? This creates a new version from v${selectedVersion}.`)) {
            onRestoreVersion(selectedVersion);
          }
        }}
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

### 3.5 Style Restore Button

**File:** `frontend/src/components/VersionHistory/VersionTimeline.css`

**Add rules:**

```css
.version-preview-actions {
  display: flex;
  gap: 0.5rem;
}

.restore-version-btn {
  background: #006FCF;
  color: white;
  border: none;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 0.75rem;
  cursor: pointer;
  white-space: nowrap;
}

.restore-version-btn:hover {
  background: #0056a8;
}

/* NOTE (Plan 009a): Replace hardcoded colors above with CSS variables:
   .restore-version-btn { background: var(--accent-primary); color: var(--text-inverse); }
   .restore-version-btn:hover { background: var(--accent-primary-hover); }
   Dark/light handled automatically via theme.css. No @media dark mode block needed. */
```

### 3.6 Wire Up Restore in App.tsx

**File:** `frontend/src/App.tsx`

**Add `handleRestoreVersion` callback in ChatApp:**

```typescript
const handleRestoreVersion = useCallback(async (version: number) => {
  if (!activeDocument?.id) return;
  try {
    await api.restoreVersion(activeDocument.id, version);
    setPreviewHtml(null);
    await refreshDocuments();
    // Refresh version timeline by toggling history panel
    setHistoryOpen(false);
    setTimeout(() => setHistoryOpen(true), 50);
  } catch (err) {
    setError(err instanceof Error ? err.message : 'Failed to restore version');
  }
}, [activeDocument, refreshDocuments]);
```

**Pass to VersionTimeline via HtmlViewer — add `onRestoreVersion` prop chain:**
- HtmlViewer props: add `onRestoreVersion: (version: number) => void`
- Pass through to VersionTimeline: `onRestoreVersion={onRestoreVersion}`
- In ChatApp, pass: `onRestoreVersion={handleRestoreVersion}`

### 3.7 Add Backend Tests

**File:** `backend/tests/test_restore_version.py` (NEW)

```python
"""Tests for version restore functionality."""
import pytest
from starlette.testclient import TestClient
from app.main import app
from app.database import init_db, close_db


@pytest.fixture(autouse=True)
async def setup_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    from app.config import settings
    settings.__init__()  # type: ignore[misc]
    await init_db()
    yield
    await close_db()


@pytest.fixture
def client():
    return TestClient(app)


def test_restore_version_creates_new_version(client: TestClient) -> None:
    # Create session + document
    session = client.post("/api/sessions").json()
    sid = session["session_id"]
    session_data = client.get(f"/api/sessions/{sid}").json()
    # No documents yet — create one via from-template
    resp = client.post(
        f"/api/sessions/{sid}/documents/from-template",
        json={"title": "Test", "html_content": "<html><body>v1</body></html>"},
    )
    doc_id = resp.json()["document_id"]

    # Save a second version
    from app.services.session_service import session_service
    import asyncio
    asyncio.get_event_loop().run_until_complete(
        session_service.save_version(doc_id, "<html><body>v2</body></html>", "edit", "changed", "claude", 100)
    )

    # Restore version 1
    resp = client.post(f"/api/documents/{doc_id}/versions/1/restore")
    assert resp.status_code == 200
    assert resp.json()["version"] == 3  # new version created

    # Verify restored HTML matches v1
    resp = client.get(f"/api/documents/{doc_id}/versions/3")
    assert resp.json()["html_content"] == "<html><body>v1</body></html>"
    assert resp.json()["edit_summary"] == "Restored from version 1"


def test_restore_nonexistent_version_returns_404(client: TestClient) -> None:
    session = client.post("/api/sessions").json()
    sid = session["session_id"]
    resp = client.post(
        f"/api/sessions/{sid}/documents/from-template",
        json={"title": "Test", "html_content": "<html><body>test</body></html>"},
    )
    doc_id = resp.json()["document_id"]

    resp = client.post(f"/api/documents/{doc_id}/versions/999/restore")
    assert resp.status_code == 404
```

### Build Verification (Phase 3)
```bash
cd backend && ruff check app/services/session_service.py app/api/sessions.py
cd backend && mypy app/services/session_service.py app/api/sessions.py
cd backend && python -m pytest tests/test_restore_version.py -v
cd frontend && npx tsc --noEmit
```

---

## Phase 4: Document Rename & Delete (P0)

### Objective
Allow users to rename document tabs (double-click) and delete documents (X button).

### 4.1 Add Backend Methods

**File:** `backend/app/services/session_service.py`

**Add two methods to SessionService class:**

```python
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
        """Delete a document. Activates another document if this was active.
        Returns False if this is the last document (cannot delete)."""
        db = await get_db()

        # Count documents in session
        cursor = await db.execute(
            "SELECT COUNT(*) as cnt FROM documents WHERE session_id = ?",
            (session_id,),
        )
        row = await cursor.fetchone()
        assert row is not None
        if row["cnt"] <= 1:
            return False  # Cannot delete last document

        # Check if this document is active
        cursor = await db.execute(
            "SELECT is_active FROM documents WHERE id = ? AND session_id = ?",
            (document_id, session_id),
        )
        doc_row = await cursor.fetchone()
        if not doc_row:
            return False  # Document not found

        was_active = bool(doc_row["is_active"])

        # Nullify document_id references in chat_messages (no CASCADE on this FK)
        await db.execute(
            "UPDATE chat_messages SET document_id = NULL WHERE document_id = ?",
            (document_id,),
        )

        # Delete the document (CASCADE deletes versions)
        await db.execute(
            "DELETE FROM documents WHERE id = ? AND session_id = ?",
            (document_id, session_id),
        )

        # If it was active, activate the most recent remaining document
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
```

### 4.2 Add Backend Endpoints

**File:** `backend/app/api/sessions.py`

**Add after `create_from_template`:**

```python
class RenameRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)


@router.patch("/api/documents/{document_id}")
async def rename_document(document_id: str, body: RenameRequest):
    success = await session_service.rename_document(document_id, body.title)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"success": True}


@router.delete("/api/sessions/{session_id}/documents/{document_id}")
async def delete_document(session_id: str, document_id: str):
    success = await session_service.delete_document(session_id, document_id)
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete document (not found or last remaining document)",
        )
    return {"success": True}
```

### 4.3 Add Frontend API Methods

**File:** `frontend/src/services/api.ts`

**Add to the `api` object:**

```typescript
  /** Rename a document. */
  renameDocument(docId: string, title: string): Promise<{ success: boolean }> {
    return json(`/api/documents/${docId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title }),
    });
  },

  /** Delete a document from a session. */
  deleteDocument(sessionId: string, docId: string): Promise<{ success: boolean }> {
    return json(`/api/sessions/${sessionId}/documents/${docId}`, {
      method: 'DELETE',
    });
  },
```

### 4.4 Update DocumentTabs Component

**File:** `frontend/src/components/DocumentTabs/DocumentTabs.tsx`

**Replace entire file with:**

```typescript
import { useState, useRef, useEffect } from 'react';
import type { Document } from '../../types';
import './DocumentTabs.css';

interface DocumentTabsProps {
  documents: Document[];
  activeDocumentId: string | null;
  onDocumentSelect: (docId: string) => void;
  onRenameDocument?: (docId: string, newTitle: string) => void;
  onDeleteDocument?: (docId: string) => void;
}

export default function DocumentTabs({
  documents,
  activeDocumentId,
  onDocumentSelect,
  onRenameDocument,
  onDeleteDocument,
}: DocumentTabsProps) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editingId && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editingId]);

  if (documents.length === 0) return null;

  const handleDoubleClick = (doc: Document) => {
    if (!onRenameDocument) return;
    setEditingId(doc.id);
    setEditValue(doc.title);
  };

  const handleRenameSubmit = () => {
    if (editingId && editValue.trim() && onRenameDocument) {
      onRenameDocument(editingId, editValue.trim());
    }
    setEditingId(null);
  };

  const handleRenameKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleRenameSubmit();
    } else if (e.key === 'Escape') {
      setEditingId(null);
    }
  };

  const handleDelete = (e: React.MouseEvent, docId: string) => {
    e.stopPropagation();
    if (onDeleteDocument && window.confirm('Delete this document? This cannot be undone.')) {
      onDeleteDocument(docId);
    }
  };

  return (
    <div className="document-tabs-container">
      <div className="document-tabs">
        {documents.map((doc) => (
          <button
            key={doc.id}
            className={`document-tab ${doc.id === activeDocumentId ? 'active' : ''}`}
            onClick={() => onDocumentSelect(doc.id)}
            onDoubleClick={() => handleDoubleClick(doc)}
            title={doc.title}
          >
            {editingId === doc.id ? (
              <input
                ref={inputRef}
                className="tab-rename-input"
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                onKeyDown={handleRenameKeyDown}
                onBlur={handleRenameSubmit}
                onClick={(e) => e.stopPropagation()}
                maxLength={200}
              />
            ) : (
              <span className="tab-title">{doc.title}</span>
            )}
            {documents.length > 1 && onDeleteDocument && editingId !== doc.id && (
              <span
                className="tab-close-btn"
                role="button"
                tabIndex={0}
                onClick={(e) => handleDelete(e, doc.id)}
                onKeyDown={(e) => { if (e.key === 'Enter') handleDelete(e as unknown as React.MouseEvent, doc.id); }}
                title="Close document"
              >
                &times;
              </span>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
```

### 4.5 Style Tab Close and Rename

**File:** `frontend/src/components/DocumentTabs/DocumentTabs.css`

**Add rules:**

```css
.document-tab {
  position: relative;
  padding-right: 24px;  /* make room for close button */
}

.tab-close-btn {
  position: absolute;
  right: 4px;
  top: 50%;
  transform: translateY(-50%);
  opacity: 0;
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 3px;
  font-size: 14px;
  color: #888;
  cursor: pointer;
  transition: opacity 0.15s, background 0.15s;
}

.document-tab:hover .tab-close-btn {
  opacity: 1;
}

.tab-close-btn:hover {
  background: rgba(0, 0, 0, 0.1);
  color: #c62828;
}

.tab-rename-input {
  background: white;
  border: 1px solid #006FCF;
  border-radius: 3px;
  padding: 1px 4px;
  font-size: inherit;
  font-family: inherit;
  width: 120px;
  outline: none;
}

/* NOTE (Plan 009a): Replace hardcoded colors above with CSS variables:
   .tab-close-btn:hover { background: var(--signal-error-muted); color: var(--signal-error); }
   .tab-rename-input { background: var(--surface-raised); border-color: var(--accent-primary); color: var(--text-primary); }
   Dark/light handled automatically via theme.css. No @media dark mode block needed. */
```

### 4.6 Wire Up in App.tsx

**File:** `frontend/src/App.tsx`

**Add handlers in ChatApp:**

```typescript
const handleRenameDocument = useCallback(async (docId: string, newTitle: string) => {
  try {
    await api.renameDocument(docId, newTitle);
    await refreshDocuments();
  } catch (err) {
    setError(err instanceof Error ? err.message : 'Failed to rename document');
  }
}, [refreshDocuments]);

const handleDeleteDocument = useCallback(async (docId: string) => {
  if (!sessionId) return;
  try {
    await api.deleteDocument(sessionId, docId);
    await refreshDocuments();
  } catch (err) {
    setError(err instanceof Error ? err.message : 'Failed to delete document');
  }
}, [sessionId, refreshDocuments]);
```

**Pass to HtmlViewer → DocumentTabs:**
- HtmlViewer props: add `onRenameDocument`, `onDeleteDocument`
- Pass through to DocumentTabs
- In ChatApp: pass `onRenameDocument={handleRenameDocument}` and `onDeleteDocument={handleDeleteDocument}` to HtmlViewer

### 4.7 Add Backend Tests

**File:** `backend/tests/test_document_management.py` (NEW)

Test cases:
- `test_rename_document_success` — rename returns true, title updated
- `test_rename_nonexistent_document` — returns 404
- `test_delete_document_success` — document removed, versions cascaded
- `test_delete_last_document_blocked` — returns 400
- `test_delete_active_document_activates_another` — another doc becomes active
- `test_delete_document_nullifies_chat_messages` — chat_messages.document_id set to NULL

### Build Verification (Phase 4)
```bash
cd backend && ruff check app/services/session_service.py app/api/sessions.py
cd backend && mypy app/services/session_service.py app/api/sessions.py
cd backend && python -m pytest tests/test_document_management.py -v
cd frontend && npx tsc --noEmit
```

---

## Phase 5: Cancel Button (P1)

### Objective
Expose the existing `cancelRequest()` function from `useSSEChat.ts` in the UI.

### 5.1 Pass cancelRequest Through Component Chain

**File:** `frontend/src/App.tsx`

**Destructure `cancelRequest` from useSSEChat (line 209):**
```typescript
const {
  ...existing...
  cancelRequest,
} = useSSEChat({...});
```

**Pass to ChatWindow:**
```typescript
<ChatWindow
  ...existing props...
  onCancelRequest={cancelRequest}
/>
```

### 5.2 Update ChatWindow Props

**File:** `frontend/src/components/ChatWindow/index.tsx`

**Add `onCancelRequest` to interface and pass to ChatInput:**

```typescript
interface ChatWindowProps {
  ...existing...
  onCancelRequest?: () => void;
}

// In the component, pass to ChatInput:
<ChatInput
  ...existing props...
  onCancelRequest={onCancelRequest}
/>
```

### 5.3 Add Cancel Button to ChatInput

**File:** `frontend/src/components/ChatWindow/ChatInput.tsx`

**Add `onCancelRequest` to ChatInputProps interface:**
```typescript
interface ChatInputProps {
  ...existing...
  onCancelRequest?: () => void;
}
```

**Destructure it:**
```typescript
const ChatInput: React.FC<ChatInputProps> = ({
  ...existing...
  onCancelRequest,
}) => {
```

**In the send button area (lines 205-222), add cancel button when processing:**

Replace the button with:
```typescript
{isProcessing ? (
  <button
    type="button"
    className="cancel-button"
    onClick={onCancelRequest}
    title="Cancel generation"
  >
    Cancel
  </button>
) : (
  <button
    type="submit"
    disabled={!message.trim() || isProcessing}
    className="send-button"
    title="Send message (Ctrl/Cmd + Enter)"
  >
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
      <path d="M2,21L23,12L2,3V10L17,12L2,14V21Z" />
    </svg>
  </button>
)}
```

### 5.4 Style Cancel Button

**File:** `frontend/src/components/ChatWindow/ChatInput.css`

**Add rules:**

```css
.cancel-button {
  background: #e53935;
  color: white;
  border: none;
  border-radius: 8px;
  padding: 8px 16px;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
  white-space: nowrap;
}

.cancel-button:hover {
  background: #c62828;
}

/* NOTE (Plan 009a): Replace hardcoded colors above with CSS variables:
   .cancel-button { background: var(--signal-error); color: var(--text-inverse); }
   .cancel-button:hover { background: #b71c1c; -- or darken var(--signal-error) }
   Dark/light handled automatically via theme.css. No @media dark mode block needed. */
```

### Build Verification (Phase 5)
```bash
cd frontend && npx tsc --noEmit
cd frontend && npm run build
```

---

## Phase 6: Viewer Header Cleanup (P1)

### Objective
Group viewer header buttons into logical clusters with visual separators.

### 6.1 Reorganize Header Layout

**File:** `frontend/src/App.tsx`

**Replace the `viewer-actions` div (lines 141-167) with grouped layout:**

```typescript
<div className="viewer-actions">
  <div className="action-group action-group--primary">
    <button
      className={`history-btn${historyOpen ? ' active' : ''}`}
      onClick={onToggleHistory}
      disabled={!activeDocumentId}
      title="Version history"
    >
      History
    </button>
    <ExportDropdown
      onExportHtml={handleExport}
      disabled={!currentHtml}
      documentId={activeDocumentId}
      documentTitle={documentTitle}
    />
  </div>
  <div className="action-group action-group--secondary">
    <button
      className="save-template-btn"
      onClick={handleSaveTemplate}
      disabled={!currentHtml}
      title="Save current document as a reusable template"
    >
      Save Template
    </button>
    <button
      className="fullscreen-btn"
      onClick={handleFullScreen}
      disabled={!currentHtml}
      title="Open in new tab"
    >
      Full Screen
    </button>
  </div>
</div>
```

### 6.2 Style Action Groups

**File:** `frontend/src/App.css`

**Add/modify rules:**

```css
.action-group {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.action-group--primary {
  /* Primary actions keep current styling */
}

.action-group--secondary {
  padding-left: 0.75rem;
  border-left: 1px solid #e0e0e0;
}

.action-group--secondary button {
  opacity: 0.7;
  font-size: 0.8rem;
}

.action-group--secondary button:hover {
  opacity: 1;
}

/* NOTE (Plan 009a): Replace hardcoded colors above with CSS variables:
   .action-group--secondary { border-left-color: var(--border-default); }
   Dark/light handled automatically via theme.css. No @media dark mode block needed. */
```

### Build Verification (Phase 6)
```bash
cd frontend && npx tsc --noEmit
cd frontend && npm run build
```

---

## Phase 7: Drag-and-Drop Upload (P1)

### Objective
Add drag-and-drop file upload to the chat input area, reusing existing upload logic.

### 7.1 Add Drag-and-Drop Handlers

**File:** `frontend/src/components/ChatWindow/ChatInput.tsx`

**Add state:**
```typescript
const [isDragging, setIsDragging] = useState(false);
```

**Add handler function (reuses existing `uploadFile` and `validateFileClient`):**

```typescript
const handleDrop = async (e: React.DragEvent) => {
  e.preventDefault();
  setIsDragging(false);
  const file = e.dataTransfer.files[0];
  if (!file) return;

  const validationError = validateFileClient(file);
  if (validationError) {
    setUploadError(validationError);
    return;
  }

  setIsUploading(true);
  setUploadError(null);
  try {
    const result: UploadResponse = await uploadFile(file);
    setMessage(result.suggested_prompt);
    setAttachedFile({ name: result.data.filename });
    textareaRef.current?.focus();
  } catch (err) {
    setUploadError(err instanceof Error ? err.message : 'Upload failed');
  } finally {
    setIsUploading(false);
  }
};
```

**Add drag event handlers to the `<form>` element (line 160):**

```typescript
<form
  className={`chat-input-container ${isDragging ? 'dragging' : ''}`}
  onSubmit={handleSubmit}
  onDragEnter={(e) => { e.preventDefault(); setIsDragging(true); }}
  onDragOver={(e) => { e.preventDefault(); }}
  onDragLeave={(e) => {
    e.preventDefault();
    // Only set false if leaving the form itself (not entering a child)
    if (e.currentTarget === e.target) setIsDragging(false);
  }}
  onDrop={handleDrop}
>
  {isDragging && (
    <div className="drop-overlay">
      <span>Drop file here to upload</span>
    </div>
  )}
  ...rest of form...
</form>
```

### 7.2 Style Drop Zone

**File:** `frontend/src/components/ChatWindow/ChatInput.css`

**Add rules:**

```css
.chat-input-container {
  position: relative;  /* needed for overlay positioning */
}

.chat-input-container.dragging {
  border-color: #006FCF;
}

.drop-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 111, 207, 0.08);
  border: 2px dashed #006FCF;
  border-radius: 12px;
  z-index: 10;
  pointer-events: none;
  font-size: 1rem;
  color: #006FCF;
  font-weight: 600;
}

/* NOTE (Plan 009a): Replace hardcoded colors above with CSS variables:
   .drop-overlay { background: var(--accent-primary-muted); border-color: var(--accent-primary); color: var(--accent-primary); }
   Dark/light handled automatically via theme.css. No @media dark mode block needed. */
```

### Build Verification (Phase 7)
```bash
cd frontend && npx tsc --noEmit
cd frontend && npm run build
```

---

## Final Verification

### Automated Tests
```bash
# Backend
cd backend && ruff check app/services/session_service.py app/api/sessions.py
cd backend && mypy app/services/session_service.py app/api/sessions.py
cd backend && python -m pytest tests/ -v

# Frontend
cd frontend && npx tsc --noEmit
cd frontend && npm run build
```

### Manual Testing Checklist
- [ ] Generate a document → viewer shows skeleton during generation → HTML appears
- [ ] Export > PowerPoint → .pptx file downloads
- [ ] Export > PDF → .pdf file downloads
- [ ] Export > Image (PNG) → .png file downloads
- [ ] Export > HTML → .html file downloads (still works)
- [ ] All export buttons disabled when no document
- [ ] Open version history → click old version → "Restore this version" button visible
- [ ] Click Restore → confirmation → viewer shows restored HTML
- [ ] Double-click document tab → inline rename → Enter saves
- [ ] Click X on tab → confirmation → document deleted, switches to another tab
- [ ] X button hidden when only 1 document remains
- [ ] While streaming → Cancel button visible → click → stops streaming
- [ ] After cancel → can send new message normally
- [ ] Viewer header: buttons grouped with visual separator
- [ ] Drag .docx file over input → "Drop file here" overlay → drop → uploads
- [ ] All features work in both dark and light themes (toggle via ThemeToggle from Plan 009a)

### Expected Test Results
- Backend: 250+/251 tests passing (1 pre-existing failure: `test_init_db_creates_file`)
- Frontend: TypeScript clean, Vite build clean
- Ruff: Clean
- Mypy: Clean on modified files

---

## Sign-off Checklist

- [ ] Phase 1: Export formats wired to backend API (PPTX, PDF, PNG)
- [ ] Phase 2: Loading skeleton shows during HTML generation
- [ ] Phase 3: Version restore creates new version from old HTML
- [ ] Phase 4: Document rename (double-click) and delete (X button) work
- [ ] Phase 5: Cancel button stops streaming requests
- [ ] Phase 6: Viewer header buttons grouped and styled
- [ ] Phase 7: Drag-and-drop file upload works
- [ ] All automated tests pass
- [ ] Both dark and light themes tested for all new UI elements (CSS variables from theme.css)
- [ ] No modifications to export backend, chat API, router, or system prompts

---

## Rollback Plan

All changes are incremental. Phases are independent enough to revert individually.

**If export wiring fails:** Revert `ExportDropdown.tsx` and `api.ts` export method. "Coming soon" labels return.

**If backend endpoints fail:** Revert `session_service.py` and `sessions.py` additions. Frontend calls will 404 but won't crash — just error banners.

**If drag-and-drop causes issues:** Revert `ChatInput.tsx` drag handlers and CSS. Button upload still works.

**Full rollback:** Single `git revert` of the commit.
