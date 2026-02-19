# AI HTML Builder v2

> Three AI models, one chat interface. Create, edit, and export professional HTML documents through conversation.

**Claude Sonnet 4.6** surgically edits your documents without content drift. **Gemini 2.5 Pro** generates new documents with top-tier aesthetics. **Nano Banana Pro** creates images and infographics on demand. All outputs are single-file HTML with CSS/JS inlined — no external dependencies, ready to share.

## How It Works

```
React 19 (SSE) ──POST──> FastAPI ──> SQLite WAL
                              |
                 ┌────────────┼────────────┐
                 v            v            v
          Claude 4.6    Gemini 2.5 Pro  Nano Banana Pro
          (edit)        (create)        (image)
                              |            |
                              └──────┬─────┘
                                     v
                              InfographicService
                         (art director + renderer)
```

A lightweight **Haiku 4.5** classifier routes each request to the right model — one token, near-zero cost:

| You say... | What happens | Model |
|------------|-------------|-------|
| First message (no document yet) | Creates a new HTML document | Gemini 2.5 Pro |
| "Remove the sidebar", "Delete the footer" | Surgically removes content | Claude Sonnet 4.6 |
| "Create an infographic about..." | Generates a visual infographic | Gemini 2.5 Pro + Nano Banana Pro |
| "Turn this into a dashboard" | Transforms the current document | Gemini 2.5 Pro |
| "Generate an image of...", "Add a photo..." | Generates and embeds an image | Nano Banana Pro |
| Everything else (with existing document) | Surgically edits your current document | Claude Sonnet 4.6 |

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
- **Infographic generation** — two-LLM pipeline: Gemini art-directs, Nano Banana Pro renders
- **Multi-document sessions** — work on multiple documents in tabs, unlimited edits
- **Version history** — browse and restore any previous version
- **4-format export** — HTML, PowerPoint (PPTX), PDF, and PNG screenshot
- **File upload** — drag & drop .txt, .md, .docx, .pdf, .csv, .xlsx (up to 50MB) as context
- **Prompt templates** — stakeholder briefs, BRDs, proposals, dashboards, and more
- **Live code editor** — CodeMirror 6 with syntax highlighting and preview toggle
- **Image generation** — AI-generated raster images embedded directly in your document
- **Cost tracking** — per-model token usage and estimated costs
- **Dark theme** — "Cyberpunk Amethyst" dark-mode interface

## Quick Start

### Prerequisites

- **Node.js** 22+ (frontend)
- **Python** 3.11+ (backend)
- **Anthropic API key** (for Claude Sonnet 4.6 — edits + Haiku 4.5 — routing)
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
ANTHROPIC_API_KEY=sk-ant-...          # Claude Sonnet 4.6 (edits) + Haiku 4.5 (routing)
GOOGLE_API_KEY=AIza...                # One key covers Gemini 2.5 Pro + Nano Banana Pro + Flash

