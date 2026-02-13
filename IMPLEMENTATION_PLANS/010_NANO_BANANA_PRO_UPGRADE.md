# Implementation Plan 010: Nano Banana Pro Image Model Upgrade

## Status: COMPLETE

---

## STOP - READ THIS FIRST

**DO NOT START** this implementation until:
- Plans 001-007, 009a, 009b are FULLY complete (they are)
- You have read this ENTIRE document
- You understand the current image pipeline: `config.py` → `GeminiImageProvider` → `ImageService` → `chat.py` IMAGE route
- You understand the SSE status event flow: backend sends `{"type": "status", "content": "..."}` → frontend `useSSEChat.ts` sets `currentStatus` → `ChatWindow/index.tsx` renders `[>] ${currentStatus}` in the status bar

**DESTRUCTIVE ACTIONS PROHIBITED:**
- Do NOT modify the SSE streaming protocol (event types, format)
- Do NOT modify `useSSEChat.ts` or any frontend file
- Do NOT modify the routing logic in `services/router.py` (beyond docstring)
- Do NOT modify `EDIT_SYSTEM_PROMPT` or `CREATION_SYSTEM_PROMPT`
- Do NOT add new API endpoints
- Do NOT add UI toggles or user-facing model selection
- Do NOT modify `IMPLEMENTATION_PLANS/` files other than this one

**DEPENDENCIES:**
- Plan 003: Multi-Model Routing (Gemini image provider)
- Plan 009a: Visual Foundation (provides the status bar UI via CSS custom properties)

**ESTIMATED EFFORT:** 1 day

---

## Context

The codebase currently uses `gemini-2.0-flash-preview-image-generation` for image generation. The intended model is **Nano Banana Pro** (`gemini-3-pro-image-preview`), Google's Gemini 3 Pro Image model released November 2025.

### Why the upgrade

| | Current (Gemini 2.0 Flash) | Target (Nano Banana Pro) |
|---|---|---|
| Text rendering in images | Basic, often garbled | Best-in-class, legible paragraphs |
| Complex prompt following | Moderate | High (uses "Thinking" reasoning) |
| Max resolution | 2K | 4K |
| Cost per image (1K/2K) | ~$0.039 | ~$0.134 |
| Typical latency | 3-5 seconds | 20-40 seconds |
| Peak-hour error rate | Low | ~45% (503/429 during peaks) |

### Key design decisions

1. **90-second timeout** (not 45s): The 503/429 errors fail fast (1-3s), not via timeout. Real hangs are rare. 45s would abort ~15-20% of legitimate slow generations. 90s is a safety net.

2. **Retry once before fallback**: Most 503s resolve on immediate retry (token bucket refills). Retry adds ~2-5s (fast failures), not 20-40s. Falling back too eagerly gives users lower quality unnecessarily.

3. **No UI toggle**: 2-5 users, complexity not justified. Flash is purely a resilience mechanism, not a user choice.

4. **Zero frontend changes**: The Plan 009a status bar (`[>] ${currentStatus}`) already renders any SSE status event dynamically. We just send better status messages from the backend.

---

## Phase 1: Update Model Config

### File: `backend/app/config.py`

Change the `image_model` default and add two new fields:

```python
# BEFORE
image_model: str = "gemini-2.0-flash-preview-image-generation"

# AFTER
image_model: str = "gemini-3-pro-image-preview"
image_fallback_model: str = "gemini-2.5-flash-image"
image_timeout_seconds: int = 90
```

**Environment variable overrides**: `IMAGE_MODEL`, `IMAGE_FALLBACK_MODEL`, `IMAGE_TIMEOUT_SECONDS`

### Verification
- `ruff check backend/app/config.py`
- `mypy backend/app/config.py`
- Existing tests that instantiate `Settings()` still pass

---

## Phase 2: Update Cost Tracking

### File: `backend/app/services/cost_tracker.py`

Update the `MODEL_PRICING` dictionary:

