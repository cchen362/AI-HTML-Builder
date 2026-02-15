"""PowerPoint exporter using Claude-generated python-pptx code.

Security Model:
- Claude generates Python code using python-pptx library
- Code is executed in sandboxed environment with restricted imports
- Only whitelisted modules allowed: pptx, io, base64, typing, math, collections
- No file system or network access
- 30-second timeout on code execution
"""

from __future__ import annotations

import asyncio
import builtins
import concurrent.futures
import hashlib
import re
from typing import Any

import structlog

from app.providers.base import LLMProvider
from .base import BaseExporter, ExportGenerationError, ExportOptions, ExportResult

logger = structlog.get_logger()

# Regex to strip base64 image payloads before sending to LLM
_BASE64_RE = re.compile(r'(data:image/[^;]+;base64,)[A-Za-z0-9+/=]{100,}')

# Modules the sandbox is allowed to import
_ALLOWED_BASE_MODULES = frozenset({"pptx", "io", "base64", "typing", "math", "collections"})

# Patterns that are forbidden in generated code
_FORBIDDEN_PATTERNS = [
    "import os",
    "import sys",
    "import subprocess",
    "import requests",
    "import urllib",
    "import socket",
    "import shutil",
    "import pathlib",
    "import glob",
    "eval(",
    "exec(",
    "compile(",
    "open(",
    "file(",
    "input(",
    "getattr(",
    "setattr(",
    "delattr(",
]


def _safe_import(
    name: str,
    globals_: dict[str, Any] | None = None,
    locals_: dict[str, Any] | None = None,
    fromlist: tuple[str, ...] = (),
    level: int = 0,
) -> Any:
    """Import function that only allows whitelisted modules."""
    base_module = name.split(".")[0]
    if base_module not in _ALLOWED_BASE_MODULES:
        raise ImportError(f"Import of '{name}' is not allowed in sandbox")
    return builtins.__import__(name, globals_, locals_, fromlist, level)


def _build_restricted_builtins() -> dict[str, Any]:
    """Build restricted __builtins__ dict for sandbox."""
    return {
        "__import__": _safe_import,
        "len": len,
        "range": range,
        "enumerate": enumerate,
        "zip": zip,
        "min": min,
        "max": max,
        "abs": abs,
        "round": round,
        "sorted": sorted,
        "reversed": reversed,
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "list": list,
        "dict": dict,
        "tuple": tuple,
        "set": set,
        "type": type,
        "isinstance": isinstance,
        "hasattr": hasattr,
        "map": map,
        "filter": filter,
        "any": any,
        "all": all,
        "sum": sum,
        "repr": repr,
        "chr": chr,
        "ord": ord,
        "hex": hex,
        "bytes": bytes,
        "bytearray": bytearray,
        "memoryview": memoryview,
        "True": True,
        "False": False,
        "None": None,
        "print": lambda *_a, **_kw: None,  # noqa: ARG005
        "ValueError": ValueError,
        "TypeError": TypeError,
        "KeyError": KeyError,
        "IndexError": IndexError,
        "AttributeError": AttributeError,
        "StopIteration": StopIteration,
        "RuntimeError": RuntimeError,
    }


def _preloaded_pptx_names() -> dict[str, Any]:
    """Pre-import common pptx names into sandbox globals.

    Claude's generated code often references these symbols. By pre-loading
    them, we avoid NameError when the LLM omits or miswrites an import.
    """
    from pptx import Presentation
    from pptx.util import Inches, Pt, Emu
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
    from pptx.enum.shapes import MSO_SHAPE
    from io import BytesIO
    import base64
    import math

    return {
        "Presentation": Presentation,
        "Inches": Inches,
        "Pt": Pt,
        "Emu": Emu,
        "RGBColor": RGBColor,
        "PP_ALIGN": PP_ALIGN,
        "MSO_ANCHOR": MSO_ANCHOR,
        "MSO_SHAPE": MSO_SHAPE,
        "BytesIO": BytesIO,
        "base64": base64,
        "math": math,
    }


