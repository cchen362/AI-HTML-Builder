import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Set required env var before any app imports trigger Settings() validation
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key-for-testing")

from app.providers.base import GenerationResult  # noqa: E402


@pytest.fixture
def mock_genai():
    """Patch the genai module at the provider import site."""
    with patch("app.providers.gemini_provider.genai") as mock:
        mock_client = MagicMock()
        mock.Client.return_value = mock_client
        # Set up async API surface
        mock_client.aio.models.generate_content = AsyncMock()
        yield mock_client, mock


@pytest.fixture
def provider(mock_genai):
    """Create a GeminiProvider with mocked genai."""
    from app.providers.gemini_provider import GeminiProvider

    return GeminiProvider(api_key="test-key", model="gemini-2.5-pro")


# --- generate() tests ---


@pytest.mark.asyncio
async def test_generate_returns_generation_result(mock_genai, provider):
    client, _ = mock_genai
    mock_response = MagicMock()
    mock_response.text = "<html><body>Hello</body></html>"
    mock_response.usage_metadata.prompt_token_count = 100
    mock_response.usage_metadata.candidates_token_count = 200
    client.aio.models.generate_content.return_value = mock_response

    result = await provider.generate(
        system="You are an expert.",
        messages=[{"role": "user", "content": "Create a page"}],
    )

    assert isinstance(result, GenerationResult)
    assert result.text == "<html><body>Hello</body></html>"
    assert result.input_tokens == 100
    assert result.output_tokens == 200
    assert result.model == "gemini-2.5-pro"


@pytest.mark.asyncio
async def test_generate_handles_none_usage_metadata(mock_genai, provider):
    client, _ = mock_genai
    mock_response = MagicMock()
    mock_response.text = "HTML content"
    mock_response.usage_metadata = None
    client.aio.models.generate_content.return_value = mock_response

    result = await provider.generate(
        system="test",
        messages=[{"role": "user", "content": "test"}],
    )

    assert result.input_tokens == 0
    assert result.output_tokens == 0


@pytest.mark.asyncio
async def test_generate_handles_none_text(mock_genai, provider):
    client, _ = mock_genai
    mock_response = MagicMock()
    mock_response.text = None
    mock_response.usage_metadata = None
    client.aio.models.generate_content.return_value = mock_response

    result = await provider.generate(
        system="test",
        messages=[{"role": "user", "content": "test"}],
    )

    assert result.text == ""


@pytest.mark.asyncio
async def test_generate_converts_assistant_to_model_role(mock_genai, provider):
    client, _ = mock_genai
    mock_response = MagicMock()
    mock_response.text = "output"
    mock_response.usage_metadata = None
    client.aio.models.generate_content.return_value = mock_response

    await provider.generate(
        system="sys",
        messages=[
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
            {"role": "user", "content": "create page"},
        ],
    )

    call_args = client.aio.models.generate_content.call_args
    contents = call_args.kwargs.get("contents", call_args[1].get("contents") if len(call_args) > 1 else None)

    # Verify the assistant role was converted to model
    roles = [c.role for c in contents]
    assert "model" in roles
    assert "assistant" not in roles


@pytest.mark.asyncio
async def test_generate_passes_system_instruction(mock_genai, provider):
    client, _ = mock_genai
    mock_response = MagicMock()
    mock_response.text = "output"
    mock_response.usage_metadata = None
    client.aio.models.generate_content.return_value = mock_response

    await provider.generate(
        system="You are an HTML expert.",
        messages=[{"role": "user", "content": "test"}],
        max_tokens=4000,
        temperature=0.5,
    )

    call_args = client.aio.models.generate_content.call_args
    config = call_args.kwargs.get("config", call_args[1].get("config") if len(call_args) > 1 else None)

    assert config.system_instruction == "You are an HTML expert."
    assert config.max_output_tokens == 4000
    assert config.temperature == 0.5


# --- stream() tests ---


@pytest.mark.asyncio
async def test_stream_yields_chunks(mock_genai, provider):
    client, _ = mock_genai

    # Create mock chunks
    chunk1 = MagicMock()
    chunk1.text = "<html>"
    chunk2 = MagicMock()
    chunk2.text = "<body>Hello</body>"
    chunk3 = MagicMock()
    chunk3.text = "</html>"

    async def mock_stream(*args, **kwargs):
        for c in [chunk1, chunk2, chunk3]:
            yield c

    client.aio.models.generate_content_stream = AsyncMock(
        return_value=mock_stream()
    )

    chunks = []
    async for text in provider.stream(
        system="test",
        messages=[{"role": "user", "content": "test"}],
    ):
        chunks.append(text)

    assert chunks == ["<html>", "<body>Hello</body>", "</html>"]


@pytest.mark.asyncio
async def test_stream_skips_empty_chunks(mock_genai, provider):
    client, _ = mock_genai

    chunk1 = MagicMock()
    chunk1.text = "hello"
    chunk2 = MagicMock()
    chunk2.text = None
    chunk3 = MagicMock()
    chunk3.text = ""
    chunk4 = MagicMock()
    chunk4.text = "world"

    async def mock_stream(*args, **kwargs):
        for c in [chunk1, chunk2, chunk3, chunk4]:
            yield c

    client.aio.models.generate_content_stream = AsyncMock(
        return_value=mock_stream()
    )

    chunks = []
    async for text in provider.stream(
        system="test",
        messages=[{"role": "user", "content": "test"}],
    ):
        chunks.append(text)

    assert chunks == ["hello", "world"]


# --- generate_with_tools() tests ---


@pytest.mark.asyncio
async def test_generate_with_tools_raises_not_implemented(mock_genai, provider):
    with pytest.raises(NotImplementedError, match="does not support tool-based generation"):
        await provider.generate_with_tools(
            system="sys",
            messages=[{"role": "user", "content": "test"}],
            tools=[],
        )


# --- Constructor tests ---


def test_constructor_requires_api_key():
    with patch("app.providers.gemini_provider.genai"):
        with patch("app.providers.gemini_provider.settings") as mock_settings:
            mock_settings.google_api_key = ""
            from app.providers.gemini_provider import GeminiProvider

            with pytest.raises(ValueError, match="Google API key required"):
                GeminiProvider()


def test_constructor_uses_settings_defaults():
    with patch("app.providers.gemini_provider.genai") as mock_genai:
        mock_genai.Client.return_value = MagicMock()
        with patch("app.providers.gemini_provider.settings") as mock_settings:
            mock_settings.google_api_key = "test-key-123"
            mock_settings.creation_model = "gemini-custom"
            from app.providers.gemini_provider import GeminiProvider

            p = GeminiProvider()
            assert p.model == "gemini-custom"
