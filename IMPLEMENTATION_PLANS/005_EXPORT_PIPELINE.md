# Implementation Plan 005: Export Pipeline

## ⚠️ STOP - READ THIS FIRST ⚠️

**DO NOT START** this implementation until:
- ✅ Plan 002 (Surgical Editing System) is FULLY complete and tested
- ✅ Plan 003 (Multi-Model Support) is FULLY complete and tested
- ✅ You have read this ENTIRE document
- ✅ You understand the security implications of sandboxed code execution
- ✅ You have verified Playwright installation requirements

**DESTRUCTIVE ACTIONS PROHIBITED:**
- ❌ Do NOT modify existing export functionality until Phase 2
- ❌ Do NOT expose unsandboxed code execution endpoints
- ❌ Do NOT skip sandbox security validation
- ❌ Do NOT commit until ALL phases pass tests

**DEPENDENCIES:**
- Plan 002: Document versioning system required for version-specific exports
- Plan 003: Multi-model infrastructure for Claude-powered PPTX generation

**ESTIMATED EFFORT:** 3-4 days

---

## Context & Rationale

### Current State
The AI HTML Builder currently has basic HTML export functionality embedded in the chat flow. Users can download the generated HTML, but there's no formal export system, no alternative formats, and no version-specific export capability.

### Why This Matters
**Problem:** Users need to share generated documents in different formats:
- **HTML**: Web publishing, email distribution
- **PDF**: Print-ready, archival, professional sharing
- **PPTX**: Presentations, boardroom meetings, client proposals
- **PNG**: Quick previews, thumbnails, social media sharing

