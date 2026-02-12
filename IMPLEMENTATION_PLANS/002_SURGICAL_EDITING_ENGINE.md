# Plan 002: Surgical Editing Engine

## STOP: Read This Entire Document Before Making Any Changes

This plan implements the tool-based surgical editing system that eliminates content drift. This is the **single most important plan** in the rebuild - it directly solves the #1 user pain point.

**Dependencies**: Plan 001 (Backend Foundation) completed
**Estimated effort**: 3-4 days

---

## IMPORTANT: Plan 001 Implementation Notes

Plan 001 deviated from its original code listings in several ways that directly affect this plan. **Read these before implementing:**

1. **aiosqlite API**: `execute_fetchone()` and `execute_fetchall()` do NOT exist. Use the cursor pattern:
   ```python
   cursor = await db.execute("SELECT ...", params)
   row = await cursor.fetchone()  # or fetchall()
   ```
2. **Error responses**: Use `raise HTTPException(status_code=N, detail="...")` not tuple returns.
3. **Mutable defaults**: Use `field(default_factory=...)` for list/dict dataclass fields.
4. **SQLite ordering**: Always add `id` as tiebreaker when ordering by `CURRENT_TIMESTAMP`.
5. **Anthropic SDK types**: Add `# type: ignore[arg-type]` when passing `list[dict]` for messages/tools.
6. **Pydantic v2**: Config uses `model_config = {}` dict, not `class Config:`.
7. **`ImageResponse` dataclass**: `ImageProvider.generate_image()` returns `ImageResponse`, not raw `bytes`.

See the "Implementation Notes" section at the end of Plan 001 for full details.

---

## Context & Rationale

### The Problem (Why Users Gave Up)
User says: "Change the title to Quarterly Report"
What happens: Title changes + formatting drifts + CSS values shift + text gets reworded
What should happen: ONLY the title changes. Everything else is physically untouched.

### The Root Cause
The v1 system asks Claude to regenerate the ENTIRE HTML document for every edit. Even with "preserve everything" prompts, the AI introduces drift because every token is a probabilistic choice.

### The Solution (How Claude Artifacts Does It)
Instead of returning a full document, Claude returns **tool calls** specifying exact search/replace operations. The replacement happens via **deterministic string operations on the server**, not AI generation.

```
v1: Claude generates 10,000 tokens (full document) → content drifts
v2: Claude generates 50 tokens (tool call) → server does string.replace() → zero drift
```

This is the same approach used by Claude Artifacts, Cursor, and Aider.

---

## Strict Rules

### MUST DO
- [ ] Use Claude `tool_use` API with custom tool definitions
- [ ] Use `temperature=0` for ALL edit operations (deterministic)
- [ ] Implement fuzzy matching fallback chain (exact → whitespace → sequence)
- [ ] Validate edit results before saving (structure check)
- [ ] Default to edit mode when HTML exists (NOT creation mode)
- [ ] Log every tool call applied and every failure
- [ ] Fall back to full regeneration ONLY when all tool calls fail
- [ ] Use prompt caching for system prompt + tool definitions

### MUST NOT DO
- [ ] Do NOT ask Claude to return complete HTML for edits
- [ ] Do NOT use temperature > 0 for edit operations
- [ ] Do NOT use the old keyword-based modification detection
- [ ] Do NOT make a separate "analysis" API call before editing
- [ ] Do NOT import any code from the old `claude_service.py`

---

## Phase 1: Tool Definitions

### Step 1.1: Define the Editing Tools

Create `app/services/editor.py`:

