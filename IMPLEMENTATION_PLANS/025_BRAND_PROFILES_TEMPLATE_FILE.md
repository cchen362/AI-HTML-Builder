# Implementation Plan 025: Brand Profiles + Template-File Flow

## Status: COMPLETE

---

## STOP — READ THIS FIRST

**DO NOT START** this implementation until:
- Plans 001–024 are FULLY complete (they are)
- You have read this ENTIRE document
- You understand the 3 phases and their dependencies

**This plan emerged from a viability workshop** reviewing the app's competitive position and identifying high-impact, low-clutter enhancements. Two features survived rigorous UX discussion; a third ("Transform to...") was dropped because the existing chat interface already handles document transformation via natural language.

**PHASE DEPENDENCIES:**
- Phase 1 (Backend Brand Infrastructure) must complete first — provides API endpoints and database table
- Phase 2 (Frontend: Brand Selector + Admin UI + Template-File Fix) depends on Phase 1 backend endpoints
- Phase 3 (Tests + Verification) depends on Phases 1-2
- Recommended order: 1 → 2 → 3 (sequential)

**EACH PHASE = ONE SESSION/COMMIT.** Do not combine phases.

**CORE DESIGN PRINCIPLE: Elegant simplicity.**
These features must integrate into the existing UI without adding visual noise. The brand selector is a preference indicator, not a primary action. The template-file fix eliminates friction without adding new UI elements. Every addition must feel like it was always there.

---

## Workshop Decisions Summary

| Topic | Decision | Rationale |
|-------|----------|-----------|
| Brand storage | Admin-managed in auth.db, NOT hardcoded data files | Friends at other companies can add their own brand via admin panel. No code deploy needed. |
| Brand admin form | 2 fields only: Name + Spec Text | Accent color auto-extracted from first hex in spec. No color picker. Minimal friction. |
| Brand spec depth | Essentials only (~20-30 lines: colors, fonts, tone) | Full 189-line spec is prescriptive overkill. LLM generates better output with constraints + creative latitude. |
| Brand selector placement | Chat input footer, right of "Templates", always visible | Brand is a user preference (like language setting), not a per-session action. |
| Brand pill styling | Pill-shaped (`border-radius-full`), lighter visual weight than action buttons | Distinguishes preference indicators from action triggers. |
| Dropdown direction | Opens upward (footer is at screen bottom) | Standard UX pattern for bottom-anchored dropdowns. |
| "Default" brand | Virtual/built-in, NOT stored in database | Means "use app's standard DM Sans / teal palette." Zero tokens injected, zero noise. |
| Brand deleted while selected | Silent fallback to Default + localStorage cleanup on next load | Two-layer safety: API returns None mid-session (graceful), selector reverts on refresh (visible). |
| Transform feature | **DROPPED** | Already works via natural language chat ("turn this into a presentation"). Adding UI = feature creep. |
| Template + file bug | Fix `suggested_prompt` override when template is active | Use raw file content (`result.data.content`) instead of server's generic wrapper prompt. |
| Template + file UX | Context-aware drop overlay + combined-state placeholder text | Subtle polish that confirms the template+file combo is intentional. No new UI elements. |

---

## Phase 1: Backend — Brand Profile Infrastructure

### 1A. Database: `brand_profiles` table

**File**: `backend/app/auth_database.py`

Add to the SCHEMA string (after the `settings` table definition):

