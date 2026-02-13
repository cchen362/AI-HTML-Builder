# Implementation Plan 018: NotebookLM-Style Infographic Generation

## Status: COMPLETE

---

## STOP - READ THIS FIRST

**DO NOT START** this implementation until:
- Plan 017 (UI/UX Makeover) is FULLY complete (it is)
- You have read this ENTIRE document end-to-end
- You understand every file path, code change, and verification step

**STRICT RULES — FOLLOW EXACTLY:**
1. Implement phases IN ORDER (1 → 6). Do NOT skip phases or reorder.
2. Run verification after EACH phase before proceeding to the next.
3. Do NOT create files not listed in this plan. Do NOT delete files not listed in this plan.
4. Do NOT add dependencies to `package.json` or `requirements.txt`.
5. Every change must preserve the existing tests, build, and lint.
6. Phase 1 MUST be done first — subsequent phases import from the new service.

**CONTEXT:**

This plan adds a **two-LLM infographic generation pipeline**:
- **Gemini 2.5 Pro** acts as an art director — reads user content, understands context, writes a detailed visual prompt describing the infographic layout, text, colors, and visuals
- **Nano Banana Pro** (Gemini 3 Pro Image) renders that visual prompt into a 2K (2560×1440) raster image (PNG/JPEG)

The result is stored as a minimal HTML wrapper around a base64 `<img>` in the existing `document_versions` table — zero schema changes. Users iterate via chat; each iteration is a full regeneration where the art director modifies its previous visual prompt based on user feedback.

**DEPENDENCIES:**
- Plans 001-017 (all complete)
- No new pip or npm dependencies

**SCOPE:**
- 2 new files, 5 modified, 0 deleted
- Zero frontend changes required for launch
- Zero schema changes
- Zero new dependencies

---

## Data Flow — Read This to Understand the Pipeline

### Scenario 1: New Infographic (from existing document)

User has a stakeholder brief and says: *"Transform the content into an infographic with buildings and bridges to depict bridging the human gap in Change Management"*

```
1. Router detects "infographic" keyword → route = "infographic"

2. _handle_infographic() in chat.py:
   - Gets active doc's HTML content
   - Strips base64 images (noise for LLM)
   - Passes CONTENT as context to InfographicService

3. InfographicService.generate() — Step 1 (Art Director):
   Messages to Gemini 2.5 Pro:
   ┌─────────────────────────────────────────────────────────────┐
   │ SYSTEM: Art Director Prompt (rules, canvas size, etc.)     │
   │                                                             │
   │ USER: "Here is the source content to create an infographic  │
   │ from:\n\n<h1>Change Management Brief</h1><p>73% adoption    │
   │ rate...</p>..."                                             │
   │                                                             │
   │ ASSISTANT: "I have the source content. I'll design a visual │
   │ infographic prompt based on this material."                 │
   │                                                             │
   │ USER: "Transform the content into an infographic with       │
   │ buildings and bridges to depict bridging the human gap       │
   │ in Change Management"                                       │
   └─────────────────────────────────────────────────────────────┘

   Gemini 2.5 Pro OUTPUT (the visual prompt):
   "A 2560x1440 landscape infographic titled 'BRIDGING THE
    HUMAN GAP' in bold white Montserrat. Background: deep navy
    gradient. Header: stylized bridge connecting two cliffs.
    Left cliff labeled 'Current State' with workers at desks,
    right cliff 'Future State' with collaborative teams.
    Three pillars: 'Communication', 'Training', 'Support'.
    Stats: '73% adoption rate', '$2.1M saved'..."

4. InfographicService.generate() — Step 2 (Renderer):
   Pass visual prompt text → Nano Banana Pro → 2K PNG image

5. Back in _handle_infographic():
   - Wrap PNG in minimal HTML (<html><body><img base64...>)
   - Create new document in session
   - Save version with visual_prompt stored in user_prompt field
   - Stream SSE events: status → html → summary
```

### Scenario 2: New Infographic (from scratch)

User types: *"Make an infographic about Q4 revenue growth — $5M total, 23% increase"*

```
Same as above but NO content_context.
Messages to Gemini 2.5 Pro:
┌─────────────────────────────────────────────────────────────┐
│ SYSTEM: Art Director Prompt                                 │
│                                                             │
│ USER: "Make an infographic about Q4 revenue growth — $5M    │
│ total, 23% increase"                                       │
└─────────────────────────────────────────────────────────────┘
Art director extracts data from user message and designs the visual.
```

### Scenario 3: Iteration / Regeneration

User is viewing an existing infographic and says: *"Change the theme to navy and gold, keeping the graphics and words"*

