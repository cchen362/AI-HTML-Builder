# Implementation Plan 017: UI/UX Makeover

## Status: COMPLETE

---

## STOP - READ THIS FIRST

**DO NOT START** this implementation until:
- Plan 016 (Transformation Context + Document Ownership) is FULLY complete (it is)
- You have read this ENTIRE document end-to-end
- You understand every file path, code change, and verification step

**STRICT RULES — FOLLOW EXACTLY:**
1. Implement phases IN ORDER (1 → 9). Do NOT skip phases or reorder.
2. Run verification after EACH phase before proceeding to the next.
3. Do NOT create files not listed in this plan. Do NOT delete files not listed in this plan.
4. Do NOT modify ANY backend files. This is a frontend-only plan.
5. Do NOT add dependencies to `package.json` or `requirements.txt`.
6. Every change must preserve the existing build (`npm run build`) and lint (`npm run lint`).
7. Phase 1 MUST be done first — all subsequent phases depend on CSS variable changes.

**CONTEXT:**

The current "Obsidian Terminal" theme (navy/blue) is being replaced with a cyberpunk-inspired palette drawn from a mechanical keyboard reference:
- **Deep purples** for surfaces (hierarchy via gradient from light to dark purple)
- **Mint green** (`#A8E6A0`) for primary text (distinctive, avoids generic white-on-dark)
- **Muted coral** (`#D4A0A0`) for secondary text
- **Golden yellow** (`#E5B800`) for accent — used with **extreme discipline**, ONLY on actionable elements (buttons, active states, CTAs)

Additional changes: dark mode only (light theme removed), font scale bumped, Enter-to-send, template card improvements, version history layout fix, remove redundant animations.

**DEPENDENCIES:**
- Plans 001-016 (all complete)

**SCOPE:**
- 19 files modified, 1 file deleted
- Zero backend changes
- Zero new npm dependencies
- CSS variable rewrite + targeted TSX tweaks

---

## Palette Reference

### Surface Colors
| Token | Old | New | Role |
|-------|-----|-----|------|
| `--surface-void` | `#08090A` | `#110B20` | Darkest purple-black |
| `--surface-base` | `#0D0F12` | `#1A0F3C` | Dark indigo (primary bg) |
| `--surface-raised` | `#141720` | `#2D1B69` | Deep purple (cards, inputs) |
| `--surface-overlay` | `#1A1E2A` | `#362272` | Lighter purple (modals) |
| `--surface-highlight` | `#232838` | `#40298A` | Focus/selection |

### Border Colors
| Token | Old | New |
|-------|-----|-----|
| `--border-subtle` | `#1E2234` | `#3B2578` |
| `--border-default` | `#2A2F42` | `#4A3490` |
| `--border-strong` | `#3D4460` | `#6B50B5` |
| `--border-accent` | `#4F6AFF` | `#E5B800` |

### Text Colors
| Token | Old | New | Role |
|-------|-----|-----|------|
| `--text-primary` | `#E8ECF4` | `#A8E6A0` | **Mint green** |
| `--text-secondary` | `#8B93A8` | `#D4A0A0` | **Muted coral** |
| `--text-tertiary` | `#555E75` | `#7B6BA0` | Lavender-grey |
| `--text-inverse` | `#0D0F12` | `#1A0F3C` | Dark on gold |

### Accent Colors
| Token | Old | New |
|-------|-----|-----|
| `--accent-primary` | `#4F6AFF` | `#E5B800` |
| `--accent-primary-hover` | `#6B82FF` | `#FFD700` |
| `--accent-primary-muted` | `rgba(79,106,255,0.12)` | `rgba(229,184,0,0.12)` |
| `--accent-primary-glow` | `rgba(79,106,255,0.35)` | `rgba(229,184,0,0.35)` |

### Signal Colors
| Token | Old | New |
|-------|-----|-----|
| `--signal-active` | `#00E5CC` | `#A8E6A0` (mint) |
| `--signal-active-glow` | `rgba(0,229,204,0.25)` | `rgba(168,230,160,0.25)` |
| `--signal-active-muted` | `rgba(0,229,204,0.08)` | `rgba(168,230,160,0.08)` |
| `--signal-warning` | `#FFB020` | `#FFB020` (keep) |
| `--signal-error` | `#FF4D6A` | `#FF4D6A` (keep) |
| `--signal-success` | `#34D399` | `#A8E6A0` (mint) |
| `--signal-success-muted` | `rgba(52,211,153,0.10)` | `rgba(168,230,160,0.10)` |

