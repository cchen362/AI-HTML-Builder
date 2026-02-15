# Implementation Plan 022: Post-Implementation UI/UX Polish

## Status: ALL PHASES COMPLETE

---

## STOP — READ THIS FIRST

**DO NOT START** this implementation until:
- Plans 001–021 are FULLY complete (they are)
- You have read this ENTIRE document
- You understand the 3 phases and their refactoring mandates

**This plan emerged from a UX workshop** reviewing the post-Plan-021 state. Three areas of the UI were identified as needing polish: the login page, the home screen session experience, and the My Sessions modal.

**PHASE DEPENDENCIES:**
- Phase 1 (Login) is independent — can be done in any order
- Phase 2 (Home Screen + Header) is independent of Phase 1
- Phase 3 (Modal) is independent of Phase 1 and Phase 2
- Recommended order: 1 → 2 → 3 (login is self-contained, easiest to verify)

**EACH PHASE = ONE SESSION/COMMIT.** Do not combine phases.

**CORE DESIGN PRINCIPLE: Clean Foundation.**
Refactor along the way. Every phase must leave the codebase cleaner than it found it:
- When restructuring a component, **delete** the old CSS rules — don't leave dead code
- When adding new patterns, **consolidate** with existing ones where possible
- No tech debt by choice. No "we'll clean this up later."
- Strip noise, preserve signal. If something is unused after a change, remove it immediately.

**DESTRUCTIVE ACTIONS PROHIBITED:**
- Do NOT change AI model routing, editing engine, or creation pipeline
- Do NOT change database schema
- Do NOT modify export pipeline logic

**BACKEND DEVIATION (Phase 2, approved):**
The original plan said "Do NOT modify backend code." Phase 2C (editable session title) required the session title in `GET /api/sessions/{sid}`, which only returned `session_id`, `documents`, `active_document`. A small backend tweak was approved:
- Added `get_session_title()` to `session_service.py` (reads title from metadata JSON)
- Added `title` field to `GET /api/sessions/{sid}` response in `sessions.py`
- Added `title: string` to frontend `Session` type in `types/index.ts`
This is read-only (no schema change, no new endpoint) and all 375 tests still pass.

---

## Workshop Decisions Summary

| Observation | Decision | Implementation |
|-------------|----------|----------------|
| Login left panel feels empty, orbs barely move | Full-bleed hero + 5 orbs + centered card | Phase 1 |
| Missing glyph icon on first feature bullet | Replace text icons with inline SVGs | Phase 1 |
| No "Welcome back" greeting on home screen | Add personalized greeting from user.display_name | Phase 2 |
| Session cards look bare vs template cards | Redesign with icon, hover glow, template-card quality | Phase 2 |
| Session titles are ugly raw prompts | Backend already auto-titles with template name; add editable title in header | Phase 2 |
| "Add Visual" button adds no real value | Remove it — just prepends text, router handles image intent naturally | Phase 2 |
| My Sessions modal is bare minimum | Widen, add search, enrich rows, multi-select bulk delete | Phase 3 |

### Key Discovery: Session Auto-Title Already Works
The backend (`session_service.py:395`) already prefers `template_name` over raw prompt for auto-title. New template-based sessions get clean titles like "Stakeholder Brief". The ugly titles in the screenshots are legacy data from before Plan 021. The editable header in Phase 2 lets users fix old titles.

---

## Phase 1: Login Page — Full-Bleed Hero Layout

### Goal
Replace the rigid 45/55 split-screen layout with a full-bleed hero page. Centered floating form card. 5 animated orbs across the entire viewport. Bigger, bolder branding. Fixed SVG feature icons.

### 1A. Restructure Layout
**Files:** `frontend/src/components/Auth/LoginPage.tsx`, `frontend/src/components/Auth/SetupPage.tsx`, `frontend/src/components/Auth/Auth.css`

**Current:** `.auth-layout` is a flex row with `.auth-left` (45%) and `.auth-right` (55%).

**New:** Single-column centered layout.

