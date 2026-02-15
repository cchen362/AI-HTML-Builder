# Plan 020a: Architecture Refactoring

## Status: COMPLETE

## Problem Statement

The 020 Review identified 15 architecture items. 13 are approved for cleanup to establish a clean foundation before future UX enhancements. This plan covers the refactoring only — no new features, no behavior changes.

**Skipped**: A4 (providers per-request — no functional impact at 2-5 users), A8 (`.dockerignore` already exists and is well-configured)

---

## Phase 1: Pure Deletions & One-Line Fixes

**Risk**: Zero. Dead code removal and cosmetic fixes. Cannot break anything.

### A1: Delete Dead SVG Code (~130 lines)

Per Plan 015, the SVG branch was removed from the image handler — diagrams route to the editor. But the SVG template functions were never deleted. Nobody calls them.

**File: `backend/app/services/image_service.py`**

Delete (bottom-up to keep line numbers stable):
1. `_placeholder_svg()` (lines 302-311)
2. `_timeline_svg()` (lines 282-299)
3. `_chart_svg()` (lines 261-279)
4. `_flowchart_svg()` (lines 235-258)
5. `_get_svg_template()` (lines 224-232)
6. `generate_svg_and_embed()` method (lines 171-180)
7. `should_use_svg()` method (lines 120-133)
8. `SVG_KEYWORDS` dict (lines 25-38)
9. Update module docstring (lines 1-8): remove line 5 ("1. SVG templates for diagrams/charts (zero API cost)") and simplify to describe raster-only image service

**File: `backend/tests/test_image_service.py`**

1. Remove dead imports: `_flowchart_svg`, `_chart_svg`, `_timeline_svg`, `_placeholder_svg` (lines 12-15)
2. Delete `should_use_svg` tests (lines 46-82) — 6 tests
3. Delete `generate_svg_and_embed` tests (lines 105-136) — 4 tests
4. Delete SVG color tests (lines 170-196) — 4 tests

**Net**: ~130 source lines, ~100 test lines deleted. 14 tests removed.

---

### A10: Fix Known Failing Test

The `templates` table was removed in Plan 011 but the test still checks for it.

**File: `backend/tests/test_database.py`**

Line 75: Remove `"templates"` from the expected set:
```python
# Before
expected = {
    "sessions", "documents", "document_versions",
    "chat_messages", "cost_tracking", "templates",
}

# After
expected = {
    "sessions", "documents", "document_versions",
    "chat_messages", "cost_tracking",
}
```

---

### A12: Add `exc_info=True` to Chat Error Logging

Missing stack trace makes production debugging impossible.

**File: `backend/app/api/chat.py`**

Line 554-559: Add `exc_info=True`:
```python
logger.error(
    "Chat error",
    error=str(e),
    error_type=type(e).__name__,
    session_id=session_id[:8],
    exc_info=True,  # ← ADD THIS
)
```

Reference: `backend/app/api/export.py` line 133 already does this correctly.

---

### A13: Standardize Type Annotations in fuzzy_match.py

Only file using the old `Optional[str]` style. Everything else uses `str | None`.

**File: `backend/app/utils/fuzzy_match.py`**

1. Line 16: Delete `from typing import Optional`
2. Lines 21, 49, 72, 97: Replace `Optional[str]` → `str | None`

---

### A14: Simplify Redundant Conditional in Export Service

After the `!= "png"` guard raises, the `== "png"` check is always true.

**File: `backend/app/services/export_service.py`**

Lines 87-99, simplify:
```python
# Before
if is_infographic_html(html_content):
    if format_key.lower() != "png":
        raise ExportError(
            "Infographic documents can only be exported as PNG"
        )
    if format_key.lower() == "png":  # ← ALWAYS TRUE
        from app.services.exporters.playwright_exporter import (
            export_infographic_png,
        )
        if options is None:
            options = ExportOptions(document_title=document_id[:50])
        return await export_infographic_png(html_content, options)

# After
if is_infographic_html(html_content):
    if format_key.lower() != "png":
        raise ExportError(
            "Infographic documents can only be exported as PNG"
        )
    from app.services.exporters.playwright_exporter import (
        export_infographic_png,
    )
    if options is None:
        options = ExportOptions(document_title=document_id[:50])
    return await export_infographic_png(html_content, options)
```

