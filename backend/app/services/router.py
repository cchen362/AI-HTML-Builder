"""
Model routing based on request state and intent.

Three rules, zero ambiguity:
1. No HTML exists -> Gemini 2.5 Pro (CREATE)
2. Image/diagram requested -> Nano Banana Pro (IMAGE)
3. Everything else -> Claude Sonnet 4.5 (EDIT via tool_use)
"""

import structlog

logger = structlog.get_logger()

# Keywords that indicate image generation request
IMAGE_KEYWORDS = [
    "diagram",
    "infographic",
    "flowchart",
    "chart",
    "illustration",
    "visual",
    "picture",
    "image",
    "graph",
    "org chart",
    "process flow",
    "timeline diagram",
    "architecture diagram",
    "mind map",
    "pie chart",
    "bar chart",
    "visualization",
]

# Keywords that indicate creating a NEW document (not editing)
NEW_DOCUMENT_KEYWORDS = [
    "create a new",
    "build a new",
    "make a new",
    "generate a new",
    "start over",
    "from scratch",
    "new page",
    "new document",
    "start fresh",
    "create a separate",
    "build a separate",
    "make a separate",
    "another document",
    "new version from scratch",
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

    # Rule 1: No existing HTML -> always create
    if not has_existing_html:
        logger.info(
            "[ROUTER] No existing HTML -> CREATE",
            request=user_input[:80],
        )
        return "create"

    # Rule 2: Explicit new document request
    if any(phrase in input_lower for phrase in NEW_DOCUMENT_KEYWORDS):
        logger.info(
            "[ROUTER] New document request -> CREATE",
            request=user_input[:80],
        )
        return "create"

    # Rule 3: Image/diagram/infographic request
    if any(keyword in input_lower for keyword in IMAGE_KEYWORDS):
        logger.info(
            "[ROUTER] Image request detected -> IMAGE",
            request=user_input[:80],
        )
        return "image"

    # Rule 4: EVERYTHING ELSE -> edit (the default)
    logger.info("[ROUTER] Default -> EDIT", request=user_input[:80])
    return "edit"
