# Implementation Plan 006: File Upload and Templates System

## ✅ STATUS: COMPLETE (Plan 006 fully implemented and verified)

- 243/244 tests passing (1 pre-existing failure: test_init_db_creates_file)
- Ruff clean (3 pre-existing warnings in test_database/test_session_service)
- Mypy clean (40 files)
- Frontend: TypeScript clean, Vite build clean

---

## 🚨 ERRATA — 13 DISCREPANCIES (v1 plan vs v2 actual)

> **This plan was written before the v2 rebuild.** The code examples below contain
> v1-era patterns (PostgreSQL, Redis, WebSocket, etc.) that do NOT match the actual
> v2 implementation. The plan was used as a **requirements guide only** — all code
> was rewritten to match v2 architecture during implementation.
>
> **If you are reading this plan for reference, use the discrepancy table below
> to mentally translate every code example you encounter.**

| # | Original Plan (WRONG for v2) | Actual v2 Implementation | Lines Affected |
|---|---|---|---|
| 1 | PostgreSQL + `asyncpg` | **SQLite WAL + `aiosqlite`** | 81, 1248-1249, 1366, 1392-1460 |
| 2 | Redis dependency (`get_redis`, `Depends(get_redis)`) | **No Redis — all state in SQLite** | 6, 286, 295 |
| 3 | WebSocket (`ws://`) | **SSE + HTTP POST** | 9 |
| 4 | `app/api/endpoints/*.py` path structure | **`app/api/*.py` (flat, no endpoints/ subdir)** | 282, 872, 1475, 2282-2283 |
| 5 | `gen_random_uuid()` (PostgreSQL function) | **Python `uuid.uuid4()`** | 1218 |
| 6 | `updated_at` column + SQL triggers | **No `updated_at` column in v2 schema** | 1225, 1231-1235, 1277, 1397, 1443 |
| 7 | `asyncpg.Pool` / `pool.acquire()` | **`async with get_db() as db:` + `cursor = await db.execute()`** | 1392, 1413, 1440, 1460 |
| 8 | `pip install` deps (suggesting not installed) | **All deps pre-installed in `requirements.txt`** | 108, 1292 |
| 9 | SQL migration files (`backend/migrations/*.sql`) | **No migrations — table created in `database.py` SCHEMA** | 1216, 1246, 2267, 2338 |
| 10 | Launch new Playwright per thumbnail | **Reuse `playwright_manager.create_page()` singleton** | ~1303-1350 |
| 11 | `logging.getLogger(__name__)` | **`structlog.get_logger()`** | 287-289, 877-879, 1303-1306, 1370-1372, 1480-1482 |
| 12 | Separate `FileUpload` React component | **Integrated into existing `ChatInput.tsx`** | 438-590, 2255, 2292 |
| 13 | `RETURNING` clause in SQL (PostgreSQL) | **SQLite: use `cursor.lastrowid` or re-SELECT** | 1397 |

### Additional v2 Implementation Notes (not in original plan)
- **Lazy imports** in API endpoint functions (same pattern as `chat.py`). Tests must patch at SOURCE module, not consumer module.
- **`onSelectCustomTemplate`** passes `(templateId, templateName)` not `(htmlContent, templateName)` — HTML fetched on demand via `getCustomTemplate()`.
- **PromptLibraryModal** maps backend `prompt_template` field → frontend `template` field for `PromptTemplate` compatibility.
- **`template_service.py`** uses singleton pattern: `template_service = TemplateService()`.
- **Playwright thumbnail** gracefully returns `None` if Playwright not initialized (no crash).
- **`from-template` endpoint** at `POST /api/sessions/{session_id}/documents/from-template` (not in original plan).

---

## ⚠️ STOP - READ BEFORE STARTING

**DO NOT proceed until you have:**
- [x] Completed Plan 001 (Backend Foundation) - SQLite, session management, health checks
- [x] Completed Plan 004 (Frontend Foundation) - React setup, routing, chat interface
- [x] Verified backend is running and accepting requests
- [x] Verified frontend can connect via SSE
- [x] Read this ENTIRE document top to bottom
- [x] Understood the different flows: file upload → context injection vs template selection → document creation

**Estimated Time**: 3-4 days
**Complexity**: Medium-High (file processing, thumbnail generation, dual template flows)

---

## Context & Rationale

### What We're Building
A comprehensive file upload and template system that enables:
1. **File Upload Pipeline**: Users upload .docx, .pdf, .txt, .md, .csv, .xlsx files (up to 50MB), content is extracted and fed to Claude as context
2. **Smart Starter Prompts**: 6-8 built-in template cards with pre-filled prompts and placeholders for common document types
3. **Custom Templates**: Save generated HTML as reusable templates with auto-generated thumbnails
4. **Dual Template Flows**:
   - Built-in templates → fill chat input with prompt → user customizes → Claude generates
   - Custom templates → spawn new document with pre-loaded HTML → user iterates via chat

### Why This Matters
- **Reduces friction**: Users don't start from blank slate
- **Content reuse**: Upload existing documents and transform them into styled HTML
- **Data visualization**: Upload .csv/.xlsx and auto-suggest dashboard creation
- **Template library**: Organization-wide template sharing and reuse
- **Faster onboarding**: New users see examples immediately

### Architecture Decision
```
File Upload Flow:
User selects file → Frontend uploads → Backend extracts content → Returns text/data →
Frontend auto-fills chat: "Create document from: [content]" → Claude generates HTML

Built-in Template Flow:
User clicks template card → Prompt with [placeholders] fills chat input →
User customizes placeholders → Sends → Claude generates HTML

Custom Template Flow:
User clicks "Save as Template" → Backend stores HTML + generates thumbnail →
User clicks custom template → Backend spawns new session with template HTML pre-loaded →
User iterates via chat
```

---

## Strict Implementation Rules

### Database Schema Requirements
- [ ] Create `templates` table with columns: id (UUID), name (VARCHAR 200), description (TEXT), html_content (TEXT), thumbnail_base64 (TEXT), created_by (VARCHAR 100), created_at (TIMESTAMP)
- [ ] Add index on `created_by` for fast user template lookups
- [ ] Add index on `created_at` for sorting
- [ ] Store built-in templates as seed data with `created_by = 'system'`

### File Upload Rules
- [ ] Maximum file size: 50MB (52,428,800 bytes)
- [ ] Allowed extensions: .docx, .pdf, .txt, .md, .csv, .xlsx
- [ ] Use python-multipart for form data handling
- [ ] File validation BEFORE processing (extension + MIME type check)
- [ ] Extract text content for document files (.docx, .pdf, .txt, .md)
- [ ] Parse structured data for data files (.csv, .xlsx) → return as list of dicts
- [ ] Return JSON: `{"filename": str, "content": str, "content_type": "text|data", "data_structure": dict|null}`

### File Processing Dependencies
- [ ] Install: `python-docx`, `PyPDF2`, `openpyxl`
- [ ] For .docx: extract all paragraphs and table text
- [ ] For .pdf: extract text from all pages, handle encoding
- [ ] For .csv: parse with csv.DictReader, return list of dicts
- [ ] For .xlsx: read first sheet by default, include sheet names, return structured data

