# Implementation Plan 003: Multi-Model Routing & Image Generation

## ⛔ STOP - READ THIS FIRST

**DO NOT START** until you have verified:
- ✅ Plan 001 (Backend Foundation) is **100% complete** and tested
- ✅ Plan 002 (Claude Editor Integration) is **100% complete** and tested
- ✅ All database migrations from Plans 001-002 are applied
- ✅ SQLite database is initialized and accessible (WAL mode)
- ✅ You have valid API keys for: Anthropic, Google AI (Gemini)
- ✅ Environment variables are set: `GOOGLE_API_KEY`, `ANTHROPIC_API_KEY`

**CRITICAL**: This plan implements the multi-model routing system with Gemini 2.5 Pro for document creation and Gemini 3 Pro for image generation. Any deviation from this plan will break the cost tracking and routing logic.

---

## IMPORTANT: Plan 001 Implementation Notes

Plan 001 deviated from its original code listings. Key items for this plan:
- **aiosqlite**: Use `cursor = await db.execute(); row = await cursor.fetchone()` (NOT `execute_fetchone`)
- **ImageProvider**: Returns `ImageResponse` dataclass (not raw `bytes`) - see `providers/base.py`
- **Anthropic SDK**: Needs `# type: ignore[arg-type]` for messages/tools params
- **cost_tracker.py**: Fully implemented with UPSERT, pricing dict, and `get_cost_summary()`/`get_cost_by_model()`

See "Implementation Notes" at the end of Plan 001 for full details.

---

## Context & Rationale

### Why Multi-Model Routing?

The AI HTML Builder uses **different AI models for different tasks** to optimize for cost, performance, and quality:

1. **Document Creation** (Gemini 2.5 Pro)
   - **Why**: 1M token context window handles large templates without truncation
   - **Cost**: $0.075 per 1M input tokens (50% cheaper than Claude Sonnet 4)
   - **Use Case**: Initial HTML generation from scratch, template rendering

2. **Document Editing** (Claude Sonnet 4)
   - **Why**: Superior semantic targeting and content preservation
   - **Cost**: $0.15 per 1M input tokens
   - **Use Case**: Iterative modifications, surgical edits, content refinement

3. **Image Generation** (Gemini 3 Pro Image Preview)
   - **Why**: Native image generation with high quality (4K resolution)
   - **Cost**: $0.13-0.24 per image
   - **Use Case**: Charts, diagrams, decorative images, hero images

### Architecture Overview

```
User Request
    ↓
Router Service (determines route)
    ↓
├─→ "create" → Document Creator → Gemini 2.5 Pro → New HTML
├─→ "edit"   → Document Editor  → Claude Sonnet 4 → Modified HTML
└─→ "image"  → Image Service    → Gemini 3 Pro   → Embedded Image
                                     ↓
                              Claude html_insert_after → Updated HTML
```

### Dependencies

- **External**: `google-genai>=0.3.0`, `pillow>=10.0.0`
- **Internal**: Plan 001 (database, providers ABC), Plan 002 (Claude editor)
- **Services**: SQLite for session state and cost tracking (Plan 001 foundation)

---

## Strict Rules

### ✅ MUST DO

- [ ] Implement `GeminiProvider` with full streaming support
- [ ] Implement `GeminiImageProvider` with PNG output
- [ ] Create `ImageService` with base64 encoding and SVG fallback
- [ ] Create `DocumentCreator` service with design guidelines
- [ ] Update `chat.py` with three-way routing logic
- [ ] Track every API call in `cost_tracking` table with accurate token counts
- [ ] Implement fallback: Gemini down → use Claude for creation
- [ ] Add SVG generation for simple diagrams (keyword detection: "flowchart", "diagram", "chart")
- [ ] Support explicit "Add Visual" button in frontend (route == "image")
- [ ] Auto-detect image keywords: "image", "photo", "illustration", "graphic", "visual"
- [ ] Stream creation responses via SSE for real-time feedback
- [ ] Set Gemini temperature to 0.7 for creative generation
- [ ] Use 1M token context window - NO truncation for Gemini
- [ ] Preserve existing color palette and design guidelines in creation prompt
- [ ] Version control: Save new documents as version 1 in `document_versions` table

### ❌ MUST NOT DO

