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


def fuzzy_find_and_replace(
    html: str, old_text: str, new_text: str
) -> str | None:
    """
    Try to find and replace old_text in html using fuzzy matching.
    Returns modified html if a match was found, None otherwise.
    """
    if not old_text:
        return None

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


def _try_stripped_whitespace(
    html: str, old_text: str, new_text: str
) -> str | None:
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
        original_chunk = "\n".join(html_lines[start_line : end_line + 1])
        if html.count(original_chunk) == 1:
            return html.replace(original_chunk, new_text, 1)

    return None


def _try_normalized_whitespace(
    html: str, old_text: str, new_text: str
) -> str | None:
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
            return html[: match.start()] + new_text + html[match.end() :]

    return None


def _try_sequence_match(
    html: str,
    old_text: str,
    new_text: str,
    threshold: float = 0.85,
) -> str | None:
    """Match using difflib SequenceMatcher with a high similarity threshold."""
    old_lines = old_text.strip().split("\n")
    html_lines = html.split("\n")
    window = len(old_lines)

    if window == 0 or window > len(html_lines):
        return None

    best_ratio = 0.0
    best_start = 0

    for i in range(len(html_lines) - window + 1):
        candidate = html_lines[i : i + window]
        ratio = difflib.SequenceMatcher(None, old_lines, candidate).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_start = i

    if best_ratio >= threshold:
        original_chunk = "\n".join(
            html_lines[best_start : best_start + window]
        )
        if html.count(original_chunk) == 1:
            return html.replace(original_chunk, new_text, 1)

    return None