### Phase 1 Verification
```bash
cd backend && python -m pytest tests/ -x   # All pass, 14 fewer tests, A10 test now passes
cd backend && ruff check . && mypy .        # Clean
```

---

## Phase 2: Safety Hardening

**Risk**: Low. Small targeted changes to error handling. Testable in isolation.

### A5: Fix Silent Route Fallthrough

If the router returns an unexpected value, users get no response and no error — just silence.

**File: `backend/app/api/chat.py`**

Lines 544-551: Add error handling for unknown routes:
```python
# Before
else:
    handler = None

if handler:
    async for event in handler:
        yield _sse(event)

yield _sse({"type": "done"})

# After
else:
    handler = None

if handler:
    async for event in handler:
        yield _sse(event)
else:
    logger.warning(
        "Unexpected route from classifier",
        route=route,
        session_id=session_id[:8],
    )
    yield _sse({
        "type": "error",
        "content": "Unable to process your request. Please try again.",
    })

yield _sse({"type": "done"})
```

---

### A6: Fix Migration Error Swallowing

The bare `except Exception: pass` hides genuine errors (disk full, permissions, corruption).

**File: `backend/app/database.py`**

Lines 33-38:
```python
# Before
for migration in _MIGRATIONS:
    try:
        await _db.execute(migration)
    except Exception:
        pass  # Column already exists

# After
for migration in _MIGRATIONS:
    try:
        await _db.execute(migration)
    except Exception as e:
        # ADD COLUMN raises OperationalError with "duplicate column"
        # when column already exists — safe to ignore.
        # All other errors must propagate.
        if "duplicate column" not in str(e).lower():
            raise
```

**Note**: `aiosqlite` wraps `sqlite3.OperationalError` — checking the string message is the most reliable approach. The string "duplicate column" is stable across all SQLite 3.x versions.

---

### A7: Replace `assert` with `if/raise`

`assert` is a debug tool — disabled by `python -O`. Production code must use proper exceptions.

**File: `backend/app/services/session_service.py`**

Line 122:
```python
# Before
assert row is not None  # COALESCE guarantees a result

# After
if row is None:
    raise RuntimeError(
        f"Failed to determine next version for document {document_id}"
    )
```

Line 232:
```python
# Before
assert row is not None

# After
if row is None:
    raise RuntimeError(
        f"Failed to count documents for session {session_id}"
    )
```

**File: `backend/app/utils/file_processors.py`** (bonus — same pattern, file is already modified in Phase 4)

Line 179:
```python
# Before
assert sheet is not None

# After
if sheet is None:
    raise FileProcessingError("Excel workbook has no active sheet")
```

### Phase 2 Verification
```bash
cd backend && python -m pytest tests/ -x   # All pass
cd backend && ruff check . && mypy .        # Clean
```

---

## Phase 3: Extract Shared Utilities

**Risk**: Medium. Creates new files, changes import paths. More moving parts.

### A3: Extract Duplicated Export Utilities

`_validate_html()` and `_generate_filename()`/`_sanitize_title()` are copy-pasted between two files.

**Create: `backend/app/utils/export_utils.py`**

```python
"""Shared utilities for document export."""

from app.services.exporters.base import ExportError


def validate_html(html_content: str) -> None:
    """Validate HTML content before export. Raises ExportError on failure."""
    if not html_content or not html_content.strip():
        raise ExportError("HTML content is empty")
    stripped = html_content.strip()
    if not stripped.startswith("<!DOCTYPE") and not stripped.startswith("<html"):
        raise ExportError("Invalid HTML: must start with <!DOCTYPE or <html>")


def sanitize_title(title: str) -> str:
    """Sanitize document title for use in filenames."""
    safe = "".join(
        c if c.isalnum() or c in (" ", "-", "_") else "_"
        for c in title
    ).strip()
    return safe or "document"


def generate_filename(title: str, extension: str) -> str:
    """Generate sanitized filename for exported document."""
    return f"{sanitize_title(title)}.{extension}"
```