```python
"""
Surgical HTML editing engine using Claude tool_use.

This is the core of the rebuild. Instead of asking Claude to regenerate
an entire HTML document, we define tools that let Claude specify exact
search/replace operations. The server applies these deterministically.

Approach inspired by: Claude Artifacts, Cursor, Aider (EditBlock format)
"""

import structlog
from app.providers.base import LLMProvider, ToolResult, ToolCall
from app.utils.fuzzy_match import fuzzy_find_and_replace
from app.utils.html_validator import validate_edit_result

logger = structlog.get_logger()

# Tool definitions sent to Claude
EDIT_TOOLS = [
    {
        "name": "html_replace",
        "description": (
            "Replace a specific section of the HTML document with new content. "
            "The old_text must appear EXACTLY ONCE in the current document. "
            "Use the SHORTEST possible old_text that uniquely identifies the section to change. "
            "Include 1-3 surrounding lines only if needed for uniqueness. "
            "Do NOT include long runs of unchanging lines."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "old_text": {
                    "type": "string",
                    "description": (
                        "The exact text to find in the current HTML document. "
                        "Must match character-for-character including whitespace. "
                        "Must appear exactly once in the document. "
                        "Keep as short as possible while being unique."
                    )
                },
                "new_text": {
                    "type": "string",
                    "description": "The replacement text. Use empty string to delete the section."
                }
            },
            "required": ["old_text", "new_text"]
        }
    },
    {
        "name": "html_insert_after",
        "description": (
            "Insert new HTML content immediately after a specific anchor point in the document. "
            "The anchor_text must appear EXACTLY ONCE in the document. "
            "Use this for adding new sections, paragraphs, or elements."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "anchor_text": {
                    "type": "string",
                    "description": (
                        "The exact text after which to insert new content. "
                        "Must appear exactly once in the document."
                    )
                },
                "new_content": {
                    "type": "string",
                    "description": "The new HTML content to insert after the anchor point."
                }
            },
            "required": ["anchor_text", "new_content"]
        }
    },
    {
        "name": "html_delete",
        "description": (
            "Delete a specific section of text from the HTML document. "
            "The text_to_delete must appear EXACTLY ONCE."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "text_to_delete": {
                    "type": "string",
                    "description": "The exact text to remove from the document. Must appear exactly once."
                }
            },
            "required": ["text_to_delete"]
        }
    }
]

# System prompt for surgical editing (cached across requests)
EDIT_SYSTEM_PROMPT = [
    {
        "type": "text",
        "text": """You are an expert HTML editor. You modify HTML documents using ONLY the provided tools.

RULES:
1. Use html_replace for every change. Keep old_text SHORT (1-5 lines) but unique.
2. Use html_insert_after to add new sections or elements.
3. Use html_delete to remove sections.
4. Make ONLY the changes the user requested. NOTHING else.
5. You MUST use the tools. Do NOT describe changes in prose.
6. Break complex changes into multiple small tool calls.

NEVER CHANGE:
- Text content the user did not mention
- CSS values the user did not ask to change
- JavaScript functionality
- HTML structure or element hierarchy
- Comments, metadata, or whitespace
- Anything not explicitly requested

If the user says "change the title" — you change ONLY the title element.
If the user says "make the header blue" — you change ONLY the header's color/background.
The existing document represents deliberate design decisions. Respect them.""",
        "cache_control": {"type": "ephemeral"}
    }
]
```

---

## Phase 2: Edit Application Engine

### Step 2.1: Apply Tool Calls to HTML

Continue in `app/services/editor.py`:

