import anthropic
from typing import AsyncIterator
from app.providers.base import LLMProvider, GenerationResult, ToolResult, ToolCall
from app.config import settings
import structlog

logger = structlog.get_logger()


class AnthropicProvider(LLMProvider):
    """Claude provider for surgical editing and PPT export."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        key = api_key or settings.anthropic_api_key
        if not key or not key.startswith("sk-ant-"):
            raise ValueError("Valid Anthropic API key required (starts with sk-ant-)")
        self.client = anthropic.AsyncAnthropic(api_key=key)
        self.model = model or settings.edit_model

    async def generate(
        self,
        system: str,
        messages: list[dict],
        max_tokens: int = 8000,
        temperature: float = 0.7,
    ) -> GenerationResult:
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=messages,  # type: ignore[arg-type]
        )
        return GenerationResult(
            text=response.content[0].text,  # type: ignore[union-attr]
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=self.model,
        )

    async def stream(
        self,
        system: str,
        messages: list[dict],
        max_tokens: int = 8000,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        async with self.client.messages.stream(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=messages,  # type: ignore[arg-type]
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def generate_with_tools(
        self,
        system: str | list[dict],
        messages: list[dict],
        tools: list[dict],
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> ToolResult:
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,  # type: ignore[arg-type]
            tools=tools,  # type: ignore[arg-type]
            messages=messages,  # type: ignore[arg-type]
        )

        tool_calls: list[ToolCall] = []
        text_parts: list[str] = []

        for block in response.content:
            if block.type == "tool_use":
                tool_calls.append(ToolCall(
                    name=block.name,
                    input=block.input,
                    id=block.id,
                ))
            elif block.type == "text":
                text_parts.append(block.text)

        return ToolResult(
            tool_calls=tool_calls,
            text="\n".join(text_parts),
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=self.model,
        )