**Modify: `backend/app/services/export_service.py`**

1. Delete `_validate_html()` (lines 28-34) and `_sanitize_title()` (lines 37-43)
2. Add: `from app.utils.export_utils import validate_html, sanitize_title`
3. Update `_export_html()`: `_validate_html(...)` → `validate_html(...)`, `_sanitize_title(...)` → `sanitize_title(...)`

**Modify: `backend/app/services/exporters/playwright_exporter.py`**

1. Delete `_validate_html()` (lines 64-70) and `_generate_filename()` (lines 73-81)
2. Add: `from app.utils.export_utils import validate_html, generate_filename`
3. Update all callers: `_validate_html(...)` → `validate_html(...)`, `_generate_filename(...)` → `generate_filename(...)`

---

### A2: Extract Shared Image Retry Logic

The retry logic is copy-pasted between `image_service.py` and `infographic_service.py` — same 3-attempt strategy, same timeout handling, same exception patterns.

**Create: `backend/app/utils/image_retry.py`**

```python
"""Shared image generation retry logic with fallback."""

from __future__ import annotations

import asyncio

import structlog

from app.providers.base import ImageProvider, ImageResponse

logger = structlog.get_logger()


async def generate_image_with_retry(
    primary: ImageProvider,
    prompt: str,
    resolution: str,
    timeout: float,
    fallback: ImageProvider | None = None,
    context: str = "image",
) -> ImageResponse:
    """Generate image with retry on primary, then fallback to secondary model.

    Strategy:
        1. Primary model, attempt 1 (timeout seconds)
        2. Primary model, attempt 2 — most 503s resolve on retry
        3. Fallback model (30s timeout) — different capacity pool
        4. Raise if all fail
    """
    # Attempt 1: Primary
    try:
        return await asyncio.wait_for(
            primary.generate_image(prompt, resolution),
            timeout=timeout,
        )
    except (asyncio.TimeoutError, RuntimeError, Exception) as e:
        logger.warning(
            f"{context.capitalize()} generation attempt 1 failed",
            error=str(e),
            error_type=type(e).__name__,
        )

    # Attempt 2: Primary retry
    try:
        return await asyncio.wait_for(
            primary.generate_image(prompt, resolution),
            timeout=timeout,
        )
    except (asyncio.TimeoutError, RuntimeError, Exception) as e:
        logger.warning(
            f"{context.capitalize()} generation attempt 2 failed",
            error=str(e),
            error_type=type(e).__name__,
        )

    # Attempt 3: Fallback model
    if fallback:
        logger.info(f"Falling back to secondary {context} model")
        try:
            return await asyncio.wait_for(
                fallback.generate_image(prompt, resolution),
                timeout=30,
            )
        except (asyncio.TimeoutError, RuntimeError, Exception) as e:
            logger.error(
                f"Fallback {context} generation failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise RuntimeError(
                f"{context.capitalize()} generation failed after all attempts"
            ) from e

    raise RuntimeError(
        f"{context.capitalize()} generation failed and no fallback configured"
    )
```

**Modify: `backend/app/services/image_service.py`**

1. Delete `_generate_with_retry()` method (lines 52-118)
2. In `generate_and_embed()`, replace `self._generate_with_retry(prompt, resolution)` with:
   ```python
   from app.config import settings
   from app.utils.image_retry import generate_image_with_retry

   img_response = await generate_image_with_retry(
       primary=self.image_provider,
       prompt=prompt,
       resolution=resolution,
       timeout=settings.image_timeout_seconds,
       fallback=self.fallback_provider,
       context="image",
   )
   ```
3. Keep the `if not self.image_provider: raise` guard above (line 142) — it runs before retry

**Modify: `backend/app/services/infographic_service.py`**