### Gradients
| Token | New Value |
|-------|-----------|
| `--gradient-header` | `linear-gradient(135deg, #1A0F3C 0%, #2D1B69 60%, #362272 100%)` |
| `--gradient-send-btn` | `linear-gradient(135deg, #E5B800 0%, #D4A017 100%)` |
| `--gradient-send-hover` | `linear-gradient(135deg, #FFD700 0%, #E5B800 100%)` |
| `--gradient-user-msg` | `linear-gradient(135deg, #2D1B69 0%, #1A0F3C 100%)` |
| `--gradient-ai-glow` | `linear-gradient(135deg, rgba(168,230,160,0.04) 0%, rgba(229,184,0,0.04) 100%)` |

### Shadows
| Token | New Value |
|-------|-----------|
| `--shadow-sm` | `0 1px 3px rgba(0, 0, 0, 0.4)` (keep) |
| `--shadow-md` | `0 4px 16px rgba(0, 0, 0, 0.5)` (keep) |
| `--shadow-lg` | `0 12px 40px rgba(0, 0, 0, 0.6)` (keep) |
| `--shadow-glow-accent` | `0 0 20px rgba(229, 184, 0, 0.15)` |
| `--shadow-glow-signal` | `0 0 20px rgba(168, 230, 160, 0.15)` |

### Font Scale (bumped)
| Token | Old | New |
|-------|-----|-----|
| `--fs-xs` | `0.6875rem` (11px) | `0.75rem` (12px) |
| `--fs-sm` | `0.75rem` (12px) | `0.8125rem` (13px) |
| `--fs-base` | `0.875rem` (14px) | `1rem` (16px) |
| `--fs-md` | `1rem` (16px) | `1.125rem` (18px) |
| `--fs-lg` | `1.25rem` (20px) | `1.5rem` (24px) |
| `--fs-xl` | `1.75rem` (28px) | `2rem` (32px) |
| `--fs-display` | `2.5rem` (40px) | `3rem` (48px) |

### Modal Overlay
- Old: `rgba(0, 0, 0, 0.75)`
- New: `rgba(17, 11, 32, 0.8)` (purple-tinted)

---

## Phase 1: Theme Foundation + Light Mode Removal

Everything depends on this phase. CSS variables power ALL component styles.

### Step 1.1: Rewrite theme.css

**File:** `frontend/src/theme.css`

**Replace the two `:root` blocks (lines 8-98) with a single merged block** containing:
- Typography tokens (keep font families, weights, tracking, leading as-is)
- Bump all `--fs-*` values per the Font Scale table above
- Replace ALL color/surface/border/text/accent/signal/gradient/shadow values per the Palette Reference tables above
- Keep radius and animation timing tokens unchanged

**Delete the entire `[data-theme="light"]` block** (lines 101-147).

**Keep all `@keyframes` animations** (lines 152-234) unchanged — they reference CSS variables and will auto-update.

**Update the file comment** (line 2): `"Obsidian Terminal"` → descriptive name. Remove `Light mode = [data-theme="light"] overrides.` from the comment.

### Step 1.2: Delete ThemeToggle component

**Delete file:** `frontend/src/components/ThemeToggle.tsx`

### Step 1.3: Remove ThemeToggle from ChatWindow

**File:** `frontend/src/components/ChatWindow/index.tsx`

- **Line 6**: Delete `import ThemeToggle from '../ThemeToggle';`
- **Line 70**: Delete `<ThemeToggle />` from the JSX

### Step 1.4: Remove theme toggle styles from index.css

**File:** `frontend/src/index.css`

**Delete lines 66-85** (the `.theme-toggle` and `.theme-toggle:hover` rules, including the comment).

### Step 1.5: Remove theme init script from index.html

**File:** `frontend/index.html`