```
.auth-layout (full viewport, relative, overflow hidden, centered gradient bg)
  .auth-orb x5 (positioned absolutely, z-index 0)
  .auth-center (z-index 2, centered flex column, max-width ~440px)
    .auth-branding (title, subtitle, feature bullets — bigger typography)
    .auth-form-container (frosted glass card: backdrop-filter blur, semi-transparent bg, border)
```

**Refactoring mandate:**
- DELETE `.auth-left` and `.auth-right` CSS rules entirely — they become dead code
- DELETE the `width: 45%` / `width: 55%` split — replaced by single centered column
- CONSOLIDATE: `.auth-layout` becomes the background container (absorbs `.auth-left`'s gradient)
- The frosted card effect on `.auth-form-container` replaces `.auth-right`'s solid surface-base background

**Typography scale-up:**
- `.auth-branding-title`: `2.25rem` → `3rem` or `3.5rem`
- `.auth-branding-subtitle`: `--fs-sm` → `--fs-base`, wider letter-spacing
- `.auth-features`: more vertical gap (`1rem` → `1.25rem`)

### 1B. 5 Orbs with Noticeable Motion
**File:** `frontend/src/components/Auth/Auth.css`

Replace the single `@keyframes orb-float` with 5 unique keyframe sets. Each orb gets a distinct animation name, duration, and path.

| Orb | CSS Class | Color Var | Size | Duration | Translate Range | Blur | Position |
|-----|-----------|-----------|------|----------|----------------|------|----------|
| Gold | `auth-orb--gold` | `--accent-primary` | 400px | 11s | ±100px | 90px | top: 10%, left: 15% |
| Mint | `auth-orb--mint` | `--signal-active` | 300px | 9s | ±90px | 80px | bottom: 15%, right: 10% |
| Coral | `auth-orb--coral` | `--text-secondary` | 250px | 13s | ±80px | 85px | top: 55%, left: 5% |
| Purple | `auth-orb--purple` | `--text-tertiary` | 350px | 10s | ±95px | 100px | top: 8%, right: 15% |
| Teal | `auth-orb--teal` | `#14B8A6` | 200px | 8s | ±70px | 70px | bottom: 10%, left: 45% |

Design notes:
- Prime-like durations (8, 9, 10, 11, 13s) ensure they rarely synchronize
- Staggered `animation-delay` values: 0s, -2s, -4s, -6s, -3s
- Each keyframe set has 5 stops with asymmetric paths (not simple bounce)
- Opacity: 0.3–0.4 (atmospheric, not overwhelming)
- All `pointer-events: none`

**Refactoring mandate:**
- DELETE the old `@keyframes orb-float` — replaced by 5 new keyframe sets
- Keep orb base styles (`.auth-orb` shared class) — only modifier classes change

### 1C. Fix Feature Icons
**File:** `frontend/src/components/Auth/LoginPage.tsx`

Replace text glyphs with inline SVGs (20x20 viewBox, `currentColor` for gold accent):

| Current | Icon | SVG Description |
|---------|------|-----------------|
| `{ }` (empty braces) | Sparkle/star | 4-point star path — represents AI generation |
| `</>` (code tag) | Keep as text | Already reads well as a code reference |
| `■` (filled square) | Download arrow | Arrow-down-to-tray — represents export |

**CSS addition** in Auth.css:
```css
.auth-feature-icon {
  /* existing rules... */
  display: flex;
  align-items: center;
  justify-content: center;
}
.auth-feature-icon svg { flex-shrink: 0; }
```

### 1D. Update SetupPage
**File:** `frontend/src/components/Auth/SetupPage.tsx`

SetupPage shares Auth.css classes. Update its JSX to match the new layout structure (wrap content in `.auth-center` instead of `.auth-left` + `.auth-right`). Add the 2 new orb divs.

### Phase 1 Verification
1. Log out → verify full-bleed layout with centered card
2. 5 orbs should be visible and noticeably moving
3. Frosted glass card should have `backdrop-filter: blur` effect
4. Feature icons: sparkle SVG, `</>` text, download SVG — all gold-colored
5. Tab toggle (Sign In / Create Account) still works
6. Navigate to setup page (clear auth DB) → same layout
7. Mobile responsive: card fills width, orbs hidden (existing media query hides left panel content)
8. `npm run lint && npm run build` passes

---

## Phase 2: Home Screen — Greeting, Session Cards, Editable Title

### Goal
Add "Welcome back" greeting. Redesign session cards to match template card quality. Add editable session title in the chat header (right side, next to kebab menu) as a soft push for users to name their sessions.

### 2A. Personalized Greeting
**Files:** `frontend/src/components/ChatWindow/index.tsx`, `frontend/src/components/ChatWindow/MessageList.tsx`

**Prop chain:** `user.display_name` flows from `App.tsx` → `ChatWindow` (already has `user` prop) → needs to pass to `MessageList`.

In `ChatWindow/index.tsx` (line 151), add prop:
```tsx
<MessageList
  ...existing props...
  displayName={user?.display_name}
/>
```

In `MessageList.tsx`:
- Add `displayName?: string` to `MessageListProps`
- Render greeting at top of home content:
```tsx
{displayName && (
  <h1 className="home-welcome">Welcome back, {displayName}</h1>
)}
```

**CSS:** `.home-welcome` already exists in `HomeScreen.css:18` with correct styling. Add entrance animation: `animation: fade-up var(--duration-normal) var(--ease-out-expo)`.

### 2B. Redesign Session Cards
**Files:** `frontend/src/components/HomeScreen/SessionCard.tsx`, `frontend/src/components/HomeScreen/HomeScreen.css`

Redesign to match template card quality (`TemplateCards.css` patterns):

**New SessionCard structure:**
```tsx
<button className="session-card" onClick={onClick} style={style}>
  <span className="session-card-icon">
    {/* 22x22 document SVG icon, currentColor */}
  </span>
  <div className="session-card-title">{session.title}</div>
  <div className="session-card-meta">
    <span>{doc_count} docs</span>
    <span>·</span>
    <span>{timeAgo}</span>
    <span>·</span>
    <span style={{ color: expiryColor }}>{daysLeft}d</span>
  </div>
</button>
```

**CSS changes in HomeScreen.css:**

| Property | Old | New |
|----------|-----|-----|
| padding | `1rem 1.2rem` | `24px` |
| gap | none | `8px` |
| flex-basis | `200px` | `240px` |
| max-width | `280px` | `300px` |
| hover | left-border gold | `::before` gold accent bar + `shadow-glow-accent` + `translateY(-2px)` |
| icon | none | 44px mint-green container with document SVG |

**Refactoring mandate:**
- DELETE old `.session-card:hover` border-left rule — replaced by `::before` pattern
- REUSE hover pattern from `TemplateCards.css` (same `::before` + glow approach) — don't duplicate, but keep in separate file since these are different components
- DELETE `.session-card-expiry` class (expiry now inline in meta row)

Skip `first_message_preview` display on home cards — it often duplicates the title for template-based sessions and adds no value.

### 2C. Editable Session Title in Chat Header
**Files:** `backend/app/api/sessions.py`, `backend/app/services/session_service.py`, `frontend/src/types/index.ts`, `frontend/src/hooks/useSSEChat.ts`, `frontend/src/App.tsx`, `frontend/src/components/ChatWindow/index.tsx`, `frontend/src/components/ChatWindow/ChatWindow.css`

**Header layout:**
```
[ AI HTML Builder ]                    [ Session Title (editable) ]  [ ⋮ ]
```

"AI HTML Builder" stays as the static app name on the left. Session title appears on the **right side**, next to the kebab menu.

**Implementation:**

1. **`useSSEChat.ts`** — expose `sessionTitle` state:
   - Add `sessionTitle: string` to return type
   - Set it from session metadata when `loadSession` is called
   - Set it from first message when `sendFirstMessage` creates a session
   - Add `setSessionTitle` to allow updates from parent
   - Expose `renameSession` callback that calls `api.updateSessionTitle()` + updates local state

2. **`App.tsx`** — pass session title to ChatWindow:
   - Destructure `sessionTitle` and `renameSession` from `useSSEChat`
   - Pass as props to `ChatWindow`

3. **`ChatWindow/index.tsx`** — render editable title in header:
   - New props: `sessionTitle?: string`, `onRenameSession?: (title: string) => void`
   - In `.chat-header`, wrap the right side (title + kebab) in a flex container
   - When `sessionTitle` exists: render as clickable text, hover shows pencil SVG icon
   - On click: switch to inline input (same pattern as MySessionsModal rename)
   - Save on blur/Enter, cancel on Escape
   - Styling: `--text-secondary`, `--fs-sm`, `--font-mono`, `max-width: 300px`, ellipsis overflow
   - `gap: 0.75rem` between title and kebab menu

4. **`ChatWindow.css`** — new rules:
   - `.header-session-title` — text display with hover pencil
   - `.header-session-input` — inline rename input
   - `.header-right-group` — flex container for title + kebab

**Refactoring mandate:**
- The inline rename pattern (click → input, blur/Enter saves, Escape cancels) already exists in `MySessionsModal.tsx`. Extract the reusable logic? **No** — the modal version has more state (editingId for multi-row). Keep them separate but follow the same UX pattern. The header version is simpler (single title, local state only).

### 2D. Remove "Add Visual" Button
**Files:** `frontend/src/components/ChatWindow/ChatInput.tsx`, `frontend/src/components/ChatWindow/ChatInput.css`

The "Add Visual" button only prepends `"Generate an image: "` to the chat input text (ChatInput.tsx:419-422). It provides no real value — the LLM router already classifies image intent from natural language. Users who want images say "add a photo" or "create an infographic" naturally.

**Remove:**
- Delete the `<button className="add-visual-btn">` block (ChatInput.tsx ~lines 415-428)
- Delete `.add-visual-btn` from the combined CSS selectors in ChatInput.css (lines 228, 243, 250)
  - If `.attach-file-btn` is the only remaining selector, simplify to just `.attach-file-btn`

**Refactoring mandate:**
- Don't leave orphaned CSS selectors referencing `.add-visual-btn`
- Clean footer: only "Attach File" and "Templates" buttons remain

### Phase 2 Verification
1. Log in → "Welcome back, {display_name}" greeting appears with fade-up animation
2. Session cards: icon + title + meta, hover shows gold accent bar + glow
3. Click a session card → session loads, title appears in header right side
4. Hover header title → pencil icon appears
5. Click → inline input, type new name, press Enter → saves
6. Press Escape → cancels rename
7. Start new session via template → title auto-populates with template name
8. "Add Visual" button is gone — footer shows only "Attach File" + "Templates"
9. `npm run lint && npm run build` passes

---

## Phase 3: My Sessions Modal Redesign

### Goal
Widen the modal. Add search/filter. Enrich session rows with icons and doc count badges.

### 3A. Widen Modal
**File:** `frontend/src/components/HomeScreen/MySessionsModal.css`

- `.sessions-panel` `max-width`: `640px` → `860px`

### 3B. Add Search/Filter
**File:** `frontend/src/components/HomeScreen/MySessionsModal.tsx`

New state: `const [filterText, setFilterText] = useState('')`

Reset on modal open (inside existing `useEffect`):
```tsx
if (isOpen) {
  loadSessions(0);
  setEditingId(null);
  setFilterText('');  // NEW
}
```

Compute filtered sessions:
```tsx
const filteredSessions = filterText.trim()
  ? sessions.filter(s =>
      s.title.toLowerCase().includes(filterText.toLowerCase()) ||
      s.first_message_preview.toLowerCase().includes(filterText.toLowerCase())
    )
  : sessions;
```

Add search input between policy note and session list:
```tsx
<div className="sessions-search">
  <svg className="sessions-search-icon" ...>{/* magnifying glass */}</svg>
  <input
    type="text"
    className="sessions-search-input"
    placeholder="Filter sessions..."
    value={filterText}
    onChange={(e) => setFilterText(e.target.value)}
  />
</div>
```

Replace `sessions.map(...)` with `filteredSessions.map(...)` in render.

Note: filter is client-side on loaded sessions only. Acceptable for 2–5 user scale.

### 3C. Enrich Session Rows
**File:** `frontend/src/components/HomeScreen/MySessionsModal.tsx`

Each session row gains:

1. **Row icon** (36px, mint-green bg, document SVG) — left of content area
2. **Doc count badge** — pill-shaped, right-aligned in title line (moved from meta row)
3. Better visual hierarchy: title at `--fs-sm` `--fw-medium`, meta as tertiary
4. Rows get `border-bottom` separator for visual structure

Updated row structure:
```tsx
<div className="session-row">
  <div className="session-row-icon">{/* document SVG */}</div>
  <div className="session-row-info">
    <div className="session-row-title-line">
      <span className="session-row-title">{session.title}</span>
      {isCurrent && <span className="session-current-badge">Current</span>}
      <span className="session-doc-badge">{doc_count} docs</span>
    </div>
    <div className="session-row-meta">
      <span>{relativeTime}</span> · <span style={color}>{daysLeft}d left</span>
    </div>
  </div>
  <div className="session-row-actions">{/* existing rename/delete */}</div>
</div>
```

### 3D. Multi-Select Bulk Delete
**File:** `frontend/src/components/HomeScreen/MySessionsModal.tsx`

Add checkbox multi-select with bulk delete action bar:

**New state:**
```tsx
const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
```

Reset on modal open (alongside existing resets).

**UI elements:**

1. **"Select All" checkbox** in the modal header (next to "My Sessions" title):
   - Toggles all visible (filtered) sessions
   - Shows indeterminate state when partially selected

2. **Row checkboxes** — left of each row icon:
   - Toggle individual session selection
   - Visible always (not just on hover)

3. **Bulk action bar** — appears at bottom of modal when `selectedIds.size > 0`:
   ```
   [ ✓ N selected ]                    [ Cancel ]  [ Delete N Sessions ]
   ```
   - Fixed to bottom of `.sessions-panel` (above "Load more" if present)
   - "Delete N Sessions" uses danger styling (`--signal-error`)
   - One `ConfirmDialog` for the batch: "Permanently delete N sessions and all their documents?"

4. **Bulk delete handler:**
   ```tsx
   const handleBulkDelete = async () => {
     for (const id of selectedIds) {
       await api.deleteSession(id);
     }
     setSessions(prev => prev.filter(s => !selectedIds.has(s.id)));
     setSelectedIds(new Set());
   };
   ```

**Note:** Sessions are auto-cleaned after 30 days of inactivity (backend `_cleanup_loop` in `main.py:64-71`). This bulk delete is for users who want to proactively tidy up active sessions they're done with.

**Refactoring mandate:**
- Reuse the existing `ConfirmDialog` component for bulk delete confirmation
- The single-delete flow (trash icon → confirm) remains unchanged for quick one-off deletes

### 3E. New CSS Rules
**File:** `frontend/src/components/HomeScreen/MySessionsModal.css`

New classes:
- `.sessions-search` — flex row, bottom border, padding
- `.sessions-search-icon` — `--text-tertiary`, flex-shrink
- `.sessions-search-input` — transparent bg, no border, `--text-primary`
- `.session-row-icon` — 36px square, `--signal-active-muted` bg, `--signal-active` color, `border-radius: --radius-sm`
- `.session-doc-badge` — `--font-mono`, `0.65rem`, pill bg `--surface-highlight`, `margin-left: auto`
- `.session-row-checkbox` — styled checkbox, accent color on checked
- `.sessions-bulk-bar` — sticky bottom bar, flex between count + actions, danger button
- `.sessions-select-all` — header checkbox label

Updated rules:
- `.session-row` — add `border-bottom: 1px solid var(--border-subtle)`, slightly more padding
- `.session-row:last-of-type` — no bottom border

**Refactoring mandate:**
- The doc count was previously shown in `.session-row-meta` as text. REMOVE it from meta since it's now a badge in the title line. Don't show it twice.
- DELETE any unused `.session-row-meta` gap rules if the meta line becomes simpler

### Phase 3 Verification
1. Open "My Sessions" → modal is wider (~860px)
2. Search input visible, type to filter sessions by title
3. Each row has: checkbox, icon, title, doc badge, meta line
4. Click checkboxes → bulk action bar appears at bottom with count
5. "Select All" in header toggles all visible sessions
6. "Delete N Sessions" → confirm dialog → sessions deleted
7. Rename (double-click) still works
8. Single delete (trash icon on hover) still works with confirm dialog
9. "Load more" pagination still works
10. `npm run lint && npm run build` passes

---

## Files Modified (Complete List)

| File | Phase | Summary |
|------|-------|---------|
| `frontend/src/components/Auth/Auth.css` | 1 | Full-bleed layout, 5 orb keyframes, frosted card, delete dead split-panel CSS |
| `frontend/src/components/Auth/LoginPage.tsx` | 1 | Single-column layout, 2 new orb divs, SVG feature icons |
| `frontend/src/components/Auth/SetupPage.tsx` | 1 | Same layout restructure, 2 new orb divs |
| `frontend/src/components/ChatWindow/ChatInput.tsx` | 2 | Remove "Add Visual" button |
| `frontend/src/components/ChatWindow/ChatInput.css` | 2 | Remove `.add-visual-btn` CSS selectors |
| `frontend/src/components/ChatWindow/index.tsx` | 2 | displayName prop to MessageList, editable session title in header |
| `frontend/src/components/ChatWindow/ChatWindow.css` | 2 | Header title styles, header right-group flex |
| `frontend/src/components/ChatWindow/MessageList.tsx` | 2 | displayName prop, greeting render |
| `frontend/src/components/HomeScreen/SessionCard.tsx` | 2 | Icon container, restructured layout |
| `frontend/src/components/HomeScreen/HomeScreen.css` | 2 | Session card redesign, delete old hover rules |
| `frontend/src/App.tsx` | 2 | Pass sessionTitle + renameSession to ChatWindow |
| `frontend/src/hooks/useSSEChat.ts` | 2 | Expose sessionTitle, renameSession |
| `frontend/src/types/index.ts` | 2 | Add `title` to `Session` interface |
| `backend/app/api/sessions.py` | 2 | Add `title` to GET /api/sessions/{sid} response (deviation) |
| `backend/app/services/session_service.py` | 2 | Add `get_session_title()` method (deviation) |
| `frontend/src/components/HomeScreen/MySessionsModal.tsx` | 3 | Search filter, row icons, doc badges |
| `frontend/src/components/HomeScreen/MySessionsModal.css` | 3 | Wider modal, search bar, row icon/badge styles |

---

## Existing Utilities to Reuse

| Utility | Location | Used In |
|---------|----------|---------|
| `relativeTime()` | `frontend/src/components/HomeScreen/sessionUtils.ts` | SessionCard, MySessionsModal |
| `daysUntilExpiry()` | `frontend/src/components/HomeScreen/sessionUtils.ts` | SessionCard, MySessionsModal |
| `expiryColor()` | `frontend/src/components/HomeScreen/sessionUtils.ts` | SessionCard, MySessionsModal |
| `api.updateSessionTitle()` | `frontend/src/services/api.ts` | ChatWindow header rename |
| `api.listSessions()` | `frontend/src/services/api.ts` | MySessionsModal |
| CSS vars: `--accent-primary`, `--signal-active`, `--surface-raised`, etc. | `frontend/src/theme.css` | All components |
| `@keyframes card-enter`, `@keyframes fade-up`, `@keyframes materialize` | `frontend/src/theme.css` | Animations |

---

## Final Verification (All Phases)

1. Log out → login page: full-bleed, 5 orbs, centered card, SVG icons
2. Log in → "Welcome back, {name}", redesigned session cards
3. Click session → loads, title in header right side, editable
4. Footer: only "Attach File" + "Templates" (no "Add Visual")
5. "My Sessions" modal → wider, search works, enriched rows
6. Multi-select sessions → bulk delete with confirmation
7. All existing functionality unchanged (chat, edit, create, export, versions)
8. `cd frontend && npm run lint && npm run build` — clean
9. `cd backend && pytest` — 375 tests pass (small backend deviation in Phase 2: `get_session_title()` added)