1. Delete `_generate_image_with_retry()` method (lines 225-287)
2. In `generate()` (line 146), replace `self._generate_image_with_retry(visual_prompt, "2k")` with:
   ```python
   from app.config import settings
   from app.utils.image_retry import generate_image_with_retry

   img_response = await generate_image_with_retry(
       primary=self.image_provider,
       prompt=visual_prompt,
       resolution="2k",
       timeout=settings.image_timeout_seconds,
       fallback=self.fallback_image_provider,
       context="infographic",
   )
   ```
3. Remove `import asyncio` if no longer used elsewhere in the file

**Modify: `backend/tests/test_image_service.py`**

The retry tests (lines 218-317) currently call `service._generate_with_retry()` directly. Update them to test the standalone function:

```python
# Before
result = await service._generate_with_retry("test prompt", "hd")

# After
from app.utils.image_retry import generate_image_with_retry
result = await generate_image_with_retry(
    primary=mock_provider,
    prompt="test prompt",
    resolution="hd",
    timeout=90,
    fallback=mock_fallback,  # or None
    context="image",
)
```

Update all 5 retry tests (lines 221-317) to use the standalone function. Update error message matchers where needed (e.g., `match="Image generation failed"` → `match="generation failed"`).

### Phase 3 Verification
```bash
cd backend && python -m pytest tests/ -x                    # All pass
cd backend && python -m pytest tests/test_image_service.py   # Retry tests work
cd backend && python -m pytest tests/test_export*.py         # Export tests work
cd backend && ruff check . && mypy .                         # Clean
```

---

## Phase 4: Provider & Async Fixes

**Risk**: Medium. Changes ABC hierarchy and async behavior.

### A15: Fix Liskov Substitution Violation

`GeminiProvider` inherits from `LLMProvider` but throws `NotImplementedError` on `generate_with_tools()`. This violates the Liskov Substitution Principle.

**Approach**: Make `generate_with_tools()` non-abstract with a default `NotImplementedError`. This is the least disruptive fix — no interface splitting, no caller changes.

**File: `backend/app/providers/base.py`**

Lines 71-81: Remove `@abstractmethod`, add default implementation:
```python
# Before
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

# After
async def generate_with_tools(
    self,
    system: str | list[dict],
    messages: list[dict],
    tools: list[dict],
    max_tokens: int = 4096,
    temperature: float = 0.0,
) -> ToolResult:
    """Generate a response using tool definitions. Used for surgical editing.

    Not all providers support tool use. Override in providers that do
    (e.g., AnthropicProvider). Default raises NotImplementedError.
    """
    raise NotImplementedError(
        f"{type(self).__name__} does not support tool-based generation"
    )
```

**File: `backend/app/providers/gemini_provider.py`**

Lines 100-110: Delete the entire `generate_with_tools()` override — the base class default now provides the same behavior.

**File: `backend/tests/test_gemini_provider.py`**

Line 205: Update error message matcher:
```python
# Before
with pytest.raises(NotImplementedError, match="Gemini is not used"):

# After
with pytest.raises(NotImplementedError, match="does not support tool-based generation"):
```

---

### A11: Wrap Sync I/O in `asyncio.to_thread()`

`process_file()` is declared `async` but does only synchronous I/O (PDF parsing, DOCX parsing, etc.), blocking the event loop.

**File: `backend/app/utils/file_processors.py`**

1. Add `import asyncio` at top
2. Rename current `process_file()` body to `_process_file_sync()` (regular sync function)
3. Make `process_file()` a thin async wrapper:

```python
async def process_file(filename: str, content: bytes) -> dict[str, Any]:
    """Process an uploaded file and return extracted content.

    Runs synchronous file parsing in a thread to avoid blocking the event loop.
    """
    return await asyncio.to_thread(_process_file_sync, filename, content)


def _process_file_sync(filename: str, content: bytes) -> dict[str, Any]:
    """Synchronous file processing implementation."""
    ext = _get_extension(filename)

    if ext in {".txt", ".md"}:
        text = _process_text(content)
        return _text_result(filename, ext, text)

    # ... rest of existing logic, unchanged ...
```

