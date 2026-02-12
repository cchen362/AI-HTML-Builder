# Plan 000: Master Rebuild Plan - AI HTML Builder v2

## STOP: Read This Entire Document Before Making Any Changes

This is the master architecture document for the complete rebuild of the AI HTML Builder. Every subsequent implementation plan (001-007) is derived from the decisions documented here.

---

## Why We're Rebuilding

The current application works but has fundamental architectural problems that make it unreliable for daily use:

| Problem | Root Cause | Impact |
|---------|-----------|--------|
| **Content drift on edits** | AI regenerates entire HTML document for every edit | Users gave up and stopped using the tool |
| **Fragile session management** | Redis with silent failures, data loss on restart | Lost work, inconsistent state |
| **Over-engineered backend** | 1,200-line Claude service with 2-phase semantic analysis | Extra latency, extra cost, marginal benefit |
| **Missing core UX features** | No syntax highlighting, no markdown in chat, no version history | Tool feels unfinished |
| **No export to PPT** | Only HTML export available | Users manually recreate in PowerPoint |
| **Single model locked in** | Hardcoded to Claude Sonnet 4, no ability to use better models per task | Can't leverage best-in-class models |
| **5-edit limit per session** | Context window fills up from regenerating full HTML each time | Artificially constrains usefulness |

**The rebuild addresses ALL of these by changing the fundamental architecture, not by patching symptoms.**

---

## Architecture Overview

### Current Architecture (v1)
```
React 19 ←── WebSocket ──→ FastAPI ──→ Claude Sonnet 4 (only)
                              │
                           Redis (fragile)
```

### New Architecture (v2)
```
                     Internet
                        │
              ┌─────────────────────┐
              │ Nginx Proxy Manager │  Reverse Proxy + SSL (already on server)
              └──────────┬──────────┘
                        │
              ┌─────────┴─────────┐
              │   FastAPI App     │
              │                   │
              │  ┌─────────────┐  │
              │  │ Static React│  │  (Vite build served by FastAPI)
              │  └─────────────┘  │
              │                   │
              │  ┌─────────────┐  │        ┌──────────────────┐
              │  │ SSE Stream  │──┼───────→│ Claude Sonnet 4.5│ (edits)
              │  │ + HTTP POST │  │        └──────────────────┘
              │  └─────────────┘  │        ┌──────────────────┐
              │                   │───────→│ Gemini 2.5 Pro   │ (creation)
              │  ┌─────────────┐  │        └──────────────────┘
              │  │ SQLite (WAL)│  │        ┌──────────────────┐
              │  │ Sessions    │  │───────→│ Nano Banana Pro  │ (images)
              │  │ Versions    │  │        └──────────────────┘
              │  │ Analytics   │  │
              │  └─────────────┘  │
              │                   │
              │  ┌─────────────┐  │
              │  │ Playwright  │  │  (PDF/PNG export)
              │  └─────────────┘  │
              └───────────────────┘
                        │
                 Docker Volume
                  └── data.db
```

### Key Architecture Changes

| Component | v1 (Current) | v2 (Rebuild) | Why |
|-----------|-------------|-------------|-----|
| **Editing approach** | Full HTML regeneration | Tool-based `html_replace` via Claude `tool_use` | Eliminates content drift permanently |
| **AI models** | Claude Sonnet 4 only | Claude Sonnet 4.5 + Gemini 2.5 Pro + Nano Banana Pro | Best model for each task |
| **Database** | Redis (fragile, ephemeral) | SQLite WAL mode | Persistent, queryable, zero ops overhead |
| **Streaming** | WebSocket (stateful, complex) | SSE + HTTP POST (stateless) | Simpler, proxy-friendly, industry standard |
| **Auth** | Custom JWT + hardcoded password | Nginx Proxy Manager (existing) | Zero auth code in application |
| **Session model** | One document per session, 5-edit limit | Multi-document per session, unlimited edits | Users aren't artificially constrained |
| **Frontend code view** | Raw `<pre>` tag | CodeMirror 6 with syntax highlighting | Actually usable for reviewing code |
| **Chat rendering** | Plain text | Streamdown (streaming markdown) | Modern chat UX |
| **Export** | HTML only | HTML + PPTX + PDF | Corporate workflow support |

---

## Model Strategy

### Three Models, Three Roles