```
1. Router detects "infographic" keyword → route = "infographic"
   (Note: even if user says "change the theme" without "infographic",
    _is_infographic_doc() detects the active doc IS an infographic)

2. _handle_infographic():
   - Detects active doc is an infographic (minimal HTML wrapper)
   - Retrieves the PREVIOUS VISUAL PROMPT from document_versions.user_prompt
   - Passes it as previous_visual_prompt (NOT content_context)

3. InfographicService.generate() — Step 1 (Art Director):
   Messages to Gemini 2.5 Pro:
   ┌─────────────────────────────────────────────────────────────┐
   │ SYSTEM: Art Director Prompt                                 │
   │                                                             │
   │ USER: "Here is the visual prompt you previously created     │
   │ for this infographic:\n\nA 2560x1440 landscape infographic  │
   │ titled 'BRIDGING THE HUMAN GAP'... teal palette... 73%     │
   │ adoption rate..."                                           │
   │                                                             │
   │ ASSISTANT: "I have my previous visual prompt. I'll modify   │
   │ it based on the new feedback."                              │
   │                                                             │
   │ USER: "Change the theme to navy and gold, keeping the       │
   │ graphics and words"                                         │
   └─────────────────────────────────────────────────────────────┘

   Art director modifies: swap teal→navy, add gold accents,
   keep all text/layout/illustrations.

4. Step 2 (Renderer): New visual prompt → Nano Banana Pro → new PNG

5. Save as new VERSION of same document (not a new document)
   - Version 1: Original infographic
   - Version 2: Navy/gold variant
   User can browse version history to compare.
```

---

## Files Summary

| File | Action | Phase |
|------|--------|-------|
| `backend/app/services/infographic_service.py` | **CREATE** | 1 |
| `backend/app/services/router.py` | EDIT | 2 |
| `backend/app/api/chat.py` | EDIT | 3 |
| `backend/tests/test_infographic_service.py` | **CREATE** | 4 |
| `backend/tests/test_router.py` | EDIT | 4 |
| `backend/tests/test_chat_create_image.py` | EDIT | 4 |
| `CLAUDE.md` | EDIT | 5 |

---

## Phase 1: InfographicService (New File)

**Create:** `backend/app/services/infographic_service.py`

This is the core two-LLM pipeline service. It has no side effects (no DB writes, no SSE events) — it takes inputs and returns an `InfographicResult`.

### 1.1 Imports and Dataclass

```python
"""
Two-LLM infographic pipeline: Gemini 2.5 Pro (art director) → Nano Banana Pro (renderer).

The art director reads user content and style direction, then writes a detailed visual
prompt describing layout, text, colors, and imagery. Nano Banana Pro renders that prompt
into a 2K raster infographic. Each iteration is a full regeneration — the art director
modifies its previous visual prompt based on user feedback.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import structlog

from app.providers.base import ImageProvider, ImageResponse, LLMProvider

logger = structlog.get_logger()


@dataclass
class InfographicResult:
    """Result from the infographic generation pipeline."""
    image_bytes: bytes
    image_format: str          # "PNG" or "JPEG"
    visual_prompt: str         # The prompt sent to Nano Banana Pro
    model_prompt: str          # Art director model (e.g., "gemini-2.5-pro")
    model_image: str           # Renderer model (e.g., "gemini-3-pro-image-preview")
    prompt_input_tokens: int
    prompt_output_tokens: int
```

### 1.2 Art Director System Prompt

```python
ART_DIRECTOR_SYSTEM_PROMPT = """\
You are an expert infographic art director. Your job is to write a detailed \
visual prompt that an AI image generation model will use to create a stunning, \
professional infographic.

YOUR OUTPUT is a text prompt — NOT an image, NOT code, NOT HTML.

RULES:
1. Describe a COMPLETE infographic layout in vivid, precise detail
2. Specify exact text, numbers, and labels — the image model renders text literally, \
so every word must be exactly as it should appear
3. Describe visual hierarchy: what is large/prominent, what is secondary
4. Specify a color palette (hex codes or descriptive names)
5. Describe the typography style (bold headlines, clean body text, etc.)
6. Describe data visualizations concretely (bar chart with specific values, etc.)
7. Include decorative elements: icons, illustrations, divider lines, backgrounds
8. Canvas: 2560x1440 pixels, landscape orientation
9. Style: magazine-quality, modern, professional infographic
10. Keep ALL text in the infographic SHORT — titles 3-6 words, bullets 5-10 words max
11. Maximum 5-7 sections/blocks — do not cram too much information

AVOID:
- Generic descriptions ("nice colors", "clean layout")
- Vague text placeholders ("add a title here")
- More than 200 words of body text total in the infographic — it must be VISUAL
- Tiny text that would be illegible at 2560x1440

OUTPUT: Return ONLY the visual prompt. No markdown, no code fences, no explanation.\
"""
```

### 1.3 InfographicService Class

