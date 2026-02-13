# AI HTML Builder v2

> Three AI models, one chat interface. Create, edit, and export professional HTML documents through conversation.

**Claude Sonnet 4.5** surgically edits your documents without content drift. **Gemini 2.5 Pro** generates new documents with top-tier aesthetics. **Nano Banana Pro** creates images on demand. All outputs are single-file HTML with CSS/JS inlined — no external dependencies, ready to share.

## How It Works

```
React 19 (SSE) ──POST──> FastAPI ──> SQLite WAL
                              |
                 ┌────────────┼────────────┐
                 v            v            v
          Claude 4.5    Gemini 2.5 Pro  Nano Banana Pro
          (edit)        (create)        (image)
```

The system automatically routes your request to the right model:

| You say... | What happens | Model |
|------------|-------------|-------|
| First message (no document yet) | Creates a new HTML document | Gemini 2.5 Pro |
| "Create a new...", "Start fresh..." | Creates a new document | Gemini 2.5 Pro |
| "Generate an image of...", "Add a diagram..." | Generates and embeds an image | Nano Banana Pro |
| Everything else | Surgically edits your current document | Claude Sonnet 4.5 |

### The Surgical Editing Engine

This is the core innovation. Most AI HTML tools regenerate the entire document on every edit, causing **content drift** — your carefully refined sections get rewritten, formatting changes, content disappears. We solved this:

1. Claude receives your full HTML + your edit request
2. Claude responds with **tool calls** (`html_replace`, `html_insert_after`) — not regenerated HTML
3. The server applies replacements via **deterministic string matching**
4. A fuzzy matching fallback chain (exact -> whitespace-stripped -> normalized -> 85% sequence match) handles minor discrepancies
5. Temperature = 0 for edits (deterministic), 0.7 for creation (creative)

Result: edit #50 is just as precise as edit #1.

## Features

- **Chat-driven creation** — describe what you want in plain language
- **Surgical editing** — change a heading color without touching anything else
- **Multi-document sessions** — work on multiple documents in tabs, unlimited edits
- **Version history** — browse and restore any previous version
- **4-format export** — HTML, PowerPoint (PPTX), PDF, and PNG screenshot
- **File upload** — drag & drop .txt, .md, .docx, .pdf, .csv, .xlsx (up to 50MB) as context
- **8 builtin templates** — stakeholder briefs, BRDs, proposals, dashboards, and more
- **Live code editor** — CodeMirror 6 with syntax highlighting and preview toggle
- **Image generation** — AI-generated raster images embedded directly in your document
- **Cost tracking** — per-model token usage and estimated costs
- **Dark/light theme** — "Obsidian Terminal" dark theme with light mode toggle

## Quick Start

### Prerequisites

- **Node.js** 22+ (frontend)
- **Python** 3.11+ (backend)
- **Anthropic API key** (for Claude Sonnet 4.5 — edits)
- **Google API key** (one key covers Gemini 2.5 Pro, Nano Banana Pro, and Flash fallback)

### Development

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                               # Add your API keys
uvicorn app.main:app --reload                      # http://localhost:8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev                                        # http://localhost:5173
```

The Vite dev server proxies `/api` requests to `localhost:8000` automatically.

### Docker (Production)

```bash
docker build -t ai-html-builder .
docker run -d -p 8080:8000 --env-file .env ai-html-builder
```

The multi-stage Dockerfile builds the React frontend with Node 22-alpine, then packages everything into a Python 3.11-slim image with Playwright Chromium for PDF/PNG export.

## Environment Variables

Create a `.env` file in the project root (or use `--env-file` with Docker):

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...          # Claude Sonnet 4.5 for surgical edits
GOOGLE_API_KEY=AIza...                # One key covers Gemini 2.5 Pro + Nano Banana Pro + Flash

# Optional (defaults shown)
DATABASE_PATH=./data/app.db
LOG_LEVEL=info
RATE_LIMIT_REQUESTS=30
RATE_LIMIT_WINDOW=60
SESSION_TIMEOUT_HOURS=24
MAX_UPLOAD_SIZE_MB=50
EDIT_MODEL=claude-sonnet-4-5-20250929
CREATION_MODEL=gemini-2.5-pro
IMAGE_MODEL=gemini-3-pro-image-preview
IMAGE_FALLBACK_MODEL=gemini-2.5-flash-image
IMAGE_TIMEOUT_SECONDS=90
```

## Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Frontend | React 19, TypeScript 5.8, Vite 7.1 | CodeMirror 6 editor, SSE streaming |
| Backend | FastAPI, Python 3.11+, aiosqlite | SQLite WAL mode, sse-starlette |
| AI (Edit) | Claude Sonnet 4.5 | Tool-use with `html_replace` / `html_insert_after` |
| AI (Create) | Gemini 2.5 Pro | Streaming creation, top aesthetics |
| AI (Image) | Nano Banana Pro | Raster image generation, Flash fallback |
| Export | Playwright Chromium | PDF and PNG rendering |
| Export | python-pptx | PowerPoint generation via sandboxed code execution |
| Deploy | Docker multi-stage | Node 22-alpine + Python 3.11-slim |
| Proxy | Nginx Proxy Manager | External reverse proxy (not bundled) |