| Model | Role | When Used | Cost/Request |
|-------|------|-----------|-------------|
| **Claude Sonnet 4.5** | Surgical editing + PPT export | Every edit, every PPT export | ~$0.03/edit, ~$0.08/export |
| **Gemini 2.5 Pro** | Document creation | New document requests | ~$0.06/creation |
| **Nano Banana Pro** | Image/infographic generation | When user asks for visuals (auto-detect or button) | ~$0.13-0.24/image |

### Routing Logic (3 Rules, Zero Ambiguity)

```
Request arrives
    │
    ├─ No existing HTML in session? ──────────► Gemini 2.5 Pro (CREATE)
    │
    ├─ User explicitly said "create new/separate"? ► Gemini 2.5 Pro (CREATE new document)
    │
    ├─ Image/diagram/infographic detected?
    │  (auto-detect keywords OR explicit button) ─► Nano Banana Pro (IMAGE)
    │                                                then Claude embeds in HTML
    │
    └─ Everything else (THE DEFAULT) ─────────► Claude Sonnet 4.5 (EDIT via tool_use)
```

**Routing is based on STATE (does HTML exist?) and EXPLICIT INTENT (image keyword or new doc request), not keyword guessing.**

### Why These Specific Models

**Claude Sonnet 4.5 for edits:**
- 0% edit error rate on code editing benchmarks (Anthropic's data)
- Best-in-class at `tool_use` / `str_replace` pattern (same approach as Claude Artifacts)
- Strong negative constraint following ("don't change X" actually works)
- Temperature 0 for deterministic precision

**Gemini 2.5 Pro for creation:**
- #1 on WebDev Arena for aesthetics (human preference for web design)
- 1M token context window (no truncation needed)
- 35% cheaper than Claude for generation
- Free tier available (5 RPM, 100 RPD) for development
- GA status (stable, proven)

**Nano Banana Pro for images:**
- Only model that renders legible text in generated images
- Search-grounded (factually accurate diagrams)
- 4K resolution output
- $0.13-0.24 per image (reasonable for occasional use)
- Unique capability no other model provides

### Monthly Cost Estimate

**Usage: ~100 docs/month, ~4 edits each, ~20 images, ~30 PPT exports**

| Model | Calls | Cost |
|-------|-------|------|
| Gemini 2.5 Pro (creation) | ~100 | $6.00 |
| Claude Sonnet 4.5 (edits) | ~400 | $12.00 |
| Claude Sonnet 4.5 (PPT export) | ~30 | $2.40 |
| Nano Banana Pro (images) | ~20 | $2.60 |
| **Total** | **~550** | **~$23/month** |

With prompt caching on Claude: **~$19/month**

---

## The Surgical Editing Revolution

### The Core Insight

Every major AI editing tool (Claude Artifacts, Cursor, Aider, OpenAI Codex) has converged on the same principle: **never ask the AI to regenerate content it shouldn't change.**

### How v1 Works (Broken)
```
User: "Change the title to Quarterly Report"
  ↓
System: Sends full HTML + request to Claude
  ↓
Claude: Regenerates entire 10,000+ token document
  ↓
Result: Title changed + formatting drifted + CSS values shifted + text reworded
```

### How v2 Works (Fixed)
```
User: "Change the title to Quarterly Report"
  ↓
System: Sends HTML (cached) + request + tool definitions to Claude
  ↓
Claude: Returns tool call:
  html_replace(
    old_text="<title>Monthly Summary</title>",
    new_text="<title>Quarterly Report</title>"
  )
  ↓
Server: Applies literal string replacement: html.replace(old, new, 1)
  ↓
Result: ONLY the title changed. Everything else physically untouched.
```

### Why This Eliminates Content Drift

- Claude outputs ~50 tokens (the tool call) instead of ~10,000 tokens (full document)
- The replacement is a **deterministic string operation** on the server, not AI generation
- The AI never has the opportunity to "improve" or "clean up" anything
- Temperature 0 ensures deterministic tool call generation
- Fuzzy matching fallback handles minor whitespace mismatches
- Validation layer catches any catastrophic failures

### Tools Defined

```python
tools = [
    html_replace(old_text, new_text)    # Find and replace (must match exactly once)
    html_insert_after(anchor_text, new_content)  # Insert after anchor point
    html_delete(text_to_delete)         # Remove text (must match exactly once)
]
```

### Fallback Chain
1. **Exact match** → apply replacement
2. **Fuzzy match** (strip whitespace, normalize) → apply replacement
3. **Sequence matching** (>85% similarity) → apply replacement
4. **All failed** → fall back to full regeneration with strong preservation prompt

---

## Data Model

### SQLite Schema

```sql
-- Sessions: one per user conversation
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,                    -- UUID
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP,
    metadata TEXT                           -- JSON: color_scheme, preferences
);

-- Documents: multiple per session
CREATE TABLE documents (
    id TEXT PRIMARY KEY,                    -- UUID
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    title TEXT DEFAULT 'Untitled',
    is_active BOOLEAN DEFAULT TRUE,         -- Currently selected document
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Document versions: append-only, enables unlimited undo/redo
CREATE TABLE document_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    html_content TEXT NOT NULL,
    user_prompt TEXT,                        -- What the user asked
    edit_summary TEXT,                       -- Brief description of what changed
    model_used TEXT,                         -- Which AI model generated this version
    tokens_used INTEGER,                    -- For cost tracking
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(document_id, version)
);

-- Chat messages: the conversation thread
CREATE TABLE chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    document_id TEXT REFERENCES documents(id),  -- Which doc this message relates to
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    message_type TEXT DEFAULT 'text',        -- text, edit_confirmation, error
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Cost tracking: aggregated per model per day
CREATE TABLE cost_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,                      -- YYYY-MM-DD
    model TEXT NOT NULL,                     -- claude-sonnet-4-5, gemini-2.5-pro, nano-banana-pro
    request_count INTEGER DEFAULT 0,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    images_generated INTEGER DEFAULT 0,
    estimated_cost_usd REAL DEFAULT 0,
    UNIQUE(date, model)
);

-- Custom templates: user-saved document templates
CREATE TABLE templates (
    id TEXT PRIMARY KEY,                    -- UUID
    name TEXT NOT NULL,
    description TEXT,
    html_content TEXT NOT NULL,
    thumbnail_base64 TEXT,                  -- Mini preview image
    created_by TEXT,                        -- Username (optional)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for common queries
CREATE INDEX idx_documents_session ON documents(session_id);
CREATE INDEX idx_versions_document ON document_versions(document_id);
CREATE INDEX idx_messages_session ON chat_messages(session_id);
CREATE INDEX idx_cost_date ON cost_tracking(date);
```

### Key Design Decisions

1. **Append-only versions**: Every edit creates a new version row. Undo = load previous version. No data loss.
2. **Multi-document sessions**: `documents` table links to `sessions`. Users can create multiple docs in one conversation.
3. **Cost tracking by model by day**: Simple aggregation for the cost dashboard. No per-request event storage (simpler than v1's analytics).
4. **Custom templates**: Users can save documents as reusable templates.
5. **Cascade deletes**: Deleting a session cleans up all related data automatically.

---

## Backend Project Structure (New)

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI app, static file serving, startup/shutdown
│   ├── config.py                   # Pydantic settings (env vars)
│   ├── database.py                 # SQLite connection, migrations, WAL mode
│   │
│   ├── models/                     # Pydantic models (request/response schemas)
│   │   ├── __init__.py
│   │   ├── session.py              # Session, Document, Version schemas
│   │   ├── chat.py                 # ChatRequest, ChatResponse, SSE event schemas
│   │   └── export.py               # ExportRequest, ExportResponse schemas
│   │
│   ├── providers/                  # LLM provider interface + implementations
│   │   ├── __init__.py
│   │   ├── base.py                 # LLMProvider ABC, ImageProvider ABC
│   │   ├── anthropic_provider.py   # Claude Sonnet 4.5 (edits + PPT)
│   │   ├── gemini_provider.py      # Gemini 2.5 Pro (creation)
│   │   └── gemini_image_provider.py # Nano Banana Pro (images)
│   │
│   ├── services/                   # Business logic
│   │   ├── __init__.py
│   │   ├── router.py               # Model routing (3 rules)
│   │   ├── editor.py               # Tool-based surgical editing engine
│   │   ├── creator.py              # Document creation service
│   │   ├── image_service.py        # Image generation + embedding
│   │   ├── session_service.py      # Session/document/version management
│   │   └── cost_tracker.py         # Per-model cost aggregation
│   │
│   ├── api/                        # API endpoints
│   │   ├── __init__.py
│   │   ├── chat.py                 # POST /api/chat/{session_id} + SSE streaming
│   │   ├── sessions.py             # Session CRUD, document management
│   │   ├── export.py               # PPTX, PDF, HTML export endpoints
│   │   ├── templates.py            # Template CRUD
│   │   ├── upload.py               # File upload processing
│   │   ├── costs.py                # Cost tracking dashboard API
│   │   └── health.py               # Health check
│   │
│   └── utils/                      # Shared utilities
│       ├── __init__.py
│       ├── fuzzy_match.py          # Aider-style fuzzy string matching
│       ├── html_validator.py       # Post-edit HTML validation
│       └── rate_limiter.py         # In-memory rate limiter
│
├── requirements.txt
├── Dockerfile
└── .env.example
```

### What's Removed (v1 → v2)

| Removed | Why |
|---------|-----|
| `services/claude_service.py` (1,200 lines) | Replaced by `providers/` + `services/editor.py` + `services/creator.py` (~300 lines total) |
| `services/redis_service.py` | Replaced by `database.py` (SQLite) |
| `services/memory_store.py` | No longer needed (SQLite is persistent) |
| `services/analytics_service.py` | Replaced by `services/cost_tracker.py` (much simpler) |
| `api/websocket.py` (569 lines) | Replaced by `api/chat.py` with SSE (~100 lines) |
| `middleware/auth.py` (JWT) | Auth handled by Nginx Proxy Manager, not the application |
| `api/admin/` (entire directory) | Replaced by simple `api/costs.py` |

**Estimated reduction: ~2,500 lines of backend code removed, ~800 lines of new code added.**

---

## Frontend Changes Summary

### Keep (What Works)
- Split-pane layout (chat left, preview right)
- Dark mode support
- Professional color palette
- React 19 + TypeScript + Vite

### Add
- **CodeMirror 6**: Syntax highlighting in code view
- **Streamdown**: Streaming markdown rendering in chat
- **Version history**: Timeline/slider to browse document versions
- **Multi-document tabs**: Tab bar or sidebar for switching between documents
- **Copy buttons**: On code view and chat messages
- **"Add Visual" button**: Triggers Nano Banana Pro image generation
- **Smart starter prompts**: Template cards on empty state
- **Export dropdown**: HTML / PPTX / PDF options
- **File upload area**: Drag-drop zone for documents and data files
- **Cost tracker page**: Simple usage/cost display

### Remove
- Admin dashboard (replaced by cost tracker)
- Admin login/JWT system (auth is now Nginx Proxy Manager)
- WebSocket connection management (replaced by SSE)
- Template modal (replaced by inline starter prompts)

---

## Implementation Phases

### Phase 1: Backend Foundation (Plan 001) - COMPLETE
**Goal**: New project structure, SQLite, provider interface, SSE streaming
**Effort**: ~3-5 days
**Outcome**: Backend skeleton that compiles, serves static files, handles SSE
**Completed**: February 12, 2026 - 14 new files, 29/29 tests passing. See "Implementation Notes" section at the end of Plan 001 for deviations from the original code listings (aiosqlite cursor pattern, Pydantic v2 config, etc.)

### Phase 2: Surgical Editing Engine (Plan 002)
**Goal**: Tool-based editing with Claude Sonnet 4.5
**Effort**: ~3-4 days
**Outcome**: Users can edit HTML without content drift
**Dependencies**: Plan 001

### Phase 3: Multi-Model Routing (Plan 003)
**Goal**: Gemini 2.5 Pro for creation, Nano Banana Pro for images, model router
**Effort**: ~3-4 days
**Outcome**: Best model used for each task automatically
**Dependencies**: Plan 001

### Phase 4: Frontend Enhancements (Plan 004)
**Goal**: CodeMirror 6, Streamdown, version history, multi-doc UI
**Effort**: ~5-7 days
**Outcome**: Modern, polished frontend with all UX gaps filled
**Dependencies**: Plan 001

### Phase 5: Export Pipeline (Plan 005)
**Goal**: PPTX export (Claude-generated), PDF export (Playwright)
**Effort**: ~3-4 days
**Outcome**: Users can export to PowerPoint and PDF
**Dependencies**: Plans 002, 003

### Phase 6: File Upload & Templates (Plan 006)
**Goal**: Document/data file upload, smart starter prompts, custom templates
**Effort**: ~3-4 days
**Outcome**: Users can upload files and use/save templates
**Dependencies**: Plans 001, 004

### Phase 7: Deployment & Security (Plan 007)
**Goal**: Docker single-container build, Nginx Proxy Manager integration, cost tracker
**Effort**: ~2-3 days
**Outcome**: Production-ready deployment on Debian server
**Dependencies**: All above

### Total Estimated Effort: ~22-31 days

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Claude tool_use fails on complex HTML | Fuzzy matching fallback + full regeneration as last resort |
| Gemini 2.5 Pro produces lower quality than Claude | Can swap to Claude for creation via config change |
| Nano Banana Pro API changes (preview status) | Image generation is optional; tool works without it |
| SQLite write contention with concurrent users | WAL mode handles this; 2-5 users is well within SQLite's limits |
| Playwright adds container size (~1.5GB) | Can split into sidecar container if needed |
| dom-to-pptx client-side alternative needed | Architecture supports adding client-side export later |

---

## Code Cleanup Policy

**Principle**: Each plan deletes the old v1 files it replaces. No dead code is carried forward. Clean as you go.

| Old v1 File | Deleted In | Replaced By |
|-------------|-----------|-------------|
| `services/redis_service.py` | Plan 001 | `database.py` (SQLite) |
| `services/memory_store.py` | Plan 001 | `database.py` (SQLite) |
| `services/analytics_service.py` | Plan 001 | `services/cost_tracker.py` |
| `services/file_processor.py` | Plan 001 | Removed (deprecated) |
| `middleware/` (entire dir) | Plan 001 | NPM auth (no app code) |
| `api/admin/` (entire dir) | Plan 001 | `api/costs.py` |
| `api/endpoints/upload.py` | Plan 001 | Removed (deprecated) |
| `api/websocket.py` | Plan 001 | `api/chat.py` (SSE) |
| `models/analytics.py` | Plan 001 | `cost_tracking` table |
| `core/` (entire dir) | Plan 001 | `app/config.py` |
| `services/claude_service.py` | Plan 002 | `services/editor.py` + `providers/anthropic_provider.py` |
| `services/artifact_manager.py` | Plan 002 | `services/session_service.py` (versions) |
| `models/session.py` | Plan 002 | `models/session.py` (new) |
| `models/schemas.py` | Plan 002 | `models/chat.py` (new) |
| `utils/logger.py` | Plan 002 | structlog config in `main.py` |
| `utils/sanitizer.py` | Plan 002 | `utils/html_validator.py` |
| `api/endpoints/health.py` | Plan 003 | `api/health.py` (new) |
| `api/endpoints/export.py` | Plan 003 | `api/export.py` (new, Plan 005) |

**Final verification in Plan 007**: Confirm zero old v1 files remain in `backend/app/`.

---

## Success Criteria

The rebuild is successful when:

1. **Content preservation**: User says "change the title" → only the title changes (no drift)
2. **Unlimited edits**: Users can iterate 20+ times on a document without degradation
3. **Multi-document sessions**: Users can create and switch between documents in one conversation
4. **PPT export**: Users can export to editable PowerPoint
5. **Version history**: Users can undo/redo any edit
6. **Image generation**: Users can add infographics/diagrams to documents
7. **File upload**: Users can upload .docx, .csv, etc. as content source
8. **Sub-10-second response time**: Edits complete in under 5 seconds, creation in under 10
9. **Monthly cost under $30**: For typical team usage (~100 docs/month)
10. **Single `docker-compose up`**: Deployment is one container (app), behind existing Nginx Proxy Manager

---

## Non-Goals (Explicitly Out of Scope)

- Real-time collaboration between users
- User accounts / registration system
- Public-facing deployment
- Mobile-optimized experience (desktop-first, responsive is sufficient)
- Integration with external services (Slack, Teams, etc.)
- AI model fine-tuning
- Self-hosted open-source LLMs

---

*Created: February 12, 2026*
*Based on: Product review, architecture research, model landscape analysis, surgical editing research*
*Decision participants: Project owner + Claude analysis*