```python
class SurgicalEditor:
    """
    Applies Claude's tool calls to HTML documents.

    Flow:
    1. Send HTML + user request + tools to Claude (temperature=0)
    2. Claude returns tool calls (html_replace, html_insert_after, html_delete)
    3. Apply each tool call as a deterministic string operation
    4. Validate the result
    5. Fall back to full regeneration if all tool calls fail
    """

    def __init__(self, provider: LLMProvider):
        self.provider = provider

    async def edit(self, current_html: str, user_request: str, conversation_context: list[dict] | None = None) -> EditResult:
        """
        Perform surgical edit on HTML using tool-based approach.

        Args:
            current_html: The current HTML document
            user_request: What the user wants changed
            conversation_context: Recent chat messages for context

        Returns:
            EditResult with modified HTML, applied edits, and metadata
        """
        # Build messages with conversation context
        messages = self._build_messages(current_html, user_request, conversation_context)

        # Call Claude with tools (temperature=0 for deterministic precision)
        tool_result = await self.provider.generate_with_tools(
            system=EDIT_SYSTEM_PROMPT,
            messages=messages,
            tools=EDIT_TOOLS,
            max_tokens=4096,
            temperature=0.0,
        )

        # Apply tool calls to HTML
        modified_html, applied, errors = self._apply_tool_calls(current_html, tool_result.tool_calls)

        # Validate result
        if applied:
            is_valid, validation_msg = validate_edit_result(current_html, modified_html)
            if not is_valid:
                logger.warning("Edit validation failed", reason=validation_msg)
                errors.append(f"Validation: {validation_msg}")
                # Revert to original
                modified_html = current_html
                applied = []

        # If ALL tool calls failed, fall back to full regeneration
        if errors and not applied:
            logger.warning("All tool calls failed, attempting full regeneration fallback",
                          error_count=len(errors), errors=errors[:3])
            modified_html = await self._fallback_full_edit(current_html, user_request)
            applied = ["full_regeneration_fallback"]

        # Generate edit summary from applied changes
        edit_summary = self._summarize_edits(applied, tool_result.text)

        return EditResult(
            html=modified_html,
            edit_summary=edit_summary,
            applied_count=len(applied),
            error_count=len(errors),
            input_tokens=tool_result.input_tokens,
            output_tokens=tool_result.output_tokens,
            model=tool_result.model,
            used_fallback=("full_regeneration_fallback" in applied),
        )

    def _build_messages(self, html: str, request: str, context: list[dict] | None) -> list[dict]:
        """Build the message list for Claude, including conversation context."""
        messages = []

        # Add conversation context (last 3-4 exchanges for continuity)
        if context:
            recent = context[-8:]  # Last 4 user+assistant pairs
            for msg in recent:
                if msg.get("role") in ("user", "assistant"):
                    messages.append({
                        "role": msg["role"],
                        "content": msg.get("content", "")[:500]  # Truncate long messages
                    })

        # Add the current HTML as context
        messages.append({
            "role": "user",
            "content": f"Here is the current HTML document:\n\n{html}"
        })
        messages.append({
            "role": "assistant",
            "content": "I have the HTML document loaded. What changes would you like?"
        })

        # Add the user's edit request
        messages.append({
            "role": "user",
            "content": request
        })

        return messages

    def _apply_tool_calls(self, html: str, tool_calls: list[ToolCall]) -> tuple[str, list[str], list[str]]:
        """
        Apply tool calls sequentially to the HTML.
        Returns (modified_html, applied_descriptions, error_descriptions).
        """
        modified = html
        applied = []
        errors = []

        for tc in tool_calls:
            if tc.name == "html_replace":
                modified, ok, desc = self._apply_replace(modified, tc.input)
            elif tc.name == "html_insert_after":
                modified, ok, desc = self._apply_insert_after(modified, tc.input)
            elif tc.name == "html_delete":
                modified, ok, desc = self._apply_delete(modified, tc.input)
            else:
                ok, desc = False, f"Unknown tool: {tc.name}"

            if ok:
                applied.append(desc)
                logger.info("Tool call applied", tool=tc.name, description=desc[:80])
            else:
                errors.append(desc)
                logger.warning("Tool call failed", tool=tc.name, error=desc[:80])

        return modified, applied, errors

    def _apply_replace(self, html: str, params: dict) -> tuple[str, bool, str]:
        """Apply an html_replace tool call with fuzzy matching fallback."""
        old_text = params["old_text"]
        new_text = params["new_text"]

        # Level 1: Exact match
        count = html.count(old_text)
        if count == 1:
            return html.replace(old_text, new_text, 1), True, f"Replaced: {old_text[:60]}"
        elif count > 1:
            return html, False, f"Ambiguous ({count} matches): {old_text[:60]}"

        # Level 2-4: Fuzzy matching
        result = fuzzy_find_and_replace(html, old_text, new_text)
        if result is not None:
            return result, True, f"Fuzzy replaced: {old_text[:60]}"

        return html, False, f"Not found: {old_text[:60]}"

    def _apply_insert_after(self, html: str, params: dict) -> tuple[str, bool, str]:
        """Apply an html_insert_after tool call."""
        anchor = params["anchor_text"]
        new_content = params["new_content"]

        count = html.count(anchor)
        if count == 1:
            modified = html.replace(anchor, anchor + new_content, 1)
            return modified, True, f"Inserted after: {anchor[:60]}"
        elif count > 1:
            return html, False, f"Ambiguous anchor ({count} matches): {anchor[:60]}"
        else:
            # Try fuzzy match for anchor
            import re
            anchor_normalized = " ".join(anchor.split())
            pattern = re.escape(anchor_normalized).replace(r"\ ", r"\s+")
            match = re.search(pattern, html, re.DOTALL)
            if match:
                modified = html[:match.end()] + new_content + html[match.end():]
                return modified, True, f"Fuzzy inserted after: {anchor[:60]}"
            return html, False, f"Anchor not found: {anchor[:60]}"

    def _apply_delete(self, html: str, params: dict) -> tuple[str, bool, str]:
        """Apply an html_delete tool call."""
        target = params["text_to_delete"]

        count = html.count(target)
        if count == 1:
            return html.replace(target, "", 1), True, f"Deleted: {target[:60]}"
        elif count > 1:
            return html, False, f"Ambiguous delete ({count} matches): {target[:60]}"
        else:
            result = fuzzy_find_and_replace(html, target, "")
            if result is not None:
                return result, True, f"Fuzzy deleted: {target[:60]}"
            return html, False, f"Delete target not found: {target[:60]}"

    def _summarize_edits(self, applied: list[str], ai_text: str) -> str:
        """Generate a brief summary of what was changed."""
        if not applied:
            return "No changes applied"
        if len(applied) == 1 and "full_regeneration_fallback" in applied[0]:
            return "Document regenerated (surgical edit was not possible for this change)"
        if ai_text:
            # Use Claude's own text response as the summary (if any)
            return ai_text[:200]
        return f"Applied {len(applied)} change(s)"

    async def _fallback_full_edit(self, html: str, request: str) -> str:
        """Last resort: ask Claude to regenerate with strong preservation prompt."""
        logger.info("Using full regeneration fallback")
        result = await self.provider.generate(
            system=(
                "You are modifying an existing HTML document. Make ONLY the change requested. "
                "Copy ALL other content exactly as it appears. Do not improve, clean up, or restructure "
                "anything the user did not ask you to change. Return the complete HTML."
            ),
            messages=[
                {"role": "user", "content": f"Current HTML:\n\n{html}\n\nRequested change: {request}"}
            ],
            max_tokens=16000,
            temperature=0.1,  # Low but not zero (needs some flexibility for full regen)
        )

        # Extract HTML from response
        text = result.text
        if "<!DOCTYPE" in text:
            start = text.index("<!DOCTYPE")
            end = text.rfind("</html>") + len("</html>")
            if end > start:
                return text[start:end]
        return text


from dataclasses import dataclass

@dataclass
class EditResult:
    html: str
    edit_summary: str
    applied_count: int
    error_count: int
    input_tokens: int
    output_tokens: int
    model: str
    used_fallback: bool = False
```