**Delete lines 11-14:**
```html
<script>
  const t = localStorage.getItem('ai-html-builder-theme');
  if (t === 'light') document.documentElement.dataset.theme = 'light';
</script>
```

### Step 1.6: Delete light mode hljs overrides from StreamingMarkdown.css

**File:** `frontend/src/components/Chat/StreamingMarkdown.css`

**Delete lines 154-162** (the `[data-theme="light"] .hljs*` rules, including the comment).

**Keep lines 146-152** (dark theme syntax highlighting — VS Code Dark+) unchanged.

### Phase 1 Verification

```bash
cd frontend && npm run build && npm run lint
```

- Build must succeed with no errors
- No TypeScript errors from removing ThemeToggle import
- `npm run dev` — app loads in dark purple theme, no light mode toggle visible
- All text should be mint green, coral, or lavender-grey (not white or blue)

---

## Phase 2: Header Redesign

Remove "Systems Nominal" status indicator. Simplify header to single row.

### Step 2.1: Remove status indicator from ChatWindow TSX

**File:** `frontend/src/components/ChatWindow/index.tsx`

**Delete lines 100-104:**
```tsx
<div className="session-info">
  <div className={`status-indicator ${isStreaming ? 'processing' : 'ready'}`}>
    {isStreaming ? `[>] ${currentStatus || 'PROCESSING...'}` : '[*] SYSTEMS NOMINAL'}
  </div>
</div>
```

The header should now be just the outer `<div className="chat-header">` containing:
- The flex row with `<h2>AI HTML Builder</h2>` and `<div className="header-actions">` (which has the 3-dot menu)

Note: `currentStatus` prop is still used by `MessageList` (via streaming label), so do NOT remove it from the component props.

### Step 2.2: Clean up status indicator CSS

**File:** `frontend/src/components/ChatWindow/ChatWindow.css`

Delete ALL `.status-indicator` rules (`.status-indicator`, `.status-indicator.ready`, `.status-indicator.processing`).
Delete `.session-info` rules if present.

**File:** `frontend/src/App.css`

Delete `.session-info` rules (lines 44-48).
Delete `.status-indicator` and `.status-indicator.ready` and `.status-indicator.processing` rules (lines 50-77).

### Phase 2 Verification

```bash
cd frontend && npm run build && npm run lint
```

- Header shows: "AI HTML Builder" (left) + 3-dot menu (right)
- No "SYSTEMS NOMINAL" or processing status
- Header has purple gradient background
- No console warnings about unused props

---

## Phase 3: Enter Key Behavior

Standard chat convention: Enter sends, Shift+Enter for newline.

### Step 3.1: Flip key handler

**File:** `frontend/src/components/ChatWindow/ChatInput.tsx`

**Replace lines 171-176:**
```tsx
const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
    e.preventDefault();
    handleSubmit(e);
  }
};
```

**With:**
```tsx
const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    handleSubmit(e);
  }
};
```

### Step 3.2: Update help text

**Same file, line 432:**

Replace `Ctrl/Cmd + Enter to send` with `Shift + Enter for new line`

### Step 3.3: Update send button title

**Same file, line 374:**

Replace `Send message (Ctrl/Cmd + Enter)` with `Send message (Enter)`

### Phase 3 Verification

- `npm run build && npm run lint`
- Enter key sends message
- Shift+Enter inserts newline
- Footer shows "Shift + Enter for new line"
- Send button tooltip shows "Send message (Enter)"

---

## Phase 4: Document Tabs Overhaul

Bigger, more visible tabs with gold active indicator.

### Step 4.1: Update DocumentTabs CSS

**File:** `frontend/src/components/DocumentTabs/DocumentTabs.css`

Changes to make:
- `.document-tab`: font-size `var(--fs-xs)` → `var(--fs-sm)`, padding `6px 24px 6px 14px` → `10px 28px 10px 18px`
- `.document-tab.active`: Replace `border-top: 2px solid` + `border-top-color: var(--accent-primary)` with `border-bottom: 3px solid var(--accent-primary)`, remove `border-top`. Background: `var(--surface-raised)`. Text color: `var(--text-primary)` (mint).
- `.document-tab` (inactive): background `var(--surface-base)`, color `var(--text-secondary)` (coral)
- `.document-tabs-container`: add subtle `border-bottom: 1px solid var(--border-default)` if not present
- Remove `text-transform: uppercase` from tab text if present

