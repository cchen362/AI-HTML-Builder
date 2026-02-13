"""
Surgical HTML editing engine using Claude tool_use.

This is the core of the rebuild. Instead of asking Claude to regenerate
an entire HTML document, we define tools that let Claude specify exact
search/replace operations. The server applies these deterministically.

Approach inspired by: Claude Artifacts, Cursor, Aider (EditBlock format)
"""

import re
from dataclasses import dataclass
from typing import Any

import structlog

from app.providers.base import LLMProvider, ToolCall, ToolResult  # noqa: F401
from app.utils.fuzzy_match import fuzzy_find_and_replace
from app.utils.html_validator import validate_edit_result

logger = structlog.get_logger()

# Regex to match data URIs with base64 content (images, fonts, etc.)
# Captures: data:mime/type;base64,<long_base64_string>
_DATA_URI_RE = re.compile(
    r'(data:[a-zA-Z0-9+/.-]+;base64,)'  # Group 1: prefix
    r'([A-Za-z0-9+/=]{100,})'            # Group 2: base64 payload (100+ chars)
)


def _strip_base64(html: str) -> tuple[str, dict[str, str]]:
    """Replace long base64 data URIs with short placeholders.

    Returns the stripped HTML and a mapping of placeholder → original base64.
    This prevents sending megabytes of image data to Claude for edits.
    """
    store: dict[str, str] = {}
    counter = 0

    def _replace(m: Any) -> str:
        nonlocal counter
        counter += 1
        placeholder = f"__B64_{counter}__"
        store[placeholder] = m.group(2)  # the base64 payload
        return m.group(1) + placeholder   # keep the data:mime;base64, prefix

    stripped = _DATA_URI_RE.sub(_replace, html)
    if store:
        logger.info(
            "Stripped base64 for edit",
            count=len(store),
            saved_chars=len(html) - len(stripped),
        )
    return stripped, store


def _restore_base64(html: str, store: dict[str, str]) -> str:
    """Restore base64 placeholders back to original data."""
    for placeholder, b64_data in store.items():
        html = html.replace(placeholder, b64_data)
    return html


# Tool definitions sent to Claude
EDIT_TOOLS = [
    {
        "name": "html_replace",
        "description": (
            "Replace a specific section of the HTML document with new content. "
            "The old_text must appear EXACTLY ONCE in the current document. "
            "Use the SHORTEST possible old_text that uniquely identifies the "
            "section to change. Include 1-3 surrounding lines only if needed "
            "for uniqueness. Do NOT include long runs of unchanging lines."
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
                    ),
                },
                "new_text": {
                    "type": "string",
                    "description": (
                        "The replacement text. Use empty string to delete "
                        "the section."
                    ),
                },
            },
            "required": ["old_text", "new_text"],
        },
    },
    {
        "name": "html_insert_after",
        "description": (
            "Insert new HTML content immediately after a specific anchor "
            "point in the document. The anchor_text must appear EXACTLY ONCE "
            "in the document. Use this for adding new sections, paragraphs, "
            "or elements."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "anchor_text": {
                    "type": "string",
                    "description": (
                        "The exact text after which to insert new content. "
                        "Must appear exactly once in the document."
                    ),
                },
                "new_content": {
                    "type": "string",
                    "description": (
                        "The new HTML content to insert after the anchor point."
                    ),
                },
            },
            "required": ["anchor_text", "new_content"],
        },
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
                    "description": (
                        "The exact text to remove from the document. "
                        "Must appear exactly once."
                    ),
                },
            },
            "required": ["text_to_delete"],
        },
    },
]

# System prompt for surgical editing (cached across requests)
EDIT_SYSTEM_PROMPT = [
    {
        "type": "text",
        "text": (
            "You are an expert HTML editor. You modify HTML documents using "
            "ONLY the provided tools.\n\n"
            "RULES:\n"
            "1. Use html_replace for every change. Keep old_text SHORT "
            "(1-5 lines) but unique.\n"
            "2. Use html_insert_after to add new sections or elements.\n"
            "3. Use html_delete to remove sections.\n"
            "4. Make ONLY the changes the user requested. NOTHING else.\n"
            "5. You MUST use the tools. Do NOT describe changes in prose.\n"
            "6. Break complex changes into multiple small tool calls.\n\n"
            "NEVER CHANGE:\n"
            "- Text content the user did not mention\n"
            "- CSS values the user did not ask to change\n"
            "- JavaScript functionality\n"
            "- HTML structure or element hierarchy\n"
            "- Comments, metadata, or whitespace\n"
            "- Anything not explicitly requested\n\n"
            "If the user says \"change the title\" - you change ONLY the "
            "title element.\n"
            "If the user says \"make the header blue\" - you change ONLY "
            "the header's color/background.\n"
            "The existing document represents deliberate design decisions. "
            "Respect them."
        ),
        "cache_control": {"type": "ephemeral"},
    }
]