**Current Limitations:**
1. Only HTML export available (informal)
2. No version-specific export (can't export old versions)
3. No format conversion capabilities
4. No systematic export infrastructure

### Strategic Goals
1. **Extensibility**: Plugin architecture for adding new formats easily
2. **Intelligence**: Claude-powered PPTX generation for semantic document conversion
3. **Reliability**: Playwright-based rendering for accurate PDF/PNG exports
4. **Security**: Sandboxed execution environment for generated code
5. **Performance**: Browser instance reuse, async processing, timeout handling

### Architecture Decision: Claude-Generated PPTX vs Template-Based

**Why Claude Generation?**
- **Semantic Understanding**: Claude analyzes document structure and creates appropriate slide layouts
- **Flexibility**: Handles any document type without pre-built templates
- **Intelligence**: Makes design decisions (what's a title vs body, how to group content)
- **Simplicity**: No need to maintain complex HTML → PPTX parsing logic

**Security Trade-off:**
- **Risk**: Executing generated Python code
- **Mitigation**: Restricted globals, import whitelisting, timeout limits, retry logic
- **Benefit**: Worth the controlled risk for the flexibility gained

### Cost Analysis
- **PPTX Export**: ~$0.08 per export (5-15K tokens at Claude Sonnet 4.5 pricing)
- **PDF/PNG Export**: Negligible (local Playwright rendering)
- **Optimization**: Cache generated PPTX code for identical HTML documents

---

## Strict Rules - Check Before Each Commit

### Security Rules
- [ ] Sandboxed exec() uses restricted `__builtins__` dictionary
- [ ] Only whitelisted imports allowed: `pptx`, `io`, `base64`, `typing`
- [ ] No file system access in generated code
- [ ] No network access in generated code
- [ ] Generated code timeout enforced (30 seconds max)
- [ ] Error messages sanitized before returning to client
- [ ] No user input directly concatenated into exec() code

### Code Quality Rules
- [ ] All exporters implement `BaseExporter` abstract class
- [ ] Export registry uses dependency injection pattern
- [ ] Playwright browser initialized in lifespan context
- [ ] Browser crashes handled with automatic restart
- [ ] All export operations are async
- [ ] Comprehensive error logging for debugging
- [ ] Type hints on all functions and classes

### Testing Rules
- [ ] Each exporter has unit tests with mock HTML
- [ ] Sandbox security tested with malicious code attempts
- [ ] Large HTML (100KB+) export tested without timeout
- [ ] Version-specific export tested for all formats
- [ ] Playwright lifecycle tested (startup, reuse, crash recovery)
- [ ] Integration tests for all API endpoints
- [ ] Generated files validated (openable, not corrupted)

### Performance Rules
- [ ] Browser instance reused across exports (not recreated)
- [ ] Claude PPTX code cached by HTML content hash
- [ ] Export operations timeout after 60 seconds
- [ ] Concurrent exports limited to 5 at a time
- [ ] Large exports don't block other requests

---

## Phase 1: Extensible Export Interface

### Objective
Create a plugin-based export architecture that allows easy addition of new formats.

### Implementation

#### 1.1 Create Base Exporter Class

**File:** `backend/app/services/exporters/base.py`

```python
"""
Base exporter interface for document export system.
All exporters must inherit from BaseExporter.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class ExportResult:
    """Result of an export operation."""
    content: bytes
    content_type: str
    file_extension: str
    filename: str
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ExportOptions:
    """Options for export operations."""
    # Common options
    document_title: str = "document"
    include_metadata: bool = True

    # PDF/PNG specific
    page_format: str = "A4"  # A4, Letter, Legal
    landscape: bool = False
    scale: float = 1.0

    # PPTX specific
    slide_width: int = 10  # inches
    slide_height: int = 7.5  # inches
    theme: str = "default"

    # PNG specific
    full_page: bool = True
    width: Optional[int] = None
    height: Optional[int] = None

    # Custom options
    custom: Dict[str, Any] = None

    def __post_init__(self):
        if self.custom is None:
            self.custom = {}


class ExportError(Exception):
    """Base exception for export operations."""
    pass


class UnsupportedFormatError(ExportError):
    """Raised when export format is not supported."""
    pass


class ExportGenerationError(ExportError):
    """Raised when export generation fails."""
    pass


class BaseExporter(ABC):
    """
    Abstract base class for all exporters.

    Each exporter implements a specific export format (HTML, PDF, PPTX, PNG).
    Exporters are registered in the ExportRegistry and invoked by the export service.
    """

    @property
    @abstractmethod
    def format_name(self) -> str:
        """
        Human-readable format name (e.g., 'PDF', 'PowerPoint').
        """
        pass

    @property
    @abstractmethod
    def file_extension(self) -> str:
        """
        File extension without dot (e.g., 'pdf', 'pptx').
        """
        pass

    @property
    @abstractmethod
    def content_type(self) -> str:
        """
        MIME type for this format (e.g., 'application/pdf').
        """
        pass

    @abstractmethod
    async def export(
        self,
        html_content: str,
        options: ExportOptions
    ) -> ExportResult:
        """
        Export HTML content to the target format.

        Args:
            html_content: The HTML document to export
            options: Export options and configuration

        Returns:
            ExportResult with content bytes and metadata

        Raises:
            ExportGenerationError: If export fails
        """
        pass

    def validate_html(self, html_content: str) -> None:
        """
        Validate HTML content before export.
        Override for format-specific validation.

        Args:
            html_content: HTML to validate

        Raises:
            ExportError: If HTML is invalid
        """
        if not html_content or not html_content.strip():
            raise ExportError("HTML content is empty")

        if not html_content.strip().startswith("<!DOCTYPE") and not html_content.strip().startswith("<html"):
            raise ExportError("Invalid HTML: must start with <!DOCTYPE or <html>")

    def generate_filename(self, options: ExportOptions) -> str:
        """
        Generate filename for exported document.

        Args:
            options: Export options containing document title

        Returns:
            Filename with extension
        """
        # Sanitize title for filename
        safe_title = "".join(
            c if c.isalnum() or c in (' ', '-', '_') else '_'
            for c in options.document_title
        ).strip()

        if not safe_title:
            safe_title = "document"

        return f"{safe_title}.{self.file_extension}"
```

#### 1.2 Create Export Registry

**File:** `backend/app/services/exporters/registry.py`

```python
"""
Export registry for managing available exporters.
Uses dependency injection pattern for extensibility.
"""

from typing import Dict, Type, Optional
from .base import BaseExporter, UnsupportedFormatError
import logging

logger = logging.getLogger(__name__)


class ExportRegistry:
    """
    Registry of available exporters.
    Singleton pattern - one registry per application.
    """

    _instance: Optional['ExportRegistry'] = None
    _exporters: Dict[str, BaseExporter] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._exporters = {}
        return cls._instance

    def register(self, format_key: str, exporter: BaseExporter) -> None:
        """
        Register an exporter for a specific format.

        Args:
            format_key: Format identifier (e.g., 'html', 'pdf', 'pptx', 'png')
            exporter: Exporter instance
        """
        self._exporters[format_key.lower()] = exporter
        logger.info(f"Registered exporter: {format_key} ({exporter.format_name})")

    def get_exporter(self, format_key: str) -> BaseExporter:
        """
        Get exporter for a specific format.

        Args:
            format_key: Format identifier

        Returns:
            Exporter instance

        Raises:
            UnsupportedFormatError: If format not registered
        """
        exporter = self._exporters.get(format_key.lower())
        if not exporter:
            available = ", ".join(self._exporters.keys())
            raise UnsupportedFormatError(
                f"Format '{format_key}' not supported. Available: {available}"
            )
        return exporter

    def list_formats(self) -> Dict[str, str]:
        """
        List all registered export formats.

        Returns:
            Dict mapping format_key to format_name
        """
        return {
            key: exporter.format_name
            for key, exporter in self._exporters.items()
        }

    def is_format_supported(self, format_key: str) -> bool:
        """
        Check if a format is supported.

        Args:
            format_key: Format identifier

        Returns:
            True if format is registered
        """
        return format_key.lower() in self._exporters


# Global registry instance
export_registry = ExportRegistry()
```

#### 1.3 Create Export Service

**File:** `backend/app/services/export_service.py`

```python
"""
Main export service coordinating all export operations.
Integrates with document storage and export registry.
"""

from typing import Optional
from .exporters.base import ExportResult, ExportOptions, ExportError
from .exporters.registry import export_registry
from .document_storage import DocumentStorage
import logging

logger = logging.getLogger(__name__)


class ExportService:
    """
    Service for exporting documents to various formats.
    """

    def __init__(self, document_storage: DocumentStorage):
        """
        Initialize export service.

        Args:
            document_storage: Document storage service (from Plan 002)
        """
        self.document_storage = document_storage

    async def export_document(
        self,
        session_id: str,
        document_id: str,
        format_key: str,
        version: Optional[int] = None,
        options: Optional[ExportOptions] = None
    ) -> ExportResult:
        """
        Export a document to the specified format.

        Args:
            session_id: Session identifier
            document_id: Document identifier
            format_key: Export format (html, pdf, pptx, png)
            version: Specific version to export (None = latest)
            options: Export options

        Returns:
            ExportResult with exported content

        Raises:
            ExportError: If export fails
        """
        try:
            # Get document HTML
            if version is not None:
                document = await self.document_storage.get_version(
                    session_id, document_id, version
                )
                html_content = document.content
            else:
                html_content = await self.document_storage.get_latest_html(
                    session_id, document_id
                )

            if not html_content:
                raise ExportError(f"Document {document_id} not found")

            # Get exporter
            exporter = export_registry.get_exporter(format_key)

            # Set default options if not provided
            if options is None:
                options = ExportOptions(document_title=document_id)

            # Validate HTML
            exporter.validate_html(html_content)

            # Perform export
            logger.info(
                f"Exporting document {document_id} (version={version}) "
                f"to {format_key} for session {session_id}"
            )

            result = await exporter.export(html_content, options)

            logger.info(
                f"Export successful: {len(result.content)} bytes, "
                f"filename={result.filename}"
            )

            return result

        except Exception as e:
            logger.error(f"Export failed: {str(e)}", exc_info=True)
            raise ExportError(f"Export failed: {str(e)}") from e

    def list_available_formats(self) -> dict:
        """
        List all available export formats.

        Returns:
            Dict of format_key -> format_name
        """
        return export_registry.list_formats()
```

#### 1.4 Update Service Dependencies

**File:** `backend/app/services/__init__.py`

```python
"""
Service layer exports.
"""

from .claude_service import ClaudeService
from .document_storage import DocumentStorage
from .export_service import ExportService
from .exporters.registry import export_registry

__all__ = [
    "ClaudeService",
    "DocumentStorage",
    "ExportService",
    "export_registry",
]
```

### Validation Checklist - Phase 1
- [ ] BaseExporter abstract class created with all required methods
- [ ] ExportResult and ExportOptions dataclasses defined
- [ ] ExportRegistry implements singleton pattern
- [ ] ExportService integrates with DocumentStorage
- [ ] Type hints present on all functions
- [ ] Comprehensive docstrings written
- [ ] Error classes defined and documented

---

## Phase 2: HTML Export (Simple)

### Objective
Formalize the existing HTML export functionality with the new interface.

### Implementation

#### 2.1 Create HTML Exporter

**File:** `backend/app/services/exporters/html_exporter.py`

```python
"""
HTML exporter - returns raw HTML content.
This is the simplest exporter, just wrapping the existing functionality.
"""

from .base import BaseExporter, ExportResult, ExportOptions
import logging

logger = logging.getLogger(__name__)


class HTMLExporter(BaseExporter):
    """
    Exports documents as raw HTML files.
    No transformation needed - just returns the HTML as-is.
    """

    @property
    def format_name(self) -> str:
        return "HTML"

    @property
    def file_extension(self) -> str:
        return "html"

    @property
    def content_type(self) -> str:
        return "text/html"

    async def export(
        self,
        html_content: str,
        options: ExportOptions
    ) -> ExportResult:
        """
        Export HTML content as HTML file.

        Args:
            html_content: The HTML document
            options: Export options

        Returns:
            ExportResult with HTML bytes
        """
        logger.info(f"Exporting HTML document: {options.document_title}")

        # Validate
        self.validate_html(html_content)

        # Convert to bytes
        content_bytes = html_content.encode('utf-8')

        # Generate filename
        filename = self.generate_filename(options)

        # Build metadata
        metadata = {
            "size_bytes": len(content_bytes),
            "encoding": "utf-8",
        }

        if options.include_metadata:
            metadata["original_format"] = "HTML"

        return ExportResult(
            content=content_bytes,
            content_type=self.content_type,
            file_extension=self.file_extension,
            filename=filename,
            metadata=metadata
        )
```

#### 2.2 Register HTML Exporter

**File:** `backend/app/main.py` (modify lifespan)

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.services.exporters.html_exporter import HTMLExporter
from app.services.exporters.registry import export_registry

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown tasks.
    """
    # Startup
    logger.info("Starting AI HTML Builder...")

    # Initialize Redis connection pool
    # ... existing code ...

    # Register exporters
    export_registry.register("html", HTMLExporter())
    logger.info("Registered HTML exporter")

    yield

    # Shutdown
    logger.info("Shutting down AI HTML Builder...")
    # ... existing shutdown code ...
```

### Validation Checklist - Phase 2
- [ ] HTMLExporter implements BaseExporter
- [ ] HTML content returned as UTF-8 bytes
- [ ] Filename generated correctly with .html extension
- [ ] Metadata includes size and encoding
- [ ] Exporter registered in lifespan startup
- [ ] Unit tests pass for HTML export

---

## Phase 3: PPTX Export (Claude-Generated)

### Objective
Use Claude Sonnet 4.5 to analyze HTML and generate python-pptx code, then execute it safely.

### Implementation

#### 3.1 Create PPTX Exporter

**File:** `backend/app/services/exporters/pptx_exporter.py`

```python
"""
PowerPoint exporter using Claude-generated python-pptx code.

Security Model:
- Claude generates Python code using python-pptx library
- Code is executed in sandboxed environment with restricted imports
- Only whitelisted modules allowed: pptx, io, base64, typing
- No file system or network access
- 30-second timeout on code execution
"""

from .base import BaseExporter, ExportResult, ExportOptions, ExportGenerationError
from typing import Optional, Dict, Any
import logging
import hashlib
import io
import asyncio
from functools import lru_cache

logger = logging.getLogger(__name__)


class PPTXExporter(BaseExporter):
    """
    Exports documents as PowerPoint presentations.
    Uses Claude to analyze HTML and generate python-pptx code.
    """

    def __init__(self, claude_service):
        """
        Initialize PPTX exporter.

        Args:
            claude_service: ClaudeService instance for code generation
        """
        self.claude_service = claude_service
        self._code_cache: Dict[str, str] = {}

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
        options: ExportOptions
    ) -> ExportResult:
        """
        Export HTML to PowerPoint presentation.

        Args:
            html_content: The HTML document
            options: Export options

        Returns:
            ExportResult with PPTX bytes

        Raises:
            ExportGenerationError: If generation fails
        """
        logger.info(f"Exporting PPTX document: {options.document_title}")

        # Validate
        self.validate_html(html_content)

        try:
            # Check cache first
            cache_key = self._get_cache_key(html_content, options)
            python_code = self._code_cache.get(cache_key)

            if python_code:
                logger.info("Using cached PPTX generation code")
            else:
                # Generate python-pptx code with Claude
                python_code = await self._generate_pptx_code(html_content, options)
                self._code_cache[cache_key] = python_code

            # Execute generated code in sandbox
            pptx_bytes = await self._execute_pptx_code(python_code, max_retries=1)

            # Generate filename
            filename = self.generate_filename(options)

            # Build metadata
            metadata = {
                "size_bytes": len(pptx_bytes),
                "generated_with": "claude-sonnet-4.5",
                "code_cached": python_code in self._code_cache.values(),
            }

            return ExportResult(
                content=pptx_bytes,
                content_type=self.content_type,
                file_extension=self.file_extension,
                filename=filename,
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"PPTX export failed: {str(e)}", exc_info=True)
            raise ExportGenerationError(f"PPTX generation failed: {str(e)}") from e

    def _get_cache_key(self, html_content: str, options: ExportOptions) -> str:
        """
        Generate cache key for HTML + options combination.

        Args:
            html_content: HTML document
            options: Export options

        Returns:
            SHA256 hash as cache key
        """
        # Include relevant options in cache key
        key_data = f"{html_content}|{options.slide_width}|{options.slide_height}|{options.theme}"
        return hashlib.sha256(key_data.encode()).hexdigest()

    async def _generate_pptx_code(
        self,
        html_content: str,
        options: ExportOptions
    ) -> str:
        """
        Use Claude to generate python-pptx code.

        Args:
            html_content: HTML to convert
            options: Export options

        Returns:
            Python code as string
        """
        prompt = self._build_generation_prompt(html_content, options)

        # Use Claude Sonnet 4.5 for code generation
        response = await self.claude_service.generate_code(
            prompt=prompt,
            model="claude-sonnet-4-20250514",
            max_tokens=8000,
        )

        # Extract code from response
        python_code = self._extract_code(response)

        # Validate code safety
        self._validate_code_safety(python_code)

        return python_code

    def _build_generation_prompt(
        self,
        html_content: str,
        options: ExportOptions
    ) -> str:
        """
        Build prompt for Claude to generate python-pptx code.
        """
        return f"""You are an expert Python developer specializing in document conversion.

TASK: Analyze the following HTML document and generate Python code using the python-pptx library to create a PowerPoint presentation that captures the document's content and structure.

HTML DOCUMENT:
```html
{html_content}
```

REQUIREMENTS:
1. Use ONLY the python-pptx library (already imported as 'from pptx import Presentation')
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
- Code will run in a restricted sandbox

OUTPUT FORMAT:
Return ONLY executable Python code with no explanations. The code must:
1. Create a Presentation object
2. Add slides with content
3. Save to BytesIO and return bytes

Example structure:
```python
from pptx import Presentation
from pptx.util import Inches, Pt
from io import BytesIO

def generate_presentation():
    prs = Presentation()
    prs.slide_width = Inches({options.slide_width})
    prs.slide_height = Inches({options.slide_height})

    # Add slides based on HTML structure
    # ... your generated code ...

    output = BytesIO()
    prs.save(output)
    output.seek(0)
    return output.read()

# Execute
result = generate_presentation()
```

Generate the Python code now:"""

    def _extract_code(self, response: str) -> str:
        """
        Extract Python code from Claude's response.

        Args:
            response: Claude's text response

        Returns:
            Extracted Python code
        """
        # Look for code blocks
        if "```python" in response:
            start = response.find("```python") + len("```python")
            end = response.find("```", start)
            code = response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            code = response[start:end].strip()
        else:
            # Assume entire response is code
            code = response.strip()

        return code

    def _validate_code_safety(self, code: str) -> None:
        """
        Validate that generated code is safe to execute.

        Args:
            code: Python code to validate

        Raises:
            ExportGenerationError: If code contains unsafe patterns
        """
        # Forbidden patterns
        forbidden = [
            "import os",
            "import sys",
            "import subprocess",
            "import requests",
            "import urllib",
            "import socket",
            "__import__",
            "eval(",
            "exec(",
            "compile(",
            "open(",
            "file(",
            "input(",
            "raw_input(",
        ]

        code_lower = code.lower()
        for pattern in forbidden:
            if pattern.lower() in code_lower:
                raise ExportGenerationError(
                    f"Generated code contains forbidden pattern: {pattern}"
                )

        # Required patterns
        if "from pptx import Presentation" not in code:
            raise ExportGenerationError(
                "Generated code must import Presentation from pptx"
            )

    async def _execute_pptx_code(
        self,
        python_code: str,
        max_retries: int = 1
    ) -> bytes:
        """
        Execute generated python-pptx code in sandboxed environment.

        Args:
            python_code: Python code to execute
            max_retries: Maximum retry attempts on failure

        Returns:
            PPTX file as bytes

        Raises:
            ExportGenerationError: If execution fails
        """
        for attempt in range(max_retries + 1):
            try:
                # Create restricted globals
                restricted_globals = {
                    "__builtins__": {
                        # Safe builtins only
                        "len": len,
                        "range": range,
                        "enumerate": enumerate,
                        "str": str,
                        "int": int,
                        "float": float,
                        "bool": bool,
                        "list": list,
                        "dict": dict,
                        "tuple": tuple,
                        "set": set,
                        "True": True,
                        "False": False,
                        "None": None,
                    },
                }

                # Create locals for execution
                exec_locals = {}

                # Execute with timeout
                await asyncio.wait_for(
                    self._run_in_executor(python_code, restricted_globals, exec_locals),
                    timeout=30.0
                )

                # Get result
                result = exec_locals.get("result")
                if not result or not isinstance(result, bytes):
                    raise ExportGenerationError(
                        "Generated code did not return bytes"
                    )

                return result

            except asyncio.TimeoutError:
                raise ExportGenerationError("Code execution timeout (30s)")

            except Exception as e:
                logger.warning(
                    f"PPTX code execution failed (attempt {attempt + 1}/{max_retries + 1}): {str(e)}"
                )

                if attempt < max_retries:
                    # Retry with error feedback to Claude
                    error_msg = str(e)
                    python_code = await self._regenerate_with_error(python_code, error_msg)
                else:
                    raise ExportGenerationError(
                        f"Code execution failed after {max_retries + 1} attempts: {str(e)}"
                    ) from e

    async def _run_in_executor(
        self,
        code: str,
        globals_dict: dict,
        locals_dict: dict
    ) -> None:
        """
        Run code in thread pool executor to prevent blocking.

        Args:
            code: Python code to execute
            globals_dict: Restricted globals
            locals_dict: Locals dictionary for results
        """
        import concurrent.futures

        def execute():
            exec(code, globals_dict, locals_dict)

        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            await loop.run_in_executor(executor, execute)

    async def _regenerate_with_error(
        self,
        failed_code: str,
        error_message: str
    ) -> str:
        """
        Ask Claude to fix failed code.

        Args:
            failed_code: Code that failed
            error_message: Error message

        Returns:
            Fixed code
        """
        prompt = f"""The following python-pptx code failed with an error. Please fix it.

FAILED CODE:
```python
{failed_code}
```

ERROR:
{error_message}

Please provide corrected Python code that fixes this error while maintaining all requirements from the original task.
Return ONLY the corrected code, no explanations."""

        response = await self.claude_service.generate_code(
            prompt=prompt,
            model="claude-sonnet-4-20250514",
            max_tokens=8000,
        )

        return self._extract_code(response)
```

#### 3.2 Add Code Generation Method to ClaudeService

**File:** `backend/app/services/claude_service.py` (add method)

```python
async def generate_code(
    self,
    prompt: str,
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 8000,
) -> str:
    """
    Generate code using Claude.

    Args:
        prompt: Code generation prompt
        model: Claude model to use
        max_tokens: Maximum tokens in response

    Returns:
        Generated code as string
    """
    try:
        response = await self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.0,  # Deterministic for code generation
        )

        return response.content[0].text

    except Exception as e:
        logger.error(f"Code generation failed: {str(e)}", exc_info=True)
        raise
```

#### 3.3 Install python-pptx

**File:** `backend/requirements.txt` (add)

```
python-pptx==0.6.21
```

#### 3.4 Register PPTX Exporter

**File:** `backend/app/main.py` (modify lifespan)

```python
from app.services.exporters.pptx_exporter import PPTXExporter

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting AI HTML Builder...")

    # ... existing initialization ...

    # Register exporters
    export_registry.register("html", HTMLExporter())
    export_registry.register("pptx", PPTXExporter(claude_service))
    logger.info("Registered exporters: HTML, PPTX")

    yield

    # Shutdown
    # ... existing shutdown ...
```

### Validation Checklist - Phase 3
- [ ] PPTXExporter implements BaseExporter
- [ ] Claude generates valid python-pptx code
- [ ] Sandboxed execution restricts imports correctly
- [ ] Generated PPTX files are openable in PowerPoint
- [ ] Cache prevents redundant Claude API calls
- [ ] Retry logic handles code execution failures
- [ ] Timeout enforced at 30 seconds
- [ ] Error messages sanitized before returning
- [ ] Unit tests for code validation and execution

---

## Phase 4: PDF Export (Playwright)

### Objective
Use Playwright to render HTML in headless browser and generate PDF.

### Implementation

#### 4.1 Create Playwright Manager

**File:** `backend/app/services/playwright_manager.py`

```python
"""
Playwright browser lifecycle manager.
Manages headless browser instance for PDF/PNG exports.
"""

from typing import Optional
from playwright.async_api import async_playwright, Browser, Page
import logging
import asyncio

logger = logging.getLogger(__name__)


class PlaywrightManager:
    """
    Manages Playwright browser lifecycle.
    Singleton pattern - one browser instance per application.
    """

    _instance: Optional['PlaywrightManager'] = None
    _browser: Optional[Browser] = None
    _playwright = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def initialize(self) -> None:
        """
        Initialize Playwright and launch browser.
        Called during application startup.
        """
        try:
            logger.info("Initializing Playwright browser...")

            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--disable-gpu',
                ]
            )

            logger.info(f"Playwright browser launched: {self._browser.version}")

        except Exception as e:
            logger.error(f"Failed to initialize Playwright: {str(e)}", exc_info=True)
            raise

    async def shutdown(self) -> None:
        """
        Shutdown browser and Playwright.
        Called during application shutdown.
        """
        try:
            if self._browser:
                logger.info("Closing Playwright browser...")
                await self._browser.close()
                self._browser = None

            if self._playwright:
                await self._playwright.stop()
                self._playwright = None

            logger.info("Playwright shutdown complete")

        except Exception as e:
            logger.error(f"Error during Playwright shutdown: {str(e)}", exc_info=True)

    async def create_page(self) -> Page:
        """
        Create a new browser page.
        Reuses existing browser instance.

        Returns:
            New page instance

        Raises:
            RuntimeError: If browser not initialized
        """
        if not self._browser:
            # Try to restart browser if it crashed
            logger.warning("Browser not initialized, attempting restart...")
            await self.initialize()

        try:
            page = await self._browser.new_page()
            return page

        except Exception as e:
            logger.error(f"Failed to create page: {str(e)}", exc_info=True)

            # Attempt browser restart on failure
            logger.info("Attempting browser restart...")
            await self.shutdown()
            await self.initialize()

            # Retry page creation
            page = await self._browser.new_page()
            return page

    @property
    def is_initialized(self) -> bool:
        """Check if browser is initialized."""
        return self._browser is not None


# Global manager instance
playwright_manager = PlaywrightManager()
```

#### 4.2 Create PDF Exporter

**File:** `backend/app/services/exporters/pdf_exporter.py`

```python
"""
PDF exporter using Playwright for HTML rendering.
Handles JavaScript-heavy HTML and interactive elements.
"""

from .base import BaseExporter, ExportResult, ExportOptions, ExportGenerationError
from ..playwright_manager import playwright_manager
import logging

logger = logging.getLogger(__name__)


class PDFExporter(BaseExporter):
    """
    Exports documents as PDF files.
    Uses Playwright to render HTML in headless browser.
    """

    @property
    def format_name(self) -> str:
        return "PDF"

    @property
    def file_extension(self) -> str:
        return "pdf"

    @property
    def content_type(self) -> str:
        return "application/pdf"

    async def export(
        self,
        html_content: str,
        options: ExportOptions
    ) -> ExportResult:
        """
        Export HTML to PDF.

        Args:
            html_content: The HTML document
            options: Export options

        Returns:
            ExportResult with PDF bytes

        Raises:
            ExportGenerationError: If generation fails
        """
        logger.info(f"Exporting PDF document: {options.document_title}")

        # Validate
        self.validate_html(html_content)

        page = None
        try:
            # Create new page
            page = await playwright_manager.create_page()

            # Set viewport size
            await page.set_viewport_size({
                "width": 1920,
                "height": 1080
            })

            # Load HTML content
            await page.set_content(html_content, wait_until="networkidle")

            # Wait for any JavaScript to execute
            await page.wait_for_timeout(1000)  # 1 second for JS

            # Generate PDF
            pdf_options = {
                "format": options.page_format,
                "landscape": options.landscape,
                "print_background": True,
                "scale": options.scale,
                "margin": {
                    "top": "0.5in",
                    "right": "0.5in",
                    "bottom": "0.5in",
                    "left": "0.5in",
                }
            }

            pdf_bytes = await page.pdf(**pdf_options)

            # Generate filename
            filename = self.generate_filename(options)

            # Build metadata
            metadata = {
                "size_bytes": len(pdf_bytes),
                "page_format": options.page_format,
                "landscape": options.landscape,
                "rendered_with": "playwright-chromium",
            }

            return ExportResult(
                content=pdf_bytes,
                content_type=self.content_type,
                file_extension=self.file_extension,
                filename=filename,
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"PDF export failed: {str(e)}", exc_info=True)
            raise ExportGenerationError(f"PDF generation failed: {str(e)}") from e

        finally:
            if page:
                await page.close()
```

#### 4.3 Install Playwright

**File:** `backend/requirements.txt` (add)

```
playwright==1.40.0
```

**Post-install command** (add to deployment docs):
```bash
# Install browser binaries
playwright install chromium
```

#### 4.4 Register PDF Exporter

**File:** `backend/app/main.py` (modify lifespan)

```python
from app.services.exporters.pdf_exporter import PDFExporter
from app.services.playwright_manager import playwright_manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting AI HTML Builder...")

    # ... existing initialization ...

    # Initialize Playwright
    await playwright_manager.initialize()

    # Register exporters
    export_registry.register("html", HTMLExporter())
    export_registry.register("pptx", PPTXExporter(claude_service))
    export_registry.register("pdf", PDFExporter())
    logger.info("Registered exporters: HTML, PPTX, PDF")

    yield

    # Shutdown
    logger.info("Shutting down AI HTML Builder...")

    # Shutdown Playwright
    await playwright_manager.shutdown()

    # ... existing shutdown ...
```

### Validation Checklist - Phase 4
- [ ] PlaywrightManager implements singleton pattern
- [ ] Browser initialized on startup, closed on shutdown
- [ ] Browser restart works after crashes
- [ ] PDFExporter creates valid PDF files
- [ ] JavaScript in HTML executes correctly
- [ ] Page format options work (A4, Letter, landscape)
- [ ] Print backgrounds included in PDF
- [ ] Unit tests for PDF generation

---

## Phase 5: PNG Screenshot Export

### Objective
Use same Playwright instance to generate PNG screenshots.

### Implementation

#### 5.1 Create PNG Exporter

**File:** `backend/app/services/exporters/png_exporter.py`

```python
"""
PNG screenshot exporter using Playwright.
Useful for generating previews and thumbnails.
"""

from .base import BaseExporter, ExportResult, ExportOptions, ExportGenerationError
from ..playwright_manager import playwright_manager
import logging

logger = logging.getLogger(__name__)


class PNGExporter(BaseExporter):
    """
    Exports documents as PNG screenshots.
    Uses Playwright to render and capture HTML.
    """

    @property
    def format_name(self) -> str:
        return "PNG"

    @property
    def file_extension(self) -> str:
        return "png"

    @property
    def content_type(self) -> str:
        return "image/png"

    async def export(
        self,
        html_content: str,
        options: ExportOptions
    ) -> ExportResult:
        """
        Export HTML to PNG screenshot.

        Args:
            html_content: The HTML document
            options: Export options

        Returns:
            ExportResult with PNG bytes

        Raises:
            ExportGenerationError: If generation fails
        """
        logger.info(f"Exporting PNG screenshot: {options.document_title}")

        # Validate
        self.validate_html(html_content)

        page = None
        try:
            # Create new page
            page = await playwright_manager.create_page()

            # Set viewport size if specified
            if options.width and options.height:
                await page.set_viewport_size({
                    "width": options.width,
                    "height": options.height
                })
            else:
                # Default viewport
                await page.set_viewport_size({
                    "width": 1920,
                    "height": 1080
                })

            # Load HTML content
            await page.set_content(html_content, wait_until="networkidle")

            # Wait for any JavaScript to execute
            await page.wait_for_timeout(1000)  # 1 second for JS

            # Generate screenshot
            screenshot_options = {
                "full_page": options.full_page,
                "type": "png",
            }

            if options.width and options.height and not options.full_page:
                screenshot_options["clip"] = {
                    "x": 0,
                    "y": 0,
                    "width": options.width,
                    "height": options.height,
                }

            png_bytes = await page.screenshot(**screenshot_options)

            # Generate filename
            filename = self.generate_filename(options)

            # Build metadata
            metadata = {
                "size_bytes": len(png_bytes),
                "full_page": options.full_page,
                "rendered_with": "playwright-chromium",
            }

            if options.width and options.height:
                metadata["width"] = options.width
                metadata["height"] = options.height

            return ExportResult(
                content=png_bytes,
                content_type=self.content_type,
                file_extension=self.file_extension,
                filename=filename,
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"PNG export failed: {str(e)}", exc_info=True)
            raise ExportGenerationError(f"PNG generation failed: {str(e)}") from e

        finally:
            if page:
                await page.close()
```

#### 5.2 Register PNG Exporter

**File:** `backend/app/main.py` (modify lifespan)

```python
from app.services.exporters.png_exporter import PNGExporter

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting AI HTML Builder...")

    # ... existing initialization ...

    # Initialize Playwright
    await playwright_manager.initialize()

    # Register exporters
    export_registry.register("html", HTMLExporter())
    export_registry.register("pptx", PPTXExporter(claude_service))
    export_registry.register("pdf", PDFExporter())
    export_registry.register("png", PNGExporter())
    logger.info("Registered exporters: HTML, PPTX, PDF, PNG")

    yield

    # Shutdown
    # ... existing shutdown ...
```

### Validation Checklist - Phase 5
- [ ] PNGExporter implements BaseExporter
- [ ] Full-page screenshots work correctly
- [ ] Custom viewport sizes respected
- [ ] PNG files valid and openable
- [ ] JavaScript rendered before screenshot
- [ ] Useful for thumbnail generation
- [ ] Unit tests for PNG generation

---

## Phase 6: Export API Endpoints

### Objective
Create REST endpoints for all export formats.

### Implementation

#### 6.1 Create Export Router

**File:** `backend/app/api/routes/export.py`

```python
"""
Export API endpoints.
Handles document export to various formats.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from app.services.export_service import ExportService
from app.services.exporters.base import ExportOptions, ExportError, UnsupportedFormatError
from typing import Optional
import logging
import io

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/export", tags=["export"])


# Dependency injection
def get_export_service() -> ExportService:
    """Get export service instance."""
    from app.dependencies import get_export_service as _get_service
    return _get_service()


@router.post("/{session_id}/{document_id}/html")
async def export_html(
    session_id: str,
    document_id: str,
    version: Optional[int] = Query(None, description="Document version (None = latest)"),
    title: str = Query("document", description="Document title for filename"),
    export_service: ExportService = Depends(get_export_service),
):
    """
    Export document as HTML file.

    Args:
        session_id: Session identifier
        document_id: Document identifier
        version: Document version to export (None = latest)
        title: Document title for filename

    Returns:
        HTML file download
    """
    try:
        options = ExportOptions(document_title=title)

        result = await export_service.export_document(
            session_id=session_id,
            document_id=document_id,
            format_key="html",
            version=version,
            options=options,
        )

        return StreamingResponse(
            io.BytesIO(result.content),
            media_type=result.content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{result.filename}"'
            }
        )

    except ExportError as e:
        logger.error(f"HTML export failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during HTML export: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Export failed")


@router.post("/{session_id}/{document_id}/pptx")
async def export_pptx(
    session_id: str,
    document_id: str,
    version: Optional[int] = Query(None, description="Document version (None = latest)"),
    title: str = Query("presentation", description="Document title for filename"),
    slide_width: int = Query(10, description="Slide width in inches"),
    slide_height: int = Query(7.5, description="Slide height in inches"),
    theme: str = Query("default", description="Presentation theme"),
    export_service: ExportService = Depends(get_export_service),
):
    """
    Export document as PowerPoint presentation.

    Args:
        session_id: Session identifier
        document_id: Document identifier
        version: Document version to export (None = latest)
        title: Document title for filename
        slide_width: Slide width in inches
        slide_height: Slide height in inches
        theme: Presentation theme

    Returns:
        PPTX file download
    """
    try:
        options = ExportOptions(
            document_title=title,
            slide_width=slide_width,
            slide_height=slide_height,
            theme=theme,
        )

        result = await export_service.export_document(
            session_id=session_id,
            document_id=document_id,
            format_key="pptx",
            version=version,
            options=options,
        )

        return StreamingResponse(
            io.BytesIO(result.content),
            media_type=result.content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{result.filename}"'
            }
        )

    except ExportError as e:
        logger.error(f"PPTX export failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during PPTX export: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Export failed")