```python
# BEFORE
MODEL_PRICING: dict[str, dict[str, float]] = {
    "claude-sonnet-4-5-20250929": {"input": 3.0, "output": 15.0},
    "gemini-2.5-pro": {"input": 1.25, "output": 10.0},
    "gemini-2.0-flash-preview-image-generation": {"input": 0.1, "output": 0.4},
}

# AFTER
MODEL_PRICING: dict[str, dict[str, float]] = {
    "claude-sonnet-4-5-20250929": {"input": 3.0, "output": 15.0},
    "gemini-2.5-pro": {"input": 1.25, "output": 10.0},
    "gemini-3-pro-image-preview": {"input": 0.0, "output": 120.0},
    "gemini-2.5-flash-image": {"input": 0.0, "output": 30.0},
}
```

Pricing rationale:
- Nano Banana Pro: ~1,120 output tokens/image × $120/M output tokens = ~$0.134/image
- Nano Banana Flash: ~1,290 output tokens/image × $30/M output tokens = ~$0.039/image
- Input tokens set to 0.0 because image generation input is negligible

### Verification
- `ruff check backend/app/services/cost_tracker.py`
- `mypy backend/app/services/cost_tracker.py`
- Existing cost tracker tests still pass

---

## Phase 3: Add Retry + Fallback Logic to Image Service

### File: `backend/app/services/image_service.py`

#### 3a. Update `__init__` signature

```python
# BEFORE
class ImageService:
    def __init__(self, image_provider: ImageProvider | None = None):
        self.image_provider = image_provider

# AFTER
class ImageService:
    def __init__(
        self,
        image_provider: ImageProvider | None = None,
        fallback_provider: ImageProvider | None = None,
    ):
        self.image_provider = image_provider
        self.fallback_provider = fallback_provider
```

#### 3b. Add `_generate_with_retry` private method

Add this method to the `ImageService` class, AFTER `__init__` and BEFORE `generate_and_embed`:

```python
async def _generate_with_retry(
    self,
    prompt: str,
    resolution: str,
) -> ImageResponse:
    """Generate image with retry on primary, then fallback to secondary model.

    Strategy:
        1. Primary model, attempt 1 (90s timeout)
        2. Primary model, attempt 2 (90s timeout) — most 503s resolve on retry
        3. Fallback model (30s timeout) — different capacity pool
        4. Raise if all fail
    """
    from app.config import settings

    timeout = settings.image_timeout_seconds

    if not self.image_provider:
        raise RuntimeError("No image provider configured")

    # Attempt 1: Primary
    try:
        return await asyncio.wait_for(
            self.image_provider.generate_image(prompt, resolution),
            timeout=timeout,
        )
    except (asyncio.TimeoutError, RuntimeError, Exception) as e:
        logger.warning(
            "Image generation attempt 1 failed",
            error=str(e),
            error_type=type(e).__name__,
        )

    # Attempt 2: Primary retry
    try:
        return await asyncio.wait_for(
            self.image_provider.generate_image(prompt, resolution),
            timeout=timeout,
        )
    except (asyncio.TimeoutError, RuntimeError, Exception) as e:
        logger.warning(
            "Image generation attempt 2 failed",
            error=str(e),
            error_type=type(e).__name__,
        )

    # Attempt 3: Fallback model
    if self.fallback_provider:
        logger.info("Falling back to secondary image model")
        try:
            return await asyncio.wait_for(
                self.fallback_provider.generate_image(prompt, resolution),
                timeout=30,
            )
        except (asyncio.TimeoutError, RuntimeError, Exception) as e:
            logger.error(
                "Fallback image generation failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise RuntimeError(
                "Image generation failed after all attempts"
            ) from e
    else:
        raise RuntimeError(
            "Image generation failed and no fallback model configured"
        )
```

#### 3c. Add `import asyncio` to the top of the file

```python
# Add to imports at top of file
import asyncio
```

#### 3d. Update `generate_and_embed` to use `_generate_with_retry`

```python
# BEFORE (line 67-69)
img_response = await self.image_provider.generate_image(
    prompt, resolution
)

# AFTER
img_response = await self._generate_with_retry(prompt, resolution)
```

### Verification
- `ruff check backend/app/services/image_service.py`
- `mypy backend/app/services/image_service.py`
- All existing image service tests pass
- New tests pass (see Phase 5)