@dataclass
class EditResult:
    """Result of a surgical editing operation."""

    html: str
    edit_summary: str
    applied_count: int
    error_count: int
    input_tokens: int
    output_tokens: int
    model: str
    used_fallback: bool = False


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

    async def edit(
        self,
        current_html: str,
        user_request: str,
        conversation_context: list[dict] | None = None,
    ) -> EditResult:
        """
        Perform surgical edit on HTML using tool-based approach.

        Args:
            current_html: The current HTML document
            user_request: What the user wants changed
            conversation_context: Recent chat messages for context

        Returns:
            EditResult with modified HTML, applied edits, and metadata
        """
        # Strip base64 data URIs to avoid sending megabytes of image data
        # to Claude. Edits operate on the stripped HTML; base64 is restored after.
        stripped_html, b64_store = _strip_base64(current_html)

        # Build messages with conversation context
        messages = self._build_messages(
            stripped_html, user_request, conversation_context
        )

        # Call Claude with tools (temperature=0 for deterministic precision)
        tool_result = await self.provider.generate_with_tools(
            system=EDIT_SYSTEM_PROMPT,  # type: ignore[arg-type]
            messages=messages,  # type: ignore[arg-type]
            tools=EDIT_TOOLS,  # type: ignore[arg-type]
            max_tokens=4096,
            temperature=0.0,
        )

        # Apply tool calls to the stripped HTML
        modified_html, applied, errors = self._apply_tool_calls(
            stripped_html, tool_result.tool_calls
        )

        # Validate result (compare stripped versions)
        if applied:
            is_valid, validation_msg = validate_edit_result(
                stripped_html, modified_html
            )
            if not is_valid:
                logger.warning(
                    "Edit validation failed", reason=validation_msg
                )
                errors.append(f"Validation: {validation_msg}")
                # Revert to stripped original
                modified_html = stripped_html
                applied = []

        # If ALL tool calls failed, fall back to full regeneration
        if errors and not applied:
            logger.warning(
                "All tool calls failed, attempting full regeneration fallback",
                error_count=len(errors),
                errors=errors[:3],
            )
            modified_html = await self._fallback_full_edit(
                stripped_html, user_request
            )
            applied = ["full_regeneration_fallback"]

        # Restore base64 data URIs back into the final HTML
        modified_html = _restore_base64(modified_html, b64_store)

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

    def _build_messages(
        self,
        html: str,
        request: str,
        context: list[dict] | None,
    ) -> list[dict]:
        """Build the message list for Claude, including conversation context."""
        messages: list[dict] = []

        # Add conversation context (last 3-4 exchanges for continuity)
        if context:
            recent = context[-8:]  # Last 4 user+assistant pairs
            for msg in recent:
                if msg.get("role") in ("user", "assistant"):
                    messages.append(
                        {
                            "role": msg["role"],
                            "content": msg.get("content", "")[:500],
                        }
                    )

        # Add the current HTML as context
        messages.append(
            {
                "role": "user",
                "content": f"Here is the current HTML document:\n\n{html}",
            }
        )
        messages.append(
            {
                "role": "assistant",
                "content": (
                    "I have the HTML document loaded. "
                    "What changes would you like?"
                ),
            }
        )

        # Add the user's edit request
        messages.append({"role": "user", "content": request})

        return messages

    def _apply_tool_calls(
        self, html: str, tool_calls: list[ToolCall]
    ) -> tuple[str, list[str], list[str]]:
        """
        Apply tool calls sequentially to the HTML.
        Returns (modified_html, applied_descriptions, error_descriptions).
        """
        modified = html
        applied: list[str] = []
        errors: list[str] = []

        for tc in tool_calls:
            if tc.name == "html_replace":
                modified, ok, desc = self._apply_replace(modified, tc.input)
            elif tc.name == "html_insert_after":
                modified, ok, desc = self._apply_insert_after(
                    modified, tc.input
                )
            elif tc.name == "html_delete":
                modified, ok, desc = self._apply_delete(modified, tc.input)
            else:
                ok, desc = False, f"Unknown tool: {tc.name}"

            if ok:
                applied.append(desc)
                logger.info(
                    "Tool call applied",
                    tool=tc.name,
                    description=desc[:80],
                )
            else:
                errors.append(desc)
                logger.warning(
                    "Tool call failed",
                    tool=tc.name,
                    error=desc[:80],
                )

        return modified, applied, errors

    def _apply_replace(
        self, html: str, params: dict
    ) -> tuple[str, bool, str]:
        """Apply an html_replace tool call with fuzzy matching fallback."""
        try:
            old_text = params["old_text"]
            new_text = params["new_text"]
        except KeyError as e:
            return html, False, f"Missing parameter: {e}"

        # Level 1: Exact match
        count = html.count(old_text)
        if count == 1:
            return (
                html.replace(old_text, new_text, 1),
                True,
                f"Replaced: {old_text[:60]}",
            )
        elif count > 1:
            return (
                html,
                False,
                f"Ambiguous ({count} matches): {old_text[:60]}",
            )

        # Level 2-4: Fuzzy matching
        result = fuzzy_find_and_replace(html, old_text, new_text)
        if result is not None:
            return result, True, f"Fuzzy replaced: {old_text[:60]}"

        return html, False, f"Not found: {old_text[:60]}"

    def _apply_insert_after(
        self, html: str, params: dict
    ) -> tuple[str, bool, str]:
        """Apply an html_insert_after tool call."""
        try:
            anchor = params["anchor_text"]
            new_content = params["new_content"]
        except KeyError as e:
            return html, False, f"Missing parameter: {e}"

        count = html.count(anchor)
        if count == 1:
            modified = html.replace(anchor, anchor + new_content, 1)
            return modified, True, f"Inserted after: {anchor[:60]}"
        elif count > 1:
            return (
                html,
                False,
                f"Ambiguous anchor ({count} matches): {anchor[:60]}",
            )
        else:
            # Try fuzzy match for anchor
            anchor_normalized = " ".join(anchor.split())
            pattern = re.escape(anchor_normalized).replace(r"\ ", r"\s+")
            match = re.search(pattern, html, re.DOTALL)
            if match:
                modified = (
                    html[: match.end()] + new_content + html[match.end() :]
                )
                return (
                    modified,
                    True,
                    f"Fuzzy inserted after: {anchor[:60]}",
                )
            return html, False, f"Anchor not found: {anchor[:60]}"

    def _apply_delete(
        self, html: str, params: dict
    ) -> tuple[str, bool, str]:
        """Apply an html_delete tool call."""
        try:
            target = params["text_to_delete"]
        except KeyError as e:
            return html, False, f"Missing parameter: {e}"

        count = html.count(target)
        if count == 1:
            return (
                html.replace(target, "", 1),
                True,
                f"Deleted: {target[:60]}",
            )
        elif count > 1:
            return (
                html,
                False,
                f"Ambiguous delete ({count} matches): {target[:60]}",
            )
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
            return (
                "Document regenerated (surgical edit was not possible "
                "for this change)"
            )
        if ai_text:
            # Use Claude's own text response as the summary (if any)
            return ai_text[:200]
        return f"Applied {len(applied)} change(s)"

    async def _fallback_full_edit(
        self, html: str, request: str
    ) -> str:
        """Last resort: ask Claude to regenerate with strong preservation prompt."""
        logger.info("Using full regeneration fallback")
        result = await self.provider.generate(
            system=(
                "You are modifying an existing HTML document. Make ONLY the "
                "change requested. Copy ALL other content exactly as it "
                "appears. Do not improve, clean up, or restructure anything "
                "the user did not ask you to change. Return the complete HTML "
                "starting with <!DOCTYPE html>. No markdown fences, no explanation."
            ),
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Current HTML:\n\n{html}\n\n"
                        f"Requested change: {request}"
                    ),
                }
            ],
            max_tokens=24000,
            temperature=0.1,
        )

        text = result.text

        # Try extracting HTML from markdown fences first
        if "```html" in text:
            start = text.index("```html") + len("```html")
            end = text.rfind("```")
            if end > start:
                text = text[start:end].strip()

        # Look for <!DOCTYPE
        if "<!DOCTYPE" in text:
            start = text.index("<!DOCTYPE")
            end = text.rfind("</html>") + len("</html>")
            if end > start:
                return text[start:end]

        # Look for <html tag as fallback
        if "<html" in text.lower():
            idx = text.lower().index("<html")
            end = text.rfind("</html>") + len("</html>")
            if end > idx:
                return text[idx:end]

        # Nothing HTML-like found — return ORIGINAL to preserve document
        logger.error(
            "Fallback regeneration produced no HTML, preserving original",
            response_length=len(text),
            response_preview=text[:200],
        )
        return html