### Phase 4 Verification

- `npm run build`
- Tabs are visually larger and more prominent
- Active tab has gold bottom border + mint text
- Inactive tabs have coral text
- Multiple document tabs are clearly distinguishable

---

## Phase 5: Empty State & Template Cards

Fix duplicate icons, enlarge cards, improve empty state.

### Step 5.1: Switch to per-template icon mapping

**File:** `frontend/src/components/EmptyState/TemplateCards.tsx`

**Replace the `CATEGORY_ICONS` map (lines 8-15):**
```tsx
const CATEGORY_ICONS: Record<string, string> = {
  'Business Reports': '📊',
  'Technical': '📖',
  'Analytics': '📈',
  'Project Management': '📋',
  'Operations': '⚙️',
  'Presentation': '🎯',
};
```

**With a `TEMPLATE_ICONS` map keyed by template `id`:**
```tsx
const TEMPLATE_ICONS: Record<string, string> = {
  'impact-assessment': '📊',
  'documentation': '📖',
  'dashboard': '📈',
  'project-report': '🗓️',
  'process-documentation': '🔄',
  'presentation': '🎬',
  'stakeholder-brief': '📝',
  'brd': '📐',
};
```

**Update the icon lookup in JSX (line 34):**

Replace `{CATEGORY_ICONS[t.category] || '📄'}` with `{TEMPLATE_ICONS[t.id] || '📄'}`

### Step 5.2: Enlarge template cards CSS

**File:** `frontend/src/components/EmptyState/TemplateCards.css`

Changes:
- `.template-cards-grid`: `grid-template-columns: repeat(auto-fill, minmax(180px, 1fr))` → `minmax(260px, 1fr)`
- `.template-card`: padding `12px` → `24px`
- `.template-card-title`: font-size `var(--fs-sm)` → `var(--fs-base)`
- `.template-card-desc`: font-size `var(--fs-xs)` → `var(--fs-sm)`
- `.template-card-icon` container: width/height `36px` → `52px`, add `border: 1px solid var(--accent-primary)` (gold ring), font-size increase proportionally
- `.template-cards-heading`: font-size `var(--fs-xs)` → `var(--fs-sm)`
- `.template-card:hover`: add `box-shadow: var(--shadow-glow-accent)` + `border-left: 3px solid var(--accent-primary)`

### Step 5.3: Fix right pane empty state

**File:** `frontend/src/App.css`

**Replace `.placeholder` background** (lines 261-266):

Remove the grid pattern:
```css
background:
  linear-gradient(var(--border-subtle) 1px, transparent 1px),
  linear-gradient(90deg, var(--border-subtle) 1px, transparent 1px);
background-size: 40px 40px;
background-position: center center;
```

Replace with:
```css
background: var(--surface-base);
background-image: radial-gradient(ellipse at center, var(--surface-raised) 0%, var(--surface-base) 70%);
```

Bump `.placeholder h3` font-size to `var(--fs-sm)` and `.placeholder p` to `var(--fs-sm)`.

### Phase 5 Verification

- `npm run build && npm run lint`
- All 8 template cards show unique icons (no duplicates)
- Cards are larger, text is readable
- Right pane shows subtle purple radial gradient (no grid)
- Card hover shows gold glow

---

## Phase 6: Chat Messages & Input

Most message styling auto-propagates via CSS variables. Fix send button and footer contrast.

### Step 6.1: Send button dark text

**File:** `frontend/src/components/ChatWindow/ChatInput.css`

The send button (`.send-button`, line 113) currently uses `color: white`. The gradient will auto-update via `--gradient-send-btn` (now gold).

**Change:** `.send-button` → `color: var(--text-inverse)` (dark text on gold background).

This ensures the send arrow icon is dark on gold, not white on gold.

### Step 6.2: Fix footer button contrast

**Same file**, `.add-visual-btn, .attach-file-btn` (lines 228-241):

Change `color: var(--text-tertiary)` → `color: var(--text-secondary)` (coral — visible, not grey-out).

### Step 6.3: Verify message auto-propagation