---

## Phase 3: Fuzzy Matching (Aider-Inspired)

### Step 3.1: utils/fuzzy_match.py

```python
"""
Fuzzy string matching for HTML editing, inspired by Aider's EditBlock format.

When Claude's tool call specifies old_text that doesn't match exactly
(usually due to whitespace differences), this module tries progressively
looser matching strategies before giving up.

Matching chain:
1. Strip trailing whitespace from each line
2. Normalize all whitespace (collapse to single spaces)
3. Sequence matching (difflib) with 85% threshold
"""

import re
import difflib
from typing import Optional

def fuzzy_find_and_replace(html: str, old_text: str, new_text: str) -> Optional[str]:
    """
    Try to find and replace old_text in html using fuzzy matching.
    Returns modified html if a match was found, None otherwise.
    """
    # Level 1: Strip trailing whitespace from each line
    result = _try_stripped_whitespace(html, old_text, new_text)
    if result is not None:
        return result

    # Level 2: Normalize all whitespace
    result = _try_normalized_whitespace(html, old_text, new_text)
    if result is not None:
        return result

    # Level 3: Sequence matching (last resort)
    result = _try_sequence_match(html, old_text, new_text)
    if result is not None:
        return result

    return None


def _try_stripped_whitespace(html: str, old_text: str, new_text: str) -> Optional[str]:
    """Match after stripping trailing whitespace from each line."""
    old_lines = [line.rstrip() for line in old_text.split("\n")]
    old_stripped = "\n".join(old_lines)

    html_lines = html.split("\n")
    html_stripped_lines = [line.rstrip() for line in html_lines]
    html_stripped = "\n".join(html_stripped_lines)

    if html_stripped.count(old_stripped) == 1:
        idx = html_stripped.index(old_stripped)
        # Find the corresponding lines in the original
        start_line = html_stripped[:idx].count("\n")
        end_line = start_line + old_stripped.count("\n")
        original_chunk = "\n".join(html_lines[start_line:end_line + 1])
        if html.count(original_chunk) == 1:
            return html.replace(original_chunk, new_text, 1)

    return None


def _try_normalized_whitespace(html: str, old_text: str, new_text: str) -> Optional[str]:
    """Match using regex with flexible whitespace."""
    old_normalized = " ".join(old_text.split())
    if not old_normalized:
        return None

    # Build regex pattern: each word separated by flexible whitespace
    pattern = re.escape(old_normalized)
    pattern = pattern.replace(r"\ ", r"\s+")

    match = re.search(pattern, html, re.DOTALL)
    if match:
        # Verify uniqueness
        all_matches = list(re.finditer(pattern, html, re.DOTALL))
        if len(all_matches) == 1:
            return html[:match.start()] + new_text + html[match.end():]

    return None


def _try_sequence_match(html: str, old_text: str, new_text: str, threshold: float = 0.85) -> Optional[str]:
    """Match using difflib SequenceMatcher with a high similarity threshold."""
    old_lines = old_text.strip().split("\n")
    html_lines = html.split("\n")
    window = len(old_lines)

    if window == 0 or window > len(html_lines):
        return None

    best_ratio = 0.0
    best_start = 0

    for i in range(len(html_lines) - window + 1):
        candidate = html_lines[i:i + window]
        ratio = difflib.SequenceMatcher(None, old_lines, candidate).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_start = i

    if best_ratio >= threshold:
        original_chunk = "\n".join(html_lines[best_start:best_start + window])
        if html.count(original_chunk) == 1:
            return html.replace(original_chunk, new_text, 1)

    return None
```