```python
class InfographicService:
    """Two-LLM pipeline: Gemini 2.5 Pro (art director) → Nano Banana Pro (renderer)."""

    def __init__(
        self,
        prompt_provider: LLMProvider,
        image_provider: ImageProvider,
        fallback_image_provider: ImageProvider | None = None,
    ):
        self.prompt_provider = prompt_provider
        self.image_provider = image_provider
        self.fallback_image_provider = fallback_image_provider

    async def generate(
        self,
        user_message: str,
        content_context: str | None = None,
        previous_visual_prompt: str | None = None,
    ) -> InfographicResult:
        """Generate an infographic via the two-LLM pipeline.

        Args:
            user_message: The user's request (e.g., "make an infographic about Q4 revenue")
            content_context: Existing HTML doc content (base64-stripped) for first-time creation.
                            Passed when transforming an existing document into an infographic.
            previous_visual_prompt: The art director's previous visual prompt, for iteration.
                                  Passed when user is refining an existing infographic.
        """
        # Step 1: Art Director — generate visual prompt
        messages = self._build_messages(user_message, content_context, previous_visual_prompt)

        logger.info(
            "Infographic art director generating visual prompt",
            user_message=user_message[:80],
            has_context=content_context is not None,
            is_iteration=previous_visual_prompt is not None,
        )

        result = await self.prompt_provider.generate(
            system=ART_DIRECTOR_SYSTEM_PROMPT,
            messages=messages,
            max_tokens=2000,
            temperature=0.7,
        )
        visual_prompt = result.text.strip()

        logger.info(
            "Visual prompt generated",
            prompt_length=len(visual_prompt),
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
        )

        # Step 2: Renderer — generate image from visual prompt
        img_response = await self._generate_image_with_retry(visual_prompt, "2k")

        # Compress if needed
        image_bytes = img_response.image_bytes
        if len(image_bytes) > 5 * 1024 * 1024:  # 5MB
            from app.services.image_service import _compress_image
            image_bytes = _compress_image(image_bytes, img_response.format)

        return InfographicResult(
            image_bytes=image_bytes,
            image_format=img_response.format,
            visual_prompt=visual_prompt,
            model_prompt=result.model,
            model_image=img_response.model,
            prompt_input_tokens=result.input_tokens,
            prompt_output_tokens=result.output_tokens,
        )
```

### 1.4 Message Building

```python
    def _build_messages(
        self,
        user_message: str,
        content_context: str | None,
        previous_visual_prompt: str | None,
    ) -> list[dict]:
        """Build the message chain for the art director.

        Two modes:
        - First creation: content_context (existing doc HTML) as source material
        - Iteration: previous_visual_prompt (art director's last spec) for modification
        """
        messages: list[dict] = []

        # Source material (existing doc content, for first-time creation)
        if content_context:
            messages.append({
                "role": "user",
                "content": (
                    "Here is the source content to create an infographic from:\n\n"
                    + content_context
                ),
            })
            messages.append({
                "role": "assistant",
                "content": (
                    "I have the source content. I'll design a visual infographic "
                    "prompt based on this material."
                ),
            })

        # Previous visual prompt (for iteration — the art director's last spec)
        if previous_visual_prompt:
            messages.append({
                "role": "user",
                "content": (
                    "Here is the visual prompt you previously created for this "
                    "infographic:\n\n" + previous_visual_prompt
                ),
            })
            messages.append({
                "role": "assistant",
                "content": (
                    "I have my previous visual prompt. I'll modify it based "
                    "on the new feedback."
                ),
            })

        # Current user request
        messages.append({"role": "user", "content": user_message})
        return messages
```

### 1.5 Retry Logic

Replicate the same retry pattern from `ImageService._generate_with_retry()` in `backend/app/services/image_service.py` (lines 52-118):

```python
    async def _generate_image_with_retry(
        self,
        prompt: str,
        resolution: str,
    ) -> ImageResponse:
        """Generate image with retry on primary, then fallback to secondary model.

        Strategy (identical to ImageService):
            1. Primary model, attempt 1 (timeout from settings)
            2. Primary model, attempt 2 — most 503s resolve on retry
            3. Fallback model (30s timeout) — different capacity pool
        """
        from app.config import settings

        timeout = settings.image_timeout_seconds

        # Attempt 1: Primary
        try:
            return await asyncio.wait_for(
                self.image_provider.generate_image(prompt, resolution),
                timeout=timeout,
            )
        except (asyncio.TimeoutError, RuntimeError, Exception) as e:
            logger.warning(
                "Infographic image attempt 1 failed",
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
                "Infographic image attempt 2 failed",
                error=str(e),
                error_type=type(e).__name__,
            )

        # Attempt 3: Fallback model
        if self.fallback_image_provider:
            logger.info("Falling back to secondary image model for infographic")
            try:
                return await asyncio.wait_for(
                    self.fallback_image_provider.generate_image(prompt, resolution),
                    timeout=30,
                )
            except (asyncio.TimeoutError, RuntimeError, Exception) as e:
                logger.error(
                    "Fallback infographic image generation failed",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                raise RuntimeError(
                    "Infographic image generation failed after all attempts"
                ) from e
        else:
            raise RuntimeError(
                "Infographic image generation failed and no fallback configured"
            )
```

### 1.6 HTML Wrapper Function

Module-level function (not a method):

```python
def wrap_infographic_html(
    image_bytes: bytes, image_format: str, alt_text: str
) -> str:
    """Wrap infographic image bytes in a minimal HTML document.

    The HTML structure is intentionally minimal — no <main>, <header>, <section>.
    This distinctness is used by _is_infographic_doc() in chat.py to detect
    infographic documents for iteration routing.
    """
    import base64

    b64 = base64.b64encode(image_bytes).decode("utf-8")
    mime = f"image/{image_format.lower()}"
    safe_alt = alt_text.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")[:200]

    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head><meta charset=\"utf-8\"><meta name=\"viewport\" "
        'content="width=device-width,initial-scale=1">'
        "<title>Infographic</title>\n"
        "<style>*{margin:0;padding:0;box-sizing:border-box}"
        "body{background:#0a0a0f;display:flex;justify-content:center;"
        "align-items:center;min-height:100vh}"
        "img{max-width:100%;height:auto;display:block}</style>\n"
        "</head>\n"
        f'<body><img src="data:{mime};base64,{b64}" '
        f'alt="{safe_alt}"/></body>\n'
        "</html>"
    )
```

