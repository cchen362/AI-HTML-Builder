# Implementation Plan 023: My Sessions Modal Overhaul

## Status: PENDING

---

## STOP — READ THIS FIRST

**DO NOT START** this implementation until:
- Plans 001–022 are FULLY complete (they are)
- You have read this ENTIRE document
- You understand the 4 phases and their dependencies

**This plan emerged from a UX review** of the My Sessions modal. Three major problems were identified: (1) session titles are raw template prompts, not meaningful names, (2) the flat row list is visually monotonous and hard to scan, (3) document types aren't tracked, so sessions with mixed content (docs + infographics) all look identical.

**PHASE DEPENDENCIES:**
- Phase 1 (Backend) must complete first — provides AI titles, doc_type column, and title_source tracking
- Phase 2 (Frontend SSE + Timezone) depends on Phase 1 backend changes
- Phase 3 (Visual Redesign) depends on Phase 2 type updates
- Phase 4 (Testing + Deploy) depends on all previous phases
- Recommended order: 1 → 2 → 3 → 4 (sequential)

**EACH PHASE = ONE SESSION/COMMIT.** Do not combine phases.

**CORE DESIGN PRINCIPLE: Clean Foundation.**
Refactor along the way. Every phase must leave the codebase cleaner than it found it:
- When restructuring a component, **delete** the old CSS rules — don't leave dead code
- When adding new patterns, **consolidate** with existing ones where possible
- No tech debt by choice. Strip noise, preserve signal.

---

## Workshop Decisions Summary

| Problem | Decision | Phase |
|---------|----------|-------|
| Session titles show raw template prompts like `Create a polished stakeholder brief from the following content: {{CONTENT}} IMP` | AI-generated 3-5 word titles via Haiku 4.5 after first AI response (~$0.0001/session) | 1 |
| AI title might conflict with manual renames (header + modal) | `title_source` metadata: `auto` → `ai` → `manual`. AI only fires on `auto`, never overwrites `manual` | 1 |
| Documents have no type — can't distinguish infographics from regular docs in session list | New `doc_type` column on `documents` table (`document` \| `infographic`) | 1 |
| Flat row list is monotonous, no visual hierarchy | Card grid layout (3 columns, ~9 visible before scroll, time-grouped sections) | 3 |
| Checkboxes always visible but rarely used | Select mode toggle — checkboxes hidden by default, appear on "Select" button click | 3 |
| "8h ago" shown for just-created sessions (timezone bug) | SQLite UTC timestamps missing `Z` suffix — JS interprets as local time. Fix: append `Z` | 2 |
| `3 docs` count reveals nothing about content mix | Split into `doc_count` + `infographic_count`, show typed badges per card | 1+3 |
| Filter/search and 30-day expiry policy | **Preserved** — search bar with count indicator, policy note in header, per-card expiry in footer | 3 |

---

## Phase 1: Backend — AI Titles + Document Types

### 1A. New file: `backend/app/services/title_generator.py`

Small service that calls Haiku 4.5 to produce a 3-5 word title from the user's first message.

```python
async def generate_session_title(user_message: str) -> str | None:
```