---

## Phase 4: Update Chat API — Fallback Init + Progressive Status

### File: `backend/app/api/chat.py`

#### 4a. Add `import asyncio` if not already present

Check the top of the file. If `import asyncio` is missing, add it to the imports.

#### 4b. Update IMAGE route provider initialization (lines ~182-191)

```python
# BEFORE
try:
    from app.providers.gemini_image_provider import (
        GeminiImageProvider,
    )
    img_provider = GeminiImageProvider()
except (ValueError, Exception):
    img_provider = None  # type: ignore[assignment]

img_service = ImageService(img_provider)

# AFTER
try:
    from app.providers.gemini_image_provider import (
        GeminiImageProvider,
    )
    img_provider = GeminiImageProvider()
except (ValueError, Exception):
    img_provider = None  # type: ignore[assignment]

img_fallback: ImageProvider | None = None  # type: ignore[assignment]
if img_provider:
    try:
        from app.config import settings as _settings
        img_fallback = GeminiImageProvider(
            model=_settings.image_fallback_model,
        )
    except (ValueError, Exception):
        pass  # No fallback available, primary only

img_service = ImageService(
    img_provider,
    fallback_provider=img_fallback,
)
```

NOTE: The `ImageProvider` type import may need to be added at the appropriate location. Use a lazy import or add to existing imports as appropriate. Check if `from app.providers.base import ImageProvider` is already imported; if not, add it inside the elif block alongside the other lazy imports.

#### 4c. Add progressive status update using asyncio.wait (replace the image generation block)

Find the block that currently looks like this (approximately lines 202-211):

```python
elif img_provider:
    updated_html, img_resp = (
        await img_service.generate_and_embed(
            current_html,
            request.message,
            resolution="hd",
        )
    )
    model_used = img_resp.model
    images_generated = 1
```

Replace with:

```python
elif img_provider:
    gen_task = asyncio.create_task(
        img_service.generate_and_embed(
            current_html,
            request.message,
            resolution="hd",
        )
    )
    timer_task = asyncio.create_task(asyncio.sleep(8))

    done, _pending = await asyncio.wait(
        {gen_task, timer_task},
        return_when=asyncio.FIRST_COMPLETED,
    )

    if timer_task in done and gen_task not in done:
        yield _sse({
            "type": "status",
            "content": "Still generating... high-quality images can take 15-30 seconds",
        })
        updated_html, img_resp = await gen_task
    else:
        timer_task.cancel()
        updated_html, img_resp = gen_task.result()

    model_used = img_resp.model
    images_generated = 1
```

**How this works with the existing UI:**

The status bar in `ChatWindow/index.tsx` (Plan 009a) already renders:
```tsx
{isStreaming ? `[>] ${currentStatus || 'PROCESSING...'}` : '[*] SYSTEMS NOMINAL'}
```

So the user sees this sequence in the Obsidian Terminal theme status bar:
```
[>] Generating image...                    ← immediate (existing line 172)
[>] Still generating... high-quality       ← after 8s if still waiting
    images can take 15-30 seconds
[*] SYSTEMS NOMINAL                        ← on completion
```

All styling uses the existing CSS custom properties from `theme.css` (Plan 009a). No new CSS needed.

### Verification
- `ruff check backend/app/api/chat.py`
- `mypy backend/app/api/chat.py`
- Existing chat tests pass
- Manual test: send an image request, verify status bar updates

---

## Phase 5: Tests

### File: `backend/tests/test_image_service.py` (add to existing file)

Add 5 new tests. Use `unittest.mock.AsyncMock` and `unittest.mock.patch` to mock the providers.