---

## Phase 4: Request Classifier

### Step 4.1: services/router.py

```python
"""
Model routing based on request state and intent.

Three rules, zero ambiguity:
1. No HTML exists → Gemini 2.5 Pro (CREATE)
2. Image/diagram requested → Nano Banana Pro (IMAGE)
3. Everything else → Claude Sonnet 4.5 (EDIT via tool_use)
"""

import structlog

logger = structlog.get_logger()

# Keywords that indicate image generation request
IMAGE_KEYWORDS = [
    "diagram", "infographic", "flowchart", "chart", "illustration",
    "visual", "picture", "image", "graph", "org chart",
    "process flow", "timeline diagram", "architecture diagram",
    "mind map", "pie chart", "bar chart", "visualization"
]

# Keywords that indicate creating a NEW document (not editing)
NEW_DOCUMENT_KEYWORDS = [
    "create a new", "build a new", "make a new", "generate a new",
    "start over", "from scratch", "new page", "new document",
    "start fresh", "create a separate", "build a separate",
    "make a separate", "another document", "new version from scratch"
]


def classify_request(user_input: str, has_existing_html: bool) -> str:
    """
    Classify the user's request into a routing category.

    Returns:
        'create' - Route to Gemini 2.5 Pro for new document creation
        'image' - Route to Nano Banana Pro for image generation
        'edit' - Route to Claude Sonnet 4.5 for surgical editing (DEFAULT)
    """
    input_lower = user_input.lower()

    # Rule 1: No existing HTML → always create
    if not has_existing_html:
        logger.info("[ROUTER] No existing HTML → CREATE", request=user_input[:80])
        return "create"

    # Rule 2: Explicit new document request
    if any(phrase in input_lower for phrase in NEW_DOCUMENT_KEYWORDS):
        logger.info("[ROUTER] New document request → CREATE", request=user_input[:80])
        return "create"

    # Rule 3: Image/diagram/infographic request
    if any(keyword in input_lower for keyword in IMAGE_KEYWORDS):
        logger.info("[ROUTER] Image request detected → IMAGE", request=user_input[:80])
        return "image"

    # Rule 4: EVERYTHING ELSE → edit (the default)
    logger.info("[ROUTER] Default → EDIT", request=user_input[:80])
    return "edit"
```