**Implementation details:**
- Reuse the lazy Anthropic client pattern from `router.py` (same `_get_client()` singleton)
- System prompt constrains output: 3-5 words, title case, no quotes/punctuation, focus on WHAT not HOW
- Examples in prompt: "Q3 Metrics Dashboard", "Sales Pitch Deck", "Team Onboarding Guide"
- `max_tokens=20`, `temperature=0`
- Strip base64 images via regex before sending (same `_BASE64_RE` pattern used in `chat.py`)
- Strip `{{PLACEHOLDER}}` template boilerplate before sending
- Truncate input to first 500 chars (Haiku doesn't need more for a title)
- Track cost via `cost_tracker.record_usage()` (Haiku pricing already in cost_tracker)
- Return `str | None` — catch all exceptions, never throw (safety for fire-and-forget pattern)
- Log success/failure via structlog

**Reference:** `backend/app/services/router.py` — same lazy client + Haiku + cost tracking pattern.

### 1B. Modify: `backend/app/services/session_service.py`

**Add `title_source` tracking** in session metadata JSON (no schema migration — just a new JSON key in existing metadata column):

1. In `add_chat_message()` (~line 395): when auto-title is set from first user message, also set `metadata["title_source"] = "auto"`
2. In `update_session_title()` (~line 353): add `source: str = "manual"` parameter, set `metadata["title_source"] = source`
3. In `get_user_sessions()` (~line 285): include `title_source` and `infographic_count` in returned summaries

**Title hierarchy** (higher priority source wins, AI never overwrites manual):

| Source | Meaning | Can AI overwrite? |
|--------|---------|-------------------|
| `"auto"` | Raw first-message text (truncated 80 chars) | YES — this is the target for AI improvement |
| `"ai"` | Haiku-generated 3-5 word title | NO — already done, don't regenerate |
| `"manual"` | User renamed via header or modal | NEVER — user's explicit choice is sacred |

**Modify `create_document()`**: Add `doc_type: str = "document"` parameter, store in new column.

**Modify `get_user_sessions()` SQL**: Add infographic count:
```sql
COUNT(d.id) as doc_count,
SUM(CASE WHEN d.doc_type = 'infographic' THEN 1 ELSE 0 END) as infographic_count
```

### 1C. Modify: `backend/app/api/chat.py`

Wire title generation into the SSE stream. In `event_stream()`, after the main handler completes but **before** yielding `{"type": "done"}`:

```python
# After all handler events yielded, before "done":
# 1. Read session metadata
# 2. If title_source is "auto" or missing → generate AI title
# 3. If title generated → save and yield SSE event
```

1. Fetch session metadata, check `title_source`
2. If `"auto"` (or missing for legacy sessions): `await generate_session_title(user_message)`
3. If title returned: `await session_service.update_session_title(sid, title, source="ai")`
4. Yield new SSE event: `{"type": "title", "content": "Q3 Metrics Dashboard"}`

**Why synchronous (not fire-and-forget)?**
- Haiku latency: ~100-200ms with `max_tokens=20` (trivial prompt)
- Imperceptible after 2-30 second main AI response
- Avoids race condition where `refreshDocuments()` fires before background task completes
- Title appears immediately in header via SSE event

**No conflict with manual rename:** Both header and modal rename call the same `PATCH /api/sessions/{sid}` endpoint → `update_session_title(sid, title, source="manual")`. Once set to `"manual"`, the title_source check in chat.py skips AI generation.

**Set `doc_type` on document creation:**
- `_handle_create`: pass `doc_type="document"` to `create_document()`
- `_handle_infographic`: pass `doc_type="infographic"` to `create_document()`

### 1D. Modify: `backend/app/database.py`

Add migration to `_MIGRATIONS` list:

```python
# Migration: Add doc_type column to documents table
(
    "ALTER TABLE documents ADD COLUMN doc_type TEXT DEFAULT 'document'",
    "doc_type_column",
)
```

**Backfill existing infographic docs** after migration: iterate all documents, check latest version HTML via `is_infographic_html()` from `html_validator.py`, update `doc_type = 'infographic'` for matches. Run as part of the migration (safe to re-run — idempotent UPDATE).

**Note:** SQLite CHECK constraint (`CHECK(doc_type IN ('document', 'infographic'))`) can't be added via ALTER TABLE. Skip the CHECK — enforce at application level in `create_document()`.

### 1E. New tests: `backend/tests/test_title_generator.py`

~6-8 tests:
1. `test_generate_title_success` — mock Anthropic, verify Haiku called with correct params, verify title returned
2. `test_generate_title_strips_base64` — pass message with base64, verify stripped before sending
3. `test_generate_title_strips_template_boilerplate` — pass `{{PLACEHOLDER}}` message, verify cleanup
4. `test_generate_title_truncates_long_message` — verify only first 500 chars sent
5. `test_generate_title_error_returns_none` — mock Anthropic to raise, verify None (no throw)
6. `test_generate_title_cost_tracked` — verify `cost_tracker.record_usage()` called
7. `test_title_source_auto_on_first_message` — verify `title_source="auto"` after `add_chat_message()`
8. `test_title_source_manual_on_rename` — verify `title_source="manual"` after `update_session_title()`
9. `test_ai_title_skipped_for_manual_source` — verify title_source="manual" prevents AI generation
10. `test_infographic_count_in_sessions` — verify `infographic_count` returned correctly

---

## Phase 2: Frontend — SSE Title + Timezone Fix

### 2A. Modify: `frontend/src/types/index.ts`

Add `'title'` to SSE event type union:
```typescript
export interface SSEEvent {
  type: 'status' | 'chunk' | 'html' | 'summary' | 'error' | 'done' | 'title';
  // ...
}
```

Update `SessionSummary`:
```typescript
export interface SessionSummary {
  id: string;
  title: string;
  doc_count: number;
  infographic_count: number;     // NEW — count of infographic docs
  first_message_preview: string;
  last_active: string;
  created_at: string;
  title_source?: 'auto' | 'ai' | 'manual';  // NEW — how the title was set
}
```

### 2B. Modify: `frontend/src/hooks/useSSEChat.ts`

Handle new `'title'` SSE event in the event processing switch:
```typescript
case 'title':
  if (event.content) setSessionTitle(event.content);
  break;
```

Two lines. The title updates in the header immediately. The My Sessions modal picks it up on next open via `listSessions()`.

### 2C. Fix timezone bug: `frontend/src/components/HomeScreen/sessionUtils.ts`

**Bug:** SQLite `CURRENT_TIMESTAMP` stores UTC timestamps without `Z` suffix (e.g., `"2026-02-19 06:30:00"`). JavaScript's `new Date()` interprets strings without timezone suffix as **local time**. In Singapore (UTC+8), this makes sessions appear 8 hours older than reality — a just-created session shows "8h ago".

**Fix:** Force UTC interpretation by appending `Z`:
```typescript
// Helper to parse UTC timestamps from SQLite
function parseUTC(dateStr: string): number {
  return new Date(dateStr.endsWith('Z') ? dateStr : dateStr + 'Z').getTime();
}
```

Apply to:
- `relativeTime()` line 4: `const then = parseUTC(dateStr);`
- `daysUntilExpiry()` line 22: `const expiresAt = parseUTC(lastActive) + 30 * 86400000;`

---

## Phase 3: Visual Redesign — Card Grid Modal

### 3A. Modify: `frontend/src/components/HomeScreen/sessionUtils.ts`

Add time grouping utility:
```typescript
export type TimeGroup = 'Today' | 'This Week' | 'This Month' | 'Earlier';

export function getTimeGroup(dateStr: string): TimeGroup {
  // Use parseUTC helper from 2C
  // Compare against current date boundaries
}

export function groupSessionsByTime(sessions: SessionSummary[]): Map<TimeGroup, SessionSummary[]> {
  // Group sessions, maintaining order within each group
  // Omit empty groups
}
```

### 3B. Overhaul: `frontend/src/components/HomeScreen/MySessionsModal.tsx`

**Transform from flat row list to card grid layout.**

**Modal structure (top to bottom):**
```
+------------------------------------------------------------------+
|  [] My Sessions (12)                              [Select]    x  |
|  Sessions are automatically removed after 30 days of inactivity  |
|  [search] Filter sessions...                3 of 12 sessions     |
+------------------------------------------------------------------+
|                                                                   |
|  TODAY                                                            |
|  +--------------+  +--------------+  +--------------+             |
|  |              |  |              |  |              |             |
|  |  Card 1      |  |  Card 2      |  |  Card 3      |             |
|  |              |  |              |  |              |             |
|  +--------------+  +--------------+  +--------------+             |
|                                                                   |
|  THIS WEEK                                                        |
|  +--------------+  +--------------+                               |
|  |              |  |              |                               |
|  |  Card 4      |  |  Card 5      |                               |
|  |              |  |              |                               |
|  +--------------+  +--------------+                               |
|                                                                   |
|  ... scrollable ...                                               |
|                                                                   |
+------------------------------------------------------------------+
|  [Bulk bar -- only visible in select mode]                        |
+------------------------------------------------------------------+
```

**Modal specs:**
- Width: ~1060px (up from 860px)
- Max height: 80vh (unchanged)
- Header: "My Sessions" + total count in parens + "Select" toggle button + close button
- Policy note: italic, monospace, "Sessions are automatically removed after 30 days of inactivity"
- Search bar: existing filter input + count indicator "3 of 12 sessions" (shown when filtering)
- Card grid: `display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem;`
- ~3 visible rows (9 cards) before scrolling
- Time group headers: full-width, sticky, uppercase, monospace, subtle bottom border
- Bulk action bar: fixed at modal bottom, only visible in select mode
- Load more: pagination trigger at bottom of scroll area (existing pattern)

**Individual card design (~180px tall x ~320px wide):**
```
+------------------------------+
|  []                     [e][d]|  <- Top: checkbox (select mode) + hover actions (top-right)
|                               |
|  Stakeholder Brief            |  <- Title: --font-display, bold, 2-line clamp
|                               |
|  Polished executive summary   |  <- Subtitle: first_message_preview
|  of Q4 quarterly results...   |     --font-body, --fs-xs, --text-tertiary, 2-line clamp
|                               |     Only shown if different from title
|                               |
|  [doc 2]  [infographic 1]    |  <- Doc type badges (mini colored pills)
|                               |     Green for docs, coral for infographics
|                               |     Only show badges with count > 0
|  9h ago              30d left |  <- Footer: --font-mono, --fs-xs, space-between
|                               |     Expiry color: green (>14d), mint (7-14d), red (<7d)
+------------------------------+
```

**Card states:**
- **Default**: `--surface-raised` background, `1px solid var(--border-subtle)`, `var(--radius-lg)` corners
- **Hover**: `translateY(-2px)` lift + `border-color: var(--accent-primary-muted)` + subtle box-shadow glow
- **Current session**: 3px mint green left border + "Current" badge (small pill, top area)
- **Selected (select mode)**: Checkbox visible in top-left, `border-color: var(--accent-primary)` highlight
- **Empty (0 docs)**: `opacity: 0.5`, no doc badges, "(empty)" text in badge area
- **Click**: Navigates to session (calls `onSelectSession(session.id)`)

**Hover overlay actions:**
- Pencil icon (rename) + trash icon (delete) appear in top-right corner on card hover
- `opacity: 0` by default, `opacity: 1` on `.session-card:hover`
- Click pencil → inline rename (title becomes editable input)
- Click trash → delete confirmation dialog (reuse existing pattern)

**Select mode:**
- "Select" ghost button in modal header toggles `selectMode` state
- When active: button shows "Cancel" + accent color, checkboxes appear in top-left of each card
- Select-all checkbox in header (next to "My Sessions" title)
- Bulk delete bar at bottom with count + "Delete Selected" button
- Escape key exits select mode (existing keyboard handler pattern)

**Doc type badges:**
- Regular docs: green pill with doc icon + count where count = `doc_count - infographic_count`
- Infographics: coral pill with palette icon + count where count = `infographic_count`
- Only show badges with count > 0
- If both counts > 0, show both side by side
- If total = 0, show "(empty)" in muted text instead

**Inline rename (preserved from current):**
- Double-click title text → transforms to input field
- Enter saves (calls `api.updateSessionTitle()`)
- Escape cancels
- Blur saves
- Same UX as current row rename, just in card context

### 3C. Overhaul: `frontend/src/components/HomeScreen/MySessionsModal.css`

**Complete CSS rewrite.** Delete all existing row-based styles, replace with card grid:

- `.sessions-panel`: max-width 1060px (up from 860px)
- `.sessions-grid`: CSS Grid, 3 columns, 1rem gap
- `.session-card`: flex column, padding, rounded corners, border, hover transition
- `.session-card:hover`: translateY(-2px), border glow, elevated shadow
- `.session-card--current`: 3px mint left border
- `.session-card--empty`: opacity 0.5
- `.session-card--selected`: accent border
- `.session-card-title`: font-display, bold, 2-line webkit-line-clamp
- `.session-card-subtitle`: font-body, xs, tertiary, 2-line clamp
- `.session-card-badges`: flex row, gap
- `.session-card-badge--doc`: green background pill
- `.session-card-badge--infographic`: coral background pill
- `.session-card-footer`: flex, space-between, mono, xs
- `.session-card-actions`: absolute top-right, opacity 0 → 1 on card hover
- `.session-card-checkbox`: absolute top-left, hidden by default, shown in select mode
- `.session-group-header`: full-width (grid-column: 1/-1), sticky, uppercase, mono, border-bottom
- `.sessions-select-btn`: ghost button style, accent when active
- `.sessions-filter-count`: mono, xs, tertiary
- `.sessions-bulk-bar`: fixed at modal bottom, flex, select mode only
- Animations: `materialize` for cards, staggered `animation-delay` per card

---

## Phase 4: Integration + Testing + Deploy

### Backend verification
```bash
cd backend && pytest          # 375+ existing + ~10 new tests
ruff check .                  # Linting
mypy .                        # Type checking
```

### Frontend verification
```bash
cd frontend && npm run lint   # ESLint
npm run build                 # TypeScript + Vite build
```

### Manual testing checklist
1. Create new session → send message → verify AI title appears in header ~200ms after response
2. Open My Sessions → verify card grid layout with 3 columns and time groups
3. Create session with infographic + regular doc → verify typed badges show doc + infographic counts
4. Rename via header → reopen modal → verify updated title shown on card
5. Rename via modal (double-click title) → verify header shows updated title
6. Send another message in renamed session → verify AI does NOT overwrite manual title
7. Toggle select mode → select cards → verify bulk delete works
8. Type in filter → verify count shows "X of Y sessions" → verify cards filter
9. Verify timezone: create new session → should show "just now" (NOT "8h ago")
10. Verify 0-doc sessions show faded card with "(empty)"
11. Test hover → verify action icons (rename/delete) appear on card hover
12. Test delete single card via hover trash icon → verify confirmation → verify removal
13. Verify "30d left" expiry still shows in card footer with correct color coding
14. Verify policy note "Sessions are automatically removed after 30 days of inactivity" in header

### Deploy
```bash
git push  # Then on server:
# cd ~/aihtml && ./deploy.sh
```
Verify on `clhtml.zyroi.com`

---

## Files Changed

| File | Action | Phase |
|------|--------|-------|
| `backend/app/services/title_generator.py` | **NEW** — Haiku 4.5 title generation service | 1 |
| `backend/tests/test_title_generator.py` | **NEW** — ~10 tests for title gen + title_source + doc_type | 1 |
| `backend/app/services/session_service.py` | Modify — title_source tracking, doc_type param, infographic_count query | 1 |
| `backend/app/api/chat.py` | Modify — wire title gen + SSE title event, pass doc_type to create_document | 1 |
| `backend/app/database.py` | Modify — add doc_type migration to `_MIGRATIONS` + backfill | 1 |
| `frontend/src/types/index.ts` | Modify — add `'title'` SSE type, update SessionSummary | 2 |
| `frontend/src/hooks/useSSEChat.ts` | Modify — handle `'title'` SSE event (2 lines) | 2 |
| `frontend/src/components/HomeScreen/sessionUtils.ts` | Modify — timezone fix (parseUTC), time grouping utils | 2+3 |
| `frontend/src/components/HomeScreen/MySessionsModal.tsx` | **Full rewrite** — card grid layout | 3 |
| `frontend/src/components/HomeScreen/MySessionsModal.css` | **Full rewrite** — card grid CSS | 3 |

### Database migration
- `ALTER TABLE documents ADD COLUMN doc_type TEXT DEFAULT 'document'` — added to `_MIGRATIONS` in `database.py`
- Backfill: detect existing infographics via `is_infographic_html()`, update `doc_type = 'infographic'`
- No other schema changes — `title_source` lives in existing `sessions.metadata` JSON

### Key reference files (patterns to reuse)
- `backend/app/services/router.py` — Haiku 4.5 lazy client singleton + cost tracking pattern
- `backend/app/utils/html_validator.py` — `is_infographic_html()` for backfill detection
- `backend/app/providers/anthropic_provider.py` — Anthropic SDK usage reference
- `frontend/src/components/HomeScreen/SessionCard.tsx` — Home screen card component (separate, unchanged)
- `frontend/src/components/HomeScreen/sessionUtils.ts` — Existing time utils to extend
