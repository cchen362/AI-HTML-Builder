"""Base exporter interface for document export system."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExportResult:
    """Result of an export operation."""

    content: bytes
    content_type: str
    file_extension: str
    filename: str
    metadata: dict[str, Any] | None = None


@dataclass
class ExportOptions:
    """Options for export operations."""

    # Common
    document_title: str = "document"
    include_metadata: bool = True

    # PDF/PNG specific
    page_format: str = "A4"
    landscape: bool = False
    scale: float = 1.0

    # PPTX specific
    slide_width: float = 13.333
    slide_height: float = 7.5
    theme: str = "default"

    # PNG specific
    full_page: bool = True
    width: int | None = None
    height: int | None = None

    # Custom options
    custom: dict[str, Any] = field(default_factory=dict)


class ExportError(Exception):
    """Base exception for export operations."""


class ExportGenerationError(ExportError):
    """Raised when export generation fails."""


class BaseExporter(ABC):
    """Abstract base class for all exporters."""

    @property
    @abstractmethod
    def format_name(self) -> str:
        """Human-readable format name (e.g., 'PDF', 'PowerPoint')."""
        ...

    @property
    @abstractmethod
    def file_extension(self) -> str:
        """File extension without dot (e.g., 'pdf', 'pptx')."""
        ...

    @property
    @abstractmethod
    def content_type(self) -> str:
        """MIME type for this format (e.g., 'application/pdf')."""
        ...

    @abstractmethod
    async def export(
        self,
        html_content: str,
        options: ExportOptions,
    ) -> ExportResult:
        """Export HTML content to the target format."""
        ...

    def validate_html(self, html_content: str) -> None:
        """Validate HTML content before export."""
        if not html_content or not html_content.strip():
            raise ExportError("HTML content is empty")
        stripped = html_content.strip()
        if not stripped.startswith("<!DOCTYPE") and not stripped.startswith("<html"):
            raise ExportError("Invalid HTML: must start with <!DOCTYPE or <html>")

    def generate_filename(self, options: ExportOptions) -> str:
        """Generate sanitised filename for exported document."""
        from app.utils.export_utils import sanitize_title

        return f"{sanitize_title(options.document_title)}.{self.file_extension}"
