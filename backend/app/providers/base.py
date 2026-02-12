from abc import ABC, abstractmethod
from typing import AsyncIterator
from dataclasses import dataclass, field


@dataclass
class GenerationResult:
    """Result from an LLM generation call."""
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""


@dataclass
class ToolCall:
    """A tool call returned by the LLM."""
    name: str
    input: dict = field(default_factory=dict)
    id: str = ""


@dataclass
class ToolResult:
    """Result from an LLM call that uses tools."""
    tool_calls: list[ToolCall] = field(default_factory=list)
    text: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""


@dataclass
class ImageResponse:
    """Response from image generation provider."""
    image_bytes: bytes = b""
    format: str = "PNG"
    width: int = 0
    height: int = 0
    model: str = ""
    prompt: str = ""


class LLMProvider(ABC):
    """Base interface for text/code generation providers."""

    @abstractmethod
    async def generate(
        self,
        system: str,
        messages: list[dict],
        max_tokens: int = 8000,
        temperature: float = 0.7,
    ) -> GenerationResult:
        """Generate a complete response."""
        ...

    @abstractmethod
    async def stream(
        self,
        system: str,
        messages: list[dict],
        max_tokens: int = 8000,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """Stream a response token by token."""
        ...
        # yield is needed to make this an async generator in implementations
        yield ""  # pragma: no cover

    @abstractmethod
    async def generate_with_tools(
        self,
        system: str | list[dict],
        messages: list[dict],
        tools: list[dict],
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> ToolResult:
        """Generate a response using tool definitions. Used for surgical editing."""
        ...


class ImageProvider(ABC):
    """Base interface for image generation providers."""

    @abstractmethod
    async def generate_image(
        self,
        prompt: str,
        resolution: str = "2k",
    ) -> ImageResponse:
        """Generate an image from a text prompt. Returns PNG bytes."""
        ...