class PPTXExporter(BaseExporter):
    """Exports documents as PowerPoint presentations via Claude-generated code."""

    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider
        self._code_cache: dict[str, str] = {}

    @property
    def format_name(self) -> str:
        return "PowerPoint"

    @property
    def file_extension(self) -> str:
        return "pptx"

    @property
    def content_type(self) -> str:
        return "application/vnd.openxmlformats-officedocument.presentationml.presentation"

    async def export(
        self,
        html_content: str,
        options: ExportOptions,
    ) -> ExportResult:
        self.validate_html(html_content)

        try:
            cache_key = self._get_cache_key(html_content, options)
            python_code = self._code_cache.get(cache_key)

            if python_code:
                logger.info("Using cached PPTX generation code")
            else:
                python_code = await self._generate_pptx_code(html_content, options)
                self._code_cache[cache_key] = python_code

            pptx_bytes = await self._execute_pptx_code(python_code, max_retries=1)

            return ExportResult(
                content=pptx_bytes,
                content_type=self.content_type,
                file_extension=self.file_extension,
                filename=self.generate_filename(options),
                metadata={
                    "size_bytes": len(pptx_bytes),
                    "generated_with": self.provider.model if hasattr(self.provider, "model") else "claude",  # type: ignore[attr-defined]
                    "code_cached": cache_key in self._code_cache,
                },
            )
        except ExportGenerationError:
            raise
        except Exception as e:
            logger.error("PPTX export failed", error=str(e), exc_info=True)
            raise ExportGenerationError(f"PPTX generation failed: {e}") from e

    # ------------------------------------------------------------------
    # Code generation
    # ------------------------------------------------------------------

    def _get_cache_key(self, html_content: str, options: ExportOptions) -> str:
        key_data = f"{html_content}|{options.slide_width}|{options.slide_height}|{options.theme}"
        return hashlib.sha256(key_data.encode()).hexdigest()

    async def _generate_pptx_code(
        self, html_content: str, options: ExportOptions
    ) -> str:
        prompt = self._build_generation_prompt(html_content, options)
        result = await self.provider.generate(
            system=(
                "You are an expert Python developer. "
                "Generate ONLY executable Python code, no explanations."
            ),
            messages=[{"role": "user", "content": prompt}],
            max_tokens=8000,
            temperature=0.0,
        )
        python_code = self._extract_code(result.text)
        self._validate_code_safety(python_code)
        return python_code

    def _build_generation_prompt(
        self, html_content: str, options: ExportOptions
    ) -> str:
        # Strip base64 images to save tokens and reduce noise
        clean_html = _BASE64_RE.sub(r'\1[IMAGE_DATA_REMOVED]', html_content)

        return f"""Analyze this HTML document and generate Python code using python-pptx to create a professional PowerPoint presentation.

HTML DOCUMENT:
```html
{clean_html}
```

SLIDE DIMENSIONS:
- Width: {options.slide_width} inches, Height: {options.slide_height} inches
- Set via: prs.slide_width = Inches({options.slide_width}); prs.slide_height = Inches({options.slide_height})

COLOR EXTRACTION (CRITICAL):
- Extract the primary, secondary, and accent colors from the HTML's <style> block, CSS variables, or inline styles.
- Use these EXACT colors as RGBColor values throughout the presentation.
- If colors are in hex (e.g., #0D7377), convert: RGBColor(0x0D, 0x73, 0x77).
- Do NOT default to plain black text on white slides — match the document's color palette.

SLIDE STRUCTURE RULES:
1. Slide 1 = Title slide: document's h1 as title, first subtitle/description text below.
2. Each h2 heading starts a NEW slide. Never put two h2 sections on one slide.
3. Maximum 5 bullet points per slide. If more content exists, split into continuation slides titled "Section Name (1/2)", "(2/2)".
4. Maximum ~10 words per bullet point. Summarize if the HTML text is longer.
5. Tables get their own slide. Render as a python-pptx Table shape.

VISUAL FORMATTING (MANDATORY):
- Title bar: Add a filled rectangle shape (MSO_SHAPE.RECTANGLE) across the top 1.2 inches of each slide, filled with the primary color. Place the slide title as white text ON this bar.
- Body text: 16-18pt Calibri, dark color from the palette, 1.15 line spacing.
- Sub-headings within slides: bold, accent color, 20pt.
- Card-like groups: If the HTML uses cards or boxed sections, create rounded rectangle shapes (MSO_SHAPE.ROUNDED_RECTANGLE) with a light fill (10% opacity of accent) behind the text.
- Accent line: Add a thin horizontal line shape below the title bar using the accent color.
- Content margins: All text content starts at 0.7 inches from left/right edges, 1.5 inches from top (below title bar).

FONT SIZES:
- Slide title (on title bar): 28-32pt, bold, white
- Body text: 16-18pt
- Bullet sub-text: 14pt
- NEVER use fonts smaller than 14pt

IMPORTS TO USE:
```python
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from io import BytesIO
```

DO NOT:
- Cram excessive text onto slides — split instead
- Use fonts smaller than 14pt
- Leave text running to slide edges (maintain 0.7" margins)
- Use default blank layouts with unstyled text — add visual shapes
- Import modules other than: pptx, io, base64, typing, math, collections

OUTPUT: Return ONLY executable Python code ending with:
```
output = BytesIO()
prs.save(output)
result = output.getvalue()
```"""

    def _extract_code(self, response: str) -> str:
        if "```python" in response:
            start = response.find("```python") + len("```python")
            end = response.find("```", start)
            if end == -1:
                return response[start:].strip()
            return response[start:end].strip()
        if "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            if end == -1:
                return response[start:].strip()
            return response[start:end].strip()
        return response.strip()

    # ------------------------------------------------------------------
    # Code safety
    # ------------------------------------------------------------------

    def _validate_code_safety(self, code: str) -> None:
        code_lower = code.lower()
        for pattern in _FORBIDDEN_PATTERNS:
            if pattern.lower() in code_lower:
                raise ExportGenerationError(
                    f"Generated code contains forbidden pattern: {pattern}"
                )
        if "from pptx import" not in code and "import pptx" not in code:
            raise ExportGenerationError(
                "Generated code must import from pptx"
            )

    # ------------------------------------------------------------------
    # Sandbox execution
    # ------------------------------------------------------------------

    async def _execute_pptx_code(
        self, python_code: str, max_retries: int = 1
    ) -> bytes:
        for attempt in range(max_retries + 1):
            try:
                restricted_globals: dict[str, Any] = {
                    "__builtins__": _build_restricted_builtins(),
                    **_preloaded_pptx_names(),
                }
                exec_locals: dict[str, Any] = {}

                await asyncio.wait_for(
                    self._run_in_executor(python_code, restricted_globals, exec_locals),
                    timeout=30.0,
                )

                result = exec_locals.get("result")
                if not result or not isinstance(result, bytes):
                    raise ExportGenerationError(
                        "Generated code did not produce a 'result' variable containing bytes"
                    )
                return result

            except asyncio.TimeoutError:
                raise ExportGenerationError("Code execution timeout (30s)")

            except ExportGenerationError:
                raise

            except Exception as e:
                logger.warning(
                    "PPTX code execution failed",
                    attempt=attempt + 1,
                    max_attempts=max_retries + 1,
                    error=str(e),
                )
                if attempt < max_retries:
                    python_code = await self._regenerate_with_error(
                        python_code, str(e)
                    )
                else:
                    raise ExportGenerationError(
                        f"Code execution failed after {max_retries + 1} attempts: {e}"
                    ) from e

        # Should not reach here, but satisfy mypy
        raise ExportGenerationError("Unexpected execution path")  # pragma: no cover

    async def _run_in_executor(
        self,
        code: str,
        globals_dict: dict[str, Any],
        locals_dict: dict[str, Any],
    ) -> None:
        def execute() -> None:
            exec(code, globals_dict, locals_dict)  # noqa: S102

        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            await loop.run_in_executor(executor, execute)

    async def _regenerate_with_error(
        self, failed_code: str, error_message: str
    ) -> str:
        prompt = f"""The following python-pptx code failed with an error. Fix it.

FAILED CODE:
```python
{failed_code}
```

ERROR:
{error_message}

Return ONLY corrected Python code, no explanations. The code must end with:
output = BytesIO()
prs.save(output)
result = output.getvalue()"""

        result = await self.provider.generate(
            system="You are an expert Python developer fixing code errors.",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=8000,
            temperature=0.0,
        )
        code = self._extract_code(result.text)
        self._validate_code_safety(code)
        return code