### Phase 1 Verification

```bash
cd backend
python -c "from app.services.infographic_service import InfographicService, InfographicResult, wrap_infographic_html, ART_DIRECTOR_SYSTEM_PROMPT; print('Phase 1 OK')"
ruff check app/services/infographic_service.py
mypy app/services/infographic_service.py
```

---

## Phase 2: Router Update

**Edit:** `backend/app/services/router.py`

### 2.1 Add infographic regex (after `_TRANSFORM_RE`, around line 38)

```python
_INFOGRAPHIC_RE = re.compile(
    r"\binfographic\b",
    re.IGNORECASE,
)
```

### 2.2 Update valid routes (line 55)

Change:
```python
_VALID_ROUTES = frozenset({"create", "edit", "image"})
```
To:
```python
_VALID_ROUTES = frozenset({"create", "edit", "image", "infographic"})
```

### 2.3 Update `classify_request()` return type docstring (line 74-82)

Change:
```python
    Returns:
        'create' - Route to Gemini 2.5 Pro for new document creation
        'image'  - Route to Nano Banana Pro for raster image generation
        'edit'   - Route to Claude Sonnet 4.5 for surgical editing (DEFAULT)
```
To:
```python
    Returns:
        'create'      - Route to Gemini 2.5 Pro for new document creation
        'infographic' - Route to InfographicService (2-LLM pipeline)
        'image'       - Route to Nano Banana Pro for raster image generation
        'edit'        - Route to Claude Sonnet 4.5 for surgical editing (DEFAULT)
```

### 2.4 Reorder classification rules in `classify_request()` body

The NEW rule order must be:

```python
    # Rule 1: Removal/deletion intent → always EDIT (only with existing HTML)
    if has_existing_html and _REMOVAL_RE.search(user_input):
        logger.info("[ROUTER] Removal intent -> EDIT", request=user_input[:80])
        return "edit"

    # Rule 2: Infographic keyword → always INFOGRAPHIC (with or without HTML)
    if _INFOGRAPHIC_RE.search(user_input):
        logger.info("[ROUTER] Infographic intent -> INFOGRAPHIC", request=user_input[:80])
        return "infographic"

    # Rule 3: No existing HTML → always CREATE (no LLM call needed)
    if not has_existing_html:
        logger.info("[ROUTER] No existing HTML -> CREATE", request=user_input[:80])
        return "create"

    # Rule 4: Transform intent → CREATE (full document reconceptualization)
    if _TRANSFORM_RE.search(user_input):
        logger.info("[ROUTER] Transform intent -> CREATE", request=user_input[:80])
        return "create"

    # Rule 5: LLM classification via Haiku 4.5
    # (unchanged from current implementation)
```

**Critical ordering rationale:**
- Rule 1 (removal) before Rule 2 (infographic): "remove the infographic" → EDIT (correct)
- Rule 2 (infographic) before Rule 3 (no HTML): "make an infographic" with no docs → INFOGRAPHIC (correct, not CREATE)
- Rule 2 (infographic) before Rule 4 (transform): "turn this into an infographic" → INFOGRAPHIC (correct, not CREATE)

**Haiku prompt stays unchanged.** The word "infographic" is multi-token and would be truncated by `max_tokens=1`. Pre-routing regex catches all uses of the word. If a user asks for something infographic-like without the keyword (e.g., "make a visual poster"), it routes to CREATE — an acceptable fallback (Gemini creates an HTML document).

### Phase 2 Verification

```bash
cd backend
python -m pytest tests/test_router.py -v
ruff check app/services/router.py
mypy app/services/router.py
```

**Note:** The existing test `test_infographic_is_create` (line 113) will NOW FAIL because "infographic" routes to "infographic" not "create". This test is updated in Phase 4.

---

## Phase 3: Chat Handler

**Edit:** `backend/app/api/chat.py`

### 3.1 Add `_is_infographic_doc()` helper (after `_strip_base64_for_context`, around line 50)

```python
def _is_infographic_doc(html: str) -> bool:
    """Detect infographic wrapper docs (minimal HTML with single base64 <img>).

    Infographic documents have a distinctive structure: <500 chars of HTML
    after removing base64 payloads, with a single <img> tag. This is how
    wrap_infographic_html() creates them — no <main>, <header>, <section>.
    """
    stripped = _BASE64_RE.sub("", html)
    return len(stripped) < 500 and "<img" in html and "data:image" in html
```

### 3.2 Add `_get_latest_version_prompt()` helper (after `_is_infographic_doc`)

We need to retrieve the `user_prompt` field from the latest version for iteration context. The existing `get_latest_html()` only returns `html_content`. Add a small helper:

```python
async def _get_latest_version_prompt(
    session_service: Any, document_id: str
) -> str | None:
    """Get the user_prompt from the latest version of a document.

    For infographic docs, this stores the art director's visual prompt.
    """
    history = await session_service.get_version_history(document_id)
    if history:
        return history[0].get("user_prompt")  # history is DESC ordered
    return None
```

### 3.3 Add `_handle_infographic()` handler (after `_handle_image`, before the main endpoint)