@router.post("/{session_id}/{document_id}/pdf")
async def export_pdf(
    session_id: str,
    document_id: str,
    version: Optional[int] = Query(None, description="Document version (None = latest)"),
    title: str = Query("document", description="Document title for filename"),
    page_format: str = Query("A4", description="Page format (A4, Letter, Legal)"),
    landscape: bool = Query(False, description="Landscape orientation"),
    scale: float = Query(1.0, description="Page scale (0.1 - 2.0)"),
    export_service: ExportService = Depends(get_export_service),
):
    """
    Export document as PDF file.

    Args:
        session_id: Session identifier
        document_id: Document identifier
        version: Document version to export (None = latest)
        title: Document title for filename
        page_format: Page format (A4, Letter, Legal)
        landscape: Landscape orientation
        scale: Page scale

    Returns:
        PDF file download
    """
    try:
        options = ExportOptions(
            document_title=title,
            page_format=page_format,
            landscape=landscape,
            scale=scale,
        )

        result = await export_service.export_document(
            session_id=session_id,
            document_id=document_id,
            format_key="pdf",
            version=version,
            options=options,
        )

        return StreamingResponse(
            io.BytesIO(result.content),
            media_type=result.content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{result.filename}"'
            }
        )

    except ExportError as e:
        logger.error(f"PDF export failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during PDF export: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Export failed")