No CSS edits needed in `MessageList.css` — the variables handle it:
- User message gradient: `--gradient-user-msg` (now purple depth)
- AI left border: `--accent-primary` (now gold)
- Text: `--fs-base` (now 16px)
- Template badge: `--accent-primary` (now gold)

### Phase 6 Verification

- `npm run build`
- Send button: gold gradient with dark arrow icon
- Footer buttons ("Attach File", "Add Visual"): coral text, not grey
- Footer button hover: gold border + gold text (auto via `--border-accent`, `--accent-primary`)
- User messages: purple gradient background
- AI messages: gold left border

---

## Phase 7: Version History Overhaul

Widen panel, fix crowded preview bar by stacking vertically.

### Step 7.1: Widen panel

**File:** `frontend/src/components/VersionHistory/VersionTimeline.css`

Change panel width from `260px` to `300px`. Look for `.version-timeline` or `.version-panel` width rule.

### Step 7.2: Stack preview bar vertically

Find the `.version-preview-bar` rule. Currently it's a horizontal flex row with 3 elements fighting for space.

Change to:
```css
.version-preview-bar {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  /* ... keep existing background/border */
}
```

The buttons inside should wrap or stack:
```css
.version-preview-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
```

If the TSX structure in `VersionTimeline.tsx` doesn't have a wrapping element around the buttons, add one with `className="version-preview-actions"`.

### Step 7.3: Gold current version marker

Change the current version indicator from green (`--signal-success` or `--signal-active`) to gold (`--accent-primary`). Look for `.version-item.current` or similar selector with `border-left-color` or `background` using signal-success/signal-active.

### Phase 7 Verification

- `npm run build`
- Version history panel is 300px wide
- Preview bar shows "Viewing vN" on top, buttons below (no overlap)
- Current version has gold left border
- Buttons in preview bar are fully visible and clickable

---

## Phase 8: Right Pane (Viewer)

View controls, export, code viewer — all need gold active states and better disabled opacity.

### Step 8.1: View controls active state

**File:** `frontend/src/App.css`

`.view-controls button.active` (line 165-169): These will auto-update since they use `--accent-primary` for background and `--text-inverse` for color. Verify the active button is gold bg + dark text.

### Step 8.2: Fix disabled opacity globally

Search all CSS files for `opacity: 0.35` and change to `opacity: 0.5`:

- `frontend/src/App.css`: `.history-btn:disabled`, `.fullscreen-btn:disabled`, `.export-btn:disabled`
- `frontend/src/components/ChatWindow/ChatInput.css`: `.add-visual-btn:disabled`, `.attach-file-btn:disabled`
- `frontend/src/components/Export/ExportDropdown.css`: any disabled states
- `frontend/src/components/ChatWindow/PromptLibraryButton.css`: disabled state (line ~36)

Change all from `opacity: 0.35` to `opacity: 0.5`.

### Step 8.3: Export dropdown gold highlights

**File:** `frontend/src/components/Export/ExportDropdown.css`

Hover states should auto-update via `--accent-primary` variables. Verify export menu items show gold on hover.

### Step 8.4: CodeView gold buttons

**File:** `frontend/src/components/CodeViewer/CodeView.css`

- Copy button: should use gold bg + dark text on active/success state
- Save button: verify gold gradient via `--gradient-send-btn`
- Discard button: ghost outline style (border only, no fill)
- CodeMirror background: will auto-update via `--surface-void` / `--surface-base` variables
- **Keep VS Code Dark+ syntax colors** — they are hardcoded in StreamingMarkdown.css, not themed

### Phase 8 Verification

- `npm run build`
- View toggle: active tab is gold bg + dark text
- Disabled buttons: 50% opacity (not 35%)
- Export dropdown: gold hover highlights
- Code view: purple surfaces, syntax colors unchanged
- Copy/Save buttons: gold themed

---

## Phase 9: Remaining Components & Polish

### Step 9.1: Remove SplitPane transmitting animation

**File:** `frontend/src/components/Layout/SplitPane.css`

**Delete ALL `.split-pane-divider.transmitting` rules** — the transmitting class, `::after` pseudo-element, and any associated animation. This includes:
- `.split-pane-divider.transmitting` selector and its rules
- `.split-pane-divider.transmitting::after` selector and its rules