4. Also fix `assert sheet is not None` (line 179) → `if sheet is None: raise FileProcessingError(...)` (from Phase 2 A7 bonus)

### Phase 4 Verification
```bash
cd backend && python -m pytest tests/ -x                       # All pass
cd backend && python -m pytest tests/test_gemini_provider.py    # A15 test works
cd backend && python -m pytest tests/test_file_processors.py    # A11 still passes
cd backend && ruff check . && mypy .                            # Clean
```

---

## Phase 5: Pin Requirements

**Risk**: Low but requires capturing real versions.

### A9: Pin `requirements.txt` Versions

**File: `backend/requirements.txt`**

Change all `>=X.Y.Z` to `==X.Y.Z` using exact installed versions.

**Process**:
1. Activate backend venv: `cd backend && venv\Scripts\activate` (Windows)
2. Run `pip freeze` to capture exact versions of each listed package
3. Replace `>=` with `==` using the frozen versions
4. Keep `[standard]` extras on uvicorn: `uvicorn[standard]==X.Y.Z`
5. Docker rebuild serves as verification that pinned versions resolve correctly

**Example** (versions TBD from `pip freeze`):
```
# Before
fastapi>=0.111.0
anthropic>=0.40.0

# After
fastapi==0.115.0
anthropic==0.42.0
```

### Phase 5 Verification
```bash
# Local verification
cd backend && pip install -r requirements.txt   # All resolve

# Full verification via Docker build
docker build -t ai-html-builder .               # Succeeds
```

---

## Post-Phase: Housekeeping

After all phases complete:

1. **CLAUDE.md updates**:
   - Add Plan 020a to implementation plans table
   - Remove known test failure bullet (`test_init_db_creates_file` reference)
   - Update test count after SVG test removal
   - Update `image_service.py` description (remove SVG mention)

2. **MEMORY.md**: Add Plan 020a status

---

## Files Summary

| Action | File | Items |
|--------|------|-------|
| Modify | `backend/app/services/image_service.py` | A1 (delete SVG), A2 (extract retry) |
| Modify | `backend/app/services/infographic_service.py` | A2 (extract retry) |
| Modify | `backend/app/services/export_service.py` | A3 (extract utils), A14 (simplify conditional) |
| Modify | `backend/app/services/exporters/playwright_exporter.py` | A3 (extract utils) |
| Modify | `backend/app/services/session_service.py` | A7 (assert→if/raise) |
| Modify | `backend/app/api/chat.py` | A5 (route fallthrough), A12 (exc_info) |
| Modify | `backend/app/database.py` | A6 (migration errors) |
| Modify | `backend/app/providers/base.py` | A15 (remove @abstractmethod) |
| Modify | `backend/app/providers/gemini_provider.py` | A15 (remove override) |
| Modify | `backend/app/utils/fuzzy_match.py` | A13 (type annotations) |
| Modify | `backend/app/utils/file_processors.py` | A11 (asyncio.to_thread), A7 (assert fix) |
| Modify | `backend/requirements.txt` | A9 (pin versions) |
| Modify | `backend/tests/test_image_service.py` | A1 (delete SVG tests), A2 (update retry tests) |
| Modify | `backend/tests/test_database.py` | A10 (remove templates) |
| Modify | `backend/tests/test_gemini_provider.py` | A15 (update error match) |
| Create | `backend/app/utils/export_utils.py` | A3 |
| Create | `backend/app/utils/image_retry.py` | A2 |

**Total**: 15 files modified, 2 files created. ~260 lines deleted, ~100 lines extracted to shared utilities.

---

## Deployment

Standard workflow after all phases pass locally:
```bash
git push origin main
# On server:
ssh chee@100.94.82.35
cd ~/aihtml && ./deploy.sh
```

The Docker build (`pip install -r requirements.txt`) validates A9 pinned versions. The health check validates the app starts correctly.