```sql
CREATE TABLE IF NOT EXISTS brand_profiles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    accent_color TEXT NOT NULL DEFAULT '#64748B',
    spec_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

No migration entry needed — this is `CREATE TABLE IF NOT EXISTS`, safe for existing databases.

### 1B. New file: `backend/app/api/brands.py`

API router for brand profile CRUD. Three endpoints:

**`GET /api/brands`** — List all brand profiles
- Auth: `Depends(get_current_user)` — any logged-in user can see available brands
- Query: `SELECT id, name, accent_color FROM brand_profiles ORDER BY created_at`
- Returns: `{ "brands": [{ "id", "name", "accent_color" }] }`
- **Note**: `spec_text` is NOT returned in the list (it can be large). Only used server-side for LLM injection.

**`POST /api/brands`** — Create a brand profile
- Auth: `Depends(require_admin)`
- Body model:
  ```python
  class CreateBrandRequest(BaseModel):
      name: str
      spec_text: str
  ```
- Validation:
  - `name`: required, strip whitespace, max 50 chars, non-empty
  - `spec_text`: required, strip whitespace, max 5000 chars, non-empty
  - Reject with 400 and clear message if validation fails
- **Accent color auto-extraction**: Regex scan `spec_text` for first `#[0-9A-Fa-f]{6}` match. Use as `accent_color`. If no hex found, default to `#64748B` (slate gray).
- Generate `id` via `uuid.uuid4().hex[:12]` (short, readable, collision-safe at this scale)
- Returns: `{ "id", "name", "accent_color" }`

**`DELETE /api/brands/{brand_id}`** — Delete a brand profile
- Auth: `Depends(require_admin)`
- 404 if not found
- Returns: `{ "deleted": true }`

**Pattern reference**: Follow `backend/app/api/auth.py` for endpoint structure — same auth dependencies, same error handling patterns.

**Database access pattern**: Use `from app.auth_database import get_db as get_auth_db` since brand_profiles lives in auth.db. Follow the same `cursor = await db.execute(); row = await cursor.fetchone()` pattern used throughout the codebase.

### 1C. Register router

**File**: `backend/app/main.py`

Add after existing router registrations:
```python
from app.api.brands import router as brands_router
app.include_router(brands_router)
```

### 1D. Brand spec resolution in chat.py

**File**: `backend/app/api/chat.py`

Add helper function (near the top, alongside existing helpers like `_strip_base64_for_context`):

```python
async def _resolve_brand_spec(brand_id: str | None) -> str | None:
    """Look up brand spec text from auth.db. Returns None for default/missing."""
    if not brand_id:
        return None
    from app.auth_database import get_db as get_auth_db
    db = await get_auth_db()
    cursor = await db.execute(
        "SELECT spec_text FROM brand_profiles WHERE id = ?", (brand_id,)
    )
    row = await cursor.fetchone()
    return row["spec_text"] if row else None
```

Add `brand_id` field to `ChatRequest`:
```python
class ChatRequest(BaseModel):
    message: str
    document_id: str | None = None
    template_name: str | None = None
    user_content: str | None = None
    brand_id: str | None = None  # NEW
```

### 1E. Modify creator.py — brand spec injection

**File**: `backend/app/services/creator.py`

Add `brand_spec: str | None = None` parameter to BOTH `create()` and `stream_create()`.

Currently these methods pass the `CREATION_SYSTEM_PROMPT` constant directly to `self.provider.generate()` / `self.provider.stream()`. Change to build a local `system` variable:

```python
async def stream_create(
    self,
    user_message: str,
    template_content: str | None = None,
    brand_spec: str | None = None,  # NEW
) -> AsyncIterator[str]:
    system = CREATION_SYSTEM_PROMPT
    if brand_spec:
        system += f"\n\nBRAND GUIDELINES (override the default styling above with these):\n{brand_spec}"
    messages = self._build_messages(user_message, template_content)
    # Use `system` instead of `CREATION_SYSTEM_PROMPT` in provider calls below
```

Apply the same change to the non-streaming `create()` method.

### 1F. Modify editor.py — brand spec injection

**File**: `backend/app/services/editor.py`

Add `brand_spec: str | None = None` parameter to `edit()`.

**Important**: Read the editor's system prompt construction carefully. It uses Anthropic's structured format (list of content blocks), not a plain string like the creator. Find where the system prompt blocks are assembled and append:

```python
if brand_spec:
    # Append brand context as an additional text block
    system_content.append({
        "type": "text",
        "text": f"\nBRAND GUIDELINES (apply to any new or modified styles):\n{brand_spec}",
    })
```

The exact variable name (`system_content`, `system_blocks`, etc.) must be determined by reading the file.

### 1G. Modify infographic_service.py — brand spec injection

**File**: `backend/app/services/infographic_service.py`

Add `brand_spec: str | None = None` parameter to `generate()`.

If present, append to the art director prompt (the message sent to Gemini 2.5 Pro for visual spec generation). The brand colors/fonts should influence the infographic's visual design.

### 1H. Wire brand spec through all handlers in chat.py

In the main `chat()` endpoint, after route classification:

```python
brand_spec = await _resolve_brand_spec(request.brand_id)
```

Each handler function (`_handle_edit`, `_handle_create`, `_handle_infographic`, `_handle_image`) gains a `brand_spec: str | None = None` parameter. Pass `brand_spec=brand_spec` to each handler call.

Inside each handler, pass `brand_spec` to the respective service:
- `_handle_create` → `creator.stream_create(..., brand_spec=brand_spec)`
- `_handle_edit` → `editor.edit(..., brand_spec=brand_spec)`
- `_handle_infographic` → `service.generate(..., brand_spec=brand_spec)`
- `_handle_image` → no change (image generation doesn't use brand palette)

### Phase 1 Files Summary

| File | Change |
|------|--------|
| `backend/app/auth_database.py` | Add `brand_profiles` table to SCHEMA |
| **NEW** `backend/app/api/brands.py` | GET/POST/DELETE brand profile endpoints |
| `backend/app/main.py` | Register brands router |
| `backend/app/api/chat.py` | `brand_id` in ChatRequest, `_resolve_brand_spec()`, pass brand_spec to handlers |
| `backend/app/services/creator.py` | Accept `brand_spec`, append to system prompt |
| `backend/app/services/editor.py` | Accept `brand_spec`, append to system prompt blocks |
| `backend/app/services/infographic_service.py` | Accept `brand_spec`, include in art director prompt |

---

## Phase 2: Frontend — Brand Selector, Admin UI, Template-File Fix

### 2A. Types

**File**: `frontend/src/types/index.ts`

Add:
```typescript
export interface BrandProfile {
  id: string;
  name: string;
  accent_color: string;
}
```

### 2B. API calls

**File**: `frontend/src/services/api.ts`

Add to the `api` object:
```typescript
fetchBrands: async (): Promise<{ brands: BrandProfile[] }> => { ... },
```

Add to the `adminApi` object:
```typescript
createBrand: async (name: string, specText: string): Promise<BrandProfile> => { ... },
deleteBrand: async (brandId: string): Promise<void> => { ... },
```

Add `brandId?: string` parameter to `sendChatMessage()`. Include `brand_id` in the POST body when present:
```typescript
if (brandId) {
    body.brand_id = brandId;
}
```

### 2C. New component: BrandSelector

**Files**: `frontend/src/components/ChatWindow/BrandSelector.tsx` + `BrandSelector.css`

**Props:**
```typescript
interface BrandSelectorProps {
  activeBrandId: string | null;  // null = default
  onBrandChange: (brandId: string | null) => void;
  disabled?: boolean;
}
```

**Component behavior:**

1. **On mount**: Fetch `/api/brands` → populate brand list. Check localStorage `selected_brand_id`. If stored ID not in fetched list → clear localStorage, call `onBrandChange(null)` (revert to Default).

2. **Pill button render**:
   - 6px colored circle (accent_color of selected brand, or `#14B8A6` teal for Default)
   - Label text: "BRAND" when default, brand name when custom (all uppercase, mono font)
   - 8px chevron-down SVG
   - Pill shape: `border-radius: var(--radius-full)` distinguishes from rectangular action buttons
   - Same font treatment as other footer buttons: `var(--font-mono), var(--fs-xs), uppercase, var(--tracking-wide)`

3. **Dropdown (opens upward)**:
   - Position: `absolute; bottom: calc(100% + 4px); right: 0;`
   - Width: 220px
   - Background: `var(--surface-overlay)`, border: `var(--border-default)`, shadow: `var(--shadow-lg)`
   - Animation: existing `dropdown-enter` keyframe
   - First option: "Default" with teal dot + checkmark if active
   - Then each brand from API: dot (accent_color) + name + checkmark if active
   - Click → select brand, update localStorage, call `onBrandChange(id)`, close dropdown
   - Close on click-outside (use same pattern as header menu in `ChatWindow/index.tsx`) or Escape

### 2D. Integrate BrandSelector into ChatInput

**File**: `frontend/src/components/ChatWindow/ChatInput.tsx`

**New state:**
```typescript
const [activeBrandId, setActiveBrandId] = useState<string | null>(
    () => localStorage.getItem('selected_brand_id')
);
```

**Brand change handler:**
```typescript
const handleBrandChange = useCallback((brandId: string | null) => {
    setActiveBrandId(brandId);
    if (brandId) {
        localStorage.setItem('selected_brand_id', brandId);
    } else {
        localStorage.removeItem('selected_brand_id');
    }
}, []);
```

**Footer-left layout** — add BrandSelector after PromptLibraryButton:
```tsx
<div className="footer-left">
    <button className="attach-file-btn" ...>Attach File</button>
    <PromptLibraryButton ... />
    <BrandSelector
        activeBrandId={activeBrandId}
        onBrandChange={handleBrandChange}
        disabled={isProcessing}
    />
</div>
```

**Modify `handleSubmit`**: Pass `activeBrandId` as last argument in the `onSendMessage` call (both the template path and the direct-message path).

### 2E. Thread brandId through component chain

All `onSendMessage` signatures gain `brandId?: string` as the last parameter:

1. **`ChatInput` props**: `onSendMessage: (message, files?, templateName?, userContent?, brandId?) => void`
2. **`ChatWindowProps`**: same signature change
3. **`ChatWindow/index.tsx`**: pass brandId through to parent
4. **`App.tsx` `handleSendMessage`**: receive brandId, pass to `sendFirstMessage` / `sendMessage`
5. **`useSSEChat.ts`**: `sendMessage()` and `sendFirstMessage()` gain `brandId?: string`, pass to `api.sendChatMessage()`
6. **`api.ts` `sendChatMessage()`**: gain `brandId?: string`, include in POST body

### 2F. Admin Panel — Brands Tab

**File**: `frontend/src/components/Auth/AdminPanel.tsx`

Add "Brands" as third tab:
```typescript
type AdminTab = 'settings' | 'costs' | 'brands';
```

**Brands tab content:**

1. **Brand list**: Each row shows:
   - Colored dot (10px circle, `accent_color`)
   - Brand name
   - Delete button (danger style, with confirm dialog)
   - Empty state: "No brand profiles yet. Add one below."

2. **"Add Brand" section** (always visible below the list):
   - Text input: Brand Name (max 50 chars)
   - Textarea: Brand Spec (8 rows, with placeholder hint showing example format)
   - Save button + Cancel to clear form
   - On save: call `adminApi.createBrand()`, refresh list, clear form
   - Validation feedback: show error if name/spec empty

**Placeholder hint for textarea:**
```
Paste brand colors, fonts, and style guidelines. Example:

COLORS:
- Primary: #006FCF (headers, CTAs)
- Dark: #003478 (backgrounds, text)
- Accent: #00A3A1 (highlights, charts)

TYPOGRAPHY:
- Headings: 'Helvetica Neue', sans-serif
- Body: 'Inter', sans-serif

TONE: Corporate-premium, data-forward, confident.
```

**Styling**: Reuse existing admin panel CSS classes (`admin-section`, `admin-section-title`, `admin-btn`, `admin-btn--danger`). New styles needed in `Auth.css`:
- `.brand-list` — list container
- `.brand-list-item` — flex row: dot + name + delete
- `.brand-dot` — 10px colored circle
- `.brand-form` — add-brand inline form
- `.brand-spec-input` — textarea with dark background, mono font

### 2G. Template-File Flow Fix

**File**: `frontend/src/components/ChatWindow/ChatInput.tsx`

**Bug fix** — in BOTH `handleFileSelect` and `handleDrop`, change:
```typescript
setMessage(result.suggested_prompt);
```
to:
```typescript
if (activeTemplate) {
    // Template active: use raw file content as source material
    setMessage(result.data.content);
} else {
    // No template: use server's suggested prompt as today
    setMessage(result.suggested_prompt);
}
```

**Polish 1** — Context-aware drop overlay text:
```tsx
<div className="drop-overlay">
    <span>
        {activeTemplate
            ? `Drop file for ${activeTemplate.name}`
            : 'Drop file here'}
    </span>
</div>
```

**Polish 2** — Combined-state placeholder:
```typescript
placeholder={
    activeTemplate && attachedFile
        ? 'Add extra instructions (optional) — file content will be used as source material'
        : activeTemplate
            ? `Add your content for "${activeTemplate.name}"... (or send directly to use template defaults)`
            : placeholder
}
```

### 2H. Template Description Updates

**File**: `frontend/src/data/promptTemplates.ts`

| Template | Current | Updated |
|----------|---------|---------|
| Business Dashboard | "Interactive dashboard with KPI cards, SVG charts, and data tables" | "Turn data and spreadsheets into interactive dashboards with KPI cards and charts" |
| Presentation Slides | "Slide presentation with keyboard navigation, slide counter, and professional layouts" | "Transform notes and content into polished slide decks with navigation and transitions" |

### Phase 2 Files Summary

| File | Change |
|------|--------|
| `frontend/src/types/index.ts` | Add `BrandProfile` interface |
| `frontend/src/services/api.ts` | Brand API calls + `brandId` in `sendChatMessage` |
| **NEW** `frontend/src/components/ChatWindow/BrandSelector.tsx` | Pill + dropdown component |
| **NEW** `frontend/src/components/ChatWindow/BrandSelector.css` | Styles |
| `frontend/src/components/ChatWindow/ChatInput.tsx` | Brand state + selector + template-file fix + polish |
| `frontend/src/components/ChatWindow/index.tsx` | Thread brandId |
| `frontend/src/hooks/useSSEChat.ts` | brandId param in sendMessage/sendFirstMessage |
| `frontend/src/App.tsx` | Thread brandId through handleSendMessage |
| `frontend/src/components/Auth/AdminPanel.tsx` | "Brands" tab with list + add form |
| `frontend/src/components/Auth/Auth.css` | Brand management styles |
| `frontend/src/data/promptTemplates.ts` | 2 template description updates |

---

## Phase 3: Tests + Verification

### 3A. Backend Tests

**New test file**: `backend/tests/test_brands.py`

Tests via TestClient (following existing test patterns with auth overrides in conftest.py):

- **CRUD**: Create brand → list includes it → delete → list doesn't include it
- **Validation**: Empty name → 400, empty spec → 400, spec > 5000 chars → 400
- **Accent color extraction**: Spec with `#006FCF` → accent_color is `#006FCF`. Spec without hex → accent_color is `#64748B`.
- **List excludes spec_text**: GET response items have `id`, `name`, `accent_color` only
- **Auth**: Non-admin create → 403, non-admin delete → 403, non-admin list → 200

**Brand injection tests** (can be in `test_brands.py` or separate):
- **`_resolve_brand_spec`**: Valid ID → returns spec text. Missing ID → None. None → None.
- **Creator integration**: Mock provider, create with brand_spec, assert system prompt passed to `provider.generate()` contains "BRAND GUIDELINES"
- **Editor integration**: Mock provider, edit with brand_spec, assert system prompt blocks contain brand text
- **ChatRequest**: POST to `/api/chat/{sid}` with `brand_id` field → no error (field accepted)

### 3B. Existing Test Compatibility

All 393+ existing tests MUST pass unchanged. The `brand_id` field is optional with `None` default — no existing test sends it, no existing behavior changes.

### 3C. Linting + Build

- `ruff check backend/` — clean
- `mypy backend/` — clean
- `npm run lint` (frontend) — clean
- `npm run build` (frontend) — clean

### 3D. Manual QA Checklist

**Brand Profiles — Admin:**
- [ ] Admin Panel shows "Brands" tab
- [ ] Empty state shows "No brand profiles yet"
- [ ] Create brand with name + spec text → appears in list with correct dot color
- [ ] Delete brand → removed from list (with confirmation)
- [ ] Validation: empty name rejected, empty spec rejected

**Brand Profiles — User:**
- [ ] Brand pill in chat footer shows "BRAND" with teal dot (default)
- [ ] Click pill → dropdown opens upward with "Default" option
- [ ] After admin creates a brand → dropdown includes it on next load
- [ ] Select brand → pill updates: shows brand name + brand's accent color
- [ ] Refresh page → selection persists (localStorage)
- [ ] Admin deletes selected brand → on refresh, pill reverts to "BRAND" (default)

**Brand Profiles — Generation:**
- [ ] Create document with brand selected → output uses brand colors/fonts (not default teal/DM Sans)
- [ ] Edit document with brand selected → new/modified styles use brand palette
- [ ] Switch to Default → create document → uses standard palette
- [ ] Brand + Template → both combine (template structures, brand styles)

**Template + File Flow:**
- [ ] Select template → drop file → textarea fills with raw file content (NOT "Create a styled HTML document...")
- [ ] Drop overlay says "Drop file for Stakeholder Brief" when template active
- [ ] Template + file active → placeholder says "Add extra instructions (optional)..."
- [ ] Can type extra instructions → send → template + file content + instructions all combine
- [ ] No template → drop file → uses `suggested_prompt` as before (no regression)
- [ ] Template → attach file via button (not drag-drop) → same correct behavior

**Integration:**
- [ ] Brand + Template + File: All three combine. Brand = colors/fonts, template = structure, file = content.
- [ ] Brand switch mid-session: New creations use new brand. Existing content unchanged.

---

## Architecture Notes

### Why auth.db and not app.db?
Brand profiles are organizational settings (like invite codes and user management), not per-session data. They belong in the auth database alongside users and settings, following the existing separation: auth.db = org/admin concerns, app.db = document/session data.

### Why NOT hardcoded brand data files?
The user's vision is shareability — friends at different companies adding their own brands. Hardcoded data requires a code deploy for each new brand. Database storage + admin UI = 2 minutes to add a brand, no deploy needed.

### Why NOT store brand_id on the session or document?
The brand is a user preference that applies to all their work, not a session attribute. Stored in localStorage (client-side). If you switch brands mid-session, only NEW creations/edits use the new brand. Old content stays unchanged — surgical editing doesn't rewrite untouched content. This is correct behavior: brand choice affects styling intent going forward, not retroactive restyling.

### Token cost of brand injection
A concise brand spec (~20-30 lines) adds ~300-500 input tokens per creation/edit call:
- Gemini 2.5 Pro (creation): ~$0.001 extra per call
- Claude Sonnet 4.6 (edit): ~$0.002 extra per call
- Negligible at 2-5 user scale

### The "Default" brand
"Default" is a virtual concept, not a database record. When `brand_id` is null or absent, no brand spec is injected. The existing `CREATION_SYSTEM_PROMPT` with DM Sans / teal palette applies unchanged. Zero extra tokens, zero noise.
