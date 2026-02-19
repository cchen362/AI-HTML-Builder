import pytest
from unittest.mock import AsyncMock
from app.services.creator import DocumentCreator, extract_html
from app.providers.base import LLMProvider, GenerationResult


SAMPLE_HTML = """<!DOCTYPE html>
<html lang="en">
<head><title>Test</title></head>
<body><h1>Hello</h1></body>
</html>"""


@pytest.fixture
def mock_provider():
    return AsyncMock(spec=LLMProvider)


@pytest.fixture
def mock_fallback():
    return AsyncMock(spec=LLMProvider)


@pytest.fixture
def creator(mock_provider, mock_fallback):
    return DocumentCreator(mock_provider, mock_fallback)


# --- create() tests ---


@pytest.mark.asyncio
async def test_create_returns_html_and_result(mock_provider, creator):
    mock_provider.generate.return_value = GenerationResult(
        text=SAMPLE_HTML,
        input_tokens=50,
        output_tokens=200,
        model="gemini-2.5-pro",
    )

    html, result = await creator.create("Create a landing page")

    assert "<!DOCTYPE html>" in html
    assert "</html>" in html
    assert result.input_tokens == 50
    assert result.output_tokens == 200
    assert result.model == "gemini-2.5-pro"


@pytest.mark.asyncio
async def test_create_extracts_html_from_markdown(mock_provider, creator):
    wrapped = f"Here is the HTML:\n\n```html\n{SAMPLE_HTML}\n```\n\nEnjoy!"
    mock_provider.generate.return_value = GenerationResult(
        text=wrapped,
        model="gemini-2.5-pro",
    )

    html, _ = await creator.create("Create a page")
    assert html.startswith("<!DOCTYPE html>")
    assert html.endswith("</html>")
    assert "```" not in html


@pytest.mark.asyncio
async def test_create_with_template_context(mock_provider, creator):
    mock_provider.generate.return_value = GenerationResult(
        text=SAMPLE_HTML, model="test"
    )

    await creator.create(
        "Create a page",
        template_content="<div>Template</div>",
    )

    call_args = mock_provider.generate.call_args
    messages = call_args.kwargs["messages"]

    # Template should add 2 extra messages (template + ack) before user message
    assert len(messages) == 3
    assert "existing document" in messages[0]["content"].lower()
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"
    assert messages[2]["content"] == "Create a page"


@pytest.mark.asyncio
async def test_create_without_template(mock_provider, creator):
    mock_provider.generate.return_value = GenerationResult(
        text=SAMPLE_HTML, model="test"
    )

    await creator.create("Create a page")

    call_args = mock_provider.generate.call_args
    messages = call_args.kwargs["messages"]

    assert len(messages) == 1
    assert messages[0]["content"] == "Create a page"


@pytest.mark.asyncio
async def test_create_uses_correct_params(mock_provider, creator):
    mock_provider.generate.return_value = GenerationResult(
        text=SAMPLE_HTML, model="test"
    )

    await creator.create("Create a page")

    call_args = mock_provider.generate.call_args.kwargs
    assert call_args["max_tokens"] == 24000
    assert call_args["temperature"] == 0.7
    assert "system" in call_args


@pytest.mark.asyncio
async def test_create_fallback_on_primary_failure(
    mock_provider, mock_fallback, creator
):
    mock_provider.generate.side_effect = RuntimeError("API error")
    mock_fallback.generate.return_value = GenerationResult(
        text=SAMPLE_HTML,
        model="claude-sonnet-4-6",
    )

    html, result = await creator.create("Create a page")

    assert "<!DOCTYPE html>" in html
    assert result.model == "claude-sonnet-4-6"
    mock_fallback.generate.assert_called_once()


@pytest.mark.asyncio
async def test_create_no_fallback_reraises(mock_provider):
    creator = DocumentCreator(mock_provider, fallback_provider=None)
    mock_provider.generate.side_effect = RuntimeError("API error")

    with pytest.raises(RuntimeError, match="API error"):
        await creator.create("Create a page")


# --- stream_create() tests ---


@pytest.mark.asyncio
async def test_stream_create_yields_chunks(mock_provider, creator):
    async def mock_stream(*args, **kwargs):
        for chunk in ["<html>", "<body>", "</body>", "</html>"]:
            yield chunk

    mock_provider.stream = mock_stream

    chunks = []
    async for chunk in creator.stream_create("Create a page"):
        chunks.append(chunk)

    assert chunks == ["<html>", "<body>", "</body>", "</html>"]


@pytest.mark.asyncio
async def test_stream_create_fallback_on_error(
    mock_provider, mock_fallback, creator
):
    async def failing_stream(*args, **kwargs):
        raise RuntimeError("stream failed")
        yield ""  # pragma: no cover

    async def fallback_stream(*args, **kwargs):
        for chunk in ["<html>", "</html>"]:
            yield chunk

    mock_provider.stream = failing_stream
    mock_fallback.stream = fallback_stream

    chunks = []
    async for chunk in creator.stream_create("Create a page"):
        chunks.append(chunk)

    assert chunks == ["<html>", "</html>"]


# --- extract_html() tests ---


def test_extract_html_plain_document():
    result = extract_html(SAMPLE_HTML)
    assert result.startswith("<!DOCTYPE html>")
    assert result.endswith("</html>")


def test_extract_html_with_markdown_fences():
    text = "Sure!\n\n```html\n" + SAMPLE_HTML + "\n```\n"
    result = extract_html(text)
    assert result.startswith("<!DOCTYPE html>")
    assert result.endswith("</html>")
    assert "```" not in result


def test_extract_html_with_preamble():
    text = "Here's the document:\n\n" + SAMPLE_HTML + "\n\nEnjoy!"
    result = extract_html(text)
    assert result.startswith("<!DOCTYPE html>")
    assert result.endswith("</html>")
    assert "Enjoy" not in result


def test_extract_html_no_html_returns_original():
    text = "This is just plain text with no HTML."
    result = extract_html(text)
    assert result == text
