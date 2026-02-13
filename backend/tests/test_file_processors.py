"""Tests for file processing utilities."""

import os

os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key-for-testing")

import pytest

from app.utils.file_processors import (
    FileProcessingError,
    _get_extension,
    _process_text,
    _process_csv,
    _rows_to_text,
    generate_upload_prompt,
    process_file,
    validate_file,
)


# ---------------------------------------------------------------------------
# validate_file
# ---------------------------------------------------------------------------


def test_validate_file_valid_txt() -> None:
    validate_file("test.txt", 1000)  # Should not raise


def test_validate_file_valid_docx() -> None:
    validate_file("document.docx", 5_000_000)


def test_validate_file_all_extensions() -> None:
    for ext in (".txt", ".md", ".docx", ".pdf", ".csv", ".xlsx"):
        validate_file(f"file{ext}", 100)


def test_validate_file_too_large() -> None:
    with pytest.raises(FileProcessingError, match="exceeds maximum"):
        validate_file("big.txt", 60_000_000, max_size_mb=50)


def test_validate_file_bad_extension() -> None:
    with pytest.raises(FileProcessingError, match="not allowed"):
        validate_file("virus.exe", 100)


def test_validate_file_no_extension() -> None:
    with pytest.raises(FileProcessingError, match="not allowed"):
        validate_file("noext", 100)


# ---------------------------------------------------------------------------
# _get_extension
# ---------------------------------------------------------------------------


def test_get_extension_normal() -> None:
    assert _get_extension("file.TXT") == ".txt"
    assert _get_extension("doc.DOCX") == ".docx"
    assert _get_extension("data.CSV") == ".csv"


def test_get_extension_no_dot() -> None:
    assert _get_extension("noext") == ""


def test_get_extension_multiple_dots() -> None:
    assert _get_extension("my.file.name.pdf") == ".pdf"


# ---------------------------------------------------------------------------
# _process_text
# ---------------------------------------------------------------------------


def test_process_text_utf8() -> None:
    assert _process_text(b"Hello World") == "Hello World"


def test_process_text_latin1_fallback() -> None:
    # latin-1 bytes that are NOT valid utf-8
    latin_bytes = bytes([0xC0, 0xC1])
    result = _process_text(latin_bytes)
    assert isinstance(result, str)
    assert len(result) == 2


# ---------------------------------------------------------------------------
# _process_csv
# ---------------------------------------------------------------------------


def test_process_csv_basic() -> None:
    content = b"name,age,city\nAlice,30,NYC\nBob,25,LA"
    rows, columns = _process_csv(content)
    assert columns == ["name", "age", "city"]
    assert len(rows) == 2
    assert rows[0]["name"] == "Alice"


def test_process_csv_with_bom() -> None:
    # UTF-8 BOM prefix
    content = b"\xef\xbb\xbfname,value\na,1"
    rows, columns = _process_csv(content)
    assert columns == ["name", "value"]
    assert len(rows) == 1


# ---------------------------------------------------------------------------
# _rows_to_text
# ---------------------------------------------------------------------------


def test_rows_to_text_basic() -> None:
    rows = [{"a": "1", "b": "2"}, {"a": "3", "b": "4"}]
    text = _rows_to_text(rows, ["a", "b"], max_rows=10)
    assert "a | b" in text
    assert "1 | 2" in text
    assert "3 | 4" in text


def test_rows_to_text_truncation() -> None:
    rows = [{"x": str(i)} for i in range(50)]
    text = _rows_to_text(rows, ["x"], max_rows=5)
    assert "45 more rows" in text


# ---------------------------------------------------------------------------
# process_file (async)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_file_txt() -> None:
    result = await process_file("test.txt", b"Hello content")
    assert result["filename"] == "test.txt"
    assert result["file_type"] == ".txt"
    assert result["content_type"] == "text"
    assert result["content"] == "Hello content"
    assert result["data_preview"] is None
    assert result["row_count"] is None


@pytest.mark.asyncio
async def test_process_file_md() -> None:
    result = await process_file("readme.md", b"# Heading\n\nBody text")
    assert result["content_type"] == "text"
    assert "# Heading" in result["content"]


@pytest.mark.asyncio
async def test_process_file_csv() -> None:
    csv_content = b"name,age,city\nAlice,30,NYC\nBob,25,LA"
    result = await process_file("data.csv", csv_content)
    assert result["content_type"] == "data"
    assert result["row_count"] == 2
    assert result["columns"] == ["name", "age", "city"]
    assert result["data_preview"] is not None
    assert "2 rows" in result["data_preview"]


@pytest.mark.asyncio
async def test_process_file_unsupported() -> None:
    with pytest.raises(FileProcessingError, match="Unsupported"):
        await process_file("bad.xyz", b"data")


# ---------------------------------------------------------------------------
# generate_upload_prompt
# ---------------------------------------------------------------------------


def test_generate_prompt_text_file() -> None:
    result = {
        "filename": "test.txt",
        "content_type": "text",
        "content": "Hello world",
        "file_type": ".txt",
    }
    prompt = generate_upload_prompt(result)
    assert "styled HTML document" in prompt
    assert "test.txt" in prompt


def test_generate_prompt_pdf_file() -> None:
    result = {
        "filename": "report.pdf",
        "content_type": "text",
        "content": "PDF content here",
        "file_type": ".pdf",
    }
    prompt = generate_upload_prompt(result)
    assert "professional document" in prompt
    assert "report.pdf" in prompt


def test_generate_prompt_data_file() -> None:
    result = {
        "filename": "data.csv",
        "content_type": "data",
        "content": "col1 | col2\na | b",
        "file_type": ".csv",
        "data_preview": "CSV Data: 10 rows, 2 columns",
    }
    prompt = generate_upload_prompt(result)
    assert "dashboard" in prompt
    assert "data.csv" in prompt


def test_generate_prompt_truncates_long_content() -> None:
    result = {
        "filename": "big.pdf",
        "content_type": "text",
        "content": "x" * 5000,
        "file_type": ".pdf",
    }
    prompt = generate_upload_prompt(result)
    assert "full content provided" in prompt