@router.post("/{session_id}/{document_id}/png")
async def export_png(
    session_id: str,
    document_id: str,
    version: Optional[int] = Query(None, description="Document version (None = latest)"),
    title: str = Query("screenshot", description="Document title for filename"),
    full_page: bool = Query(True, description="Capture full page"),
    width: Optional[int] = Query(None, description="Screenshot width in pixels"),
    height: Optional[int] = Query(None, description="Screenshot height in pixels"),
    export_service: ExportService = Depends(get_export_service),
):
    """
    Export document as PNG screenshot.

    Args:
        session_id: Session identifier
        document_id: Document identifier
        version: Document version to export (None = latest)
        title: Document title for filename
        full_page: Capture full page
        width: Screenshot width (if not full page)
        height: Screenshot height (if not full page)

    Returns:
        PNG file download
    """
    try:
        options = ExportOptions(
            document_title=title,
            full_page=full_page,
            width=width,
            height=height,
        )

        result = await export_service.export_document(
            session_id=session_id,
            document_id=document_id,
            format_key="png",
            version=version,
            options=options,
        )

        return StreamingResponse(
            io.BytesIO(result.content),
            media_type=result.content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{result.filename}"'
            }
        )

    except ExportError as e:
        logger.error(f"PNG export failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during PNG export: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Export failed")