### Template System Rules
- [ ] Built-in templates stored in `backend/app/config/builtin_templates.json`
- [ ] Built-in template format: `{"id": str, "name": str, "description": str, "prompt_template": str, "category": str, "thumbnail": str}`
- [ ] Custom templates stored in SQLite `templates` table *(ERRATA: plan said PostgreSQL — see discrepancy #1)*
- [ ] Thumbnail generation via Playwright screenshot (1200x800 viewport, scale to 400x300)
- [ ] Thumbnail stored as base64 PNG data URI
- [ ] Template HTML must be valid, complete HTML documents (<!DOCTYPE html>...)

### Frontend Template UI Rules
- [ ] Show template cards ONLY when session has no messages (empty state)
- [ ] Template card layout: 2-column grid on desktop, 1-column on mobile
- [ ] Each card shows: thumbnail, name, description, category badge
- [ ] Built-in templates have distinct visual marker (e.g., "Starter Template" badge)
- [ ] Custom templates have "Delete" button (only for owner)
- [ ] Clicking built-in template → fills chat input with prompt
- [ ] Clicking custom template → API call to spawn document from template

### Auto-Detection Rules
- [ ] If uploaded file is .csv or .xlsx → auto-inject prompt: "Create an interactive dashboard from this data: [data preview]"
- [ ] If uploaded file is .txt or .md → auto-inject prompt: "Create a styled HTML document from this content: [text preview]"
- [ ] If uploaded file is .docx or .pdf → auto-inject prompt: "Create a professional document from this content: [text preview]"
- [ ] Truncate preview to 500 characters with "... [full content provided to AI]" suffix

---

## Phase 1: File Upload Backend (Day 1)

### Step 1.1: Install Dependencies
```bash
cd c:\Users\cchen362\OneDrive\Desktop\AI-HTML-Builder\backend
pip install python-multipart python-docx PyPDF2 openpyxl
pip freeze > requirements.txt
```

### Step 1.2: Create File Processing Utilities
```python
# backend/app/utils/file_processors.py
import csv
import io
from typing import Dict, Any, List, Optional
from docx import Document
from PyPDF2 import PdfReader
from openpyxl import load_workbook

class FileProcessor:
    """Unified file processing for multiple file types."""

    MAX_FILE_SIZE = 52_428_800  # 50MB
    ALLOWED_EXTENSIONS = {'.txt', '.md', '.docx', '.pdf', '.csv', '.xlsx'}

    @staticmethod
    def validate_file(filename: str, file_size: int) -> tuple[bool, Optional[str]]:
        """Validate file extension and size."""
        if file_size > FileProcessor.MAX_FILE_SIZE:
            return False, f"File size {file_size} bytes exceeds maximum of 50MB"

        ext = '.' + filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        if ext not in FileProcessor.ALLOWED_EXTENSIONS:
            return False, f"File type {ext} not allowed. Allowed: {FileProcessor.ALLOWED_EXTENSIONS}"

        return True, None

    @staticmethod
    async def process_text_file(content: bytes) -> str:
        """Process .txt or .md files."""
        try:
            return content.decode('utf-8')
        except UnicodeDecodeError:
            # Fallback to latin-1 if utf-8 fails
            return content.decode('latin-1')

    @staticmethod
    async def process_docx_file(content: bytes) -> str:
        """Extract text from .docx file."""
        doc = Document(io.BytesIO(content))

        # Extract paragraphs
        paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]

        # Extract tables
        tables_text = []
        for table in doc.tables:
            for row in table.rows:
                row_text = ' | '.join(cell.text.strip() for cell in row.cells)
                if row_text.strip():
                    tables_text.append(row_text)

        # Combine all text
        all_text = '\n\n'.join(paragraphs)
        if tables_text:
            all_text += '\n\n--- Tables ---\n' + '\n'.join(tables_text)

        return all_text

    @staticmethod
    async def process_pdf_file(content: bytes) -> str:
        """Extract text from .pdf file."""
        reader = PdfReader(io.BytesIO(content))

        text_parts = []
        for page_num, page in enumerate(reader.pages, 1):
            page_text = page.extract_text()
            if page_text.strip():
                text_parts.append(f"--- Page {page_num} ---\n{page_text}")

        return '\n\n'.join(text_parts)

    @staticmethod
    async def process_csv_file(content: bytes) -> Dict[str, Any]:
        """Parse .csv file into structured data."""
        text = content.decode('utf-8-sig')  # Handle BOM
        reader = csv.DictReader(io.StringIO(text))

        rows = list(reader)

        return {
            'type': 'csv',
            'rows': rows,
            'columns': list(rows[0].keys()) if rows else [],
            'row_count': len(rows)
        }

    @staticmethod
    async def process_xlsx_file(content: bytes) -> Dict[str, Any]:
        """Parse .xlsx file into structured data."""
        wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)

        # Read first sheet by default
        sheet = wb.active
        sheet_name = sheet.title

        # Get headers from first row
        headers = []
        for cell in sheet[1]:
            headers.append(str(cell.value) if cell.value is not None else '')

        # Get data rows
        rows = []
        for row in sheet.iter_rows(min_row=2, values_only=True):
            row_dict = {}
            for header, value in zip(headers, row):
                row_dict[header] = str(value) if value is not None else ''
            rows.append(row_dict)

        return {
            'type': 'xlsx',
            'sheet_name': sheet_name,
            'rows': rows,
            'columns': headers,
            'row_count': len(rows),
            'available_sheets': wb.sheetnames
        }


async def process_uploaded_file(filename: str, content: bytes) -> Dict[str, Any]:
    """
    Main entry point for file processing.
    Returns standardized response with content and metadata.
    """
    # Validate file
    is_valid, error_msg = FileProcessor.validate_file(filename, len(content))
    if not is_valid:
        raise ValueError(error_msg)

    # Determine file type
    ext = '.' + filename.rsplit('.', 1)[-1].lower()

    result = {
        'filename': filename,
        'file_type': ext,
        'content_type': 'text',  # or 'data'
        'content': None,
        'data_structure': None
    }

    # Process based on file type
    if ext in {'.txt', '.md'}:
        result['content'] = await FileProcessor.process_text_file(content)

    elif ext == '.docx':
        result['content'] = await FileProcessor.process_docx_file(content)

    elif ext == '.pdf':
        result['content'] = await FileProcessor.process_pdf_file(content)

    elif ext == '.csv':
        result['content_type'] = 'data'
        result['data_structure'] = await FileProcessor.process_csv_file(content)
        # Create text preview
        data = result['data_structure']
        result['content'] = f"CSV Data: {data['row_count']} rows, {len(data['columns'])} columns\nColumns: {', '.join(data['columns'])}"

    elif ext == '.xlsx':
        result['content_type'] = 'data'
        result['data_structure'] = await FileProcessor.process_xlsx_file(content)
        # Create text preview
        data = result['data_structure']
        result['content'] = f"Excel Data: {data['row_count']} rows, {len(data['columns'])} columns\nSheet: {data['sheet_name']}\nColumns: {', '.join(data['columns'])}"

    return result
```

### Step 1.3: Create Upload Endpoint
```python
# backend/app/api/endpoints/upload.py
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from typing import Dict, Any
from app.utils.file_processors import process_uploaded_file
from app.core.redis_manager import get_redis
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    redis=Depends(get_redis)
) -> Dict[str, Any]:
    """
    Upload and process a file.

    Accepts: .txt, .md, .docx, .pdf, .csv, .xlsx (max 50MB)
    Returns: Extracted content/data structure
    """
    try:
        logger.info(f"Receiving file upload: {file.filename}, type: {file.content_type}")

        # Read file content
        content = await file.read()

        # Process file
        result = await process_uploaded_file(file.filename, content)

        logger.info(f"File processed successfully: {file.filename}, content_type: {result['content_type']}")

        return {
            'success': True,
            'data': result
        }

    except ValueError as e:
        logger.warning(f"File validation failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"File processing error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process file: {str(e)}"
        )
```

### Step 1.4: Register Upload Endpoint
```python
# backend/app/main.py (add to existing file)
from app.api.endpoints import upload

# In create_application() function, after other routers:
app.include_router(upload.router, prefix="/api", tags=["upload"])
```

### Step 1.5: Test File Upload Endpoint
```bash
# Test with curl (from backend directory)
# Create test files first
echo "Test content for HTML generation" > test.txt

# Upload text file
curl -X POST "http://localhost:8000/api/upload" \
  -F "file=@test.txt"

# Expected response:
# {
#   "success": true,
#   "data": {
#     "filename": "test.txt",
#     "file_type": ".txt",
#     "content_type": "text",
#     "content": "Test content for HTML generation",
#     "data_structure": null
#   }
# }
```

**Checkpoint**: File upload backend complete. Verify all file types process correctly before proceeding.

---

## Phase 2: File Upload Frontend (Day 1-2)

### Step 2.1: Create Upload Service
```typescript
// frontend/src/services/uploadService.ts
export interface UploadResponse {
  success: boolean;
  data: {
    filename: string;
    file_type: string;
    content_type: 'text' | 'data';
    content: string;
    data_structure?: {
      type: 'csv' | 'xlsx';
      rows: Array<Record<string, string>>;
      columns: string[];
      row_count: number;
      sheet_name?: string;
      available_sheets?: string[];
    };
  };
}

export const uploadFile = async (file: File): Promise<UploadResponse> => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch('/api/upload', {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Upload failed');
  }

  return response.json();
};

export const generatePromptFromUpload = (uploadData: UploadResponse['data']): string => {
  const { filename, content_type, content, data_structure } = uploadData;

  // Create preview (first 500 chars)
  const preview = content.length > 500
    ? content.substring(0, 500) + '... [full content provided to AI]'
    : content;

  // Different prompts based on content type
  if (content_type === 'data') {
    const dataInfo = data_structure!;
    return `Create an interactive dashboard from this data:\n\nFile: ${filename}\nRows: ${dataInfo.row_count}\nColumns: ${dataInfo.columns.join(', ')}\n\n${preview}`;
  }

  // Text content
  const ext = filename.split('.').pop()?.toLowerCase();

  if (ext === 'txt' || ext === 'md') {
    return `Create a styled HTML document from this content:\n\nFile: ${filename}\n\n${preview}`;
  }

  if (ext === 'docx' || ext === 'pdf') {
    return `Create a professional document from this content:\n\nFile: ${filename}\n\n${preview}`;
  }

  return `Create a document from this content:\n\nFile: ${filename}\n\n${preview}`;
};
```

### Step 2.2: Create File Upload Component
```typescript
// frontend/src/components/FileUpload.tsx
import React, { useRef, useState } from 'react';
import { uploadFile, generatePromptFromUpload, UploadResponse } from '../services/uploadService';

interface FileUploadProps {
  onFileProcessed: (prompt: string, uploadData: UploadResponse['data']) => void;
}

export const FileUpload: React.FC<FileUploadProps> = ({ onFileProcessed }) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileSelect = async (file: File) => {
    setError(null);
    setIsUploading(true);

    try {
      const result = await uploadFile(file);
      const prompt = generatePromptFromUpload(result.data);
      onFileProcessed(prompt, result.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const file = e.dataTransfer.files[0];
    if (file) {
      handleFileSelect(file);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFileSelect(file);
    }
  };

  return (
    <div className="file-upload-container">
      <div
        className={`file-upload-zone ${isDragging ? 'dragging' : ''} ${isUploading ? 'uploading' : ''}`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={handleClick}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".txt,.md,.docx,.pdf,.csv,.xlsx"
          onChange={handleInputChange}
          style={{ display: 'none' }}
        />

        {isUploading ? (
          <div className="upload-status">
            <div className="spinner"></div>
            <p>Processing file...</p>
          </div>
        ) : (
          <>
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
              <path d="M7 18a4.6 4.4 0 0 1 0 -9a5 4.5 0 0 1 11 2h1a3.5 3.5 0 0 1 0 7h-1" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M9 15l3 -3l3 3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M12 12l0 9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            <p className="upload-text">Drop file here or click to browse</p>
            <p className="upload-hint">Supports: .txt, .md, .docx, .pdf, .csv, .xlsx (max 50MB)</p>
          </>
        )}
      </div>

      {error && (
        <div className="upload-error">
          <span className="error-icon">⚠</span>
          {error}
        </div>
      )}
    </div>
  );
};
```

### Step 2.3: Update Chat Input Component
```typescript
// frontend/src/components/ChatInput.tsx (update existing component)
import React, { useState, useRef } from 'react';
import { FileUpload } from './FileUpload';
import { UploadResponse } from '../services/uploadService';

interface ChatInputProps {
  onSendMessage: (message: string, uploadData?: UploadResponse['data']) => void;
  disabled?: boolean;
}

export const ChatInput: React.FC<ChatInputProps> = ({ onSendMessage, disabled }) => {
  const [message, setMessage] = useState('');
  const [showUpload, setShowUpload] = useState(false);
  const [uploadData, setUploadData] = useState<UploadResponse['data'] | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleFileProcessed = (prompt: string, data: UploadResponse['data']) => {
    setMessage(prompt);
    setUploadData(data);
    setShowUpload(false);
    // Focus textarea for user to review/edit prompt
    textareaRef.current?.focus();
  };

  const handleSend = () => {
    if (message.trim()) {
      onSendMessage(message, uploadData || undefined);
      setMessage('');
      setUploadData(null);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chat-input-container">
      {showUpload && (
        <div className="upload-modal">
          <div className="upload-modal-content">
            <button className="close-btn" onClick={() => setShowUpload(false)}>×</button>
            <FileUpload onFileProcessed={handleFileProcessed} />
          </div>
        </div>
      )}

      <div className="input-wrapper">
        <button
          className="upload-btn"
          onClick={() => setShowUpload(true)}
          disabled={disabled}
          title="Upload file"
        >
          📎
        </button>

        <textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Describe the document you want to create..."
          disabled={disabled}
          rows={3}
        />

        <button
          className="send-btn"
          onClick={handleSend}
          disabled={disabled || !message.trim()}
        >
          Send
        </button>
      </div>

      {uploadData && (
        <div className="upload-indicator">
          <span className="file-icon">📄</span>
          {uploadData.filename}
          <button onClick={() => setUploadData(null)}>×</button>
        </div>
      )}
    </div>
  );
};
```

### Step 2.4: Add Upload Styles
```css
/* frontend/src/styles/upload.css */
.file-upload-container {
  padding: 1rem;
}

.file-upload-zone {
  border: 2px dashed #A7A8AA;
  border-radius: 8px;
  padding: 3rem 2rem;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  background: #FFFFFF;
}

.file-upload-zone:hover {
  border-color: #006FCF;
  background: #F6F0FA;
}

.file-upload-zone.dragging {
  border-color: #006FCF;
  background: #B4EEFF;
  transform: scale(1.02);
}

.file-upload-zone.uploading {
  cursor: not-allowed;
  opacity: 0.7;
}

.file-upload-zone svg {
  color: #006FCF;
  margin-bottom: 1rem;
}

.upload-text {
  font-size: 1rem;
  font-weight: 600;
  color: #152835;
  margin: 0.5rem 0;
}

.upload-hint {
  font-size: 0.875rem;
  color: #A7A8AA;
  margin: 0;
}

.upload-status {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #F6F0FA;
  border-top-color: #006FCF;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.upload-error {
  margin-top: 1rem;
  padding: 0.75rem;
  background: #FFE6E6;
  border: 1px solid #FF4444;
  border-radius: 4px;
  color: #CC0000;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.upload-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.upload-modal-content {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  max-width: 600px;
  width: 90%;
  position: relative;
}

.close-btn {
  position: absolute;
  top: 1rem;
  right: 1rem;
  background: none;
  border: none;
  font-size: 2rem;
  cursor: pointer;
  color: #A7A8AA;
  line-height: 1;
}

.close-btn:hover {
  color: #152835;
}

.upload-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  background: #F6F0FA;
  border-radius: 4px;
  margin-top: 0.5rem;
  font-size: 0.875rem;
}

.upload-indicator button {
  margin-left: auto;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.25rem;
  color: #A7A8AA;
}

.upload-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0.5rem;
}

.upload-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
```

**Checkpoint**: File upload frontend complete. Test uploading various file types and verify prompts are auto-filled correctly.

---

## Phase 3: Smart Starter Prompts (Day 2)

### Step 3.1: Create Built-in Templates Config
```json
// backend/app/config/builtin_templates.json
{
  "templates": [
    {
      "id": "impact-assessment",
      "name": "Impact Assessment Report",
      "description": "Professional report with problem analysis, solutions, risks, and recommendations",
      "category": "Business",
      "prompt_template": "Create an impact assessment report for [topic] covering problem statement, technical solutions with pros/cons, risk analysis, and final recommendations. Use tabbed navigation and professional styling.",
      "thumbnail": "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjMwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iNDAwIiBoZWlnaHQ9IjMwMCIgZmlsbD0iIzAwMTc1QSIvPjx0ZXh0IHg9IjIwMCIgeT0iMTUwIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMjQiIGZpbGw9IndoaXRlIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIj5JbXBhY3QgQXNzZXNzbWVudDwvdGV4dD48L3N2Zz4="
    },
    {
      "id": "technical-docs",
      "name": "Technical Documentation",
      "description": "Clean documentation site with sidebar navigation and code examples",
      "category": "Technical",
      "prompt_template": "Create technical documentation for [system/feature] with overview, architecture diagram, setup guide, API reference, and troubleshooting section. Include sidebar navigation and code syntax highlighting.",
      "thumbnail": "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjMwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iNDAwIiBoZWlnaHQ9IjMwMCIgZmlsbD0iIzAwNkZDRiIvPjx0ZXh0IHg9IjIwMCIgeT0iMTUwIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMjQiIGZpbGw9IndoaXRlIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIj5UZWNobmljYWwgRG9jczwvdGV4dD48L3N2Zz4="
    },
    {
      "id": "business-dashboard",
      "name": "Business Dashboard",
      "description": "Interactive dashboard with charts, KPI cards, and trend analysis",
      "category": "Data",
      "prompt_template": "Create an interactive business dashboard showing [metrics/KPIs] with summary cards, charts (bar, line, pie), trend indicators, and data tables. Use modern card-based layout with responsive grid.",
      "thumbnail": "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjMwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iNDAwIiBoZWlnaHQ9IjMwMCIgZmlsbD0iIzY2QTlFMiIvPjx0ZXh0IHg9IjIwMCIgeT0iMTUwIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMjQiIGZpbGw9IndoaXRlIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIj5EYXNoYm9hcmQ8L3RleHQ+PC9zdmc+"
    },
    {
      "id": "project-report",
      "name": "Project Status Report",
      "description": "Structured report with milestones, risks, team updates, and next steps",
      "category": "Business",
      "prompt_template": "Create a project status report for [project name] including executive summary, milestones with progress bars, risk register, team updates, budget overview, and next steps timeline.",
      "thumbnail": "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjMwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iNDAwIiBoZWlnaHQ9IjMwMCIgZmlsbD0iIzE1MjgzNSIvPjx0ZXh0IHg9IjIwMCIgeT0iMTUwIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMjQiIGZpbGw9IndoaXRlIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIj5Qcm9qZWN0IFJlcG9ydDwvdGV4dD48L3N2Zz4="
    },
    {
      "id": "process-guide",
      "name": "Process Documentation",
      "description": "Step-by-step guide with flowcharts, decision points, and responsibilities",
      "category": "Operations",
      "prompt_template": "Create a step-by-step process guide for [process name] with flowchart visualization, decision points, role responsibilities, estimated timelines, and best practices. Use numbered steps and visual indicators.",
      "thumbnail": "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjMwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iNDAwIiBoZWlnaHQ9IjMwMCIgZmlsbD0iIzAwNjQ2OSIvPjx0ZXh0IHg9IjIwMCIgeT0iMTUwIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMjQiIGZpbGw9IndoaXRlIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIj5Qcm9jZXNzIEd1aWRlPC90ZXh0Pjwvc3ZnPg=="
    },
    {
      "id": "presentation",
      "name": "Presentation Slides",
      "description": "Clean slide presentation with navigation and professional styling",
      "category": "Presentation",
      "prompt_template": "Create a slide presentation about [topic] with title slide, agenda, 5-7 content slides covering key points, visual aids, and summary/Q&A slide. Include slide navigation and modern design.",
      "thumbnail": "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjMwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iNDAwIiBoZWlnaHQ9IjMwMCIgZmlsbD0iI0ZGQjkwMCIvPjx0ZXh0IHg9IjIwMCIgeT0iMTUwIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMjQiIGZpbGw9IiMxNTI4MzUiIHRleHQtYW5jaG9yPSJtaWRkbGUiPlByZXNlbnRhdGlvbjwvdGV4dD48L3N2Zz4="
    },
    {
      "id": "meeting-notes",
      "name": "Meeting Notes",
      "description": "Structured meeting notes with attendees, agenda, decisions, and action items",
      "category": "Business",
      "prompt_template": "Create meeting notes for [meeting name] including date/time, attendees, agenda items, discussion summary, key decisions, action items with owners and due dates, and next meeting schedule.",
      "thumbnail": "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjMwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iNDAwIiBoZWlnaHQ9IjMwMCIgZmlsbD0iI0I0RUVGRiIvPjx0ZXh0IHg9IjIwMCIgeT0iMTUwIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMjQiIGZpbGw9IiMxNTI4MzUiIHRleHQtYW5jaG9yPSJtaWRkbGUiPk1lZXRpbmcgTm90ZXM8L3RleHQ+PC9zdmc+"
    },
    {
      "id": "data-report",
      "name": "Data Analysis Report",
      "description": "Comprehensive data analysis with visualizations, insights, and recommendations",
      "category": "Data",
      "prompt_template": "Create a data analysis report for [dataset/topic] with executive summary, data overview, statistical analysis, visualizations (charts/graphs), key insights, trends, and actionable recommendations.",
      "thumbnail": "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjMwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iNDAwIiBoZWlnaHQ9IjMwMCIgZmlsbD0iIzI4Q0Q2RSIvPjx0ZXh0IHg9IjIwMCIgeT0iMTUwIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMjQiIGZpbGw9IndoaXRlIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIj5EYXRhIEFuYWx5c2lzPC90ZXh0Pjwvc3ZnPg=="
    }
  ]
}
```

### Step 3.2: Create Templates API Endpoint
```python
# backend/app/api/endpoints/templates.py
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Load built-in templates
TEMPLATES_FILE = Path(__file__).parent.parent.parent / "config" / "builtin_templates.json"

def load_builtin_templates() -> List[Dict[str, Any]]:
    """Load built-in templates from JSON file."""
    try:
        with open(TEMPLATES_FILE, 'r') as f:
            data = json.load(f)
            return data['templates']
    except Exception as e:
        logger.error(f"Failed to load built-in templates: {e}")
        return []

@router.get("/templates/builtin")
async def get_builtin_templates() -> Dict[str, Any]:
    """Get all built-in starter prompt templates."""
    templates = load_builtin_templates()

    return {
        'success': True,
        'data': {
            'templates': templates,
            'count': len(templates)
        }
    }

@router.get("/templates/builtin/{template_id}")
async def get_builtin_template(template_id: str) -> Dict[str, Any]:
    """Get a specific built-in template by ID."""
    templates = load_builtin_templates()

    template = next((t for t in templates if t['id'] == template_id), None)

    if not template:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")

    return {
        'success': True,
        'data': template
    }
```

### Step 3.3: Register Templates Endpoint
```python
# backend/app/main.py (add to existing file)
from app.api.endpoints import templates

# In create_application() function:
app.include_router(templates.router, prefix="/api", tags=["templates"])
```

### Step 3.4: Create Template Cards Component
```typescript
// frontend/src/components/TemplateCards.tsx
import React, { useEffect, useState } from 'react';

interface Template {
  id: string;
  name: string;
  description: string;
  category: string;
  prompt_template: string;
  thumbnail: string;
}

interface TemplateCardsProps {
  onSelectTemplate: (prompt: string) => void;
}

export const TemplateCards: React.FC<TemplateCardsProps> = ({ onSelectTemplate }) => {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchTemplates();
  }, []);

  const fetchTemplates = async () => {
    try {
      const response = await fetch('/api/templates/builtin');
      const data = await response.json();

      if (data.success) {
        setTemplates(data.data.templates);
      } else {
        setError('Failed to load templates');
      }
    } catch (err) {
      setError('Failed to fetch templates');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleTemplateClick = (template: Template) => {
    onSelectTemplate(template.prompt_template);
  };

  if (loading) {
    return (
      <div className="templates-loading">
        <div className="spinner"></div>
        <p>Loading templates...</p>
      </div>
    );
  }

  if (error) {
    return <div className="templates-error">{error}</div>;
  }

  // Group templates by category
  const categories = Array.from(new Set(templates.map(t => t.category)));

  return (
    <div className="templates-container">
      <div className="templates-header">
        <h2>Start with a Template</h2>
        <p>Choose a template to get started, then customize it for your needs</p>
      </div>

      {categories.map(category => (
        <div key={category} className="template-category">
          <h3 className="category-title">{category}</h3>
          <div className="templates-grid">
            {templates
              .filter(t => t.category === category)
              .map(template => (
                <div
                  key={template.id}
                  className="template-card"
                  onClick={() => handleTemplateClick(template)}
                >
                  <div className="template-thumbnail">
                    <img src={template.thumbnail} alt={template.name} />
                    <div className="template-badge">Starter Template</div>
                  </div>
                  <div className="template-info">
                    <h4>{template.name}</h4>
                    <p>{template.description}</p>
                  </div>
                </div>
              ))}
          </div>
        </div>
      ))}
    </div>
  );
};
```

### Step 3.5: Integrate Templates into Chat Page
```typescript
// frontend/src/pages/ChatPage.tsx (update existing component)
import React, { useState, useEffect } from 'react';
import { TemplateCards } from '../components/TemplateCards';
import { ChatInput } from '../components/ChatInput';

export const ChatPage: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');

  const showTemplates = messages.length === 0;

  const handleTemplateSelect = (prompt: string) => {
    // Fill chat input with template prompt
    setInputValue(prompt);
    // Optionally auto-focus the input
    // Focus logic handled by ChatInput component
  };

  const handleSendMessage = (message: string, uploadData?: any) => {
    // Existing message sending logic
    // ...
    setInputValue(''); // Clear input after sending
  };

  return (
    <div className="chat-page">
      <div className="chat-messages">
        {showTemplates ? (
          <TemplateCards onSelectTemplate={handleTemplateSelect} />
        ) : (
          // Existing message rendering
          messages.map(msg => <MessageBubble key={msg.id} message={msg} />)
        )}
      </div>

      <ChatInput
        value={inputValue}
        onChange={setInputValue}
        onSendMessage={handleSendMessage}
      />
    </div>
  );
};
```

### Step 3.6: Add Template Styles
```css
/* frontend/src/styles/templates.css */
.templates-container {
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
}

.templates-header {
  text-align: center;
  margin-bottom: 3rem;
}

.templates-header h2 {
  font-size: 2rem;
  color: #152835;
  margin-bottom: 0.5rem;
}

.templates-header p {
  font-size: 1rem;
  color: #A7A8AA;
}

.template-category {
  margin-bottom: 3rem;
}

.category-title {
  font-size: 1.25rem;
  color: #00175A;
  margin-bottom: 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid #B4EEFF;
}

.templates-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1.5rem;
}

.template-card {
  background: white;
  border: 1px solid #E0E0E0;
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.3s ease;
}

.template-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 23, 90, 0.15);
  border-color: #006FCF;
}

.template-thumbnail {
  position: relative;
  width: 100%;
  height: 200px;
  overflow: hidden;
  background: #F6F0FA;
}

.template-thumbnail img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.template-badge {
  position: absolute;
  top: 0.75rem;
  right: 0.75rem;
  background: #FFB900;
  color: #152835;
  padding: 0.25rem 0.75rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
}

.template-info {
  padding: 1.5rem;
}

.template-info h4 {
  font-size: 1.125rem;
  color: #152835;
  margin: 0 0 0.5rem 0;
}

.template-info p {
  font-size: 0.875rem;
  color: #A7A8AA;
  margin: 0;
  line-height: 1.5;
}

.templates-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 2rem;
}

.templates-error {
  text-align: center;
  padding: 2rem;
  color: #CC0000;
  background: #FFE6E6;
  border: 1px solid #FF4444;
  border-radius: 8px;
  margin: 2rem;
}

@media (max-width: 768px) {
  .templates-grid {
    grid-template-columns: 1fr;
  }
}
```

**Checkpoint**: Smart starter prompts complete. Verify templates load, cards render correctly, and clicking a template fills the chat input.

---

## Phase 4: Custom Templates - Backend (Day 3)

### Step 4.1: Create Database Schema
```sql
-- backend/migrations/005_create_templates_table.sql
CREATE TABLE IF NOT EXISTS templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    html_content TEXT NOT NULL,
    thumbnail_base64 TEXT,
    created_by VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_templates_created_by ON templates(created_by);
CREATE INDEX idx_templates_created_at ON templates(created_at DESC);

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_templates_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER templates_updated_at
    BEFORE UPDATE ON templates
    FOR EACH ROW
    EXECUTE FUNCTION update_templates_updated_at();
```

### Step 4.2: Run Migration
```bash
# If using PostgreSQL
psql -U postgres -d ai_html_builder -f backend/migrations/005_create_templates_table.sql

# Or add to your migration tool
```

### Step 4.3: Create Template Models
```python
# backend/app/models/template.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid

class TemplateCreate(BaseModel):
    """Request model for creating a custom template."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    html_content: str = Field(..., min_length=1)

class TemplateResponse(BaseModel):
    """Response model for template data."""
    id: str
    name: str
    description: Optional[str]
    html_content: str
    thumbnail_base64: Optional[str]
    created_by: str
    created_at: datetime
    updated_at: datetime

class TemplateListItem(BaseModel):
    """Lightweight template model for list views."""
    id: str
    name: str
    description: Optional[str]
    thumbnail_base64: Optional[str]
    created_by: str
    created_at: datetime
```

### Step 4.4: Install Playwright for Thumbnails
```bash
cd c:\Users\cchen362\OneDrive\Desktop\AI-HTML-Builder\backend
pip install playwright
playwright install chromium
pip freeze > requirements.txt
```

### Step 4.5: Create Thumbnail Generator
```python
# backend/app/utils/thumbnail_generator.py
import asyncio
import base64
from playwright.async_api import async_playwright
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class ThumbnailGenerator:
    """Generate thumbnails from HTML content using Playwright."""

    VIEWPORT_WIDTH = 1200
    VIEWPORT_HEIGHT = 800
    THUMBNAIL_WIDTH = 400
    THUMBNAIL_HEIGHT = 300

    @staticmethod
    async def generate_thumbnail(html_content: str) -> Optional[str]:
        """
        Generate a thumbnail from HTML content.
        Returns base64-encoded PNG data URI.
        """
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page(
                    viewport={'width': ThumbnailGenerator.VIEWPORT_WIDTH,
                             'height': ThumbnailGenerator.VIEWPORT_HEIGHT}
                )

                # Set content and wait for it to render
                await page.set_content(html_content, wait_until='networkidle')

                # Wait a bit for any animations or dynamic content
                await asyncio.sleep(0.5)

                # Take screenshot
                screenshot_bytes = await page.screenshot(
                    type='png',
                    clip={
                        'x': 0,
                        'y': 0,
                        'width': ThumbnailGenerator.VIEWPORT_WIDTH,
                        'height': ThumbnailGenerator.VIEWPORT_HEIGHT
                    }
                )

                await browser.close()

                # Convert to base64 data URI
                base64_image = base64.b64encode(screenshot_bytes).decode('utf-8')
                data_uri = f"data:image/png;base64,{base64_image}"

                logger.info("Thumbnail generated successfully")
                return data_uri

        except Exception as e:
            logger.error(f"Failed to generate thumbnail: {e}", exc_info=True)
            return None
```

### Step 4.6: Create Templates CRUD Service
```python
# backend/app/services/template_service.py
from typing import List, Optional
from uuid import UUID
import asyncpg
from app.models.template import TemplateCreate, TemplateResponse, TemplateListItem
from app.utils.thumbnail_generator import ThumbnailGenerator
from app.core.database import get_db_pool
import logging

logger = logging.getLogger(__name__)

class TemplateService:
    """Service for managing custom templates."""

    @staticmethod
    async def create_template(
        template_data: TemplateCreate,
        created_by: str,
        generate_thumbnail: bool = True
    ) -> TemplateResponse:
        """Create a new custom template."""
        pool = await get_db_pool()

        # Generate thumbnail if requested
        thumbnail = None
        if generate_thumbnail:
            thumbnail = await ThumbnailGenerator.generate_thumbnail(template_data.html_content)

        # Insert into database
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO templates (name, description, html_content, thumbnail_base64, created_by)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id, name, description, html_content, thumbnail_base64, created_by, created_at, updated_at
                """,
                template_data.name,
                template_data.description,
                template_data.html_content,
                thumbnail,
                created_by
            )

        return TemplateResponse(**dict(row))

    @staticmethod
    async def get_templates(created_by: Optional[str] = None) -> List[TemplateListItem]:
        """Get all templates, optionally filtered by creator."""
        pool = await get_db_pool()

        async with pool.acquire() as conn:
            if created_by:
                rows = await conn.fetch(
                    """
                    SELECT id, name, description, thumbnail_base64, created_by, created_at
                    FROM templates
                    WHERE created_by = $1
                    ORDER BY created_at DESC
                    """,
                    created_by
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT id, name, description, thumbnail_base64, created_by, created_at
                    FROM templates
                    ORDER BY created_at DESC
                    """
                )

        return [TemplateListItem(**dict(row)) for row in rows]

    @staticmethod
    async def get_template(template_id: str) -> Optional[TemplateResponse]:
        """Get a specific template by ID."""
        pool = await get_db_pool()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, name, description, html_content, thumbnail_base64, created_by, created_at, updated_at
                FROM templates
                WHERE id = $1
                """,
                template_id
            )

        if not row:
            return None

        return TemplateResponse(**dict(row))

    @staticmethod
    async def delete_template(template_id: str, created_by: str) -> bool:
        """Delete a template (only by creator)."""
        pool = await get_db_pool()

        async with pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM templates
                WHERE id = $1 AND created_by = $2
                """,
                template_id,
                created_by
            )

        return result == "DELETE 1"
```

### Step 4.7: Create Templates CRUD Endpoints
```python
# backend/app/api/endpoints/templates.py (extend existing file)
from fastapi import APIRouter, HTTPException, Header, Depends
from typing import List, Optional
from app.models.template import TemplateCreate, TemplateResponse, TemplateListItem
from app.services.template_service import TemplateService
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# ... existing builtin templates code ...

@router.post("/templates/custom", response_model=TemplateResponse)
async def create_custom_template(
    template_data: TemplateCreate,
    x_remote_user: Optional[str] = Header(None)
) -> TemplateResponse:
    """Create a new custom template."""
    created_by = x_remote_user or "anonymous"

    try:
        template = await TemplateService.create_template(template_data, created_by)
        return template
    except Exception as e:
        logger.error(f"Failed to create template: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/templates/custom", response_model=List[TemplateListItem])
async def get_custom_templates(
    x_remote_user: Optional[str] = Header(None)
) -> List[TemplateListItem]:
    """Get all custom templates for the current user."""
    created_by = x_remote_user or "anonymous"

    try:
        templates = await TemplateService.get_templates(created_by)
        return templates
    except Exception as e:
        logger.error(f"Failed to fetch templates: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/templates/custom/{template_id}", response_model=TemplateResponse)
async def get_custom_template(template_id: str) -> TemplateResponse:
    """Get a specific custom template."""
    try:
        template = await TemplateService.get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        return template
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch template: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/templates/custom/{template_id}")
async def delete_custom_template(
    template_id: str,
    x_remote_user: Optional[str] = Header(None)
) -> dict:
    """Delete a custom template (only by creator)."""
    created_by = x_remote_user or "anonymous"

    try:
        deleted = await TemplateService.delete_template(template_id, created_by)
        if not deleted:
            raise HTTPException(status_code=404, detail="Template not found or not authorized")

        return {'success': True, 'message': 'Template deleted'}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete template: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/templates/custom/{template_id}/use")
async def use_custom_template(template_id: str) -> dict:
    """Spawn a new document from a custom template."""
    try:
        template = await TemplateService.get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        # Return the HTML content to be loaded in the session
        return {
            'success': True,
            'data': {
                'html_content': template.html_content,
                'template_name': template.name
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to use template: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
```

**Checkpoint**: Custom templates backend complete. Test creating, listing, and deleting templates via API.

---

## Phase 5: Custom Templates - Frontend (Day 3-4)

### Step 5.1: Create Custom Template Service
```typescript
// frontend/src/services/templateService.ts
export interface CustomTemplate {
  id: string;
  name: string;
  description?: string;
  thumbnail_base64?: string;
  created_by: string;
  created_at: string;
}

export interface TemplateCreateData {
  name: string;
  description?: string;
  html_content: string;
}

export const createCustomTemplate = async (data: TemplateCreateData): Promise<CustomTemplate> => {
  const response = await fetch('/api/templates/custom', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to create template');
  }

  const result = await response.json();
  return result;
};

export const getCustomTemplates = async (): Promise<CustomTemplate[]> => {
  const response = await fetch('/api/templates/custom');

  if (!response.ok) {
    throw new Error('Failed to fetch templates');
  }

  return response.json();
};

export const deleteCustomTemplate = async (templateId: string): Promise<void> => {
  const response = await fetch(`/api/templates/custom/${templateId}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to delete template');
  }
};