```python
# --- Retry / Fallback Tests ---

async def test_retry_succeeds_on_second_attempt():
    """Primary fails once, succeeds on retry."""
    mock_provider = AsyncMock(spec=ImageProvider)
    mock_provider.generate_image.side_effect = [
        RuntimeError("503 overloaded"),
        ImageResponse(
            image_bytes=b"fake-png-data",
            format="PNG",
            width=1920,
            height=1080,
            model="gemini-3-pro-image-preview",
            prompt="test",
        ),
    ]
    service = ImageService(mock_provider)
    with patch("app.services.image_service.settings") as mock_settings:
        mock_settings.image_timeout_seconds = 90
        result = await service._generate_with_retry("test prompt", "hd")
    assert result.model == "gemini-3-pro-image-preview"
    assert mock_provider.generate_image.call_count == 2


async def test_fallback_to_flash_on_double_failure():
    """Primary fails twice, fallback succeeds."""
    mock_primary = AsyncMock(spec=ImageProvider)
    mock_primary.generate_image.side_effect = RuntimeError("503")

    mock_fallback = AsyncMock(spec=ImageProvider)
    mock_fallback.generate_image.return_value = ImageResponse(
        image_bytes=b"fallback-data",
        format="PNG",
        width=1920,
        height=1080,
        model="gemini-2.5-flash-image",
        prompt="test",
    )

    service = ImageService(mock_primary, fallback_provider=mock_fallback)
    with patch("app.services.image_service.settings") as mock_settings:
        mock_settings.image_timeout_seconds = 90
        result = await service._generate_with_retry("test prompt", "hd")
    assert result.model == "gemini-2.5-flash-image"
    assert mock_primary.generate_image.call_count == 2
    assert mock_fallback.generate_image.call_count == 1


async def test_timeout_triggers_retry():
    """Primary hangs (timeout), fallback succeeds."""
    async def hang_forever(*args, **kwargs):
        await asyncio.sleep(999)

    mock_primary = AsyncMock(spec=ImageProvider)
    mock_primary.generate_image.side_effect = hang_forever

    mock_fallback = AsyncMock(spec=ImageProvider)
    mock_fallback.generate_image.return_value = ImageResponse(
        image_bytes=b"fallback-data",
        format="PNG",
        width=1920,
        height=1080,
        model="gemini-2.5-flash-image",
        prompt="test",
    )

    service = ImageService(mock_primary, fallback_provider=mock_fallback)
    with patch("app.services.image_service.settings") as mock_settings:
        mock_settings.image_timeout_seconds = 1  # Short timeout for test speed
        result = await service._generate_with_retry("test prompt", "hd")
    assert result.model == "gemini-2.5-flash-image"


async def test_all_attempts_fail_raises():
    """All attempts fail, exception propagates."""
    mock_primary = AsyncMock(spec=ImageProvider)
    mock_primary.generate_image.side_effect = RuntimeError("503")

    mock_fallback = AsyncMock(spec=ImageProvider)
    mock_fallback.generate_image.side_effect = RuntimeError("Flash also failed")

    service = ImageService(mock_primary, fallback_provider=mock_fallback)
    with patch("app.services.image_service.settings") as mock_settings:
        mock_settings.image_timeout_seconds = 90
        with pytest.raises(RuntimeError, match="Image generation failed"):
            await service._generate_with_retry("test prompt", "hd")


async def test_no_fallback_provider_raises_after_retries():
    """No fallback configured, raises after primary retries exhausted."""
    mock_primary = AsyncMock(spec=ImageProvider)
    mock_primary.generate_image.side_effect = RuntimeError("503")

    service = ImageService(mock_primary)  # No fallback
    with patch("app.services.image_service.settings") as mock_settings:
        mock_settings.image_timeout_seconds = 90
        with pytest.raises(RuntimeError, match="no fallback"):
            await service._generate_with_retry("test prompt", "hd")
    assert mock_primary.generate_image.call_count == 2
```

**Required imports** (add at top of test file if not present):
```python
import asyncio
from unittest.mock import AsyncMock, patch
import pytest
from app.providers.base import ImageProvider, ImageResponse
from app.services.image_service import ImageService
```

### Verification
- `pytest backend/tests/test_image_service.py -v` — all pass
- `pytest backend/tests/ -v` — full suite passes (expect 1 pre-existing failure: `test_init_db_creates_file`)

---

## Phase 6: Update Documentation

### File: `CLAUDE.md`

Update all references to the image model. Specifically:

1. **Tech Stack table**: Change `Gemini 2.0 Flash` to `Nano Banana Pro (Gemini 3 Pro Image)` and model ID to `gemini-3-pro-image-preview`