**Keep:** `.split-pane-divider:hover` and `.split-pane-divider.dragging` rules (update accent colors to gold via variables — should auto-propagate).

### Step 9.2: Remove isProcessing prop from SplitPane

**File:** `frontend/src/components/Layout/SplitPane.tsx`

- **Line 10**: Remove `isProcessing?: boolean;` from the `SplitPaneProps` interface
- **Line 19**: Remove `isProcessing = false` from the destructured props
- **Line 94**: Remove `${isProcessing ? ' transmitting' : ''}` from the className string

**File:** `frontend/src/App.tsx`

- **Line 310**: Remove `isProcessing={isStreaming}` from the `<SplitPane>` JSX

### Step 9.3: PromptLibraryModal purple/gold theme

**File:** `frontend/src/components/ChatWindow/PromptLibraryModal.css`

- Modal overlay: change `rgba(0, 0, 0, 0.75)` → `rgba(17, 11, 32, 0.8)`
- "Use Template" button: already uses `--gradient-send-btn` (now gold) — verify it has `color: var(--text-inverse)` for dark text
- Headings: should auto-update to mint via `--text-primary`

### Step 9.4: ConfirmDialog purple overlay + gold confirm

**File:** `frontend/src/components/ConfirmDialog/ConfirmDialog.css`

- Overlay: change `rgba(0, 0, 0, 0.75)` → `rgba(17, 11, 32, 0.8)`
- Confirm button: uses `--gradient-send-btn` (now gold) — verify `color: var(--text-inverse)`
- Destructive `.danger` variant: **keep red** (`--signal-error`) — unchanged
- Cancel button: ghost style (border only, transparent bg)

### Step 9.5: StreamingMarkdown code block styling

**File:** `frontend/src/components/Chat/StreamingMarkdown.css`

- Code blocks (`.streaming-markdown pre`): bg should be `var(--surface-void)` (auto-updates to darkest purple)
- Inline code (`.streaming-markdown code`): should use gold background tint — change to `background: var(--accent-primary-muted)` and `color: var(--accent-primary)` if not already
- **Light mode hljs overrides already deleted in Phase 1, Step 1.6**
- Streaming cursor: will auto-update via `--signal-active` (now mint)

### Step 9.6: index.css scrollbar & selection polish

**File:** `frontend/src/index.css`

- Scrollbar thumb: `var(--border-strong)` (auto-updates to `#6B50B5` — lavender)
- Scrollbar track: keep `transparent`
- `::selection`: `background: var(--accent-primary-muted)` (auto-updates to gold tint), `color: var(--text-primary)` (mint)
- `:focus-visible`: `outline: 2px solid var(--border-accent)` (auto-updates to gold)
- **Theme toggle styles already deleted in Phase 1, Step 1.4**

### Phase 9 Verification

```bash
cd frontend && npm run build && npm run lint
```

- SplitPane divider: no pulsing animation during streaming, gold accent on hover/drag
- No TypeScript errors from removing `isProcessing` prop
- Prompt library modal: purple-tinted overlay, gold "Use Template" button
- Confirm dialog: purple overlay, gold confirm, red destructive
- Streaming markdown: purple code blocks, gold inline code, mint cursor
- Scrollbar: lavender thumb on transparent track
- Text selection: gold tint background

---

## Files Modified (19 + 1 deleted)