# Optional (defaults shown)
DATABASE_PATH=./data/app.db
LOG_LEVEL=info
MAX_UPLOAD_SIZE_MB=50
EDIT_MODEL=claude-sonnet-4-6
CREATION_MODEL=gemini-2.5-pro
IMAGE_MODEL=gemini-3-pro-image-preview
IMAGE_FALLBACK_MODEL=gemini-2.5-flash-image
IMAGE_TIMEOUT_SECONDS=90
ROUTER_MODEL=claude-haiku-4-5-20251001
```

## Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Frontend | React 19, TypeScript 5.8, Vite 7.1 | CodeMirror 6 editor, SSE streaming |
| Backend | FastAPI, Python 3.11+, aiosqlite | SQLite WAL mode, sse-starlette |
| AI (Edit) | Claude Sonnet 4.6 | Tool-use with `html_replace` / `html_insert_after` |
| AI (Create) | Gemini 2.5 Pro | Streaming creation, infographic art direction |
| AI (Image) | Nano Banana Pro | Raster image + infographic rendering, Flash fallback |
| AI (Route) | Claude Haiku 4.5 | Single-token intent classification |
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
    health.py                # Health check (DB + Playwright)
    costs.py                 # Token usage + cost tracking
  providers/
    base.py                  # LLMProvider / ImageProvider ABCs
    anthropic_provider.py    # Claude Sonnet 4.6 with tool_use
    gemini_provider.py       # Gemini 2.5 Pro streaming
    gemini_image_provider.py # Nano Banana Pro image generation
  services/
    editor.py                # Surgical editing engine (the core)
    creator.py               # Document creation + streaming
    router.py                # 5-rule intent classifier (regex + Haiku LLM)
    image_service.py         # Image generation + fallback
    infographic_service.py   # Two-LLM infographic pipeline
    session_service.py       # Session/document/version CRUD
    cost_tracker.py          # Per-model cost tracking
    export_service.py        # Export orchestration
    playwright_manager.py    # Browser lifecycle for PDF/PNG
    exporters/               # PPTX, PDF, PNG exporters
  utils/
    fuzzy_match.py           # Aider-inspired fuzzy string matching
    html_validator.py        # Post-edit HTML validation
    file_processors.py       # .docx/.pdf/.xlsx/.txt/.md parsing

frontend/src/
  App.tsx                    # Root layout, split-pane
  hooks/useSSEChat.ts        # Core SSE hook (single source of truth)
  services/
    api.ts                   # All REST API calls
    uploadService.ts         # Upload API wrapper
  data/
    promptTemplates.ts       # Prompt template data (frontend-only)
  components/
    ChatWindow/              # Chat input, message list, prompt library
    CodeViewer/              # CodeMirror 6 + preview toggle
    ConfirmDialog/           # Confirmation dialogs
    DocumentTabs/            # Multi-document tab bar
    VersionHistory/          # Version timeline with restore
    Export/                  # Format dropdown
    EmptyState/              # Template cards for new sessions
    Chat/                    # Streaming markdown renderer
    Layout/                  # Resizable split pane
  theme.css                  # Cyberpunk Amethyst dark theme
  types/index.ts             # TypeScript interfaces
```

## API Reference

### Chat (SSE Streaming)
- `POST /api/chat/{session_id}` — Send message, receive SSE stream of events (`status`, `chunk`, `html`, `summary`, `done`)

### Sessions & Documents

All document endpoints are session-scoped with ownership validation:

- `POST /api/sessions` — Create session
- `GET /api/sessions/{sid}` — Session info + documents
- `GET /api/sessions/{sid}/documents` — List documents
- `POST /api/sessions/{sid}/documents/{docId}/switch` — Switch active document
- `POST /api/sessions/{sid}/documents/from-template` — Create from template
- `PATCH /api/sessions/{sid}/documents/{docId}` — Rename document
- `DELETE /api/sessions/{sid}/documents/{docId}` — Delete document
- `GET /api/sessions/{sid}/documents/{docId}/html` — Latest HTML
- `GET /api/sessions/{sid}/documents/{docId}/versions` — Version history
- `GET /api/sessions/{sid}/documents/{docId}/versions/{ver}` — Specific version
- `POST /api/sessions/{sid}/documents/{docId}/versions/{ver}/restore` — Restore version
- `POST /api/sessions/{sid}/documents/{docId}/manual-edit` — Save manual code edit
- `GET /api/sessions/{sid}/chat` — Chat history

### Export
- `POST /api/sessions/{sid}/documents/{docId}/export/{format}` — Export document (format: `html`, `pptx`, `pdf`, `png`)
- `GET /api/export/formats` — List available formats

### Upload, Costs & Health
- `POST /api/upload` — Upload file (.txt/.md/.docx/.pdf/.csv/.xlsx, max 50MB)
- `GET /api/costs` — Cost summary (default 30 days)
- `GET /api/costs/today` — Today's costs
- `GET /api/health` — DB + Playwright status

## Database

SQLite in WAL mode with 5 tables: `sessions`, `documents`, `document_versions`, `chat_messages`, `cost_tracking`. Foreign keys enabled. No Redis, no external database dependencies.

## Quality Checks

```bash
# Backend
cd backend
pytest                                 # 320 tests
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