export const useCustomTemplate = async (templateId: string): Promise<{ html_content: string; template_name: string }> => {
  const response = await fetch(`/api/templates/custom/${templateId}/use`, {
    method: 'POST',
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to load template');
  }

  const result = await response.json();
  return result.data;
};
```

### Step 5.2: Create Save Template Modal
```typescript
// frontend/src/components/SaveTemplateModal.tsx
import React, { useState } from 'react';
import { createCustomTemplate } from '../services/templateService';

interface SaveTemplateModalProps {
  htmlContent: string;
  onClose: () => void;
  onSaved: () => void;
}

export const SaveTemplateModal: React.FC<SaveTemplateModalProps> = ({
  htmlContent,
  onClose,
  onSaved,
}) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSave = async () => {
    if (!name.trim()) {
      setError('Template name is required');
      return;
    }

    setIsSaving(true);
    setError(null);

    try {
      await createCustomTemplate({
        name: name.trim(),
        description: description.trim() || undefined,
        html_content: htmlContent,
      });

      onSaved();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save template');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Save as Template</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        <div className="modal-body">
          <div className="form-group">
            <label htmlFor="template-name">Template Name *</label>
            <input
              id="template-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., My Custom Report Template"
              maxLength={200}
              autoFocus
            />
          </div>

          <div className="form-group">
            <label htmlFor="template-description">Description (optional)</label>
            <textarea
              id="template-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Brief description of what this template is for..."
              rows={3}
            />
          </div>

          {error && (
            <div className="error-message">
              <span className="error-icon">⚠</span>
              {error}
            </div>
          )}

          <div className="info-message">
            <span className="info-icon">ℹ</span>
            A thumbnail will be automatically generated from your current document
          </div>
        </div>

        <div className="modal-footer">
          <button className="btn-secondary" onClick={onClose} disabled={isSaving}>
            Cancel
          </button>
          <button className="btn-primary" onClick={handleSave} disabled={isSaving}>
            {isSaving ? 'Saving...' : 'Save Template'}
          </button>
        </div>
      </div>
    </div>
  );
};
```

### Step 5.3: Update Template Cards for Custom Templates
```typescript
// frontend/src/components/TemplateCards.tsx (update existing)
import React, { useEffect, useState } from 'react';
import { getCustomTemplates, deleteCustomTemplate, useCustomTemplate } from '../services/templateService';

interface CustomTemplate {
  id: string;
  name: string;
  description?: string;
  thumbnail_base64?: string;
  created_by: string;
}

interface TemplateCardsProps {
  onSelectBuiltinTemplate: (prompt: string) => void;
  onSelectCustomTemplate: (htmlContent: string, templateName: string) => void;
}

export const TemplateCards: React.FC<TemplateCardsProps> = ({
  onSelectBuiltinTemplate,
  onSelectCustomTemplate,
}) => {
  const [builtinTemplates, setBuiltinTemplates] = useState<BuiltinTemplate[]>([]);
  const [customTemplates, setCustomTemplates] = useState<CustomTemplate[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAllTemplates();
  }, []);

  const fetchAllTemplates = async () => {
    try {
      const [builtinData, customData] = await Promise.all([
        fetch('/api/templates/builtin').then(r => r.json()),
        getCustomTemplates(),
      ]);

      setBuiltinTemplates(builtinData.data.templates);
      setCustomTemplates(customData);
    } catch (err) {
      console.error('Failed to fetch templates', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCustomTemplateClick = async (template: CustomTemplate) => {
    try {
      const { html_content, template_name } = await useCustomTemplate(template.id);
      onSelectCustomTemplate(html_content, template_name);
    } catch (err) {
      console.error('Failed to load template', err);
      alert('Failed to load template');
    }
  };

  const handleDeleteTemplate = async (templateId: string, e: React.MouseEvent) => {
    e.stopPropagation();

    if (!confirm('Are you sure you want to delete this template?')) {
      return;
    }

    try {
      await deleteCustomTemplate(templateId);
      setCustomTemplates(prev => prev.filter(t => t.id !== templateId));
    } catch (err) {
      console.error('Failed to delete template', err);
      alert('Failed to delete template');
    }
  };

  if (loading) {
    return <div className="templates-loading">Loading templates...</div>;
  }

  return (
    <div className="templates-container">
      <div className="templates-header">
        <h2>Start with a Template</h2>
        <p>Choose a template to get started, then customize it for your needs</p>
      </div>

      {/* Custom Templates Section */}
      {customTemplates.length > 0 && (
        <div className="template-category">
          <h3 className="category-title">My Templates</h3>
          <div className="templates-grid">
            {customTemplates.map(template => (
              <div
                key={template.id}
                className="template-card custom-template"
                onClick={() => handleCustomTemplateClick(template)}
              >
                <div className="template-thumbnail">
                  <img
                    src={template.thumbnail_base64 || '/placeholder.svg'}
                    alt={template.name}
                  />
                  <button
                    className="delete-template-btn"
                    onClick={(e) => handleDeleteTemplate(template.id, e)}
                    title="Delete template"
                  >
                    🗑
                  </button>
                </div>
                <div className="template-info">
                  <h4>{template.name}</h4>
                  <p>{template.description || 'Custom template'}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Built-in Templates */}
      <div className="template-category">
        <h3 className="category-title">Starter Templates</h3>
        <div className="templates-grid">
          {builtinTemplates.map(template => (
            <div
              key={template.id}
              className="template-card"
              onClick={() => onSelectBuiltinTemplate(template.prompt_template)}
            >
              <div className="template-thumbnail">
                <img src={template.thumbnail} alt={template.name} />
                <div className="template-badge">Starter</div>
              </div>
              <div className="template-info">
                <h4>{template.name}</h4>
                <p>{template.description}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
```

### Step 5.4: Add Save Template Button to Preview
```typescript
// frontend/src/components/HTMLPreview.tsx (update existing)
import React, { useState } from 'react';
import { SaveTemplateModal } from './SaveTemplateModal';

interface HTMLPreviewProps {
  htmlContent: string;
}

export const HTMLPreview: React.FC<HTMLPreviewProps> = ({ htmlContent }) => {
  const [showSaveModal, setShowSaveModal] = useState(false);

  const handleTemplateSaved = () => {
    // Optionally show success notification
    alert('Template saved successfully!');
  };

  return (
    <div className="html-preview">
      <div className="preview-toolbar">
        {/* ... existing toolbar buttons ... */}

        <button
          className="btn-save-template"
          onClick={() => setShowSaveModal(true)}
          title="Save as template"
        >
          💾 Save as Template
        </button>
      </div>

      <div className="preview-content">
        <iframe srcDoc={htmlContent} title="HTML Preview" />
      </div>

      {showSaveModal && (
        <SaveTemplateModal
          htmlContent={htmlContent}
          onClose={() => setShowSaveModal(false)}
          onSaved={handleTemplateSaved}
        />
      )}
    </div>
  );
};
```

### Step 5.5: Add Modal and Template Styles
```css
/* frontend/src/styles/templates.css (append to existing) */

/* Custom template specific styles */
.custom-template .delete-template-btn {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  background: rgba(0, 0, 0, 0.7);
  color: white;
  border: none;
  border-radius: 4px;
  padding: 0.5rem;
  cursor: pointer;
  font-size: 1.25rem;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.custom-template:hover .delete-template-btn {
  opacity: 1;
}

.delete-template-btn:hover {
  background: rgba(204, 0, 0, 0.9);
}

/* Modal styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 12px;
  max-width: 500px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid #E0E0E0;
}

.modal-header h2 {
  margin: 0;
  font-size: 1.5rem;
  color: #152835;
}

.modal-body {
  padding: 1.5rem;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  padding: 1.5rem;
  border-top: 1px solid #E0E0E0;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: #152835;
}

.form-group input,
.form-group textarea {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #E0E0E0;
  border-radius: 4px;
  font-family: inherit;
  font-size: 1rem;
}

.form-group input:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #006FCF;
}

.info-message {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0.75rem;
  background: #B4EEFF;
  border: 1px solid #006FCF;
  border-radius: 4px;
  font-size: 0.875rem;
  color: #152835;
}

.btn-primary {
  background: #006FCF;
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 4px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.3s ease;
}

.btn-primary:hover:not(:disabled) {
  background: #00175A;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: white;
  color: #152835;
  border: 1px solid #E0E0E0;
  padding: 0.75rem 1.5rem;
  border-radius: 4px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-secondary:hover:not(:disabled) {
  border-color: #006FCF;
  color: #006FCF;
}

.btn-save-template {
  background: #28CD6E;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 600;
  transition: background 0.3s ease;
}

.btn-save-template:hover {
  background: #006469;
}
```

**Checkpoint**: Custom templates complete. Test saving a template, viewing it in the template gallery, loading it, and deleting it.

---

## Build Verification Checklist

### Backend Verification
- [ ] All file types (.txt, .md, .docx, .pdf, .csv, .xlsx) upload successfully
- [ ] File size validation rejects files >50MB
- [ ] Invalid file types are rejected with clear error messages
- [ ] Text extraction works correctly for all document types
- [ ] CSV/XLSX parsing returns structured data
- [ ] Built-in templates API returns all templates
- [ ] Custom templates can be created with thumbnail generation
- [ ] Custom templates can be listed, retrieved, and deleted
- [ ] Templates table has proper indexes
- [ ] Playwright thumbnail generation works

### Frontend Verification
- [ ] File upload drag-and-drop works
- [ ] File upload click-to-browse works
- [ ] Upload progress indicator displays
- [ ] File content auto-fills chat input with appropriate prompt
- [ ] Template cards display on empty session
- [ ] Built-in template cards render correctly with thumbnails
- [ ] Clicking built-in template fills chat input
- [ ] Custom template cards display with delete button
- [ ] Clicking custom template loads HTML content
- [ ] Save template modal opens from preview
- [ ] Template name validation works
- [ ] Thumbnail displays in template cards
- [ ] Template deletion works with confirmation

### Integration Testing
- [ ] Upload .docx → prompt auto-fills → send → Claude generates HTML
- [ ] Upload .csv → dashboard prompt auto-fills → send → Claude creates dashboard
- [ ] Click built-in template → edit placeholders → send → Claude generates
- [ ] Generate HTML → save as template → verify thumbnail created
- [ ] Load custom template → edit via chat → verify changes preserved
- [ ] Delete custom template → verify removed from gallery

---

## Testing Scenarios

### Test Case 1: Document Upload Flow
```
1. Prepare test.docx with "Annual Report 2024" content
2. Drag file into chat interface
3. Verify upload progress shows
4. Verify prompt auto-fills: "Create a professional document from this content: Annual Report 2024..."
5. Click Send
6. Verify Claude generates styled HTML
7. Verify HTML preview displays correctly
```

### Test Case 2: Data Upload Flow
```
1. Prepare sales.csv with columns: Month, Revenue, Units
2. Click upload button and browse for sales.csv
3. Verify prompt auto-fills: "Create an interactive dashboard from this data: Rows: 12, Columns: Month, Revenue, Units..."
4. Verify prompt suggests dashboard creation
5. Send message
6. Verify Claude generates dashboard with charts
```

### Test Case 3: Built-in Template Flow
```
1. Start new session (empty state)
2. Verify template cards display
3. Click "Impact Assessment Report" template
4. Verify prompt fills: "Create an impact assessment report for [topic]..."
5. Replace [topic] with "Cloud Migration"
6. Send message
7. Verify Claude generates impact assessment with tabs
```

### Test Case 4: Custom Template Flow
```
1. Generate HTML document via chat
2. Click "Save as Template" button
3. Enter name: "My Report Template"
4. Enter description: "Custom quarterly report"
5. Click Save
6. Verify thumbnail generation completes
7. Verify template appears in "My Templates" section
8. Start new session
9. Click custom template
10. Verify HTML loads in preview
11. Send chat message to modify
12. Verify changes apply to loaded template
```

### Test Case 5: Template Management
```
1. Create 3 custom templates
2. Verify all 3 display in gallery
3. Click delete on second template
4. Confirm deletion
5. Verify template removed from gallery
6. Verify other 2 templates remain
```

### Test Case 6: File Validation
```
1. Attempt to upload 60MB file
2. Verify error: "File size exceeds maximum of 50MB"
3. Attempt to upload .exe file
4. Verify error: "File type .exe not allowed"
5. Upload valid .txt file
6. Verify successful processing
```

### Test Case 7: Multi-sheet Excel
```
1. Prepare test.xlsx with 2 sheets: "Sales", "Expenses"
2. Upload file
3. Verify prompt includes first sheet data
4. Verify available_sheets metadata includes both sheets
5. Send message requesting dashboard
6. Verify Claude can reference both sheets if needed
```

---

## Rollback Plan

### If Phase 1 Fails (File Upload Backend)
1. Remove upload endpoint registration from main.py
2. Remove file_processors.py
3. Revert requirements.txt
4. Document issue and root cause
5. Continue with templates without file upload

### If Phase 2 Fails (File Upload Frontend)
1. Remove FileUpload component import
2. Remove upload button from ChatInput
3. Keep backend functional for future retry
4. Document UI issues encountered

### If Phase 3 Fails (Smart Starter Prompts)
1. Keep builtin_templates.json for future use
2. Remove TemplateCards component
3. Chat interface works normally without templates
4. Document template rendering issues

### If Phase 4 Fails (Custom Templates Backend)
1. Do NOT run migration (skip templates table creation)
2. Remove template service and endpoints
3. Keep built-in templates functional
4. Document database or Playwright issues

### If Phase 5 Fails (Custom Templates Frontend)
1. Remove SaveTemplateModal component
2. Remove custom template integration from TemplateCards
3. Keep built-in templates working
4. Document frontend issues

### Complete Rollback
```bash
# Backend
cd backend
git checkout HEAD -- app/api/endpoints/upload.py
git checkout HEAD -- app/api/endpoints/templates.py
git checkout HEAD -- app/utils/file_processors.py
git checkout HEAD -- app/utils/thumbnail_generator.py
git checkout HEAD -- app/services/template_service.py
git checkout HEAD -- app/models/template.py
git checkout HEAD -- requirements.txt

# Frontend
cd frontend
git checkout HEAD -- src/components/FileUpload.tsx
git checkout HEAD -- src/components/TemplateCards.tsx
git checkout HEAD -- src/components/SaveTemplateModal.tsx
git checkout HEAD -- src/services/uploadService.ts
git checkout HEAD -- src/services/templateService.ts
git checkout HEAD -- src/styles/upload.css
git checkout HEAD -- src/styles/templates.css

# Database (if migration ran)
psql -U postgres -d ai_html_builder -c "DROP TABLE IF EXISTS templates CASCADE;"
```

---

## Sign-off Checklist

### Pre-Implementation
- [ ] Read entire document top to bottom
- [ ] Confirmed Plans 001 and 004 are complete
- [ ] Backend server running and accessible
- [ ] Frontend can connect to backend
- [ ] Redis is running
- [ ] PostgreSQL is running (for custom templates)

### Phase 1 Complete
- [ ] File processing utilities created and tested
- [ ] Upload endpoint functional
- [ ] All file types process correctly
- [ ] File validation works (size + type)
- [ ] Error handling tested

### Phase 2 Complete
- [ ] FileUpload component renders
- [ ] Drag-and-drop works
- [ ] Click-to-browse works
- [ ] Prompts auto-fill correctly based on file type
- [ ] Upload errors display properly

### Phase 3 Complete
- [ ] builtin_templates.json created with 8 templates
- [ ] Built-in templates API functional
- [ ] TemplateCards component displays templates
- [ ] Clicking template fills chat input
- [ ] Template categories render correctly

### Phase 4 Complete
- [ ] Database migration successful
- [ ] Playwright installed and chromium downloaded
- [ ] Thumbnail generation works
- [ ] Custom templates CRUD endpoints functional
- [ ] Templates can be created, listed, retrieved, deleted

### Phase 5 Complete
- [ ] SaveTemplateModal component works
- [ ] Template name validation functional
- [ ] Custom templates display in gallery
- [ ] Custom template click loads HTML
- [ ] Template deletion works with confirmation
- [ ] Thumbnail displays correctly

### Final Verification
- [ ] All 7 test scenarios pass
- [ ] No console errors in browser
- [ ] No server errors in backend logs
- [ ] File uploads integrate with Claude generation
- [ ] Templates integrate with chat flow
- [ ] Performance acceptable (thumbnail generation <5s)
- [ ] Mobile responsive design verified
- [ ] Rollback plan documented and tested

### Documentation
- [ ] Code comments added for complex logic
- [ ] README updated with new features
- [ ] API documentation updated
- [ ] Environment variables documented
- [ ] Deployment notes updated

---

## Post-Implementation Notes

### Performance Optimization Opportunities
- Lazy load template thumbnails
- Cache built-in templates in localStorage
- Compress thumbnails further
- Add pagination for large custom template libraries
- Use Web Workers for file parsing in frontend

### Future Enhancements
- Template categories/tags for filtering
- Template sharing across users/teams
- Template versioning
- Bulk template import/export
- Template preview mode (hover)
- Advanced search/filter for templates
- Template usage analytics
- Multi-file upload support
- Drag-and-drop file directly into chat area (not modal)

### Known Limitations
- Thumbnail generation requires Playwright (heavy dependency)
- Large files (near 50MB) may cause browser memory issues
- Excel files limited to first sheet by default
- PDF text extraction quality depends on PDF structure
- Template thumbnails stored as base64 (large database size)

---

**Implementation Complete**: ✅ File upload and templates system fully implemented and verified.
**Completed by**: Claude agent session (Plan 006)
**Test Results**: 243/244 passed (1 pre-existing), ruff clean, mypy clean, TypeScript clean, Vite build clean
**Discrepancies**: 13 v1→v2 corrections applied during implementation (see ERRATA section at top)
**Next Steps**: Proceed to Plan 007 (Template Optimization) then Plan 008 (Deployment).

### Files Created (11)
- `backend/app/utils/file_processors.py` — file validation + content extraction
- `backend/app/api/upload.py` — POST /api/upload endpoint
- `backend/app/config/builtin_templates.json` — 8 builtin templates
- `backend/app/api/templates.py` — builtin + custom template CRUD endpoints
- `backend/app/services/template_service.py` — custom template service (SQLite + Playwright thumbnails)
- `frontend/src/services/uploadService.ts` — client-side upload validation + API
- `frontend/src/services/templateService.ts` — builtin + custom template API client
- `backend/tests/test_file_processors.py` — 12 tests
- `backend/tests/test_upload_api.py` — 5 tests
- `backend/tests/test_template_service.py` — 10 tests
- `backend/tests/test_templates_api.py` — 23 tests

### Files Modified (11)
- `backend/app/main.py` — added upload + templates routers
- `backend/app/database.py` — added `idx_templates_created_by` index
- `backend/app/api/sessions.py` — added `POST .../from-template` endpoint
- `frontend/src/components/ChatWindow/ChatInput.tsx` — file upload UI integration
- `frontend/src/components/ChatWindow/ChatInput.css` — upload button + indicator styles
- `frontend/src/components/EmptyState/TemplateCards.tsx` — fetch from API + custom templates
- `frontend/src/components/EmptyState/TemplateCards.css` — custom template card styles
- `frontend/src/components/ChatWindow/PromptLibraryModal.tsx` — fetch from API
- `frontend/src/App.tsx` — Save Template modal + custom template handler
- `frontend/src/services/api.ts` — added `createFromTemplate` method
- `frontend/src/types/index.ts` — added BuiltinTemplate + CustomTemplate interfaces
