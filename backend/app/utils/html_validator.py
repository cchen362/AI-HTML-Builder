import re

# Regex to match base64 image data URIs (100+ chars of base64 payload)
_BASE64_IMAGE_RE = re.compile(
    r'data:image/[^;]+;base64,[A-Za-z0-9+/=]{100,}'
)


def is_infographic_html(html: str) -> bool:
    """Detect infographic wrapper docs (minimal HTML with single base64 <img>).

    Infographic documents have a distinctive structure created by
    wrap_infographic_html(): <600 chars of HTML after removing base64
    payloads, with a single <img> tag and no structural content tags
    (<main>, <header>, <section>).

    Regular docs with embedded images are excluded by the structural
    tag check.
    """
    stripped = _BASE64_IMAGE_RE.sub("", html)
    if len(stripped) >= 600:
        return False
    if "<img" not in html or "data:image" not in html:
        return False
    lower = html.lower()
    if "<main" in lower or "<header" in lower or "<section" in lower:
        return False
    return True


def validate_edit_result(original: str, modified: str) -> tuple[bool, str]:
    """Validate that edits didn't break the document structure."""
    if not modified or not modified.strip():
        return False, "Modified HTML is empty"

    # Check document didn't shrink dramatically
    if len(original) > 100:
        ratio = len(modified) / len(original)
        if ratio < 0.3:
            return False, f"Document shrank to {ratio:.0%} of original size"

    # Check critical structural elements preserved
    for tag in ["</head>", "</body>", "</html>"]:
        if tag in original.lower() and tag not in modified.lower():
            return False, f"Lost {tag} closing tag"

    # Check style and script tags preserved
    original_styles = original.lower().count("<style")
    modified_styles = modified.lower().count("<style")
    if modified_styles < original_styles:
        return False, f"Lost style tags: {original_styles} -> {modified_styles}"

    original_scripts = original.lower().count("<script")
    modified_scripts = modified.lower().count("<script")
    if modified_scripts < original_scripts:
        return False, f"Lost script tags: {original_scripts} -> {modified_scripts}"

    return True, "OK"