- [ ] Do NOT truncate Gemini context (1M token window)
- [ ] Do NOT use Gemini for editing (use Claude's semantic targeting)
- [ ] Do NOT use Claude for creation (expensive, slower)
- [ ] Do NOT generate images for every request (cost control)
- [ ] Do NOT skip cost tracking (every API call must be logged)
- [ ] Do NOT hardcode API keys (use environment variables)
- [ ] Do NOT generate SVG via API (use string templates for simple diagrams)
- [ ] Do NOT embed images > 5MB (compress with Pillow)
- [ ] Do NOT allow > 3 images per document (cost control)
- [ ] Do NOT mix model responsibilities (creation vs editing vs image)

---

## Phase 1: Gemini Provider Implementation

### Files to Create
- `backend/app/providers/gemini_provider.py`

### Implementation

```python
# backend/app/providers/gemini_provider.py

import os
import logging
from typing import AsyncGenerator, Optional, Dict, Any
from google import genai
from google.genai.types import GenerateContentConfig, Part

from app.providers.base import LLMProvider, LLMResponse
from app.core.exceptions import ProviderError

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    """
    Gemini 2.5 Pro provider for document creation.

    Features:
    - 1M token context window (no truncation needed)
    - Temperature 0.7 for creative generation
    - Streaming support via SSE
    - Automatic token counting for cost tracking

    Use cases:
    - New HTML document generation
    - Template rendering
    - Large context processing
    """

    def __init__(self):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")

        self.client = genai.Client(api_key=api_key)
        self.model_name = "gemini-2.5-pro"
        self.max_context_tokens = 1_000_000  # 1M token context

        logger.info(f"Initialized GeminiProvider with model: {self.model_name}")

    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        context: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        Generate HTML document using Gemini 2.5 Pro.

        Args:
            system_prompt: Design guidelines and requirements
            user_message: User's creation request
            context: Optional context (e.g., template content)
            temperature: 0.7 for creative generation
            max_tokens: Optional output limit (default: 8192)

        Returns:
            LLMResponse with generated HTML and token usage
        """
        try:
            # Build message content
            content_parts = []

            if system_prompt:
                content_parts.append(f"SYSTEM INSTRUCTIONS:\n{system_prompt}\n\n")

            if context:
                content_parts.append(f"CONTEXT:\n{context}\n\n")

            content_parts.append(f"USER REQUEST:\n{user_message}")

            full_content = "".join(content_parts)

            # Configure generation
            config = GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens or 8192,
                response_modalities=["TEXT"],
            )

            # Generate content
            logger.info(f"Generating with Gemini (temp={temperature})")
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=full_content,
                config=config,
            )

            # Extract text
            generated_text = response.text

            # Count tokens (Gemini provides usage metadata)
            usage = response.usage_metadata
            input_tokens = usage.prompt_token_count if usage else 0
            output_tokens = usage.candidates_token_count if usage else 0

            logger.info(
                f"Gemini generation complete: "
                f"{input_tokens} input tokens, {output_tokens} output tokens"
            )

            return LLMResponse(
                content=generated_text,
                model=self.model_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                finish_reason=response.candidates[0].finish_reason.name if response.candidates else "STOP",
            )

        except Exception as e:
            logger.error(f"Gemini generation failed: {str(e)}")
            raise ProviderError(f"Gemini API error: {str(e)}") from e

    async def stream(
        self,
        system_prompt: str,
        user_message: str,
        context: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream HTML generation for real-time preview.

        Yields:
            Chunks of generated HTML as they arrive
        """
        try:
            # Build message content (same as generate())
            content_parts = []

            if system_prompt:
                content_parts.append(f"SYSTEM INSTRUCTIONS:\n{system_prompt}\n\n")

            if context:
                content_parts.append(f"CONTEXT:\n{context}\n\n")

            content_parts.append(f"USER REQUEST:\n{user_message}")

            full_content = "".join(content_parts)

            # Configure streaming generation
            config = GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens or 8192,
                response_modalities=["TEXT"],
            )

            # Stream content
            logger.info(f"Streaming with Gemini (temp={temperature})")

            async for chunk in self.client.models.generate_content_stream(
                model=self.model_name,
                contents=full_content,
                config=config,
            ):
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            logger.error(f"Gemini streaming failed: {str(e)}")
            raise ProviderError(f"Gemini streaming error: {str(e)}") from e

    def count_tokens(self, text: str) -> int:
        """
        Count tokens for cost estimation.

        Note: Gemini provides token counts in response metadata,
        so this is mainly for pre-request estimation.
        """
        try:
            response = self.client.models.count_tokens(
                model=self.model_name,
                contents=text,
            )
            return response.total_tokens
        except Exception as e:
            logger.warning(f"Token counting failed: {str(e)}, using estimate")
            # Fallback: rough estimate (1 token ≈ 4 characters)
            return len(text) // 4
```

### Testing

```bash
# Test Gemini provider
cd backend

# Create test script
cat > test_gemini.py << 'EOF'
import asyncio
from app.providers.gemini_provider import GeminiProvider

async def test_gemini():
    provider = GeminiProvider()

    # Test generate()
    response = await provider.generate(
        system_prompt="You are an HTML expert. Generate valid HTML5 documents.",
        user_message="Create a simple landing page with a hero section.",
        temperature=0.7,
    )

    print("Generated HTML:")
    print(response.content[:500])
    print(f"\nTokens: {response.input_tokens} in, {response.output_tokens} out")
    print(f"Model: {response.model}")

    # Test streaming
    print("\n--- Streaming test ---")
    async for chunk in provider.stream(
        system_prompt="You are an HTML expert.",
        user_message="Create a simple card component.",
    ):
        print(chunk, end="", flush=True)

asyncio.run(test_gemini())
EOF

python test_gemini.py
```

---

## Phase 2: Gemini Image Provider Implementation

### Files to Create
- `backend/app/providers/gemini_image_provider.py`

### Implementation

```python
# backend/app/providers/gemini_image_provider.py

import os
import logging
from typing import Optional, Dict, Any
from google import genai
from google.genai.types import GenerateContentConfig

from app.providers.base import ImageProvider, ImageResponse
from app.core.exceptions import ProviderError

logger = logging.getLogger(__name__)


class GeminiImageProvider(ImageProvider):
    """
    Gemini 3 Pro Image Preview provider for image generation.

    Features:
    - Native image generation (PNG format)
    - 4K resolution default (3840x2160)
    - $0.13-0.24 per image
    - High quality realistic images

    Use cases:
    - Charts and diagrams
    - Hero images
    - Decorative graphics
    - Custom illustrations
    """

    def __init__(self):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")

        self.client = genai.Client(api_key=api_key)
        self.model_name = "gemini-3-pro-image-preview"

        logger.info(f"Initialized GeminiImageProvider with model: {self.model_name}")

    async def generate_image(
        self,
        prompt: str,
        style: Optional[str] = None,
        resolution: str = "4K",
        format: str = "PNG",
    ) -> ImageResponse:
        """
        Generate image using Gemini 3 Pro.

        Args:
            prompt: Image description
            style: Optional style guide (e.g., "professional", "minimalist")
            resolution: "4K" (3840x2160), "HD" (1920x1080), or "SD" (1280x720)
            format: "PNG" (default) or "JPEG"

        Returns:
            ImageResponse with image bytes and metadata
        """
        try:
            # Build enhanced prompt with style
            full_prompt = prompt
            if style:
                full_prompt = f"{prompt}\n\nStyle: {style}"

            # Add resolution hint
            resolution_map = {
                "4K": "ultra high resolution 4K quality (3840x2160)",
                "HD": "high definition 1080p quality (1920x1080)",
                "SD": "standard definition quality (1280x720)",
            }
            resolution_hint = resolution_map.get(resolution, resolution_map["4K"])
            full_prompt += f"\n\nResolution: {resolution_hint}"

            # Configure image generation
            config = GenerateContentConfig(
                temperature=0.8,  # Higher temp for creative images
                response_modalities=["IMAGE"],
            )

            # Generate image
            logger.info(f"Generating image with Gemini: {prompt[:100]}...")
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=full_prompt,
                config=config,
            )

            # Extract image bytes from first part
            if not response.candidates or not response.candidates[0].content.parts:
                raise ProviderError("No image generated in response")

            image_part = response.candidates[0].content.parts[0]

            # Get image data (bytes)
            if hasattr(image_part, 'inline_data'):
                image_bytes = image_part.inline_data.data
                mime_type = image_part.inline_data.mime_type
            else:
                raise ProviderError("No image data in response part")

            # Convert MIME type to format
            actual_format = "PNG" if "png" in mime_type.lower() else "JPEG"

            logger.info(
                f"Image generated: {len(image_bytes)} bytes, "
                f"format={actual_format}, resolution={resolution}"
            )

            return ImageResponse(
                image_bytes=image_bytes,
                format=actual_format,
                width=3840 if resolution == "4K" else 1920 if resolution == "HD" else 1280,
                height=2160 if resolution == "4K" else 1080 if resolution == "HD" else 720,
                model=self.model_name,
                prompt=prompt,
            )

        except Exception as e:
            logger.error(f"Gemini image generation failed: {str(e)}")
            raise ProviderError(f"Image generation error: {str(e)}") from e
```

### Update Base Provider

```python
# backend/app/providers/base.py (ADD THIS CLASS)

from dataclasses import dataclass
from abc import ABC, abstractmethod

@dataclass
class ImageResponse:
    """Response from image generation provider."""
    image_bytes: bytes
    format: str  # "PNG" or "JPEG"
    width: int
    height: int
    model: str
    prompt: str


class ImageProvider(ABC):
    """Abstract base class for image generation providers."""

    @abstractmethod
    async def generate_image(
        self,
        prompt: str,
        style: Optional[str] = None,
        resolution: str = "4K",
        format: str = "PNG",
    ) -> ImageResponse:
        """Generate an image from a text prompt."""
        pass
```

### Testing

```bash
# Test image provider
cd backend

cat > test_image.py << 'EOF'
import asyncio
from app.providers.gemini_image_provider import GeminiImageProvider

async def test_image():
    provider = GeminiImageProvider()

    response = await provider.generate_image(
        prompt="A modern, minimalist chart showing growth trends with blue gradients",
        style="professional",
        resolution="HD",
    )

    print(f"Image generated: {len(response.image_bytes)} bytes")
    print(f"Format: {response.format}")
    print(f"Size: {response.width}x{response.height}")

    # Save to file
    with open("test_image.png", "wb") as f:
        f.write(response.image_bytes)

    print("Saved to test_image.png")

asyncio.run(test_image())
EOF

python test_image.py
```

---

## Phase 3: Image Service Implementation

### Files to Create
- `backend/app/services/image_service.py`

### Implementation

```python
# backend/app/services/image_service.py

import base64
import logging
from typing import Optional, Tuple
from io import BytesIO
from PIL import Image

from app.providers.gemini_image_provider import GeminiImageProvider
from app.providers.claude_provider import ClaudeProvider
from app.core.exceptions import ServiceError

logger = logging.getLogger(__name__)


class ImageService:
    """
    Service for generating and embedding images in HTML documents.

    Features:
    - Image generation via Gemini 3 Pro
    - Base64 encoding for HTML embedding
    - SVG generation for simple diagrams (no API cost)
    - Auto-compression for large images (>5MB)
    - Claude html_insert_after for embedding

    Workflow:
    1. Detect image request (keywords or explicit button)
    2. Check if SVG is sufficient (flowchart, diagram, chart)
    3. If API needed, generate image via Gemini
    4. Compress if >5MB
    5. Base64 encode
    6. Use Claude to insert via html_insert_after
    """

    def __init__(
        self,
        image_provider: Optional[GeminiImageProvider] = None,
        claude_provider: Optional[ClaudeProvider] = None,
    ):
        self.image_provider = image_provider or GeminiImageProvider()
        self.claude_provider = claude_provider or ClaudeProvider()

        # Image detection keywords
        self.image_keywords = {
            "image", "photo", "picture", "illustration", "graphic",
            "visual", "screenshot", "render", "artwork"
        }

        # SVG-suitable keywords (no API cost)
        self.svg_keywords = {
            "flowchart", "diagram", "chart", "graph", "timeline",
            "tree", "hierarchy", "wireframe", "mockup"
        }

        self.max_image_size = 5 * 1024 * 1024  # 5MB

    def detect_image_request(self, message: str) -> Tuple[bool, bool]:
        """
        Detect if message requests an image.

        Returns:
            (needs_image: bool, use_svg: bool)
        """
        message_lower = message.lower()

        # Check for image keywords
        has_image_keyword = any(kw in message_lower for kw in self.image_keywords)

        # Check for SVG-suitable keywords
        has_svg_keyword = any(kw in message_lower for kw in self.svg_keywords)

        return (has_image_keyword or has_svg_keyword, has_svg_keyword)

    async def generate_svg_diagram(
        self,
        diagram_type: str,
        description: str,
    ) -> str:
        """
        Generate SVG diagram using string templates (no API cost).

        Args:
            diagram_type: "flowchart", "chart", "timeline", etc.
            description: Diagram description

        Returns:
            SVG markup as string
        """
        # Simple SVG templates for common diagrams
        if diagram_type == "flowchart":
            return self._generate_flowchart_svg(description)
        elif diagram_type in ["chart", "graph"]:
            return self._generate_chart_svg(description)
        elif diagram_type == "timeline":
            return self._generate_timeline_svg(description)
        else:
            # Fallback: simple placeholder
            return self._generate_placeholder_svg(description)

    def _generate_flowchart_svg(self, description: str) -> str:
        """Generate simple flowchart SVG."""
        return """
        <svg width="600" height="400" xmlns="http://www.w3.org/2000/svg">
            <defs>
                <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
                    <polygon points="0 0, 10 3.5, 0 7" fill="#006FCF" />
                </marker>
            </defs>

            <!-- Start -->
            <rect x="250" y="20" width="100" height="50" rx="25" fill="#006FCF" />
            <text x="300" y="50" text-anchor="middle" fill="white" font-size="14">Start</text>

            <!-- Arrow -->
            <line x1="300" y1="70" x2="300" y2="110" stroke="#006FCF" stroke-width="2" marker-end="url(#arrowhead)" />

            <!-- Process -->
            <rect x="225" y="120" width="150" height="60" fill="#66A9E2" />
            <text x="300" y="155" text-anchor="middle" fill="white" font-size="14">Process</text>

            <!-- Arrow -->
            <line x1="300" y1="180" x2="300" y2="220" stroke="#006FCF" stroke-width="2" marker-end="url(#arrowhead)" />

            <!-- End -->
            <rect x="250" y="230" width="100" height="50" rx="25" fill="#28CD6E" />
            <text x="300" y="260" text-anchor="middle" fill="white" font-size="14">End</text>
        </svg>
        """

    def _generate_chart_svg(self, description: str) -> str:
        """Generate simple bar chart SVG."""
        return """
        <svg width="600" height="400" xmlns="http://www.w3.org/2000/svg">
            <!-- Axes -->
            <line x1="50" y1="350" x2="550" y2="350" stroke="#152835" stroke-width="2" />
            <line x1="50" y1="50" x2="50" y2="350" stroke="#152835" stroke-width="2" />

            <!-- Bars -->
            <rect x="100" y="200" width="60" height="150" fill="#006FCF" />
            <rect x="200" y="150" width="60" height="200" fill="#66A9E2" />
            <rect x="300" y="100" width="60" height="250" fill="#006FCF" />
            <rect x="400" y="180" width="60" height="170" fill="#66A9E2" />

            <!-- Labels -->
            <text x="130" y="370" text-anchor="middle" font-size="12">Q1</text>
            <text x="230" y="370" text-anchor="middle" font-size="12">Q2</text>
            <text x="330" y="370" text-anchor="middle" font-size="12">Q3</text>
            <text x="430" y="370" text-anchor="middle" font-size="12">Q4</text>
        </svg>
        """

    def _generate_timeline_svg(self, description: str) -> str:
        """Generate simple timeline SVG."""
        return """
        <svg width="800" height="200" xmlns="http://www.w3.org/2000/svg">
            <!-- Timeline line -->
            <line x1="50" y1="100" x2="750" y2="100" stroke="#006FCF" stroke-width="3" />

            <!-- Points -->
            <circle cx="150" cy="100" r="8" fill="#006FCF" />
            <circle cx="350" cy="100" r="8" fill="#006FCF" />
            <circle cx="550" cy="100" r="8" fill="#006FCF" />
            <circle cx="750" cy="100" r="8" fill="#28CD6E" />

            <!-- Labels -->
            <text x="150" y="140" text-anchor="middle" font-size="14">Phase 1</text>
            <text x="350" y="140" text-anchor="middle" font-size="14">Phase 2</text>
            <text x="550" y="140" text-anchor="middle" font-size="14">Phase 3</text>
            <text x="750" y="140" text-anchor="middle" font-size="14">Complete</text>
        </svg>
        """

    def _generate_placeholder_svg(self, description: str) -> str:
        """Generate placeholder SVG."""
        return f"""
        <svg width="600" height="300" xmlns="http://www.w3.org/2000/svg">
            <rect width="600" height="300" fill="#F6F0FA" />
            <text x="300" y="150" text-anchor="middle" font-size="18" fill="#152835">
                {description[:50]}
            </text>
        </svg>
        """

    async def generate_and_embed_image(
        self,
        html_content: str,
        image_prompt: str,
        insert_after_selector: str,
        style: Optional[str] = None,
        resolution: str = "HD",
    ) -> str:
        """
        Generate image and embed it in HTML via Claude.

        Args:
            html_content: Current HTML document
            image_prompt: Image description
            insert_after_selector: CSS selector for insertion point
            style: Optional style guide
            resolution: "4K", "HD", or "SD"

        Returns:
            Updated HTML with embedded image
        """
        try:
            # Generate image
            logger.info(f"Generating image: {image_prompt[:100]}...")
            image_response = await self.image_provider.generate_image(
                prompt=image_prompt,
                style=style,
                resolution=resolution,
            )

            # Compress if needed
            image_bytes = image_response.image_bytes
            if len(image_bytes) > self.max_image_size:
                logger.info(f"Compressing image from {len(image_bytes)} bytes")
                image_bytes = self._compress_image(image_bytes, image_response.format)

            # Base64 encode
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            mime_type = f"image/{image_response.format.lower()}"
            data_uri = f"data:{mime_type};base64,{image_base64}"

            # Create image HTML
            image_html = f"""
            <div class="generated-image" style="margin: 20px 0; text-align: center;">
                <img src="{data_uri}"
                     alt="{image_prompt}"
                     style="max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);" />
            </div>
            """

            # Use Claude to insert via html_insert_after
            logger.info(f"Embedding image after: {insert_after_selector}")
            updated_html = await self.claude_provider.html_insert_after(
                html_content=html_content,
                selector=insert_after_selector,
                new_content=image_html,
            )

            return updated_html

        except Exception as e:
            logger.error(f"Image generation and embedding failed: {str(e)}")
            raise ServiceError(f"Failed to generate image: {str(e)}") from e

    def _compress_image(self, image_bytes: bytes, format: str) -> bytes:
        """
        Compress image to under max_image_size.

        Uses Pillow to reduce quality/dimensions.
        """
        try:
            img = Image.open(BytesIO(image_bytes))

            # Start with 85% quality
            quality = 85
            output = BytesIO()

            while quality > 50:
                output.seek(0)
                output.truncate()

                img.save(output, format=format, quality=quality, optimize=True)

                if len(output.getvalue()) <= self.max_image_size:
                    logger.info(f"Compressed to {len(output.getvalue())} bytes at quality={quality}")
                    return output.getvalue()

                quality -= 10

            # If still too large, resize
            img.thumbnail((1920, 1080), Image.Resampling.LANCZOS)
            output.seek(0)
            output.truncate()
            img.save(output, format=format, quality=75, optimize=True)

            logger.info(f"Resized and compressed to {len(output.getvalue())} bytes")
            return output.getvalue()

        except Exception as e:
            logger.error(f"Image compression failed: {str(e)}")
            # Return original if compression fails
            return image_bytes
```

---

## Phase 4: Document Creator Service

### Files to Create
- `backend/app/services/creator.py`

### Implementation

```python
# backend/app/services/creator.py

import logging
from typing import Optional, AsyncGenerator
from datetime import datetime

from app.providers.gemini_provider import GeminiProvider
from app.db.session import get_db
from app.models.document import Document, DocumentVersion
from app.models.analytics import CostTracking
from app.core.exceptions import ServiceError

logger = logging.getLogger(__name__)


class DocumentCreator:
    """
    Service for creating new HTML documents using Gemini 2.5 Pro.

    Features:
    - Gemini 2.5 Pro for cost-effective creation
    - 1M token context window (no truncation)
    - Temperature 0.7 for creative generation
    - Streaming support for real-time preview
    - Design guidelines enforcement
    - Version control (saves as version 1)

    System Prompt:
    - Color palette (Deep Blue, Bright Blue, etc.)
    - Typography (Benton Sans, Arial)
    - Responsive design requirements
    - Accessibility guidelines
    - Single-file HTML constraints
    """

    DESIGN_GUIDELINES = """
You are an expert HTML/CSS developer creating single-file HTML documents with modern design principles.

REQUIREMENTS:
1. Generate complete, valid HTML5 documents
2. All CSS must be inline in <style> tags
3. All JavaScript must be inline in <script> tags
4. No external dependencies or CDN links
5. Mobile-responsive with viewport meta tag
6. Use semantic HTML elements and ARIA attributes

DEFAULT STYLING (unless specified otherwise):
- Primary Colors: Deep Blue (#00175A), Bright Blue (#006FCF), Light Blue (#66A9E2)
- Neutrals: Charcoal (#152835), Gray (#A7A8AA), White (#FFFFFF)
- Accent Colors: Sky Blue (#B4EEFF), Powder Blue (#F6F0FA), Yellow (#FFB900), Forest Green (#006469), Green (#28CD6E)
- Typography: 'Benton Sans', Arial, sans-serif with proper hierarchy
- Layout: CSS Grid/Flexbox with professional spacing (margins: 20px-40px, padding: 16px-32px)
- Interactive: Smooth transitions (0.3s ease) and hover effects
- Accessibility: Proper contrast ratios (WCAG AA), focus indicators, alt text

BEST PRACTICES:
- Use semantic tags: <header>, <nav>, <main>, <section>, <article>, <footer>
- Mobile-first breakpoints: 768px (tablet), 1024px (desktop)
- Consistent spacing scale: 8px, 16px, 24px, 32px, 48px
- Professional shadows: box-shadow: 0 2px 4px rgba(0,0,0,0.1)
- Clean animations: transform, opacity (avoid layout shifts)

OUTPUT: Return only complete HTML starting with <!DOCTYPE html>
"""

    def __init__(self, gemini_provider: Optional[GeminiProvider] = None):
        self.gemini_provider = gemini_provider or GeminiProvider()

    async def create_document(
        self,
        session_id: str,
        user_message: str,
        template_content: Optional[str] = None,
    ) -> str:
        """
        Create new HTML document.

        Args:
            session_id: User session ID
            user_message: Creation request
            template_content: Optional template to use as base

        Returns:
            Generated HTML content
        """
        try:
            logger.info(f"Creating document for session: {session_id}")

            # Generate with Gemini
            response = await self.gemini_provider.generate(
                system_prompt=self.DESIGN_GUIDELINES,
                user_message=user_message,
                context=template_content,
                temperature=0.7,
            )

            html_content = response.content

            # Save to database
            async with get_db() as db:
                # Create document
                document = Document(
                    session_id=session_id,
                    content=html_content,
                    created_at=datetime.utcnow(),
                )
                db.add(document)
                await db.flush()

                # Create version 1
                version = DocumentVersion(
                    document_id=document.id,
                    version_number=1,
                    content=html_content,
                    created_at=datetime.utcnow(),
                    created_by_model=response.model,
                )
                db.add(version)

                # Track cost
                cost_entry = CostTracking(
                    session_id=session_id,
                    model=response.model,
                    operation="create",
                    input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens,
                    images_generated=0,
                    cost_usd=self._calculate_cost(response),
                    timestamp=datetime.utcnow(),
                )
                db.add(cost_entry)

                await db.commit()

                logger.info(
                    f"Document created: {document.id}, "
                    f"tokens: {response.input_tokens}/{response.output_tokens}, "
                    f"cost: ${cost_entry.cost_usd:.4f}"
                )

            return html_content

        except Exception as e:
            logger.error(f"Document creation failed: {str(e)}")
            raise ServiceError(f"Failed to create document: {str(e)}") from e

    async def stream_document_creation(
        self,
        session_id: str,
        user_message: str,
        template_content: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream document creation for real-time preview.

        Yields:
            Chunks of HTML as they are generated
        """
        try:
            logger.info(f"Streaming document creation for session: {session_id}")

            full_content = []

            # Stream from Gemini
            async for chunk in self.gemini_provider.stream(
                system_prompt=self.DESIGN_GUIDELINES,
                user_message=user_message,
                context=template_content,
                temperature=0.7,
            ):
                full_content.append(chunk)
                yield chunk

            # Save final document
            final_html = "".join(full_content)

            async with get_db() as db:
                document = Document(
                    session_id=session_id,
                    content=final_html,
                    created_at=datetime.utcnow(),
                )
                db.add(document)
                await db.flush()

                version = DocumentVersion(
                    document_id=document.id,
                    version_number=1,
                    content=final_html,
                    created_at=datetime.utcnow(),
                    created_by_model=self.gemini_provider.model_name,
                )
                db.add(version)

                await db.commit()

                logger.info(f"Streamed document saved: {document.id}")

        except Exception as e:
            logger.error(f"Streaming document creation failed: {str(e)}")
            raise ServiceError(f"Streaming failed: {str(e)}") from e

    def _calculate_cost(self, response) -> float:
        """
        Calculate cost for Gemini 2.5 Pro.

        Pricing:
        - Input: $0.075 per 1M tokens
        - Output: $0.30 per 1M tokens
        """
        input_cost = (response.input_tokens / 1_000_000) * 0.075
        output_cost = (response.output_tokens / 1_000_000) * 0.30
        return input_cost + output_cost
```

---

## Phase 5: Integrate Multi-Model Routing into Chat API

### Files to Modify
- `backend/app/api/chat.py`

### Implementation

```python
# backend/app/api/chat.py

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Literal
import logging

from app.services.creator import DocumentCreator
from app.services.editor import DocumentEditor
from app.services.image_service import ImageService
from app.core.session import get_current_session

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatRequest(BaseModel):
    session_id: str
    message: str
    route: Optional[Literal["create", "edit", "image", "auto"]] = "auto"
    template_id: Optional[str] = None
    insert_after_selector: Optional[str] = None  # For image insertion


class ChatResponse(BaseModel):
    html_content: str
    route_used: str
    model_used: str
    tokens: dict
    cost_usd: float


@router.post("/chat")
async def chat(
    request: ChatRequest,
    session = Depends(get_current_session),
) -> ChatResponse:
    """
    Main chat endpoint with multi-model routing.

    Routing logic:
    1. route == "create" → DocumentCreator → Gemini 2.5 Pro
    2. route == "edit" → DocumentEditor → Claude Sonnet 4
    3. route == "image" → ImageService → Gemini 3 Pro + Claude
    4. route == "auto" → Detect based on message and session state

    Auto-detection:
    - If no document exists → "create"
    - If document exists + image keywords → "image"
    - If document exists + modification keywords → "edit"
    """
    try:
        # Initialize services
        creator = DocumentCreator()
        editor = DocumentEditor()
        image_service = ImageService()

        # Auto-detect route if needed
        if request.route == "auto":
            request.route = await _auto_detect_route(
                session_id=request.session_id,
                message=request.message,
                image_service=image_service,
            )
            logger.info(f"Auto-detected route: {request.route}")

        # Route to appropriate service
        if request.route == "create":
            return await _handle_create(
                session_id=request.session_id,
                message=request.message,
                template_id=request.template_id,
                creator=creator,
            )

        elif request.route == "edit":
            return await _handle_edit(
                session_id=request.session_id,
                message=request.message,
                editor=editor,
            )

        elif request.route == "image":
            return await _handle_image(
                session_id=request.session_id,
                message=request.message,
                insert_after_selector=request.insert_after_selector,
                image_service=image_service,
            )

        else:
            raise HTTPException(status_code=400, detail=f"Invalid route: {request.route}")

    except Exception as e:
        logger.error(f"Chat request failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def _auto_detect_route(
    session_id: str,
    message: str,
    image_service: ImageService,
) -> str:
    """Auto-detect which route to use."""
    from app.db.session import get_db
    from app.models.document import Document

    # Check if document exists
    async with get_db() as db:
        document = await db.query(Document).filter_by(session_id=session_id).first()

    if not document:
        return "create"

    # Check for image request
    needs_image, _ = image_service.detect_image_request(message)
    if needs_image:
        return "image"

    # Check for modification keywords
    modification_keywords = {
        "change", "modify", "update", "edit", "fix", "adjust",
        "add", "remove", "delete", "replace", "improve"
    }

    message_lower = message.lower()
    if any(kw in message_lower for kw in modification_keywords):
        return "edit"

    # Default: assume edit for existing documents
    return "edit"


async def _handle_create(
    session_id: str,
    message: str,
    template_id: Optional[str],
    creator: DocumentCreator,
) -> ChatResponse:
    """Handle document creation via Gemini."""
    # Load template if specified
    template_content = None
    if template_id:
        # TODO: Load from template library
        pass

    # Create document
    html_content = await creator.create_document(
        session_id=session_id,
        user_message=message,
        template_content=template_content,
    )

    # Get cost tracking info
    async with get_db() as db:
        from app.models.analytics import CostTracking
        latest_cost = await db.query(CostTracking).filter_by(
            session_id=session_id
        ).order_by(CostTracking.timestamp.desc()).first()

    return ChatResponse(
        html_content=html_content,
        route_used="create",
        model_used=latest_cost.model if latest_cost else "gemini-2.5-pro",
        tokens={
            "input": latest_cost.input_tokens if latest_cost else 0,
            "output": latest_cost.output_tokens if latest_cost else 0,
        },
        cost_usd=latest_cost.cost_usd if latest_cost else 0.0,
    )


async def _handle_edit(
    session_id: str,
    message: str,
    editor: DocumentEditor,
) -> ChatResponse:
    """Handle document editing via Claude."""
    # Get current document
    async with get_db() as db:
        from app.models.document import Document
        document = await db.query(Document).filter_by(session_id=session_id).first()

        if not document:
            raise HTTPException(status_code=404, detail="No document to edit")

        current_html = document.content

    # Edit document
    updated_html = await editor.edit_document(
        session_id=session_id,
        current_html=current_html,
        user_message=message,
    )

    # Get cost tracking
    async with get_db() as db:
        from app.models.analytics import CostTracking
        latest_cost = await db.query(CostTracking).filter_by(
            session_id=session_id
        ).order_by(CostTracking.timestamp.desc()).first()

    return ChatResponse(
        html_content=updated_html,
        route_used="edit",
        model_used=latest_cost.model if latest_cost else "claude-sonnet-4",
        tokens={
            "input": latest_cost.input_tokens if latest_cost else 0,
            "output": latest_cost.output_tokens if latest_cost else 0,
        },
        cost_usd=latest_cost.cost_usd if latest_cost else 0.0,
    )


async def _handle_image(
    session_id: str,
    message: str,
    insert_after_selector: Optional[str],
    image_service: ImageService,
) -> ChatResponse:
    """Handle image generation and embedding."""
    # Get current document
    async with get_db() as db:
        from app.models.document import Document
        document = await db.query(Document).filter_by(session_id=session_id).first()

        if not document:
            raise HTTPException(status_code=404, detail="No document for image insertion")

        current_html = document.content

    # Check if SVG is sufficient
    _, use_svg = image_service.detect_image_request(message)

    if use_svg:
        # Generate SVG directly (no API cost)
        svg_type = _detect_svg_type(message)
        svg_content = await image_service.generate_svg_diagram(svg_type, message)

        # Insert SVG (simple string insertion)
        # TODO: Use proper HTML insertion logic
        updated_html = current_html.replace(
            "</main>",
            f"{svg_content}</main>"
        )

        cost_usd = 0.0
        model_used = "svg-template"
    else:
        # Generate via Gemini API
        updated_html = await image_service.generate_and_embed_image(
            html_content=current_html,
            image_prompt=message,
            insert_after_selector=insert_after_selector or "header",
            style="professional",
            resolution="HD",
        )

        # Track cost (image generation)
        async with get_db() as db:
            from app.models.analytics import CostTracking
            cost_entry = CostTracking(
                session_id=session_id,
                model="gemini-3-pro-image-preview",
                operation="image",
                input_tokens=0,
                output_tokens=0,
                images_generated=1,
                cost_usd=0.20,  # Average image cost
                timestamp=datetime.utcnow(),
            )
            db.add(cost_entry)
            await db.commit()

        cost_usd = 0.20
        model_used = "gemini-3-pro-image-preview"

    # Update document
    async with get_db() as db:
        from app.models.document import Document
        document.content = updated_html
        await db.commit()

    return ChatResponse(
        html_content=updated_html,
        route_used="image",
        model_used=model_used,
        tokens={"input": 0, "output": 0},
        cost_usd=cost_usd,
    )


def _detect_svg_type(message: str) -> str:
    """Detect SVG diagram type from message."""
    message_lower = message.lower()

    if "flowchart" in message_lower or "flow" in message_lower:
        return "flowchart"
    elif "chart" in message_lower or "graph" in message_lower:
        return "chart"
    elif "timeline" in message_lower:
        return "timeline"
    else:
        return "diagram"
```

---

## Build Verification

### Commands to Run

```bash
# 1. Install dependencies
cd backend
pip install google-genai pillow

# 2. Run linting
ruff check app/providers/gemini_provider.py
ruff check app/providers/gemini_image_provider.py
ruff check app/services/image_service.py
ruff check app/services/creator.py
ruff check app/api/chat.py

# 3. Type checking
mypy app/providers/gemini_provider.py
mypy app/services/creator.py

# 4. Test individual components
python -c "
import asyncio
from app.providers.gemini_provider import GeminiProvider

async def test():
    provider = GeminiProvider()
    response = await provider.generate(
        system_prompt='You are an HTML expert.',
        user_message='Create a simple card component.',
    )
    print(f'Generated {len(response.content)} characters')
    print(f'Tokens: {response.input_tokens}/{response.output_tokens}')

asyncio.run(test())
"

# 5. Test image generation
python -c "
import asyncio
from app.providers.gemini_image_provider import GeminiImageProvider

async def test():
    provider = GeminiImageProvider()
    response = await provider.generate_image(
        prompt='A professional chart with blue gradients',
        resolution='HD',
    )
    print(f'Image: {len(response.image_bytes)} bytes')
    with open('test.png', 'wb') as f:
        f.write(response.image_bytes)

asyncio.run(test())
"

# 6. Test document creation
python -c "
import asyncio
from app.services.creator import DocumentCreator

async def test():
    creator = DocumentCreator()
    html = await creator.create_document(
        session_id='test-session',
        user_message='Create a landing page with a hero section.',
    )
    print(f'Created HTML: {len(html)} characters')

asyncio.run(test())
"

# 7. Start server and test API
uvicorn app.main:app --reload &
sleep 5

curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-123",
    "message": "Create a professional landing page",
    "route": "create"
  }'

# 8. Check database
psql -U postgres -d ai_html_builder -c "SELECT * FROM cost_tracking ORDER BY timestamp DESC LIMIT 5;"
```

### Expected Results

- ✅ Gemini provider generates valid HTML
- ✅ Image provider returns PNG bytes
- ✅ Image service embeds base64 images
- ✅ Document creator saves version 1
- ✅ Chat API routes to correct service
- ✅ Cost tracking records all API calls
- ✅ No errors in logs

---

## Testing Scenarios

| Scenario | Input | Expected Route | Expected Model | Expected Output | Cost |
|----------|-------|---------------|----------------|-----------------|------|
| **New document** | "Create a landing page" | create | gemini-2.5-pro | Full HTML document | ~$0.02 |
| **Edit existing** | "Change header to blue" | edit | claude-sonnet-4 | Modified HTML | ~$0.05 |
| **Image request** | "Add a hero image of mountains" | image | gemini-3-pro-image + claude | HTML with embedded PNG | ~$0.25 |
| **SVG diagram** | "Add a flowchart showing process" | image | svg-template | HTML with SVG | $0.00 |
| **Auto-detect create** | "Make a dashboard" (no existing doc) | create | gemini-2.5-pro | New HTML | ~$0.02 |
| **Auto-detect edit** | "Update the title" (existing doc) | edit | claude-sonnet-4 | Modified HTML | ~$0.05 |
| **Template creation** | "Use impact assessment template" | create | gemini-2.5-pro | Template-based HTML | ~$0.03 |
| **Large context** | 100KB template + 50KB user content | create | gemini-2.5-pro | No truncation | ~$0.08 |
| **Streaming create** | "Create report" (streaming enabled) | create | gemini-2.5-pro | Streamed HTML chunks | ~$0.02 |
| **Fallback test** | Gemini API down | create | claude-sonnet-4 | HTML (fallback) | ~$0.10 |
| **Image compression** | Request 8K image | image | gemini-3-pro-image | Compressed to <5MB | ~$0.24 |
| **Multi-image limit** | "Add 5 images" | image | Error after 3 images | Max 3 images enforced | ~$0.75 |
| **Cost tracking** | Any request | any | any | Database entry created | N/A |

### Test Scripts

```bash
# Test 1: New document creation
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-create-001",
    "message": "Create a professional landing page with hero section, features grid, and contact form",
    "route": "create"
  }' | jq '.route_used, .model_used, .cost_usd'

# Test 2: Document editing
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-create-001",
    "message": "Change the header background to gradient blue",
    "route": "edit"
  }' | jq '.route_used, .model_used'

# Test 3: Image generation
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-create-001",
    "message": "Add a professional photo of a modern office",
    "route": "image",
    "insert_after_selector": ".hero"
  }' | jq '.route_used, .cost_usd'

# Test 4: SVG diagram
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-create-001",
    "message": "Add a flowchart showing our process",
    "route": "image"
  }' | jq '.route_used, .cost_usd'

# Test 5: Auto-routing
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-auto-001",
    "message": "Build a technical documentation site",
    "route": "auto"
  }' | jq '.route_used'

# Verify cost tracking
psql -U postgres -d ai_html_builder -c "
  SELECT
    session_id,
    model,
    operation,
    input_tokens,
    output_tokens,
    images_generated,
    cost_usd,
    timestamp
  FROM cost_tracking
  ORDER BY timestamp DESC
  LIMIT 10;
"
```

---

## Rollback Plan

### If Issues Occur

1. **Gemini API failures**
   ```bash
   # Fallback to Claude for all operations
   # Edit chat.py:
   sed -i 's/GeminiProvider/ClaudeProvider/g' backend/app/services/creator.py

   # Restart server
   pkill -f uvicorn
   uvicorn app.main:app --reload
   ```

2. **Image generation issues**
   ```bash
   # Disable image generation, use SVG only
   # Edit image_service.py:
   # Change detect_image_request() to always return (True, True)
   ```

3. **Cost tracking errors**
   ```bash
   # Clear cost tracking table
   psql -U postgres -d ai_html_builder -c "TRUNCATE cost_tracking;"

   # Restart with cost tracking disabled
   export DISABLE_COST_TRACKING=true
   uvicorn app.main:app --reload
   ```

4. **Database migration issues**
   ```bash
   # Rollback database
   alembic downgrade -1

   # Re-run migration
   alembic upgrade head
   ```

5. **Full rollback to Plan 002**
   ```bash
   # Remove new files
   rm backend/app/providers/gemini_provider.py
   rm backend/app/providers/gemini_image_provider.py
   rm backend/app/services/image_service.py
   rm backend/app/services/creator.py

   # Restore chat.py from Plan 002
   git checkout origin/plan-002 -- backend/app/api/chat.py

   # Restart server
   pkill -f uvicorn
   uvicorn app.main:app --reload
   ```

### Verification After Rollback

```bash
# 1. Check server health
curl http://localhost:8000/api/health

# 2. Test basic chat (should use Claude only)
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test", "message": "Create a page", "route": "edit"}'

# 3. Verify database state
psql -U postgres -d ai_html_builder -c "SELECT COUNT(*) FROM documents;"

# 4. Check logs
tail -f logs/app.log | grep ERROR
```

---

## Sign-off Checklist

### Before Starting Implementation
- [ ] Plan 001 is 100% complete and tested
- [ ] Plan 002 is 100% complete and tested
- [ ] Database migrations applied successfully
- [ ] Redis is running and accessible
- [ ] Environment variables set: `GOOGLE_API_KEY`, `ANTHROPIC_API_KEY`
- [ ] Google AI SDK installed: `pip install google-genai`
- [ ] Pillow installed: `pip install pillow`

### Phase 1: Gemini Provider
- [ ] `gemini_provider.py` created with full implementation
- [ ] Both `generate()` and `stream()` methods working
- [ ] Token counting accurate
- [ ] Error handling comprehensive
- [ ] Test script passes successfully
- [ ] No linting errors

### Phase 2: Image Provider
- [ ] `gemini_image_provider.py` created
- [ ] PNG generation working (4K, HD, SD)
- [ ] Image bytes returned correctly
- [ ] Test image saved successfully
- [ ] No API errors

### Phase 3: Image Service
- [ ] `image_service.py` created
- [ ] Image detection keywords working
- [ ] SVG generation for all diagram types
- [ ] Base64 encoding correct
- [ ] Image compression under 5MB
- [ ] Claude embedding via `html_insert_after`

### Phase 4: Document Creator
- [ ] `creator.py` created
- [ ] Design guidelines prompt complete
- [ ] Gemini integration working
- [ ] Streaming support functional
- [ ] Version 1 saved to database
- [ ] Cost tracking accurate

### Phase 5: Chat API Integration
- [ ] `chat.py` updated with three-way routing
- [ ] Auto-detection logic working
- [ ] All routes tested (create, edit, image)
- [ ] Cost tracking for all operations
- [ ] Error handling robust
- [ ] API responses match schema

### Testing
- [ ] All 13 test scenarios pass
- [ ] Cost tracking verified in database
- [ ] No memory leaks (check with large contexts)
- [ ] Streaming works without buffering issues
- [ ] Fallback to Claude works when Gemini down
- [ ] Image limit enforcement (max 3 per document)

### Documentation & Deployment
- [ ] Code comments added where needed
- [ ] Environment variables documented
- [ ] Rollback plan tested
- [ ] Server restart successful
- [ ] No errors in production logs
- [ ] Cost tracking dashboard shows correct data

### Final Verification
- [ ] Create new document via Gemini → Success
- [ ] Edit document via Claude → Success
- [ ] Generate image via Gemini → Success
- [ ] SVG diagram via templates → Success
- [ ] Auto-routing selects correct model → Success
- [ ] All costs tracked accurately → Success

---

## Notes

### Cost Optimization Tips

1. **Use SVG for simple diagrams** (flowcharts, timelines, charts) → $0 cost
2. **Use HD resolution** for most images (4K only when needed) → 40% savings
3. **Compress images** aggressively before embedding → Faster loads
4. **Limit images per document** to 3 → Cost control
5. **Use Gemini for creation** (50% cheaper than Claude) → Major savings

### Performance Considerations

- **Gemini streaming**: ~2-3 seconds for first chunk
- **Image generation**: ~5-10 seconds for HD, ~15-20s for 4K
- **Image compression**: ~1-2 seconds for 5MB→2MB
- **Claude embedding**: ~2-3 seconds

### Security Notes

- API keys in environment variables ONLY
- No API keys in logs or responses
- Image size validation (max 5MB embedded)
- Content sanitization before embedding

---

**Plan Status**: ⏳ Ready for Implementation
**Dependencies**: Plan 001 ✅, Plan 002 ✅
**Estimated Time**: 6-8 hours
**Complexity**: High (multi-provider integration)

### Dead Code Cleanup (End of Plan 003)
After this plan is complete, delete the following old v1 files that were kept as reference:
- `backend/app/api/endpoints/health.py` → replaced by new `api/health.py`
- `backend/app/api/endpoints/export.py` → replaced by new `api/export.py` (Plan 005)

**Next Plan**: 004_FRONTEND_REBUILD.md (React UI with multi-model support)
