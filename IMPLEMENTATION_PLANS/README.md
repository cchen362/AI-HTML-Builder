# Implementation Plans - AI HTML Builder Rebuild

This folder contains strict implementation guides for the complete rebuild of the AI HTML Builder application.

## Purpose

These documents serve as **actionable blueprints** that must be followed exactly. Each plan covers a specific phase of the rebuild, with clear dependencies, step-by-step instructions, and verification criteria.

## Document Format

Each implementation plan includes:
- **Stop warning** - Read before coding
- **Context & rationale** - Why this change is being made
- **Strict rules** - MUST DO / MUST NOT DO lists
- **Step-by-step instructions** - Exact file paths, code examples, implementation details
- **Dependencies** - What must be completed before this phase
- **Build verification** - Commands to run after each change
- **Testing scenarios** - Specific pass/fail criteria
- **Rollback plan** - How to undo if something breaks
- **Sign-off checklist** - Completion tracking

## Current Plans

| # | Name | Status | Dependencies | Description |
|---|------|--------|-------------|-------------|
| 000 | [Master Rebuild Plan](./000_MASTER_REBUILD_PLAN.md) | **Ready** | None | Architecture decisions, model strategy, full phase overview |
| 001 | [Backend Foundation](./001_BACKEND_FOUNDATION.md) | **COMPLETE** | 000 | SQLite, provider interface, SSE streaming, project structure |
| 002 | [Surgical Editing Engine](./002_SURGICAL_EDITING_ENGINE.md) | **COMPLETE** | 001 | Tool-based editing, fuzzy matching, validation, request classifier |
| 003 | [Multi-Model Routing](./003_MULTI_MODEL_ROUTING.md) | **COMPLETE** | 001 | Gemini 2.5 Pro integration, Nano Banana Pro, model router |
| 004 | [Frontend Enhancements](./004_FRONTEND_ENHANCEMENTS.md) | **COMPLETE** | 001 | CodeMirror 6, Streamdown, version history, multi-doc UI |
| 005 | [Export Pipeline](./005_EXPORT_PIPELINE.md) | **COMPLETE** | 002, 003 | PPTX (Claude-generated), PDF (Playwright), extensible exporter |
| 006 | [File Upload & Templates](./006_FILE_UPLOAD_AND_TEMPLATES.md) | **COMPLETE** | 001, 004 | Upload processing, smart starter prompts, custom templates |
| 007 | [Template Optimization](./007_TEMPLATE_OPTIMIZATION.md) | **COMPLETE** | 006 | Rewrite templates, fix placeholder bug, bump token limit, add Stakeholder Brief & BRD |
| 008 | [Deployment & Security](./008_DEPLOYMENT_AND_SECURITY.md) | **Ready** | All above | Docker single-container, Nginx Proxy Manager, cost tracker |
| 009a | [Visual Foundation](./009a_VISUAL_FOUNDATION.md) | **COMPLETE** | 001-007 | "Obsidian Terminal" theme, CSS custom properties, dark/light toggle, typography, animations |
| 009b | [Viewer Pane & UX Polish](./009b_VIEWER_PANE_UX_POLISH.md) | **COMPLETE** | 009a, 005, 006, 007 | Export wiring (PPTX/PDF/PNG), loading skeleton, version restore, doc management, cancel button, drag-drop |
| 010 | [Nano Banana Pro Upgrade](./010_NANO_BANANA_PRO_UPGRADE.md) | **COMPLETE** | 003 | Image model upgrade with fallback |
| 011 | [Remove Custom Templates](./011_REMOVE_CUSTOM_TEMPLATES.md) | **COMPLETE** | 006 | Remove custom template feature (no auth) |
| 012 | [Architecture Refactoring](./012_ARCHITECTURE_REFACTORING.md) | **COMPLETE** | 001-011 | Dead code deletion, export consolidation, template consolidation, chat.py extraction |
| 013 | [UX Improvements](./013_UX_IMPROVEMENTS.md) | **COMPLETE** | 012 | Template badge system, styled confirm dialogs, new session menu, editable CodeMirror, loading state, send debounce, doc name badges |

## Dependency Graph

```
000 Master Plan
 └── 001 Backend Foundation
      ├── 002 Surgical Editing Engine ──┐
      ├── 003 Multi-Model Routing ──────┤
      ├── 004 Frontend Enhancements     ├── 005 Export Pipeline
      │    └── 006 File Upload &        │
      │         Templates               │
      │         └── 007 Template        │
      │              Optimization       │
      └────────────────────────────────>008 Deployment & Security
      │
      ├── 001-007 ─────────────────>009a Visual Foundation (theme system)
      │                                └── 009b Viewer Pane & UX Polish
```

## How to Use

1. **Read Plan 000 (Master Plan) first** - Understand the full architecture
2. **Follow plans IN ORDER** of dependencies
3. **Read the entire document** before starting each plan
4. **Follow steps IN ORDER** - No skipping
5. **Run build verification** after each file change
6. **Mark checkboxes** as you complete each step
7. **Update the document** with any issues found

## Key Architecture Decisions (Summary)

| Decision | Choice |
|----------|--------|
| Models | Claude Sonnet 4.5 (edits) + Gemini 2.5 Pro (creation) + Nano Banana Pro (images) |
| Editing approach | Tool-based (html_replace via Claude tool_use) - NOT full regeneration |
| Database | SQLite (WAL mode) - replaces Redis |
| Streaming | SSE + HTTP POST - replaces WebSocket |
| Auth | Nginx Proxy Manager (existing on server) - replaces JWT |
| Frontend | React 19 + CodeMirror 6 + Streamdown |
| Export | PPTX (Claude python-pptx) + PDF (Playwright) |
| Docker | Single app container behind Nginx Proxy Manager |

## Code Cleanup Policy

Each plan is responsible for deleting the old v1 files it replaces. No dead code is carried forward.

- **Plan 001**: Deletes Redis, memory store, analytics, admin, websocket, JWT middleware, deprecated upload
- **Plan 002**: Deletes claude_service.py, artifact_manager.py, old models/session.py, schemas.py, logger, sanitizer
- **Plan 003**: Deletes old api/endpoints/health.py and export.py
- **Plan 008**: Final verification that zero old v1 files remain

See the "Code Cleanup Policy" section in [000_MASTER_REBUILD_PLAN.md](./000_MASTER_REBUILD_PLAN.md) for the full ownership table.

---

*Created: February 12, 2026*
*Project: AI HTML Builder Rebuild*
