# AI HTML Builder v2

AI-powered HTML/CSS document generator for 2-5 corporate users on a private Debian server. Users chat in natural language; the system creates, edits, and exports single-file HTML documents with all CSS/JS inlined. Four AI models collaborate: **Haiku 4.5** classifies intent, **Gemini 2.5 Pro** creates new documents, **Claude Sonnet 4.5** surgically edits them via `tool_use`, and **Nano Banana Pro (Gemini 3 Pro Image)** generates images.

## Quick Start

```bash
# Backend (Python 3.11+)
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload                      # http://localhost:8000

# Frontend (Node 22+)
cd frontend
npm install
npm run dev                                        # http://localhost:5173

# Quality checks
cd backend && pytest                               # 290+ tests
ruff check backend/ && mypy backend/               # Lint + types
cd frontend && npm run lint && npm run build        # ESLint + TypeScript + Vite

# Docker (production)
docker build -t ai-html-builder .
docker compose up -d
```

## Architecture

```
React 19 (SSE) ──POST──> FastAPI ──> SQLite WAL
                              |
                 ┌────────────┼────────────┐
                 v            v            v
          Claude 4.5    Gemini 2.5 Pro  Nano Banana Pro
          (edit)        (create)        (image)
                              |            |
                              └──────┬─────┘
                                     v
                              InfographicService
                         (art director + renderer)
```

### LLM Intent Routing (`services/router.py`)

| Rule | Condition | Route | Cost |
|------|-----------|-------|------|
| 1 | Removal/deletion keywords AND has HTML | EDIT | $0 |
| 2 | "infographic" keyword detected | INFOGRAPHIC | $0 |
| 3 | No existing HTML in session | CREATE | $0 |
| 4 | Transformation intent ("turn into", "convert to", "instead") | CREATE | $0 |
| 5 | HTML exists → Haiku 4.5 classifies intent | create / edit / image | ~$0.0001 |