```python
async def _handle_infographic(
    session_service: Any,
    request: ChatRequest,
    session_id: str,
    active_doc: dict | None,
    current_html: str | None,
) -> AsyncIterator[dict]:
    """Infographic generation via Gemini 2.5 Pro (art director) + Nano Banana Pro (renderer)."""
    from app.services.infographic_service import (
        InfographicService,
        wrap_infographic_html,
    )
    from app.providers.gemini_provider import GeminiProvider
    from app.providers.gemini_image_provider import GeminiImageProvider
    from app.services.cost_tracker import cost_tracker

    yield {"type": "status", "content": "Designing infographic..."}

    # Initialize prompt provider (Gemini 2.5 Pro)
    try:
        prompt_provider = GeminiProvider()
    except ValueError:
        yield {
            "type": "error",
            "content": "Infographic generation unavailable (no GOOGLE_API_KEY).",
        }
        return

    # Initialize image provider (Nano Banana Pro)
    try:
        img_provider = GeminiImageProvider()
    except (ValueError, Exception):
        yield {
            "type": "error",
            "content": "Image generation unavailable (no GOOGLE_API_KEY).",
        }
        return

    # Initialize fallback image provider
    img_fallback = None
    try:
        from app.config import settings as _settings
        img_fallback = GeminiImageProvider(model=_settings.image_fallback_model)
    except (ValueError, Exception):
        pass  # No fallback available

    service = InfographicService(prompt_provider, img_provider, img_fallback)

    # Determine context mode: first creation vs. iteration
    content_context = None
    previous_visual_prompt = None
    is_iteration = False

    if active_doc and current_html and _is_infographic_doc(current_html):
        # Active doc IS an infographic → iteration mode
        is_iteration = True
        previous_visual_prompt = await _get_latest_version_prompt(
            session_service, active_doc["id"]
        )
    elif current_html:
        # Active doc is a regular HTML doc → use as source material
        content_context = _strip_base64_for_context(current_html)

    # Generate infographic with progress updates
    gen_task = asyncio.create_task(
        service.generate(
            request.message,
            content_context=content_context,
            previous_visual_prompt=previous_visual_prompt,
        )
    )
    timer_task = asyncio.create_task(asyncio.sleep(8))

    done, _pending = await asyncio.wait(
        {gen_task, timer_task},
        return_when=asyncio.FIRST_COMPLETED,
    )

    if timer_task in done and gen_task not in done:
        yield {
            "type": "status",
            "content": "Rendering infographic... high-quality images can take 15-30 seconds",
        }
        result = await gen_task
    else:
        timer_task.cancel()
        result = gen_task.result()

    # Wrap image in HTML
    infographic_html = wrap_infographic_html(
        result.image_bytes,
        result.image_format,
        alt_text=f"Infographic: {request.message[:100]}",
    )

    title = f"Infographic: {_extract_title(request.message)}"
    model_used = f"{result.model_prompt}+{result.model_image}"

    if is_iteration and active_doc:
        # Iteration: new version of existing infographic document
        doc_id = active_doc["id"]
        version = await session_service.save_version(
            doc_id,
            infographic_html,
            user_prompt=result.visual_prompt,  # Store art director's spec for next iteration
            edit_summary="Regenerated infographic",
            model_used=model_used,
            tokens_used=result.prompt_input_tokens + result.prompt_output_tokens,
        )
        summary = "Regenerated infographic"
    else:
        # New infographic document
        doc_id = await session_service.create_document(session_id, title)
        version = await session_service.save_version(
            doc_id,
            infographic_html,
            user_prompt=result.visual_prompt,  # Store art director's spec for next iteration
            edit_summary=f"Created: {title}",
            model_used=model_used,
            tokens_used=result.prompt_input_tokens + result.prompt_output_tokens,
        )
        summary = f"Created: {title}"

    # Track costs for BOTH models
    await cost_tracker.record_usage(
        result.model_prompt,
        result.prompt_input_tokens,
        result.prompt_output_tokens,
    )
    await cost_tracker.record_usage(
        result.model_image, 0, 0, 1  # Image models charge per image, not per token
    )

    await session_service.add_chat_message(
        session_id,
        "assistant",
        summary,
        doc_id,
        "infographic_confirmation",
    )

    yield {"type": "html", "content": infographic_html, "version": version}
    yield {"type": "summary", "content": summary}
```

### 3.4 Wire into the main `chat()` endpoint dispatch

In the `event_stream()` function (around line 339-357), add the infographic route. Find:

```python
            elif route == "create":
                handler = _handle_create(
                    session_service, request, session_id,
                    current_html=current_html,
                )
            elif route == "image":
```

Insert between them:

```python
            elif route == "infographic":
                handler = _handle_infographic(
                    session_service, request, session_id,
                    active_doc, current_html,
                )
```

### Phase 3 Verification

```bash
cd backend
python -c "from app.api.chat import _handle_infographic, _is_infographic_doc; print('Phase 3 OK')"
ruff check app/api/chat.py
mypy app/api/chat.py
```

---

## Phase 4: Tests

### 4.1 Create `backend/tests/test_infographic_service.py`

New test file:

