"""Tests for HTML validator utilities including infographic detection."""

import os

os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key-for-testing")

from app.utils.html_validator import is_infographic_html, validate_edit_result


# ---------------------------------------------------------------------------
# Sample HTML fixtures
# ---------------------------------------------------------------------------

INFOGRAPHIC_HTML = (
    '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
    '<style>*{margin:0}body{background:#0a0a0f;display:flex;'
    'justify-content:center;align-items:center;min-height:100vh}'
    'img{max-width:100%;height:auto}</style></head>'
    '<body><img src="data:image/png;base64,' + 'A' * 200 + '" alt="test"/></body></html>'
)

REGULAR_HTML = (
    '<!DOCTYPE html><html><head><title>Doc</title></head><body>'
    '<header><h1>Title</h1></header><main><section><p>Content</p>'
    '</section></main></body></html>'
)

NO_IMAGE_HTML = '<html><head></head><body><p>Hello world</p></body></html>'


# ---------------------------------------------------------------------------
# is_infographic_html tests
# ---------------------------------------------------------------------------

def test_is_infographic_html_true():
    """Infographic wrapper (minimal HTML with base64 img) should return True."""
    assert is_infographic_html(INFOGRAPHIC_HTML) is True


def test_is_infographic_html_false_for_regular():
    """Regular document with structural tags should return False."""
    assert is_infographic_html(REGULAR_HTML) is False


def test_is_infographic_html_false_for_no_image():
    """Document without any image should return False."""
    assert is_infographic_html(NO_IMAGE_HTML) is False


def test_is_infographic_html_false_for_long_html():
    """Document with >600 chars of non-base64 HTML should return False."""
    long_html = (
        '<html><head></head><body>'
        '<img src="data:image/png;base64,' + 'A' * 200 + '" />'
        '<p>' + 'x' * 600 + '</p>'
        '</body></html>'
    )
    assert is_infographic_html(long_html) is False


def test_is_infographic_html_false_with_main_tag():
    """Document with <main> tag should return False even if short."""
    html = (
        '<html><head></head><body>'
        '<main><img src="data:image/png;base64,' + 'A' * 200 + '" /></main>'
        '</body></html>'
    )
    assert is_infographic_html(html) is False


def test_is_infographic_html_false_with_section_tag():
    """Document with <section> tag should return False."""
    html = (
        '<html><head></head><body>'
        '<section><img src="data:image/png;base64,' + 'A' * 200 + '" /></section>'
        '</body></html>'
    )
    assert is_infographic_html(html) is False


# ---------------------------------------------------------------------------
# validate_edit_result tests (existing function, sanity check)
# ---------------------------------------------------------------------------

def test_validate_edit_result_ok():
    original = '<!DOCTYPE html><html><head><style>.a{}</style></head><body></body></html>'
    modified = '<!DOCTYPE html><html><head><style>.a{color:red}</style></head><body><p>hi</p></body></html>'
    valid, msg = validate_edit_result(original, modified)
    assert valid is True
    assert msg == "OK"