- **Pre-routing regex**: Removal → EDIT, infographic → INFOGRAPHIC, transformation → CREATE (zero cost, zero latency)
- **No-HTML shortcut**: If no document exists (and not infographic), always routes to CREATE (no LLM call needed)
- **LLM classification**: Haiku 4.5 (`max_tokens=1, temperature=0`) classifies remaining requests
- **Fallback on ANY error**: Defaults to EDIT (safest — doesn't create docs or call image API)
- **Cost**: ~$0.0001/call for LLM classification, tracked in `cost_tracking` table

### Surgical Editing Engine (`services/editor.py`)

The core innovation that prevents content drift. Instead of regenerating full HTML:
- Claude receives the full HTML document + user request
- Claude responds with **tool calls**: `html_replace(old_text, new_text)` or `html_insert_after(anchor_text, new_content)`
- Server applies replacements **deterministically** via string matching
- **Temperature = 0** for edits (deterministic), 0.7 for creation (creative)
- **Fuzzy matching fallback chain** (Aider-inspired): exact match -> stripped whitespace -> normalized -> sequence matcher (difflib, 85% threshold)
- Post-edit HTML validation; falls back to full regeneration only if all tool calls fail

### Communication: SSE + HTTP POST (not WebSocket)

```
Client: POST /api/chat/{session_id}  { message, document_id? }
Server: text/event-stream
  -> { type: "status",  content: "Analyzing request..." }
  -> { type: "chunk",   content: "<p>partial..." }         # streaming creation
  -> { type: "html",    content: "<!DOCTYPE...", version: 3 }
  -> { type: "summary", content: "Changed header color" }
  -> { type: "done" }
```

## Tech Stack

| Layer | Technology | Version / ID |
|-------|-----------|-------------|
| Frontend | React | 19.1.1 |
| Frontend | TypeScript | 5.8.3 |
| Frontend | Vite | 7.1.2 |
| Frontend | CodeMirror 6 | 6.0.1 |
| Backend | FastAPI | 0.111.0+ |
| Backend | Python | 3.11+ |
| Backend | aiosqlite (SQLite WAL) | 0.20.0+ |
| Backend | Anthropic SDK | 0.40.0+ |
| Backend | google-genai SDK | 1.0.0+ |
| Backend | Playwright (PDF/PNG) | 1.49.0+ |
| Backend | structlog | 24.4.0+ |
| AI Edit | Claude Sonnet 4.5 | `claude-sonnet-4-5-20250929` |
| AI Create | Gemini 2.5 Pro | `gemini-2.5-pro` |
| AI Image | Nano Banana Pro (Gemini 3 Pro Image) | `gemini-3-pro-image-preview` |
| AI Router | Claude Haiku 4.5 | `claude-haiku-4-5-20251001` |
| Deploy | Docker multi-stage | Node 22-alpine + Python 3.11-slim |
| Proxy | Nginx Proxy Manager | External (already on server) |

## Project Structure

```
backend/app/
  config.py                  # Pydantic settings (all env vars)
  database.py                # SQLite init, schema (5 tables), WAL mode
  main.py                    # FastAPI app, lifespan, router registration
  api/
    chat.py                  # POST /api/chat/{sid} - SSE streaming (4 handlers: edit, create, image, infographic)
    sessions.py              # Session + document + version CRUD
    export.py                # Export to HTML/PPTX/PDF/PNG (single parameterized endpoint)
    upload.py                # File upload (.txt/.md/.docx/.pdf/.csv/.xlsx)
    health.py                # Health check (DB + Playwright)
    costs.py                 # Token usage + cost tracking
  providers/
    base.py                  # LLMProvider, ImageProvider ABCs; ToolCall, ToolResult, GenerationResult
    anthropic_provider.py    # Claude Sonnet 4.5 with tool_use
    gemini_provider.py       # Gemini 2.5 Pro streaming
    gemini_image_provider.py # Nano Banana Pro image generation
  services/
    editor.py                # SurgicalEditor - tool_use + fuzzy match (THE core)
    creator.py               # DocumentCreator - streaming creation, Claude fallback
    router.py                # classify_request() - Haiku 4.5 LLM intent classification
    image_service.py         # Image generation + SVG templates
    infographic_service.py   # Two-LLM infographic pipeline (Gemini art director + Nano Banana Pro renderer)
    session_service.py       # Session/document/version/chat CRUD
    cost_tracker.py          # Per-model token + cost tracking
    export_service.py        # Export orchestration via dict-based dispatch
    playwright_manager.py    # Browser lifecycle for PDF/PNG
    exporters/               # base.py, pptx_exporter.py, playwright_exporter.py (PDF+PNG)
  utils/
    fuzzy_match.py           # Aider-inspired fuzzy string matching
    html_validator.py        # Post-edit HTML structure validation
    file_processors.py       # File parsing (.docx/.pdf/.xlsx/.txt/.md)

frontend/src/
  App.tsx                    # Root layout, split-pane
  hooks/useSSEChat.ts        # Core SSE hook - all chat state flows through here
  services/
    api.ts                   # All REST API calls
    uploadService.ts         # Upload API wrapper
  components/
    ChatWindow/              # ChatInput, MessageList, PromptLibraryModal, index
    CodeViewer/              # CodeMirror 6 editor + preview toggle
    DocumentTabs/            # Multi-document tab bar
    VersionHistory/          # Version timeline
    Export/                  # Export format dropdown
    EmptyState/              # Template cards (frontend-only data)
    Chat/                    # StreamingMarkdown renderer
    Layout/                  # SplitPane
  types/index.ts             # All TypeScript interfaces
  data/promptTemplates.ts    # Frontend prompt template data (sole template source)
```

## Database (SQLite WAL)

5 tables in `database.py`, WAL mode + foreign keys enabled:

| Table | Key Columns | Constraints |
|-------|------------|-------------|
| `sessions` | id, created_at, last_active, metadata | PK: id |
| `documents` | id, session_id, title, is_active | FK: session_id -> sessions |
| `document_versions` | id, document_id, version, html_content, edit_summary, model_used | UNIQUE(document_id, version) |
| `chat_messages` | id, session_id, document_id, role, content, message_type | CHECK(role IN user/assistant/system) |
| `cost_tracking` | id, date, model, request_count, input/output_tokens, estimated_cost_usd | UNIQUE(date, model) |

Indexes: `idx_documents_session`, `idx_versions_document`, `idx_messages_session`, `idx_cost_date`

## API Endpoints

### Sessions
- `POST /api/sessions` - Create session
- `GET /api/sessions/{sid}` - Session info + documents
- `GET /api/sessions/{sid}/documents` - List documents
- `POST /api/sessions/{sid}/documents/{docId}/switch` - Switch active document
- `GET /api/sessions/{sid}/chat` - Chat history
- `POST /api/sessions/{sid}/documents/from-template` - Create from template HTML

### Documents
- `GET /api/documents/{docId}/html` - Latest HTML
- `GET /api/documents/{docId}/versions` - Version history
- `GET /api/documents/{docId}/versions/{ver}` - Specific version

### Chat (SSE)
- `POST /api/chat/{session_id}` - Stream response; body: `{message, document_id?}`

### Export
- `POST /api/export/{docId}/{format}` - Export document (format: html/pptx/pdf/png)
- `GET /api/export/formats` - Available formats

### Upload
- `POST /api/upload` - Multipart file upload (.txt/.md/.docx/.pdf/.csv/.xlsx, max 50MB)

### Costs & Health
- `GET /api/costs` - Cost summary (default 30 days)
- `GET /api/costs/today` - Today's costs
- `GET /api/health` - DB + Playwright status

## Environment Variables

From `backend/app/config.py` (pydantic-settings, loaded from `.env`):

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...          # Claude Sonnet 4.5 for surgical edits
GOOGLE_API_KEY=AIza...                # ONE key covers Gemini 2.5 Pro, Nano Banana Pro, AND Flash

# Optional (defaults shown)
DATABASE_PATH=./data/app.db
LOG_LEVEL=info
MAX_UPLOAD_SIZE_MB=50
EDIT_MODEL=claude-sonnet-4-5-20250929
CREATION_MODEL=gemini-2.5-pro
IMAGE_MODEL=gemini-3-pro-image-preview
IMAGE_FALLBACK_MODEL=gemini-2.5-flash-image
IMAGE_TIMEOUT_SECONDS=90
ROUTER_MODEL=claude-haiku-4-5-20251001
```

## Deployment

**Dockerfile** (multi-stage):
1. Stage 1: `node:22-alpine` - builds React frontend (`npm ci && npm run build`)
2. Stage 2: `python:3.11-slim` - installs backend deps, Playwright Chromium, copies static frontend
3. Non-root user `appuser`, port 8000, healthcheck via `curl`

**Production**: Docker container on Debian server at `100.94.82.35` (SSH as `chee@100.94.82.35`). Port 6669 external -> 8000 internal. Domain: `clhtml.zyroi.com`. Repo cloned to `~/aihtml`. Deploy workflow: local `git push` -> server `cd ~/aihtml && ./deploy.sh` (pulls, builds, restarts, health-checks). Daily DB backup via cron at 2 AM.

## Frontend Aesthetics Guidelines

These rules apply to ALL frontend work: generated HTML documents AND the app's own UI.

### Core Principle
Avoid "AI slop" - the generic, on-distribution aesthetic that plagues AI-generated frontends. Make creative, distinctive designs that surprise and delight.

### Typography
- **NEVER use**: Inter, Roboto, Open Sans, Lato, Arial, default system fonts
- **Code aesthetic**: JetBrains Mono, Fira Code, Space Grotesk
- **Editorial**: Playfair Display, Crimson Pro, Fraunces
- **Startup/Modern**: Clash Display, Satoshi, Cabinet Grotesk
- **Technical**: IBM Plex family, Source Sans 3
- **Distinctive**: Bricolage Grotesque, Obviously, Newsreader
- **Pairing**: High contrast = interesting. Display + monospace, serif + geometric sans
- **Weight extremes**: 100/200 vs 800/900 (not 400 vs 600). Size jumps of 3x+ (not 1.5x)
- Load from Google Fonts. State your font choice before coding

### Color & Theme
- Commit to a **cohesive aesthetic** using CSS variables
- **Dominant colors with sharp accents** outperform timid, evenly-distributed palettes
- Draw from IDE themes and cultural aesthetics for inspiration
- Vary between light and dark themes across generations
- Avoid: purple gradients on white backgrounds, cliched color schemes

### Motion & Animation
- CSS-only solutions for HTML document output
- Motion library for React when available
- Focus on **high-impact moments**: one well-orchestrated page load with staggered reveals (`animation-delay`) over scattered micro-interactions
- Use `transform` and `opacity` animations (avoid layout shifts)

### Backgrounds & Depth
- Layer CSS gradients, geometric patterns, or contextual effects
- Create atmosphere and depth, never default to solid colors

### Anti-Patterns to Avoid
- Overused fonts (Inter, Roboto, Arial, system fonts)
- Cliched color schemes (purple gradients on white)
- Predictable layouts and cookie-cutter component patterns
- Converging on the same "safe" choices (e.g., Space Grotesk) across generations

### Default Document Palette (from `creator.py`)
For generated HTML documents, unless user specifies otherwise:
- Primary: Ink (#0F172A), Deep Teal (#0D7377), Teal (#14B8A6)
- Neutrals: Warm Slate (#334155), Stone (#78716C), Cream (#FAFAF9)
- Accent: Amber (#D97706), Mist (#CCFBF1), Emerald (#059669), Slate Blue (#475569)
- Background: Warm White (#F8FAFC)
- Typography: 'DM Sans', sans-serif (Google Fonts — professional, clean, Arial-adjacent)

## Key Patterns for AI Agents

### Backend
- **Lazy imports** in API endpoint functions for testability - patch at SOURCE module (e.g., `app.utils.file_processors.process_file`), not the consumer module
- **Provider ABC pattern**: all AI calls go through `LLMProvider` / `ImageProvider` in `providers/base.py`
- `aiosqlite` has NO `execute_fetchone` - use `cursor = await db.execute(); row = await cursor.fetchone()`
- `pydantic-settings` `Settings()` needs `# type: ignore[call-arg]` for mypy (env vars loaded at runtime)
- Anthropic SDK types need `# type: ignore[arg-type]` when passing `list[dict]`
- `asyncio.Lock()` must be created inside async functions, NOT at module level (singleton imports happen before event loop)

### Frontend
- `useSSEChat.ts` is the single source of truth for chat state, session lifecycle, document switching
- SSE parsing: manual `ReadableStream` reader (POST-based, NOT `EventSource` which only supports GET)
- Session ID persisted in `sessionStorage` with key `ai-html-builder-session-id`
- Vite dev proxy: `/api` routes to `http://localhost:8000`

### Testing
- 290+ tests across 20+ test files, `asyncio_mode = "auto"` in pyproject.toml
- 1 known pre-existing failure: `test_init_db_creates_file`
- Patches must target source module, not consumer (e.g., `app.utils.file_processors.*`, not `app.api.upload.*`)
- `pytest-asyncio` auto mode: no need for `@pytest.mark.asyncio` decorators

## Implementation Plans

All plans in `IMPLEMENTATION_PLANS/` directory:

| Plan | Name | Status |
|------|------|--------|
| 000 | Master Rebuild Plan | Reference doc |
| 001 | Backend Foundation (SQLite, SSE, providers) | COMPLETE |
| 002 | Surgical Editing Engine (tool_use, fuzzy match) | COMPLETE |
| 003 | Multi-Model Routing (Gemini creation, images) | COMPLETE |
| 004 | Frontend Enhancements (CodeMirror, tabs, versions) | COMPLETE |
| 005 | Export Pipeline (HTML, PPTX, PDF, PNG) | COMPLETE |
| 006 | File Upload & Templates | COMPLETE |
| 007 | Template Optimization (placeholders, max_tokens) | COMPLETE |
| 008 | Deployment & Security | COMPLETE |
| 009a | Visual Foundation ("Obsidian Terminal" theme) | COMPLETE |
| 009b | Viewer Pane & UX Polish | COMPLETE |
| 010 | Nano Banana Pro Image Model Upgrade | COMPLETE |
| 011 | Remove Custom Templates | COMPLETE |
| 012 | Architecture Refactoring (dead code, export consolidation, chat.py extraction) | COMPLETE |
| 013 | UX Improvements (template badges, confirm dialogs, new session, editable CodeMirror, loading state, send debounce, doc badges) | COMPLETE |
| 014 | LLM Router + Template Fix (Haiku 4.5 intent classification, template badge fix, SVG word boundaries) | COMPLETE |
| 015 | Critical Bug Fixes (Router pre-routing, edit error guards, template titles, SVG branch removal) | COMPLETE |
| 016 | Transformation Context + Document Ownership Validation | COMPLETE |
| 017 | UI/UX Makeover (Cyberpunk Amethyst theme) | COMPLETE |
| 018 | NotebookLM-Style Infographic Generation | COMPLETE |

## Known Issues

- `docker-compose.yml` at root is still the v1 Redis-only file (dead, Plan 008 will replace)
- 1 test failure: `test_init_db_creates_file` (pre-existing, non-blocking)
- `.env.example` at root may be out of sync with `backend/app/config.py` - always trust `config.py`
- Custom templates removed (no auth mechanism). Will be re-introduced when Plan 008 adds Nginx Proxy Manager authentication.

### Future Improvements
- **Infographic text legibility**: Nano Banana Pro renders small text at reduced quality. If needed, tighten the art director prompt to enforce fewer words, larger minimum font sizes, and discourage text below ~24pt. A more advanced option: hybrid overlay (image for visuals, HTML text positioned on top) but this has alignment complexity.

### Resolved Issues
- ~~Admin dashboard components~~ — **DELETED** (legacy v1 code removed: `AdminDashboard.tsx`, `AdminLogin.tsx`, `AdminPage.tsx`, `BasicChatWindow.tsx`, `SimpleChatWindow.tsx`)
- ~~`CodeMirrorViewer.tsx` matchMedia issue~~ — **RESOLVED in Plan 009b** (replaced with `MutationObserver` on `data-theme` attribute)
- ~~"REMOVE THE SVG DIAGRAM" adds SVG instead of removing~~ — **RESOLVED in Plan 015** (pre-routing detects removal intent → edit)
- ~~`'new_text'` error after edit~~ — **RESOLVED in Plan 015** (KeyError guard + user-friendly error messages)
- ~~Template `{{PLACEHOLDER}}` visible in titles~~ — **RESOLVED in Plan 015** (server-side title extraction)
- ~~Raw text in viewer after failed edit~~ — **RESOLVED in Plan 015** (fallback preserves original HTML on failure)
- ~~Hardcoded SVG templates in image handler~~ — **RESOLVED in Plan 015** (SVG branch removed; diagrams route to editor)
- ~~"Turn this into X" creates document with hallucinated content~~ — **RESOLVED in Plan 016** (existing HTML passed as context to creator with base64 stripping)
- ~~Token estimation wrong for transformation requests~~ — **RESOLVED in Plan 016** (input estimate now includes context HTML size)
- ~~Document endpoints accessible without session validation~~ — **RESOLVED in Plan 016** (all document endpoints moved to `/api/sessions/{sid}/documents/{docId}/*` with ownership validation)

---

**Last Updated**: February 2026
**Architecture**: v2 rebuild (Plans 001-018 complete)
**AI Models**: Haiku 4.5 (routing) + Claude Sonnet 4.5 (edits) + Gemini 2.5 Pro (creation + infographic art direction) + Nano Banana Pro (images + infographic rendering)
**Database**: SQLite WAL (no Redis)
**Communication**: SSE + HTTP POST (no WebSocket)