---

## Phase 5: Integration with Chat API

### Step 5.1: Update api/chat.py

Update the chat endpoint to use the surgical editor:

```python
@router.post("/api/chat/{session_id}")
async def chat(session_id: str, request: ChatRequest):
    from app.services.session_service import session_service
    from app.services.router import classify_request
    from app.services.editor import SurgicalEditor
    from app.providers.anthropic_provider import AnthropicProvider
    from app.services.cost_tracker import cost_tracker

    # Ensure session exists
    session_id = await session_service.get_or_create_session(session_id)

    # Get or create active document
    active_doc = await session_service.get_active_document(session_id)

    # Get current HTML (if any)
    current_html = None
    if active_doc:
        current_html = await session_service.get_latest_html(active_doc["id"])

    # Save user message
    doc_id = active_doc["id"] if active_doc else None
    await session_service.add_chat_message(session_id, "user", request.message, doc_id)

    # Classify request
    route = classify_request(request.message, current_html is not None)

    async def event_stream():
        try:
            if route == "edit" and current_html:
                # SURGICAL EDIT via Claude tool_use
                yield f"data: {json.dumps({'type': 'status', 'content': 'Editing...'})}\n\n"

                editor = SurgicalEditor(AnthropicProvider())
                chat_history = await session_service.get_chat_history(session_id, limit=8)

                result = await editor.edit(current_html, request.message, chat_history)

                # Save new version
                version = await session_service.save_version(
                    active_doc["id"],
                    result.html,
                    user_prompt=request.message,
                    edit_summary=result.edit_summary,
                    model_used=result.model,
                    tokens_used=result.input_tokens + result.output_tokens,
                )

                # Track cost
                await cost_tracker.record(
                    result.model, result.input_tokens, result.output_tokens
                )

                # Save assistant message
                await session_service.add_chat_message(
                    session_id, "assistant", result.edit_summary,
                    active_doc["id"], "edit_confirmation"
                )

                yield f"data: {json.dumps({'type': 'html', 'content': result.html, 'version': version})}\n\n"
                yield f"data: {json.dumps({'type': 'summary', 'content': result.edit_summary})}\n\n"

            elif route == "create":
                # NEW DOCUMENT via Gemini (implemented in Plan 003)
                yield f"data: {json.dumps({'type': 'status', 'content': 'Creating document...'})}\n\n"
                # Placeholder - Plan 003 implements this
                yield f"data: {json.dumps({'type': 'error', 'content': 'Creation not yet implemented'})}\n\n"

            elif route == "image":
                # IMAGE generation via Nano Banana Pro (implemented in Plan 003)
                yield f"data: {json.dumps({'type': 'status', 'content': 'Generating image...'})}\n\n"
                # Placeholder - Plan 003 implements this
                yield f"data: {json.dumps({'type': 'error', 'content': 'Image generation not yet implemented'})}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            logger.error("Chat error", error=str(e), session_id=session_id[:8])
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"})
```

---

## Build Verification

```bash
# Lint and type check
ruff check app/services/editor.py app/services/router.py app/utils/fuzzy_match.py
mypy app/services/editor.py app/services/router.py app/utils/fuzzy_match.py --ignore-missing-imports

# Run tests
pytest tests/test_editor.py tests/test_fuzzy_match.py tests/test_router.py -v

# Manual test (requires valid API key)
# Start server, create a session, create a document with HTML, then send an edit request
```