## Project Structure

```
backend/app/
  config.py                  # Pydantic settings (all env vars)
  database.py                # SQLite schema (5 tables), WAL mode
  main.py                    # FastAPI app, lifespan, routers
  api/
    chat.py                  # POST /api/chat/{sid} - SSE streaming
    sessions.py              # Session + document + version CRUD
    export.py                # Export to HTML/PPTX/PDF/PNG
    upload.py                # File upload processing
    templates.py             # Builtin template API
    health.py                # Health check (DB + Playwright)
    costs.py                 # Token usage + cost tracking
  providers/
    base.py                  # LLMProvider / ImageProvider ABCs
    anthropic_provider.py    # Claude Sonnet 4.5 with tool_use
    gemini_provider.py       # Gemini 2.5 Pro streaming
    gemini_image_provider.py # Nano Banana Pro image generation
  services/
    editor.py                # Surgical editing engine (the core)
    creator.py               # Document creation + streaming
    router.py                # 4-rule request classifier
    image_service.py         # Image generation + fallback
    session_service.py       # Session/document/version CRUD
    cost_tracker.py          # Per-model cost tracking
    export_service.py        # Export orchestration
    playwright_manager.py    # Browser lifecycle for PDF/PNG
    exporters/               # HTML, PPTX, PDF, PNG exporters
  utils/
    fuzzy_match.py           # Aider-inspired fuzzy string matching
    html_validator.py        # Post-edit HTML validation
    file_processors.py       # .docx/.pdf/.xlsx/.txt/.md parsing
    rate_limiter.py          # Per-session rate limiting
  config/
    builtin_templates.json   # 8 builtin document templates

frontend/src/
  App.tsx                    # Root layout, split-pane, routing
  hooks/useSSEChat.ts        # Core SSE hook (single source of truth)
  services/                  # API, template, upload service wrappers
  components/
    ChatWindow/              # Chat input, message list, prompt library
    CodeViewer/              # CodeMirror 6 + preview toggle
    DocumentTabs/            # Multi-document tab bar
    VersionHistory/          # Version timeline with restore
    Export/                  # Format dropdown
    EmptyState/              # Template cards for new sessions
    Chat/                    # Streaming markdown renderer
    Layout/                  # Resizable split pane
  theme.css                  # CSS custom properties (dark/light)
  types/index.ts             # TypeScript interfaces
```

## API Reference

### Chat (SSE Streaming)
- `POST /api/chat/{session_id}` — Send message, receive SSE stream of events (`status`, `chunk`, `html`, `summary`, `done`)

### Sessions & Documents
- `POST /api/sessions` — Create session
- `GET /api/sessions/{sid}` — Session info + documents
- `GET /api/sessions/{sid}/documents` — List documents
- `POST /api/sessions/{sid}/documents/{docId}/switch` — Switch active document
- `POST /api/sessions/{sid}/documents/from-template` — Create from template
- `PUT /api/sessions/{sid}/documents/{docId}/rename` — Rename document
- `DELETE /api/sessions/{sid}/documents/{docId}` — Delete document
- `GET /api/sessions/{sid}/chat` — Chat history
- `GET /api/documents/{docId}/html` — Latest HTML
- `GET /api/documents/{docId}/versions` — Version history
- `GET /api/documents/{docId}/versions/{ver}` — Specific version
- `POST /api/documents/{docId}/versions/{ver}/restore` — Restore version

### Export
- `POST /api/export/{docId}/html` — Download as HTML
- `POST /api/export/{docId}/pptx` — Export as PowerPoint
- `POST /api/export/{docId}/pdf` — Export as PDF (Playwright)
- `POST /api/export/{docId}/png` — Export as PNG screenshot (Playwright)
- `GET /api/export/formats` — List available formats

### Upload, Templates, Costs & Health
- `POST /api/upload` — Upload file (.txt/.md/.docx/.pdf/.csv/.xlsx, max 50MB)
- `GET /api/templates/builtin` — List builtin templates
- `GET /api/templates/builtin/{id}` — Get specific template
- `GET /api/costs` — Cost summary (default 30 days)
- `GET /api/costs/today` — Today's costs
- `GET /api/health` — DB + Playwright status

## Database

SQLite in WAL mode with 5 tables: `sessions`, `documents`, `document_versions`, `chat_messages`, `cost_tracking`. Foreign keys enabled. No Redis, no external database dependencies.

## Quality Checks

```bash
# Backend
cd backend
pytest                                 # 244+ tests
ruff check .                           # Linting
mypy .                                 # Type checking

# Frontend
cd frontend
npm run lint                           # ESLint
npm run build                          # TypeScript + Vite build
```

## Deployment Notes

The app is designed to run behind **Nginx Proxy Manager** (or any reverse proxy) on a private server. The Dockerfile produces a single container that serves both the API and the built frontend static files. Playwright Chromium is included in the image for PDF/PNG export.

Typical setup:
- Container exposes port 8000 internally
- Map to any external port (e.g., 8080)
- Reverse proxy handles HTTPS termination
- `.env` file or `--env-file` for API keys

## License

MIT