@router.get("/formats")
async def list_formats(
    export_service: ExportService = Depends(get_export_service),
):
    """
    List all available export formats.

    Returns:
        Dict of format_key -> format_name
    """
    formats = export_service.list_available_formats()
    return {"formats": formats}
```

#### 6.2 Create Dependencies

**File:** `backend/app/dependencies.py` (add)

```python
"""
Dependency injection for FastAPI.
"""

from app.services.export_service import ExportService
from app.services.document_storage import DocumentStorage
from functools import lru_cache


@lru_cache()
def get_document_storage() -> DocumentStorage:
    """Get singleton DocumentStorage instance."""
    return DocumentStorage()


@lru_cache()
def get_export_service() -> ExportService:
    """Get singleton ExportService instance."""
    return ExportService(document_storage=get_document_storage())
```

#### 6.3 Register Router

**File:** `backend/app/main.py` (add router)

```python
from app.api.routes import export

# Register routers
app.include_router(export.router)
```

### Validation Checklist - Phase 6
- [ ] All export endpoints return correct Content-Type
- [ ] Content-Disposition headers set for file downloads
- [ ] Version parameter works for all formats
- [ ] Query parameters validated and applied
- [ ] Error handling returns appropriate HTTP codes
- [ ] OpenAPI docs generated correctly
- [ ] Integration tests for all endpoints

---

## Phase 7: Playwright Lifecycle Management

### Objective
Ensure robust browser lifecycle with crash recovery and resource management.

### Implementation

#### 7.1 Enhanced PlaywrightManager with Health Checks

**File:** `backend/app/services/playwright_manager.py` (enhance)

```python
"""
Enhanced Playwright manager with health checks and crash recovery.
"""

from typing import Optional
from playwright.async_api import async_playwright, Browser, Page, Error as PlaywrightError
import logging
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)


class PlaywrightManager:
    """
    Manages Playwright browser lifecycle with health monitoring.
    """

    _instance: Optional['PlaywrightManager'] = None
    _browser: Optional[Browser] = None
    _playwright = None
    _health_check_task: Optional[asyncio.Task] = None
    _last_health_check: Optional[datetime] = None
    _restart_lock: asyncio.Lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._restart_lock = asyncio.Lock()
        return cls._instance

    async def initialize(self) -> None:
        """Initialize Playwright and launch browser with health monitoring."""
        try:
            logger.info("Initializing Playwright browser...")

            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--disable-gpu',
                ]
            )

            logger.info(f"Playwright browser launched: {self._browser.version}")

            # Start health check task
            self._health_check_task = asyncio.create_task(self._health_check_loop())

        except Exception as e:
            logger.error(f"Failed to initialize Playwright: {str(e)}", exc_info=True)
            raise

    async def shutdown(self) -> None:
        """Shutdown browser and Playwright."""
        try:
            # Cancel health check
            if self._health_check_task:
                self._health_check_task.cancel()
                try:
                    await self._health_check_task
                except asyncio.CancelledError:
                    pass

            if self._browser:
                logger.info("Closing Playwright browser...")
                await self._browser.close()
                self._browser = None

            if self._playwright:
                await self._playwright.stop()
                self._playwright = None

            logger.info("Playwright shutdown complete")

        except Exception as e:
            logger.error(f"Error during Playwright shutdown: {str(e)}", exc_info=True)

    async def create_page(self) -> Page:
        """
        Create a new browser page with automatic recovery.

        Returns:
            New page instance
        """
        if not self._browser:
            async with self._restart_lock:
                if not self._browser:  # Double-check after acquiring lock
                    logger.warning("Browser not initialized, restarting...")
                    await self._restart_browser()

        try:
            page = await self._browser.new_page()
            return page

        except PlaywrightError as e:
            logger.error(f"Failed to create page: {str(e)}")

            # Attempt browser restart
            async with self._restart_lock:
                logger.info("Attempting browser restart after page creation failure...")
                await self._restart_browser()

                # Retry page creation
                page = await self._browser.new_page()
                return page

    async def _restart_browser(self) -> None:
        """Restart browser after crash or failure."""
        try:
            logger.warning("Restarting Playwright browser...")

            # Shutdown existing browser
            if self._browser:
                try:
                    await self._browser.close()
                except:
                    pass
                self._browser = None

            # Restart
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--disable-gpu',
                ]
            )

            logger.info(f"Browser restarted successfully: {self._browser.version}")

        except Exception as e:
            logger.error(f"Failed to restart browser: {str(e)}", exc_info=True)
            raise

    async def _health_check_loop(self) -> None:
        """Periodic health check to detect browser crashes."""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds

                if self._browser:
                    try:
                        # Try to create and close a test page
                        test_page = await self._browser.new_page()
                        await test_page.close()

                        self._last_health_check = datetime.now()
                        logger.debug("Browser health check passed")

                    except Exception as e:
                        logger.error(f"Browser health check failed: {str(e)}")

                        async with self._restart_lock:
                            await self._restart_browser()

            except asyncio.CancelledError:
                logger.info("Health check loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {str(e)}", exc_info=True)

    @property
    def is_initialized(self) -> bool:
        """Check if browser is initialized."""
        return self._browser is not None

    @property
    def last_health_check(self) -> Optional[datetime]:
        """Get timestamp of last successful health check."""
        return self._last_health_check