```python
"""Tests for the InfographicService two-LLM pipeline."""

import os
from unittest.mock import AsyncMock, MagicMock

import pytest

os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key-for-testing")

from app.services.infographic_service import (
    ART_DIRECTOR_SYSTEM_PROMPT,
    InfographicService,
    wrap_infographic_html,
)
from app.providers.base import GenerationResult, ImageResponse


@pytest.fixture
def mock_prompt_provider():
    """Mock Gemini 2.5 Pro (art director)."""
    provider = AsyncMock()
    provider.generate.return_value = GenerationResult(
        text="A 2560x1440 landscape infographic titled 'Q4 REVENUE' with teal palette...",
        input_tokens=500,
        output_tokens=200,
        model="gemini-2.5-pro",
    )
    return provider


@pytest.fixture
def mock_image_provider():
    """Mock Nano Banana Pro (renderer)."""
    provider = AsyncMock()
    provider.generate_image.return_value = ImageResponse(
        image_bytes=b"\x89PNG" + b"\x00" * 100,
        format="PNG",
        width=2560,
        height=1440,
        model="gemini-3-pro-image-preview",
        prompt="test prompt",
    )
    return provider


@pytest.fixture
def service(mock_prompt_provider, mock_image_provider):
    return InfographicService(mock_prompt_provider, mock_image_provider)


# --- Two-LLM pipeline ---


async def test_generate_calls_both_providers(
    service, mock_prompt_provider, mock_image_provider
):
    """Pipeline should call art director (prompt) then renderer (image)."""
    result = await service.generate("Create an infographic about Q4 revenue")
    mock_prompt_provider.generate.assert_called_once()
    mock_image_provider.generate_image.assert_called_once()
    assert result.image_bytes == b"\x89PNG" + b"\x00" * 100
    assert result.image_format == "PNG"
    assert result.model_prompt == "gemini-2.5-pro"
    assert result.model_image == "gemini-3-pro-image-preview"


async def test_generate_passes_visual_prompt_to_image_provider(
    service, mock_prompt_provider, mock_image_provider
):
    """The art director's output should be sent to the image provider."""
    await service.generate("Revenue infographic")
    img_call_args = mock_image_provider.generate_image.call_args
    prompt_sent = img_call_args[0][0]  # First positional arg
    assert "Q4 REVENUE" in prompt_sent  # From mock_prompt_provider fixture


async def test_generate_returns_visual_prompt(service):
    """The visual prompt should be available in the result for storage."""
    result = await service.generate("Test")
    assert "Q4 REVENUE" in result.visual_prompt
    assert result.prompt_input_tokens == 500
    assert result.prompt_output_tokens == 200


# --- Content context ---


async def test_generate_with_content_context(service, mock_prompt_provider):
    """Content context (existing doc) should appear in art director messages."""
    await service.generate(
        "Turn this into an infographic",
        content_context="<h1>Revenue Report</h1><p>$5M total</p>",
    )
    call_kwargs = mock_prompt_provider.generate.call_args
    messages = call_kwargs.kwargs.get("messages") or call_kwargs[1]["messages"]
    # Source material should be in first user message
    assert any("source content" in m["content"].lower() for m in messages if m["role"] == "user")
    assert any("Revenue Report" in m["content"] for m in messages if m["role"] == "user")


# --- Iteration with previous visual prompt ---


async def test_generate_with_previous_visual_prompt(service, mock_prompt_provider):
    """Iteration should pass the previous visual prompt to the art director."""
    prev_prompt = "A teal infographic showing revenue growth..."
    await service.generate(
        "Change the theme to navy",
        previous_visual_prompt=prev_prompt,
    )
    call_kwargs = mock_prompt_provider.generate.call_args
    messages = call_kwargs.kwargs.get("messages") or call_kwargs[1]["messages"]
    # Previous prompt should appear in messages
    assert any("teal infographic" in m["content"] for m in messages if m["role"] == "user")
    # User's modification request should be the last message
    assert messages[-1]["content"] == "Change the theme to navy"


# --- Fallback ---


async def test_generate_uses_fallback_on_primary_failure(mock_prompt_provider):
    """When primary image provider fails, fallback should be used."""
    primary = AsyncMock()
    primary.generate_image.side_effect = RuntimeError("Primary failed")

    fallback = AsyncMock()
    fallback.generate_image.return_value = ImageResponse(
        image_bytes=b"\x89PNG\x00",
        format="PNG",
        width=2560,
        height=1440,
        model="gemini-2.5-flash-image",
        prompt="test",
    )

    svc = InfographicService(mock_prompt_provider, primary, fallback)
    result = await svc.generate("Test infographic")
    assert result.model_image == "gemini-2.5-flash-image"


async def test_generate_raises_when_all_fail(mock_prompt_provider):
    """When all image providers fail, should raise RuntimeError."""
    primary = AsyncMock()
    primary.generate_image.side_effect = RuntimeError("Primary failed")

    fallback = AsyncMock()
    fallback.generate_image.side_effect = RuntimeError("Fallback failed")

    svc = InfographicService(mock_prompt_provider, primary, fallback)
    with pytest.raises(RuntimeError, match="failed after all attempts"):
        await svc.generate("Test infographic")


# --- HTML wrapper ---


def test_wrap_infographic_html_structure():
    """Wrapper should produce valid minimal HTML with base64 image."""
    html = wrap_infographic_html(b"\x89PNG\x00\x00", "PNG", "Test infographic")
    assert "<!DOCTYPE html>" in html
    assert "data:image/png;base64," in html
    assert 'alt="Test infographic"' in html
    # Must NOT have semantic sections (used by _is_infographic_doc detection)
    assert "<main" not in html
    assert "<header" not in html
    assert "<section" not in html


def test_wrap_infographic_html_dark_background():
    """Wrapper should use dark background matching app theme."""
    html = wrap_infographic_html(b"\x89PNG", "PNG", "Test")
    assert "#0a0a0f" in html


def test_wrap_infographic_html_escapes_alt():
    """Alt text should be properly escaped."""
    html = wrap_infographic_html(b"\x89PNG", "PNG", 'Test "quoted" & <special>')
    assert "&quot;" in html
    assert "&lt;" in html


def test_wrap_infographic_html_truncates_alt():
    """Alt text should be truncated to 200 chars."""
    long_alt = "x" * 300
    html = wrap_infographic_html(b"\x89PNG", "PNG", long_alt)
    # The alt attribute value should be <= 200 chars
    import re
    match = re.search(r'alt="([^"]*)"', html)
    assert match
    assert len(match.group(1)) <= 200


# --- Art director prompt ---


def test_art_director_system_prompt_specifies_canvas():
    assert "2560" in ART_DIRECTOR_SYSTEM_PROMPT
    assert "1440" in ART_DIRECTOR_SYSTEM_PROMPT


def test_art_director_system_prompt_mentions_text_accuracy():
    assert "literally" in ART_DIRECTOR_SYSTEM_PROMPT.lower()
```

