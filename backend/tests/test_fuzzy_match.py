from app.utils.fuzzy_match import fuzzy_find_and_replace


# --- Level 1: Stripped whitespace matching ---


def test_stripped_whitespace_trailing_spaces():
    """old_text has trailing spaces that html does not."""
    html = "<h1>Hello</h1>\n<p>World</p>"
    old_text = "<h1>Hello</h1>   \n<p>World</p>  "
    new_text = "<h1>New</h1>\n<p>World</p>"
    result = fuzzy_find_and_replace(html, old_text, new_text)
    assert result == "<h1>New</h1>\n<p>World</p>"


def test_stripped_whitespace_html_has_trailing():
    """html has trailing spaces that old_text does not."""
    html = "<h1>Hello</h1>   \n<p>World</p>  "
    old_text = "<h1>Hello</h1>\n<p>World</p>"
    new_text = "<h1>Changed</h1>\n<p>World</p>"
    result = fuzzy_find_and_replace(html, old_text, new_text)
    assert result is not None
    assert "<h1>Changed</h1>" in result


# --- Level 2: Normalized whitespace matching ---


def test_normalized_whitespace_different_indentation():
    """old_text has different indentation than html."""
    html = "  <div>\n    <h1>Title</h1>\n  </div>"
    old_text = "<div> <h1>Title</h1> </div>"
    new_text = "<div><h2>New Title</h2></div>"
    result = fuzzy_find_and_replace(html, old_text, new_text)
    assert result is not None
    assert "<h2>New Title</h2>" in result


def test_normalized_whitespace_newlines_vs_spaces():
    """old_text uses spaces where html uses newlines."""
    html = "<ul>\n  <li>One</li>\n  <li>Two</li>\n</ul>"
    old_text = "<ul> <li>One</li> <li>Two</li> </ul>"
    new_text = "<ul><li>A</li><li>B</li></ul>"
    result = fuzzy_find_and_replace(html, old_text, new_text)
    assert result is not None
    assert "<li>A</li>" in result


# --- Level 3: Sequence matching ---


def test_sequence_match_above_threshold():
    """old_text has minor differences but >85% similar at the line level."""
    html = (
        "<header>\n"
        "<h1>Welcome</h1>\n"
        "<p>Paragraph one text here</p>\n"
        "<p>Paragraph two text here</p>\n"
        "<p>Paragraph three text here</p>\n"
        "<p>Paragraph four text here</p>\n"
        "<p>Paragraph five text here</p>\n"
        "<p>Paragraph six text here</p>\n"
        "<p>Paragraph seven text here</p>\n"
        "<p>Paragraph eight text here</p>\n"
        "</header>"
    )
    # 8 lines: 7 identical + 1 different = 87.5% ratio (above 0.85 threshold)
    old_text = (
        "<p>Paragraph one text here</p>\n"
        "<p>Paragraph two text here</p>\n"
        "<p>Paragraph three text here</p>\n"
        "<p>Paragraph four text here</p>\n"
        "<p>Paragraph five text here</p>\n"
        "<p>Paragraph six text here</p>\n"
        "<p>DIFFERENT LINE HERE</p>\n"
        "<p>Paragraph eight text here</p>"
    )
    new_text = "<p>Replaced block</p>"
    result = fuzzy_find_and_replace(html, old_text, new_text)
    assert result is not None
    assert "<p>Replaced block</p>" in result


def test_sequence_match_below_threshold():
    """old_text is too different from anything in html."""
    html = "<h1>Hello World</h1>\n<p>Content here</p>"
    old_text = "<footer>Completely different text</footer>"
    new_text = "<div>Replacement</div>"
    result = fuzzy_find_and_replace(html, old_text, new_text)
    assert result is None


# --- Edge cases ---


def test_empty_old_text_returns_none():
    html = "<h1>Hello</h1>"
    result = fuzzy_find_and_replace(html, "", "new")
    assert result is None


def test_ambiguous_normalized_match_returns_none():
    """Normalized match finds 2 locations - should return None."""
    html = "<p>Hello World</p>\n<span>Hello World</span>"
    old_text = "Hello    World"  # Normalizes to "Hello World" - 2 matches
    new_text = "Goodbye"
    result = fuzzy_find_and_replace(html, old_text, new_text)
    assert result is None


def test_replacement_preserves_surrounding_content():
    """Content before and after the match must be untouched."""
    html = "BEFORE\n<h1>Old Title</h1>\nAFTER"
    old_text = "<h1>Old Title</h1>  "  # Trailing space triggers fuzzy
    new_text = "<h1>New Title</h1>"
    result = fuzzy_find_and_replace(html, old_text, new_text)
    assert result is not None
    assert result.startswith("BEFORE\n")
    assert result.endswith("\nAFTER")
    assert "<h1>New Title</h1>" in result


def test_multiline_replacement():
    """Replace a multi-line block."""
    html = "<div>\n  <h1>Title</h1>\n  <p>Paragraph</p>\n</div>"
    # Trailing whitespace to trigger fuzzy
    old_text = "  <h1>Title</h1>   \n  <p>Paragraph</p>  "
    new_text = "  <h1>New</h1>\n  <p>Updated</p>"
    result = fuzzy_find_and_replace(html, old_text, new_text)
    assert result is not None
    assert "<h1>New</h1>" in result
    assert "<p>Updated</p>" in result


def test_delete_operation():
    """Passing empty new_text effectively deletes the match."""
    html = "<div>Keep</div>\n<p>Delete me</p>\n<div>Keep too</div>"
    old_text = "<p>Delete me</p>  "  # Trailing space for fuzzy
    result = fuzzy_find_and_replace(html, old_text, "")
    assert result is not None
    assert "<p>Delete me</p>" not in result
    assert "<div>Keep</div>" in result
    assert "<div>Keep too</div>" in result