# Global manager instance
playwright_manager = PlaywrightManager()
```

#### 7.2 Add Health Endpoint

**File:** `backend/app/api/routes/health.py` (enhance)

```python
from app.services.playwright_manager import playwright_manager

@router.get("/health")
async def health_check():
    """Enhanced health check including Playwright status."""
    health = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "redis": "healthy",
            "playwright": "unknown",
        }
    }

    # Check Playwright
    if playwright_manager.is_initialized:
        health["components"]["playwright"] = "healthy"
        if playwright_manager.last_health_check:
            health["playwright_last_check"] = playwright_manager.last_health_check.isoformat()
    else:
        health["components"]["playwright"] = "unhealthy"
        health["status"] = "degraded"

    return health
```

### Validation Checklist - Phase 7
- [ ] Browser initialized on app startup
- [ ] Health check runs every 30 seconds
- [ ] Browser restart works after crashes
- [ ] Multiple concurrent page creations handled
- [ ] Restart lock prevents race conditions
- [ ] Health endpoint shows Playwright status
- [ ] Resource cleanup on shutdown

---

## Build Verification Steps

### After Each Phase

1. **Code Quality**
   ```bash
   # Backend linting
   cd backend
   ruff check app/
   mypy app/
   ```

2. **Unit Tests**
   ```bash
   # Run tests for completed phase
   pytest tests/test_exporters/test_<phase>.py -v
   ```

3. **Integration Tests**
   ```bash
   # Test export endpoints
   pytest tests/integration/test_export_api.py -v
   ```

4. **Manual Testing**
   - Test export via API for each format
   - Validate exported files open correctly
   - Check error handling
   - Verify version-specific exports

### Final Verification

1. **All Exporters Registered**
   ```bash
   curl http://localhost:8000/api/export/formats
   ```

2. **Export HTML**
   ```bash
   curl -X POST "http://localhost:8000/api/export/{session}/{doc}/html" \
     --output test.html
   ```

3. **Export PPTX**
   ```bash
   curl -X POST "http://localhost:8000/api/export/{session}/{doc}/pptx" \
     --output test.pptx
   ```

4. **Export PDF**
   ```bash
   curl -X POST "http://localhost:8000/api/export/{session}/{doc}/pdf" \
     --output test.pdf
   ```

5. **Export PNG**
   ```bash
   curl -X POST "http://localhost:8000/api/export/{session}/{doc}/png" \
     --output test.png
   ```

6. **Validate Files**
   - Open each exported file
   - Verify content matches original HTML
   - Check formatting and styling preserved

---

## Testing Scenarios

### Unit Tests

**File:** `backend/tests/test_exporters/test_base.py`

```python
"""
Tests for base exporter functionality.
"""

import pytest
from app.services.exporters.base import (
    BaseExporter,
    ExportOptions,
    ExportResult,
    ExportError,
)


class MockExporter(BaseExporter):
    """Mock exporter for testing."""

    @property
    def format_name(self) -> str:
        return "Mock"

    @property
    def file_extension(self) -> str:
        return "mock"

    @property
    def content_type(self) -> str:
        return "application/mock"

    async def export(self, html_content: str, options: ExportOptions) -> ExportResult:
        return ExportResult(
            content=html_content.encode(),
            content_type=self.content_type,
            file_extension=self.file_extension,
            filename=self.generate_filename(options),
        )


def test_validate_html_valid():
    """Test HTML validation with valid input."""
    exporter = MockExporter()
    html = "<!DOCTYPE html><html><body>Test</body></html>"

    # Should not raise
    exporter.validate_html(html)


def test_validate_html_empty():
    """Test HTML validation with empty input."""
    exporter = MockExporter()

    with pytest.raises(ExportError, match="HTML content is empty"):
        exporter.validate_html("")


def test_validate_html_invalid():
    """Test HTML validation with invalid input."""
    exporter = MockExporter()

    with pytest.raises(ExportError, match="Invalid HTML"):
        exporter.validate_html("not html")


def test_generate_filename():
    """Test filename generation."""
    exporter = MockExporter()
    options = ExportOptions(document_title="Test Document")

    filename = exporter.generate_filename(options)
    assert filename == "Test_Document.mock"


def test_generate_filename_sanitization():
    """Test filename sanitization."""
    exporter = MockExporter()
    options = ExportOptions(document_title="Test/Doc<>ument")

    filename = exporter.generate_filename(options)
    assert "/" not in filename
    assert "<" not in filename
    assert ">" not in filename
```

**File:** `backend/tests/test_exporters/test_html_exporter.py`

```python
"""
Tests for HTML exporter.
"""

import pytest
from app.services.exporters.html_exporter import HTMLExporter
from app.services.exporters.base import ExportOptions


@pytest.mark.asyncio
async def test_html_export_basic():
    """Test basic HTML export."""
    exporter = HTMLExporter()
    html = "<!DOCTYPE html><html><body><h1>Test</h1></body></html>"
    options = ExportOptions(document_title="test")

    result = await exporter.export(html, options)

    assert result.content == html.encode('utf-8')
    assert result.content_type == "text/html"
    assert result.file_extension == "html"
    assert result.filename == "test.html"


@pytest.mark.asyncio
async def test_html_export_metadata():
    """Test HTML export includes metadata."""
    exporter = HTMLExporter()
    html = "<!DOCTYPE html><html><body>Test</body></html>"
    options = ExportOptions(document_title="test", include_metadata=True)

    result = await exporter.export(html, options)

    assert result.metadata is not None
    assert "size_bytes" in result.metadata
    assert "encoding" in result.metadata
```

**File:** `backend/tests/test_exporters/test_pptx_exporter.py`

```python
"""
Tests for PPTX exporter.
"""

import pytest
from app.services.exporters.pptx_exporter import PPTXExporter
from app.services.exporters.base import ExportOptions, ExportGenerationError
from unittest.mock import AsyncMock, Mock


@pytest.fixture
def mock_claude_service():
    """Mock Claude service for testing."""
    service = Mock()
    service.generate_code = AsyncMock()
    return service


def test_validate_code_safety_forbidden():
    """Test code safety validation catches forbidden patterns."""
    exporter = PPTXExporter(Mock())

    # Test forbidden imports
    with pytest.raises(ExportGenerationError, match="forbidden pattern"):
        exporter._validate_code_safety("import os")

    with pytest.raises(ExportGenerationError, match="forbidden pattern"):
        exporter._validate_code_safety("import subprocess")


def test_validate_code_safety_valid():
    """Test code safety validation allows valid code."""
    exporter = PPTXExporter(Mock())

    code = """
from pptx import Presentation
from io import BytesIO

def generate():
    prs = Presentation()
    # ... code ...
    return prs
"""

    # Should not raise
    exporter._validate_code_safety(code)


@pytest.mark.asyncio
async def test_pptx_export_caching(mock_claude_service):
    """Test PPTX code caching works."""
    exporter = PPTXExporter(mock_claude_service)
    html = "<!DOCTYPE html><html><body>Test</body></html>"
    options = ExportOptions(document_title="test")

    # Mock code generation
    mock_claude_service.generate_code.return_value = """
from pptx import Presentation
from io import BytesIO

prs = Presentation()
output = BytesIO()
prs.save(output)
result = output.getvalue()
"""

    # First call should generate code
    cache_key = exporter._get_cache_key(html, options)
    assert cache_key not in exporter._code_cache

    # (Would need to mock execution for full test)
```

**File:** `backend/tests/test_exporters/test_pdf_exporter.py`

```python
"""
Tests for PDF exporter.
"""

import pytest
from app.services.exporters.pdf_exporter import PDFExporter
from app.services.exporters.base import ExportOptions
from unittest.mock import AsyncMock, Mock, patch


@pytest.mark.asyncio
async def test_pdf_export_options():
    """Test PDF export applies options correctly."""
    exporter = PDFExporter()
    html = "<!DOCTYPE html><html><body>Test</body></html>"
    options = ExportOptions(
        document_title="test",
        page_format="Letter",
        landscape=True,
        scale=0.9,
    )

    with patch('app.services.playwright_manager.playwright_manager') as mock_manager:
        mock_page = AsyncMock()
        mock_page.pdf = AsyncMock(return_value=b'fake pdf bytes')
        mock_manager.create_page = AsyncMock(return_value=mock_page)

        result = await exporter.export(html, options)

        # Verify PDF options passed correctly
        call_kwargs = mock_page.pdf.call_args[1]
        assert call_kwargs['format'] == "Letter"
        assert call_kwargs['landscape'] is True
        assert call_kwargs['scale'] == 0.9