2. **3-Model Routing table** (Rule 3): Change "Gemini 2.0 Flash" to "Nano Banana Pro"

3. **Architecture diagram** comment: Update `(image)` label

4. **Environment Variables section**: Update `IMAGE_MODEL` default to `gemini-3-pro-image-preview`, add `IMAGE_FALLBACK_MODEL` and `IMAGE_TIMEOUT_SECONDS`

5. **Project Structure**: Update `gemini_image_provider.py` comment to reference "Nano Banana Pro"

### File: `backend/app/providers/gemini_image_provider.py`

Update module docstring (lines 1-3):
```python
# BEFORE
"""
Gemini image generation provider.

Uses the google-genai SDK to generate images from text prompts.
Returns PNG/JPEG bytes for base64 embedding in HTML documents.
"""

# AFTER
"""
Nano Banana Pro (Gemini 3 Pro Image) generation provider.

Uses the google-genai SDK to generate images from text prompts.
Returns PNG/JPEG bytes for base64 embedding in HTML documents.
Fallback to Nano Banana Flash (gemini-2.5-flash-image) handled by ImageService.
"""
```

### File: `backend/app/services/router.py`

Update docstring references (lines 6 and 60):
```python
# Line 6: "Nano Banana Pro" is already correct, but update model ID
# Line 60: Update to reference correct model ID

# BEFORE (line 60)
'image' - Route to Nano Banana Pro for image generation

# AFTER
'image' - Route to Nano Banana Pro (gemini-3-pro-image-preview) for image generation
```

### Verification
- Read through all updated docs to ensure consistency
- No code changes in this phase, no tests needed

---

## Phase 7: Final Verification

Run the full quality check suite:

```bash
# Backend
cd backend
ruff check .
mypy .
pytest -v

# Frontend (should be unchanged but verify)
cd frontend
npx tsc --noEmit
npx vite build
```

**Expected results:**
- ruff: clean
- mypy: clean
- pytest: 249+ tests passing (244 existing + 5 new), 1 pre-existing failure (`test_init_db_creates_file`)
- TypeScript: clean
- Vite build: clean
- Zero frontend files modified

---

## Summary of Changes

| File | Change | Lines |
|------|--------|-------|
| `config.py` | New default + 2 fallback fields | ~3 |
| `cost_tracker.py` | Swap pricing entries | ~4 |
| `image_service.py` | `__init__` param, `_generate_with_retry()`, `import asyncio` | ~50 |
| `chat.py` | Fallback provider init, `asyncio.wait` progressive status | ~25 |
| `gemini_image_provider.py` | Docstring update | ~3 |
| `router.py` | Docstring update | ~2 |
| `CLAUDE.md` | Model name/ID updates | ~15 |
| `test_image_service.py` | 5 new retry/fallback tests | ~80 |

**Total**: ~100 lines of functional code, ~80 lines of tests, ~20 lines of docs.
**No new files. No new API endpoints. No frontend changes. No new dependencies.**

---

## Error Rate Mitigation Summary

The ~45% peak-hour error rate for Nano Banana Pro consists of fast-failing 503/429 responses (1-3 seconds), not timeouts. The mitigation strategy:

| Layer | Mechanism | Effect |
|-------|-----------|--------|
| **Retry** | Primary model retried once | Handles ~70% of transient 503s |
| **Fallback** | Flash model on double failure | Different capacity pool, much lower error rate |
| **Timeout** | 90s primary, 30s fallback | Catches genuine infrastructure hangs |
| **UX** | 8-second progressive status update | Prevents "is it broken?" perception |
| **Logging** | structlog warnings on each failure | Ops visibility into error patterns |

**Worst-case user experience**: Pro fails twice (503, ~3s each) → Flash fallback succeeds (~5s) → total ~11s with slightly lower quality image. User sees `"Generating image..."` → `"Still generating..."` → done.

**Worst-case total failure**: Pro hangs (90s) → Pro hangs (90s) → Flash hangs (30s) → error shown. This 210s scenario is theoretically possible but would indicate a total Google API outage.