| # | File | Phase | Changes |
|---|------|-------|---------|
| 1 | `frontend/src/theme.css` | 1 | Full variable rewrite, delete light theme block |
| 2 | `frontend/src/index.css` | 1, 9 | Delete theme toggle styles, verify scrollbar/selection |
| 3 | `frontend/index.html` | 1 | Delete theme init script (4 lines) |
| 4 | `frontend/src/components/ChatWindow/index.tsx` | 1, 2 | Remove ThemeToggle import + render, delete status indicator |
| 5 | `frontend/src/components/ChatWindow/ChatWindow.css` | 2 | Delete status indicator + session info CSS |
| 6 | `frontend/src/App.css` | 2, 5, 8 | Delete status CSS, fix placeholder, fix disabled opacity |
| 7 | `frontend/src/components/ChatWindow/ChatInput.tsx` | 3 | Enter-to-send, update help text + button title |
| 8 | `frontend/src/components/ChatWindow/ChatInput.css` | 6, 8 | Gold send button dark text, fix footer contrast, fix disabled opacity |
| 9 | `frontend/src/components/DocumentTabs/DocumentTabs.css` | 4 | Bigger tabs, gold bottom border, coral inactive text |
| 10 | `frontend/src/components/EmptyState/TemplateCards.tsx` | 5 | Per-template unique icon mapping |
| 11 | `frontend/src/components/EmptyState/TemplateCards.css` | 5 | Bigger cards/grid, larger text, gold icon ring, gold hover |
| 12 | `frontend/src/components/VersionHistory/VersionTimeline.css` | 7 | 300px width, stacked preview bar, gold current marker |
| 13 | `frontend/src/components/CodeViewer/CodeView.css` | 8 | Gold buttons, verify purple surfaces |
| 14 | `frontend/src/components/Export/ExportDropdown.css` | 8 | Fix disabled opacity, verify gold hover |
| 15 | `frontend/src/components/Layout/SplitPane.css` | 9 | Delete transmitting animation entirely |
| 16 | `frontend/src/components/Layout/SplitPane.tsx` | 9 | Remove `isProcessing` prop |
| 17 | `frontend/src/App.tsx` | 9 | Remove `isProcessing={isStreaming}` from SplitPane |
| 18 | `frontend/src/components/ChatWindow/PromptLibraryModal.css` | 9 | Purple overlay, verify gold button |
| 19 | `frontend/src/components/ConfirmDialog/ConfirmDialog.css` | 9 | Purple overlay, verify gold confirm |
| 20 | `frontend/src/components/Chat/StreamingMarkdown.css` | 1, 9 | Delete light hljs overrides, gold inline code |
| — | `frontend/src/components/ChatWindow/PromptLibraryButton.css` | 8 | Fix disabled opacity |

**Deleted:** `frontend/src/components/ThemeToggle.tsx`

---

## Final Verification Checklist

After ALL phases complete:

### Build & Lint
```bash
cd frontend && npm run build && npm run lint
```

### Visual States to Check (`npm run dev`)
1. **Loading screen**: Purple background, mint glyph, gold pulse animation
2. **Empty state**: Large template cards with unique icons, purple radial gradient in right pane
3. **Chat active**: Mint text, user = purple gradient, AI = gold left border
4. **Streaming**: No divider pulse, streaming text + typing indicator sufficient
5. **Multi-document tabs**: Gold bottom border on active, coral on inactive, clearly readable
6. **Code view**: Purple surfaces, VS Code Dark+ syntax colors, gold toggle
7. **Version history**: 300px panel, stacked preview bar (no button overlap), gold current marker
8. **Export dropdown**: Gold hover highlights, 50% disabled opacity
9. **Confirm dialog**: Purple overlay, gold confirm button, red destructive
10. **Template modal**: Purple overlay, gold "Use Template" button

### Responsive (Chrome DevTools)
- 768px breakpoint: layout adapts, no overflow
- 480px breakpoint: mobile layout, no broken elements

### Gold Discipline Audit
Verify gold (`#E5B800` / `--accent-primary`) appears ONLY on:
- Send button
- Active view toggle
- Active document tab border
- Template card hover glow
- Confirm button
- "Use Template" button
- Focus outlines
- Active borders/accents

Gold must NOT appear on:
- Body text
- Headings
- Static labels
- Inactive elements
- Backgrounds (except button fills)

### Generated Content Isolation
- Create a document via chat
- Verify iframe preview renders with its OWN CSS (not affected by app theme)
- Export as HTML — verify exported file is self-contained with inline styles

---

## Execution Notes

- **Phase 1 is critical path** — every other phase depends on CSS variable changes
- Most component styling auto-propagates via variables — many phases are just verification
- The TSX changes are minimal: ThemeToggle removal, status indicator removal, Enter key flip, template icon map, SplitPane prop cleanup
- No backend changes, no new dependencies, no database changes
- Commit after all phases complete with a descriptive message