```

### Integration Tests

**File:** `backend/tests/integration/test_export_api.py`

```python
"""
Integration tests for export API.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def test_session(client):
    """Create test session with document."""
    # Setup: create session and document
    # (Implementation depends on session/document creation API)
    session_id = "test-session-123"
    document_id = "test-doc-456"
    return session_id, document_id


def test_export_html_endpoint(client, test_session):
    """Test HTML export endpoint."""
    session_id, document_id = test_session

    response = client.post(
        f"/api/export/{session_id}/{document_id}/html",
        params={"title": "test"}
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html"
    assert "attachment" in response.headers["content-disposition"]


def test_export_pdf_endpoint(client, test_session):
    """Test PDF export endpoint."""
    session_id, document_id = test_session

    response = client.post(
        f"/api/export/{session_id}/{document_id}/pdf",
        params={
            "title": "test",
            "page_format": "A4",
            "landscape": False,
        }
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"


def test_export_version_specific(client, test_session):
    """Test exporting specific version."""
    session_id, document_id = test_session

    response = client.post(
        f"/api/export/{session_id}/{document_id}/html",
        params={"version": 1}
    )

    assert response.status_code == 200


def test_export_unsupported_format(client, test_session):
    """Test error handling for unsupported format."""
    session_id, document_id = test_session

    response = client.post(
        f"/api/export/{session_id}/{document_id}/docx"
    )

    assert response.status_code == 404  # Route not found


def test_list_formats_endpoint(client):
    """Test list formats endpoint."""
    response = client.get("/api/export/formats")

    assert response.status_code == 200
    formats = response.json()["formats"]

    assert "html" in formats
    assert "pdf" in formats
    assert "pptx" in formats
    assert "png" in formats
```

### Security Tests

**File:** `backend/tests/security/test_pptx_sandbox.py`

```python
"""
Security tests for PPTX code sandbox.
"""

import pytest
from app.services.exporters.pptx_exporter import PPTXExporter
from app.services.exporters.base import ExportGenerationError
from unittest.mock import Mock


@pytest.fixture
def exporter():
    """PPTX exporter for testing."""
    return PPTXExporter(Mock())


def test_sandbox_blocks_file_access(exporter):
    """Test sandbox prevents file system access."""
    malicious_code = """
import os
os.system('rm -rf /')
"""

    with pytest.raises(ExportGenerationError, match="forbidden"):
        exporter._validate_code_safety(malicious_code)


def test_sandbox_blocks_network_access(exporter):
    """Test sandbox prevents network access."""
    malicious_code = """
import requests
requests.get('http://evil.com')
"""

    with pytest.raises(ExportGenerationError, match="forbidden"):
        exporter._validate_code_safety(malicious_code)


def test_sandbox_blocks_subprocess(exporter):
    """Test sandbox prevents subprocess execution."""
    malicious_code = """
import subprocess
subprocess.call(['ls'])
"""

    with pytest.raises(ExportGenerationError, match="forbidden"):
        exporter._validate_code_safety(malicious_code)


def test_sandbox_allows_safe_code(exporter):
    """Test sandbox allows safe python-pptx code."""
    safe_code = """
from pptx import Presentation
from io import BytesIO