### 4.2 Update `backend/tests/test_router.py`

**Update** `test_infographic_is_create` (line 113-115). The old test:

```python
async def test_infographic_is_create():
    with _mock_haiku("create"):
        assert await classify_request("Add an infographic about costs", has_existing_html=True) == "create"
```

Replace with:

```python
async def test_infographic_routes_to_infographic():
    """Infographic keyword should route to infographic (pre-routing, no LLM call)."""
    result = await classify_request("Add an infographic about costs", has_existing_html=True)
    assert result == "infographic"
```

**Add** these new tests at the end of the file (after the last test):

```python
# ---------------------------------------------------------------------------
# Pre-routing: Infographic keyword → INFOGRAPHIC (no LLM call, Plan 018)
# ---------------------------------------------------------------------------


async def test_infographic_no_html_routes_to_infographic():
    """Infographic keyword should work even without existing HTML."""
    result = await classify_request("Make an infographic about revenue", has_existing_html=False)
    assert result == "infographic"


async def test_turn_into_infographic_routes_to_infographic():
    result = await classify_request("Turn this into an infographic", has_existing_html=True)
    assert result == "infographic"


async def test_remove_infographic_routes_to_edit():
    """Removal intent should override infographic keyword."""
    result = await classify_request("Remove the infographic", has_existing_html=True)
    assert result == "edit"


async def test_create_infographic_about():
    result = await classify_request("Create an infographic about Q4 growth", has_existing_html=True)
    assert result == "infographic"


async def test_infographic_case_insensitive():
    result = await classify_request("Make an INFOGRAPHIC", has_existing_html=False)
    assert result == "infographic"
```

### 4.3 Add infographic handler test to `backend/tests/test_chat_create_image.py`

Add at the END of the file. First, check what helper `_parse_sse_events` exists or create inline.

The test should mock the `InfographicService`, `GeminiProvider`, `GeminiImageProvider`, and the router, then call the `chat()` endpoint and verify SSE events.

```python
# ---------------------------------------------------------------------------
# Infographic route tests (Plan 018)
# ---------------------------------------------------------------------------


async def test_infographic_route_creates_document(tmp_path):
    """Infographic route should generate image, wrap in HTML, create doc tab."""
    from app.database import init_db, close_db
    from app.config import settings
    from app.services.infographic_service import InfographicResult

    db_path = tmp_path / "test_infographic.db"
    with patch.object(settings, "database_path", str(db_path)):
        await init_db()
        try:
            from app.api.chat import chat, ChatRequest

            mock_result = InfographicResult(
                image_bytes=b"\x89PNG" + b"\x00" * 50,
                image_format="PNG",
                visual_prompt="A detailed infographic about revenue...",
                model_prompt="gemini-2.5-pro",
                model_image="gemini-3-pro-image-preview",
                prompt_input_tokens=500,
                prompt_output_tokens=200,
            )

            mock_service_instance = AsyncMock()
            mock_service_instance.generate.return_value = mock_result

            with (
                patch(
                    "app.api.chat.InfographicService",  # Would need to adjust import
                    return_value=mock_service_instance,
                ) if False else patch(
                    "app.services.infographic_service.InfographicService",
                    return_value=mock_service_instance,
                ),
                patch("app.providers.gemini_provider.GeminiProvider"),
                patch("app.providers.gemini_image_provider.GeminiImageProvider"),
                patch(
                    "app.services.router.classify_request",
                    new_callable=AsyncMock,
                    return_value="infographic",
                ),
            ):
                request = ChatRequest(message="Create an infographic about revenue")
                response = await chat("test-session-infographic", request)

                body = ""
                async for chunk in response.body_iterator:
                    body += chunk

            # Parse SSE events
            events = []
            for line in body.split("\n"):
                if line.startswith("data: "):
                    import json
                    events.append(json.loads(line[6:]))

            event_types = [e["type"] for e in events]
            assert "status" in event_types
            assert "html" in event_types
            assert "summary" in event_types
            assert "done" in event_types

            # HTML event should contain base64 image
            html_events = [e for e in events if e["type"] == "html"]
            assert len(html_events) == 1
            assert "data:image/png;base64," in html_events[0]["content"]

        finally:
            await close_db()
```