---

## Testing Scenarios

### Surgical Editing Tests

| Test | Input | Expected Result | Pass/Fail |
|------|-------|----------------|-----------|
| Simple title change | "Change the title to Test" | Only `<title>` and/or `<h1>` text changes | [ ] |
| Color change | "Make the header background red" | Only header background-color CSS changes | [ ] |
| Add paragraph | "Add a paragraph about security after the intro" | New paragraph inserted, everything else unchanged | [ ] |
| Delete section | "Remove the footer" | Footer removed, rest intact | [ ] |
| Multi-edit | "Change title to X and make links blue" | Two tool calls, both applied, nothing else changes | [ ] |
| Whitespace mismatch | Claude returns old_text with slightly different indentation | Fuzzy match succeeds | [ ] |
| Ambiguous match | old_text appears 3 times | Error reported, no change applied | [ ] |
| All edits fail | Every tool call fails to match | Falls back to full regeneration | [ ] |
| Validation catches breakage | Edit removes `</html>` | Reverts to original, logs warning | [ ] |

### Request Classifier Tests

| Test | Input | Has HTML? | Expected Route | Pass/Fail |
|------|-------|-----------|---------------|-----------|
| "Create an impact assessment" | No | create | [ ] |
| "Change the title to X" | Yes | edit | [ ] |
| "Add a diagram showing the process" | Yes | image | [ ] |
| "Make it blue" | Yes | edit | [ ] |
| "Create a separate summary document" | Yes | create | [ ] |
| "Start over" | Yes | create | [ ] |
| "Improve the formatting" | Yes | edit | [ ] |
| "Add an infographic about costs" | Yes | image | [ ] |

### Content Preservation Tests (CRITICAL)

| Test | Steps | Expected | Pass/Fail |
|------|-------|----------|-----------|
| 5-iteration drift test | Create doc → Edit 5 times (title, color, text, add section, change font) | After all 5 edits, ONLY the 5 requested changes are present. No other differences. | [ ] |
| CSS preservation | Change one CSS property | All other CSS properties identical (compare character-by-character) | [ ] |
| JavaScript preservation | Change a text element | All JavaScript functions identical | [ ] |
| Comment preservation | Edit a heading | All HTML comments still present | [ ] |
| Large document test | 100KB HTML, change one word | File size difference is only the word length difference | [ ] |

---

## Rollback Plan

If the surgical editor fails in production:
1. The `_fallback_full_edit` method provides a safety net
2. Set `FORCE_FULL_REGEN=true` env var to bypass tool_use entirely
3. Previous versions are always available in SQLite (undo to any point)

---

## Sign-off Checklist

- [ ] `SurgicalEditor` class implemented with all tool call handlers
- [ ] Fuzzy matching passes all 3 levels (stripped, normalized, sequence)
- [ ] HTML validation catches structural breakage
- [ ] Request classifier routes correctly for all test cases
- [ ] Temperature is 0 for all edit operations
- [ ] Prompt caching enabled for system prompt
- [ ] Fallback to full regeneration works when tool calls fail
- [ ] 5-iteration drift test passes with zero unwanted changes
- [ ] All tests pass
- [ ] No imports from old `claude_service.py`
- [ ] Old v1 reference files deleted (see cleanup section below)

### Dead Code Cleanup (End of Plan 002)
After this plan is complete, delete the following old v1 files that were kept as reference:
- `backend/app/services/claude_service.py` → logic extracted into `services/editor.py`
- `backend/app/services/artifact_manager.py` → logic extracted into `services/session_service.py`
- `backend/app/models/session.py` → replaced by new `models/session.py`
- `backend/app/models/schemas.py` → replaced by new `models/chat.py`
- `backend/app/utils/logger.py` → replaced by structlog config in `main.py`
- `backend/app/utils/sanitizer.py` → replaced by `utils/html_validator.py`

---

*Created: February 12, 2026*
*Plan: 002 - Surgical Editing Engine*
*Next: Plan 003 - Multi-Model Routing*