prs = Presentation()
slide = prs.slides.add_slide(prs.slide_layouts[0])
output = BytesIO()
prs.save(output)
result = output.getvalue()
"""

    # Should not raise
    exporter._validate_code_safety(safe_code)
```

### Performance Tests

**File:** `backend/tests/performance/test_export_performance.py`

```python
"""
Performance tests for export system.
"""

import pytest
import asyncio
from app.services.exporters.html_exporter import HTMLExporter
from app.services.exporters.base import ExportOptions


@pytest.mark.asyncio
async def test_large_html_export():
    """Test exporting large HTML documents."""
    exporter = HTMLExporter()

    # Generate large HTML (100KB+)
    large_content = "<p>Test content</p>" * 5000
    html = f"<!DOCTYPE html><html><body>{large_content}</body></html>"

    options = ExportOptions(document_title="large_test")

    # Should complete within 5 seconds
    result = await asyncio.wait_for(
        exporter.export(html, options),
        timeout=5.0
    )

    assert len(result.content) > 100000


@pytest.mark.asyncio
async def test_concurrent_exports():
    """Test concurrent export operations."""
    exporter = HTMLExporter()
    html = "<!DOCTYPE html><html><body>Test</body></html>"

    # Create 10 concurrent export tasks
    tasks = [
        exporter.export(html, ExportOptions(document_title=f"test_{i}"))
        for i in range(10)
    ]

    # All should complete successfully
    results = await asyncio.gather(*tasks)

    assert len(results) == 10
    assert all(r.content == html.encode('utf-8') for r in results)
```

---

## Rollback Plan

### If Phase 3 (PPTX) Fails

**Symptoms:**
- Claude generates invalid python-pptx code
- Sandboxed execution consistently fails
- Security vulnerabilities discovered

**Rollback Steps:**
1. Remove PPTX exporter from registry
   ```python
   # In main.py lifespan, comment out:
   # export_registry.register("pptx", PPTXExporter(claude_service))
   ```

2. Return 501 Not Implemented for PPTX endpoint
   ```python
   @router.post("/{session_id}/{document_id}/pptx")
   async def export_pptx(...):
       raise HTTPException(
           status_code=501,
           detail="PPTX export temporarily unavailable"
       )
   ```

3. Document issue and plan alternative approach
   - Consider template-based PPTX generation
   - Evaluate third-party HTML→PPTX services

### If Phase 4 (PDF) Fails

**Symptoms:**
- Playwright fails to install or initialize
- Browser crashes frequently
- PDF rendering incorrect

**Rollback Steps:**
1. Remove PDF/PNG exporters from registry
2. Skip Playwright initialization in lifespan
3. Return 501 for PDF/PNG endpoints
4. Revert to HTML-only exports

**Alternative Approaches:**
- Use weasyprint for simpler PDF generation (no JS support)
- Integrate external PDF service (PDFShift, DocRaptor)
- Provide PDF instructions (print from browser)

### If Performance Issues

**Symptoms:**
- Export operations timeout
- Browser memory leaks
- Too many concurrent exports crash system

**Mitigation Steps:**
1. Add export queue with concurrency limit
   ```python
   from asyncio import Semaphore

   export_semaphore = Semaphore(5)  # Max 5 concurrent exports

   async def export_with_limit(...):
       async with export_semaphore:
           return await export_service.export_document(...)
   ```

2. Implement export caching
   ```python
   # Cache export results by content hash
   export_cache = {}

   cache_key = hashlib.sha256(html_content.encode()).hexdigest()
   if cache_key in export_cache:
       return export_cache[cache_key]
   ```

3. Add timeout enforcement
   ```python
   result = await asyncio.wait_for(
       exporter.export(html, options),
       timeout=60.0  # 60 second max
   )
   ```

---

## Sign-off Checklist

### Before Marking Complete

- [ ] **Phase 1: Extensible Interface**
  - [ ] BaseExporter abstract class created
  - [ ] ExportRegistry implements singleton pattern
  - [ ] ExportService integrates with DocumentStorage
  - [ ] All type hints and docstrings present

- [ ] **Phase 2: HTML Export**
  - [ ] HTMLExporter implements BaseExporter
  - [ ] HTML files download correctly
  - [ ] Unit tests pass

- [ ] **Phase 3: PPTX Export**
  - [ ] PPTXExporter implements BaseExporter
  - [ ] Claude generates valid python-pptx code
  - [ ] Sandboxed execution works securely
  - [ ] Generated PPTX files open in PowerPoint
  - [ ] Code caching reduces API calls
  - [ ] Security tests pass (no file/network access)

- [ ] **Phase 4: PDF Export**
  - [ ] Playwright initializes on startup
  - [ ] PDFExporter creates valid PDFs
  - [ ] JavaScript in HTML renders correctly
  - [ ] Page format options work
  - [ ] Browser restart works after crashes

- [ ] **Phase 5: PNG Export**
  - [ ] PNGExporter creates valid PNG files
  - [ ] Full-page screenshots work
  - [ ] Custom viewport sizes respected

- [ ] **Phase 6: API Endpoints**
  - [ ] All export endpoints implemented
  - [ ] Version-specific exports work
  - [ ] Error handling returns appropriate codes
  - [ ] OpenAPI documentation generated

- [ ] **Phase 7: Lifecycle Management**
  - [ ] Browser initializes on startup
  - [ ] Health checks run periodically
  - [ ] Crash recovery works
  - [ ] Clean shutdown on app termination

- [ ] **Testing**
  - [ ] All unit tests pass
  - [ ] Integration tests pass
  - [ ] Security tests pass
  - [ ] Performance tests pass
  - [ ] Manual testing completed for all formats

- [ ] **Documentation**
  - [ ] API documentation updated
  - [ ] README includes export examples
  - [ ] Environment variables documented
  - [ ] Troubleshooting guide updated

- [ ] **Security**
  - [ ] Sandboxed execution validated
  - [ ] No file system access in PPTX code
  - [ ] No network access in PPTX code
  - [ ] Error messages don't leak sensitive info

- [ ] **Performance**
  - [ ] Large HTML (100KB+) exports without timeout
  - [ ] Concurrent exports handled correctly
  - [ ] Browser memory usage acceptable
  - [ ] Cache reduces redundant operations

### Final Validation

```bash
# Run all tests
pytest tests/ -v

# Test all export formats
./scripts/test_exports.sh

# Verify OpenAPI docs
curl http://localhost:8000/docs

# Check health status
curl http://localhost:8000/api/health
```

### Ready for Production

- [ ] All tests passing
- [ ] No security vulnerabilities
- [ ] Performance metrics acceptable
- [ ] Documentation complete
- [ ] Rollback plan tested
- [ ] Team sign-off obtained

---

## Dependencies & References

### Dependencies
- **Plan 002 (Surgical Editing)**: Document versioning system required
- **Plan 003 (Multi-Model)**: Claude Sonnet 4.5 integration required

### External Dependencies
- `python-pptx==0.6.21`: PowerPoint file generation
- `playwright==1.40.0`: Browser automation for PDF/PNG
- `anthropic`: Claude API for code generation

### References
- [python-pptx Documentation](https://python-pptx.readthedocs.io/)
- [Playwright Python Documentation](https://playwright.dev/python/)
- [FastAPI File Responses](https://fastapi.tiangolo.com/advanced/custom-response/#fileresponse)
- [Anthropic Claude API](https://docs.anthropic.com/claude/reference/getting-started-with-the-api)

---

**Implementation Plan Status:** ✅ COMPLETE (implemented 2026-02-12)
**Last Updated:** 2026-02-12
**Author:** AI HTML Builder Team
**Review Required:** Yes (security review for sandboxed execution)

---

## ⚠️ POST-IMPLEMENTATION DISCREPANCIES

> **This section was added after Plan 005 was implemented.**
> The plan doc above was written before Plans 001-003 were implemented, so it contains
> assumptions about classes, methods, and patterns that don't exist in the actual codebase.
> Below is the authoritative list of what was changed during implementation.
> **Future agents: use this section as the source of truth, not the code snippets above.**

### Discrepancy Table

| # | Plan Doc Assumes | Actual Codebase | What Was Done |
|---|---|---|---|
| 1 | `DocumentStorage` class with `get_version(session_id, document_id, version)` and `get_latest_html(session_id, document_id)` | `SessionService` singleton at `app.services.session_service.session_service` with `get_version(document_id, version)` and `get_latest_html(document_id)` — no `session_id` param needed | `ExportService` imports `session_service` directly; calls `session_service.get_version(document_id, version)` returning `dict \| None`; accesses `result["html_content"]` (not `.content`) |
| 2 | `ClaudeService` with `generate_code()` method (plan proposes adding it) | `AnthropicProvider` implementing `LLMProvider` ABC with `generate()` → `GenerationResult` | `PPTXExporter.__init__(self, provider: LLMProvider)` calls `self.provider.generate(system=..., messages=[...], temperature=0.0, max_tokens=8000)` |
| 3 | `backend/app/dependencies.py` for dependency injection (`get_document_storage()`, `get_export_service()`) | No DI module; module-level singletons everywhere (`session_service`, `export_registry`, `export_service`) | No `dependencies.py` created; `export_service = ExportService()` at module level |
| 4 | `ExportRegistry` uses `__new__` singleton pattern | All singletons in codebase are module-level instances | `export_registry = ExportRegistry()` at module level in `registry.py` |
| 5 | `PlaywrightManager` uses `__new__` singleton pattern | Same as above | `playwright_manager = PlaywrightManager()` at module level in `playwright_manager.py` |
| 6 | `ExportService.__init__(self, document_storage: DocumentStorage)` constructor DI | No DI; service imports `session_service` directly at module top | `ExportService` has no constructor params; uses `from app.services.session_service import session_service` |
| 7 | `logging.getLogger(__name__)` throughout | `structlog.get_logger()` used everywhere in v2 codebase | All new files use `structlog.get_logger()` |
| 8 | API routes at `api/routes/export.py` with `session_id` + `document_id` in URL path (e.g., `/{session_id}/{document_id}/html`) | Flat router files at `api/*.py`; `document_id` is a UUID PK sufficient for lookup | Created `api/export.py` with routes like `/api/export/{document_id}/html` — no `session_id` |
| 9 | Tests in subdirectories: `tests/test_exporters/test_base.py`, etc. | All tests are flat: `tests/test_*.py` | Created flat: `test_export_base.py`, `test_export_html.py`, `test_export_pptx.py`, `test_export_pdf.py`, `test_export_api.py`, `test_playwright_manager.py` |
| 10 | `ExportOptions.custom: Dict[str, Any] = None` with `__post_init__` | Modern Python: use `field(default_factory=dict)` to avoid mutable default + `__post_init__` | Used `custom: dict[str, Any] = field(default_factory=dict)` |
| 11 | `ExportOptions.slide_height: int = 7.5` (int can't hold 7.5) | Type mismatch: 7.5 is a float | Used `slide_height: float = 7.5` |
| 12 | `from typing import Dict, Any, Optional` (old-style) | Python 3.10+ syntax used throughout v2 codebase | Used `dict[str, Any]`, `X \| None` instead of `Optional[X]`, `from __future__ import annotations` |
| 13 | Sandbox `__builtins__` has no `__import__` | `from pptx import Presentation` in generated code needs `__import__` to work | Added whitelisted `_safe_import()` function that delegates to `builtins.__import__` after checking module against `_ALLOWED_BASE_MODULES` frozenset |
| 14 | `_FORBIDDEN_PATTERNS` includes `__import__` | Can't forbid `__import__` if we provide `_safe_import` as `__import__` | Removed `__import__` from forbidden patterns list |
| 15 | `PlaywrightManager._restart_lock = asyncio.Lock()` in `__init__` | Module-level singleton is imported before event loop exists; `asyncio.Lock()` requires a running loop | `_restart_lock` created lazily inside `async def initialize()`, not in `__init__` |
| 16 | `PlaywrightManager._playwright` typed as `object \| None` | mypy errors: `"object" has no attribute "chromium"` / `"stop"` | Typed as `Playwright \| None` (from `playwright.async_api`) |
| 17 | Plan doc proposes `claude_service` variable for PPTX registration in `main.py` lifespan | No `claude_service` exists; `AnthropicProvider` is the provider | Lifespan creates `AnthropicProvider()` wrapped in try/except, passes to `PPTXExporter(pptx_provider)` |
| 18 | `ExportService.export_document()` calls `self.document_storage.get_version(session_id, doc_id, version).content` | `session_service.get_version(document_id, version)` returns `dict \| None` | Access via `version_data["html_content"]` after None check |

### Key Architectural Patterns (Actual, Not Plan Doc)

- **Singletons**: Module-level instances, NOT `__new__` or DI containers
  ```python
  # In registry.py
  export_registry = ExportRegistry()
  # In export_service.py
  export_service = ExportService()
  # In playwright_manager.py
  playwright_manager = PlaywrightManager()
  ```

- **Provider injection**: Constructor takes `LLMProvider` interface (same pattern as `SurgicalEditor`)
  ```python
  class PPTXExporter(BaseExporter):
      def __init__(self, provider: LLMProvider) -> None:
          self.provider = provider
  ```

- **Logging**: `structlog.get_logger()` everywhere (not `logging.getLogger`)

- **API routes**: Flat files at `backend/app/api/*.py`, NOT nested `api/routes/` dirs

- **DB access**: `session_service.get_version(document_id, version)` returns `dict | None` with key `"html_content"`

### Files Actually Created/Modified/Deleted

**Created (16 files):**
- `backend/app/services/exporters/__init__.py`
- `backend/app/services/exporters/base.py`
- `backend/app/services/exporters/registry.py`
- `backend/app/services/exporters/html_exporter.py`
- `backend/app/services/exporters/pptx_exporter.py`
- `backend/app/services/exporters/pdf_exporter.py`
- `backend/app/services/exporters/png_exporter.py`
- `backend/app/services/export_service.py`
- `backend/app/services/playwright_manager.py`
- `backend/app/api/export.py`
- `backend/tests/test_export_base.py`
- `backend/tests/test_export_html.py`
- `backend/tests/test_export_pptx.py`
- `backend/tests/test_export_pdf.py`
- `backend/tests/test_playwright_manager.py`
- `backend/tests/test_export_api.py`

**Modified (3 files):**
- `backend/app/main.py` — exporter registration in lifespan, Playwright init/shutdown, export router
- `backend/app/api/health.py` — Playwright status, structured response with components
- `Dockerfile` — curl, `playwright install chromium --with-deps`, curl-based HEALTHCHECK

**Deleted (2 files):**
- `backend/app/api/endpoints/export.py` — dead v1 code (imported nonexistent `redis_service`)
- `backend/app/api/endpoints/health.py` — dead v1 code (real endpoint at `api/health.py`)

**NOT created (contrary to plan doc):**
- `backend/app/dependencies.py` — not needed, module-level singletons used instead
- `backend/app/services/claude_service.py` additions — `AnthropicProvider.generate()` used directly

### Verification Results (2026-02-12)
- **Tests**: 193/194 passing (76 new + 117 existing), 1 pre-existing failure (`test_init_db_creates_file`)
- **Ruff**: clean
- **Mypy**: clean