**Note to implementor:** The test mocking may need adjustment depending on how the lazy imports work in `_handle_infographic()`. The lazy import pattern (`from app.services.infographic_service import InfographicService`) means patches need to target the source module. Follow the existing test patterns in the file.

### Phase 4 Verification

```bash
cd backend
python -m pytest tests/test_infographic_service.py -v
python -m pytest tests/test_router.py -v
python -m pytest tests/test_chat_create_image.py -v

# Full suite (all 270+ tests should pass):
python -m pytest -v

# Lint + types:
ruff check .
mypy .
```

---

## Phase 5: Documentation Updates

### 5.1 Update `CLAUDE.md`

**Plan table** — add row:
```
| 018 | NotebookLM-Style Infographic Generation | COMPLETE |
```

**LLM Intent Routing table** — add new Rule 2 and renumber:

| Rule | Condition | Route | Cost |
|------|-----------|-------|------|
| 1 | No existing HTML in session | CREATE | $0 |
| 1.5 | Removal/deletion keywords AND has HTML | EDIT | $0 |
| 2 | "infographic" keyword detected | INFOGRAPHIC | $0 |
| 3 | Transformation intent | CREATE | $0 |
| 4 | HTML exists → Haiku 4.5 classifies intent | create / edit / image | ~$0.0001 |

**Project Structure** — add to `backend/app/services/`:
```
    infographic_service.py   # Two-LLM infographic pipeline (Gemini art director + Nano Banana Pro renderer)
```

**Architecture section** — add mention of infographic pipeline.

### 5.2 Update `MEMORY.md`

Add:
```
## Plan 018 Status: COMPLETE
- Two-LLM infographic pipeline: Gemini 2.5 Pro (art director) → Nano Banana Pro (renderer)
- New "infographic" route via pre-routing regex (can't use Haiku max_tokens=1 for multi-token word)
- Visual prompt stored in user_prompt field for iteration context
- Infographic docs detected by minimal HTML structure (<500 chars after base64 removal)
- Zero schema changes, zero frontend changes, zero new dependencies
```

### Phase 5 Verification

Review CLAUDE.md changes are accurate. No automated check needed.

---

## Phase 6: Final Verification

```bash
# Full test suite
cd backend && python -m pytest -v

# Quality checks
cd backend && ruff check . && mypy .
cd frontend && npm run lint && npm run build

# Integration test (manual, after deploy):
# 1. Open app, type "Create an infographic about Q4 revenue growth with $5M total and 23% increase"
#    → Verify: status messages → infographic image appears in new tab
# 2. Type "Change the theme to navy and gold, keeping the graphics and words"
#    → Verify: new version generated, previous layout preserved
# 3. Open version history → Verify: both versions visible, can switch between them
# 4. Export as HTML → Verify: downloads HTML file with embedded image
# 5. Export as PNG → Verify: Playwright screenshots the infographic
# 6. Close tab → Verify: infographic discarded, previous doc activated
# 7. From a regular doc, type "Turn this into an infographic"
#    → Verify: existing doc content used as source material for infographic
```

---

## Key Architectural Notes for Implementors

### Why pre-routing regex, not Haiku classification?
The Haiku LLM call uses `max_tokens=1`, which can only return single-token words ("create", "edit", "image"). "infographic" is multi-token and would be truncated. Pre-routing regex is zero-cost, zero-latency, and the word "infographic" is unambiguous.

### Why store visual_prompt in user_prompt field?
The `user_prompt` field in `document_versions` already exists. For regular documents, it stores the user's chat message. For infographic documents, we repurpose it to store the art director's visual prompt — the detailed spec of what was rendered. This is critical for iteration: when the user says "change to navy", the art director needs to see what it previously specified (colors, layout, text) to make targeted modifications.

### Why _is_infographic_doc() heuristic?
Rather than adding a `document_type` column (schema change), we detect infographic documents by their HTML structure: after removing base64 data, infographic wrappers are <500 characters (just `<html><body><img>`). Regular HTML documents have `<main>`, `<header>`, `<section>`, etc. and are always >500 chars. This avoids a schema migration.

### Why full regeneration, not image editing?
Nano Banana Pro supports image editing (pass image + prompt), but:
1. Each 2K image stored per iteration adds 3-8MB to the database
2. Image editing quality for complex infographics is uncertain
3. Full regeneration with the previous visual prompt + user feedback produces consistently good results
4. The code IS architected to support image editing later (just pass image bytes to `generate_image()` contents)

### What imports are reused?
- `_compress_image` from `image_service.py` — imported in InfographicService when compression needed
- `_strip_base64_for_context` from `chat.py` — used in `_handle_infographic()` for context preparation
- `_extract_title` from `chat.py` — used for document naming
- `LLMProvider.generate()` from `base.py` — art director call
- `ImageProvider.generate_image()` from `base.py` — renderer call
- Timer pattern from `_handle_image()` — 8-second progress update
