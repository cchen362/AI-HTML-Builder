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
from typing import Any

import structlog

from app.providers.base import LLMProvider
from .base import BaseExporter, ExportGenerationError, ExportOptions, ExportResult

logger = structlog.get_logger()

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
        return f"""Analyze the following HTML document and generate Python code using the python-pptx library to create a PowerPoint presentation that captures the document's content and structure.

HTML DOCUMENT:
```html
{html_content}
```

REQUIREMENTS:
1. Use ONLY the python-pptx library (import as 'from pptx import Presentation')
2. Create a Presentation object and add slides to represent the document
3. Analyze the HTML structure to determine appropriate slide layouts:
   - Headers (h1, h2) typically become slide titles
   - Sections become separate slides
   - Lists, tables, and content blocks become slide content
   - Preserve hierarchy and grouping
4. Apply professional formatting:
   - Slide size: {options.slide_width}" x {options.slide_height}"
   - Use appropriate fonts and sizes
   - Add colors and styling where appropriate
   - Maintain visual hierarchy
5. Return the presentation as bytes using io.BytesIO()

SECURITY CONSTRAINTS:
- Do NOT import any modules except: pptx, io, base64, typing
- Do NOT access the file system
- Do NOT make network requests
- Do NOT use eval, exec, or compile

OUTPUT FORMAT:
Return ONLY executable Python code. The code must:
1. Create a Presentation object
2. Add slides with content
3. Save to BytesIO and set the result variable

The code MUST end with:
```
output = BytesIO()
prs.save(output)
result = output.getvalue()
```

Generate the Python code now:"""

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
