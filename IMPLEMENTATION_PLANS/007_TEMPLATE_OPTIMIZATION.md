# Implementation Plan 007: Template Optimization & Placeholder Bug Fix

## ⚠️ STOP - READ THIS FIRST ⚠️

**DO NOT START** this implementation until:
- ✅ Plan 006 (File Upload & Templates) is FULLY complete and tested
- ✅ You have read this ENTIRE document
- ✅ You understand the template pipeline: user clicks template card → prompt inserted in textarea → user edits placeholder → sends to Gemini 2.5 Pro via SSE
- ✅ You understand that templates are **user-facing prompt text**, NOT system prompts

**DESTRUCTIVE ACTIONS PROHIBITED:**
- ❌ Do NOT modify `CREATION_SYSTEM_PROMPT` in `creator.py` (it is well-scoped and tested)
- ❌ Do NOT modify `EDIT_SYSTEM_PROMPT` in `editor.py`
- ❌ Do NOT change the routing logic in `router.py`
- ❌ Do NOT change the template API endpoints in `templates.py` or `template_service.py`
- ❌ Do NOT modify `TemplateCards.tsx` component structure (only add category icons if needed)

**DEPENDENCIES:**
- Plan 006: Template system (builtin + custom), file upload, template cards UI

**ESTIMATED EFFORT:** 1-2 days

---

## Context & Rationale

### Current State
The AI HTML Builder has 8 builtin prompt templates in `backend/app/config/builtin_templates.json` and a frontend fallback in `frontend/src/data/promptTemplates.ts`. These templates are displayed as cards on the empty state screen and in the Prompt Library modal.

### Problems Found

#### Bug 1: Placeholder Handling Broken
The backend templates use `[YOUR TOPIC]` style placeholders, but the frontend code in `ChatInput.tsx` does `.replace('{USER_CONTENT}', '')` which is a no-op when the backend format is used. The cursor positioning code tries to select a `[Your content here]` string that was never inserted.

**Impact:** When users click a template card (normal flow with backend running), the placeholder text is NOT auto-selected. Users must manually find and delete the `[YOUR TOPIC]` text.

#### Bug 2: Frontend/Backend Template Mismatch
- Backend: 8 templates (includes Meeting Notes, Data Analysis Report)
- Frontend fallback: 6 templates (missing those 2)
- Placeholder format differs: `{USER_CONTENT}` (frontend) vs `[YOUR TOPIC]` (backend)

#### Bug 3: Template Content Too Vague
Current templates say things like "Organize into logical tabbed sections" without specifying:
- What HTML elements to use for tabs (nav buttons, panel divs, JavaScript)
- Card layouts, grid patterns, SVG chart types
- Specific interactive patterns

Gemini 2.5 Pro excels at aesthetics (WebDev Arena #1) but is weaker at constraint-following than Claude. Without specific structural instructions, output varies wildly between runs.

#### Bug 4: Low-Value Templates
"Meeting Notes" and "Data Analysis Report" are too simple to need templates. Users would just type "create meeting notes for X." Their slots are better used for templates that need structural guidance.

#### Bug 5: Token Limit Too Conservative
`max_tokens=16000` in `creator.py` could truncate very long documents (presentations with 15+ slides, large BRDs with many sections). Bumping to 24000 provides headroom at no cost (you only pay for tokens generated).

### What We're Changing

1. **Unified placeholder format**: All templates use `{{PLACEHOLDER}}` (double curly braces, descriptive per template)
2. **Fixed frontend handling**: ChatInput.tsx and PromptLibraryModal.tsx regex-match `{{[A-Z_]+}}`
3. **Rewritten template content**: Specific HTML structural instructions for Gemini
4. **Replaced 2 templates**: Meeting Notes → Stakeholder Brief, Data Analysis → BRD
5. **Synced frontend fallback**: 8 templates matching backend exactly
6. **Bumped token limit**: 16000 → 24000

### Template Design Principles

1. **Templates ADD structure, don't repeat style rules.** The `CREATION_SYSTEM_PROMPT` already covers colors, spacing, accessibility, semantic HTML. Templates specify template-specific patterns (tabs, charts, timelines).

2. **Templates are adaptive, not rigid.** They say "include sections only if content exists" so Gemini doesn't force sections that don't match the user's material.

3. **Templates serve users with weak prompting skills.** A user should be able to paste rough notes, hit send, and get a well-structured document. The template does the prompting for them.

4. **Descriptions clearly differentiate similar templates.** "Track project progress with milestones, timelines, and team status" vs "Turn rough notes and loose documents into polished stakeholder-ready summaries."

### Architecture Decision: Why `{{PLACEHOLDER}}` Format?

| Format | Pros | Cons |
|---|---|---|
| `{USER_CONTENT}` (old frontend) | Simple regex | Generic, not descriptive, confusable with JS template literals |
| `[YOUR TOPIC]` (old backend) | Descriptive, visually obvious | Hard to regex-match reliably, conflicts with markdown links |
| `{{TOPIC}}` (new unified) | Descriptive, easy to regex (`/\{\{[A-Z_]+\}\}/`), standard templating convention | Requires frontend code fix |

Decision: **`{{PLACEHOLDER}}`** — best of both worlds.

---

## Strict Rules - Check Before Each Commit

### Template Content Rules
- [ ] Templates do NOT duplicate `CREATION_SYSTEM_PROMPT` content (no color hex codes, no spacing values, no accessibility rules)
- [ ] Each template specifies at least 3 concrete HTML structure patterns (e.g., "tab nav buttons", "SVG bar chart", "CSS Grid cards")
- [ ] Each template includes adaptive language ("include only if content exists", "based on the material provided")
- [ ] Each template has exactly ONE `{{PLACEHOLDER}}` token in the opening line
- [ ] Placeholder names are descriptive: `{{TOPIC}}`, `{{PROJECT_NAME}}`, `{{SYSTEM_NAME}}`, etc.
- [ ] Template descriptions clearly differentiate from other templates (especially Project Report vs Stakeholder Brief)

### Code Quality Rules
- [ ] Frontend placeholder regex matches `{{[A-Z_]+}}` pattern (not hardcoded strings)
- [ ] Frontend fallback `promptTemplates.ts` has exactly 8 templates matching backend
- [ ] All `max_tokens` values in `creator.py` changed from 16000 to 24000 (4 occurrences)
- [ ] TypeScript compiles without errors
- [ ] Ruff and mypy pass on changed files

### Testing Rules
- [ ] `test_builtin_templates_have_all_ids` updated with new template IDs
- [ ] New test validates `{{PLACEHOLDER}}` format across all templates
- [ ] `test_create_uses_correct_params` in `test_creator.py` updated with new `max_tokens` value
- [ ] All existing tests still pass (244/245, 1 pre-existing failure: `test_init_db_creates_file`)
- [ ] Frontend builds without errors

---

## Phase 1: Fix Placeholder Handling (Frontend)

### Objective
Fix the broken placeholder detection and cursor positioning when users click template cards.

### 1.1 Fix ChatInput.tsx Template Selection

**File:** `frontend/src/components/ChatWindow/ChatInput.tsx`

**Current code (lines 102-121) — BROKEN:**
```typescript
  const handleTemplateSelect = (template: PromptTemplate) => {
    const templateText = template.template.replace('{USER_CONTENT}', '');
    setMessage(templateText);
    // Focus the textarea after inserting template
    setTimeout(() => {
      if (textareaRef.current) {
        textareaRef.current.focus();
        // Position cursor at the placeholder location
        const placeholderText = '[Your content here]';
        const withPlaceholder = templateText.replace(/\n\n$/, `\n\n${placeholderText}`);
        setMessage(withPlaceholder);

        // Select the placeholder text for easy replacement
        const startPos = withPlaceholder.indexOf(placeholderText);
        if (startPos !== -1) {
          textareaRef.current.setSelectionRange(startPos, startPos + placeholderText.length);
        }
      }
    }, 100);
  };
```

**Replace with:**
```typescript
  const handleTemplateSelect = (template: PromptTemplate) => {
    const templateText = template.template;
    setMessage(templateText);
    // Focus the textarea after inserting template
    setTimeout(() => {
      if (textareaRef.current) {
        textareaRef.current.focus();
        // Select the {{PLACEHOLDER}} token for easy replacement
        const match = templateText.match(/\{\{[A-Z_]+\}\}/);
        if (match && match.index !== undefined) {
          textareaRef.current.setSelectionRange(
            match.index,
            match.index + match[0].length
          );
        } else {
          // No placeholder found — position cursor at end
          textareaRef.current.setSelectionRange(
            templateText.length,
            templateText.length
          );
        }
      }
    }, 100);
  };
```

**What changed:**
1. Removed `.replace('{USER_CONTENT}', '')` — no longer needed
2. Removed `[Your content here]` injection — placeholder is already in the template
3. Added regex match for `{{[A-Z_]+}}` — selects the actual placeholder token
4. Added fallback to position cursor at end if no placeholder found

### 1.2 Fix PromptLibraryModal Preview

**File:** `frontend/src/components/ChatWindow/PromptLibraryModal.tsx`

**Current code (line 132-133) — BROKEN:**
```typescript
                  {selectedTemplate.template
                      .replace('{USER_CONTENT}', '[Your content will be inserted here]')
```

**Replace with:**
```typescript
                  {selectedTemplate.template
                      .replace(/\{\{[A-Z_]+\}\}/g, '[Your content here]')
```

**What changed:**
- Regex replacement matches any `{{PLACEHOLDER}}` token
- Uses `/g` flag to replace ALL placeholder occurrences (though templates should have only one)
- Display text changed to `[Your content here]` (shorter, consistent)

### 1.3 Fix PromptLibraryModal Section Header Highlighting

> **Discrepancy found during implementation:** This step was NOT in the original plan document but was required. The preview code at lines 137-143 used hardcoded `startsWith` checks for old section header names (`'DESIGN REQUIREMENTS:'`, `'CONTENT TO INCLUDE:'`, `'STRUCTURE REQUIREMENTS:'`, `'FEATURES REQUIRED:'`, `'INTERACTIVE FEATURES:'`, `'REPORT SECTIONS:'`, `'WORKFLOW FEATURES:'`). The rewritten templates use completely different headers (`'HTML STRUCTURE:'`, `'CONTENT SECTIONS:'`, `'INTERACTIVE ELEMENTS:'`, `'CHART TYPES:'`, `'DESIGN DETAILS:'`, `'SLIDE TYPES:'`, `'JAVASCRIPT REQUIREMENTS:'`, `'STATUS COMPONENTS:'`, `'VISUAL COMPONENTS:'`, `'BRD SECTIONS:'`, `'DESIGN COMPONENTS:'`, `'CRITICAL INSTRUCTIONS:'`). Without this fix, the preview would lose all section header highlighting.

**File:** `frontend/src/components/ChatWindow/PromptLibraryModal.tsx`

**Current code (lines 136-144) — BROKEN for new templates:**
```typescript
                        <div key={index} className={
                          line.startsWith('DESIGN REQUIREMENTS:') ||
                          line.startsWith('CONTENT TO INCLUDE:') ||
                          line.startsWith('STRUCTURE REQUIREMENTS:') ||
                          line.startsWith('FEATURES REQUIRED:') ||
                          line.startsWith('INTERACTIVE FEATURES:') ||
                          line.startsWith('REPORT SECTIONS:') ||
                          line.startsWith('WORKFLOW FEATURES:')
                            ? 'section-header' : 'template-line'
                        }>
```

**Replace with:**
```typescript
                        <div key={index} className={
                          /^[A-Z][A-Z _/&()-]+:/.test(line)
                            ? 'section-header' : 'template-line'
                        }>
```

**What changed:**
- Replaced 7 hardcoded `startsWith` checks with a single regex `/^[A-Z][A-Z _/&()-]+:/`
- Regex matches any line starting with 2+ uppercase letters (with spaces, slashes, ampersands, parentheses, hyphens allowed) followed by `:`
- This covers all current section headers AND any future headers without needing code changes
- More maintainable: templates can be tweaked without updating the highlighting code

### Build Verification (Phase 1)
```bash
cd frontend && npx tsc --noEmit
cd frontend && npm run build
```

---

## Phase 2: Bump Token Limit (Backend)

### Objective
Increase `max_tokens` from 16000 to 24000 for creation calls to handle longer documents.

### 2.1 Update creator.py

**File:** `backend/app/services/creator.py`

Change all 4 occurrences of `max_tokens=16000` to `max_tokens=24000`:

**Line 79 (create method, primary):**
```python
            result = await self.provider.generate(
                system=CREATION_SYSTEM_PROMPT,
                messages=messages,
                max_tokens=24000,
                temperature=0.7,
            )
```

**Line 89 (create method, fallback):**
```python
                result = await self.fallback.generate(
                    system=CREATION_SYSTEM_PROMPT,
                    messages=messages,
                    max_tokens=24000,
                    temperature=0.7,
                )
```

**Line 114 (stream_create method, primary):**
```python
            async for chunk in self.provider.stream(
                system=CREATION_SYSTEM_PROMPT,
                messages=messages,
                max_tokens=24000,
                temperature=0.7,
            ):
```

**Line 127 (stream_create method, fallback):**
```python
                async for chunk in self.fallback.stream(
                    system=CREATION_SYSTEM_PROMPT,
                    messages=messages,
                    max_tokens=24000,
                    temperature=0.7,
                ):
```

### 2.2 Update test_creator.py max_tokens Assertion

> **Discrepancy found during implementation:** This step was NOT in the original plan document. The test `test_create_uses_correct_params` in `backend/tests/test_creator.py` (line 110) asserts `call_args["max_tokens"] == 16000`. Changing `creator.py` without updating this test causes a test failure. Any future change to `max_tokens` must also update this assertion.

**File:** `backend/tests/test_creator.py`

**Current code (line 110):**
```python
    assert call_args["max_tokens"] == 16000
```

**Replace with:**
```python
    assert call_args["max_tokens"] == 24000
```

### Build Verification (Phase 2)
```bash
ruff check backend/app/services/creator.py
mypy backend/app/services/creator.py
```

---

## Phase 3: Rewrite Template Content (Backend)

### Objective
Rewrite all 8 templates in `builtin_templates.json` with specific HTML structural instructions.

### 3.1 Complete Template JSON

**File:** `backend/app/config/builtin_templates.json`

**Replace entire file with:**

```json
{
  "templates": [
    {
      "id": "impact-assessment",
      "name": "Impact Assessment Report",
      "category": "Business Reports",
      "description": "Professional report with tabbed navigation, analysis sections, and risk assessment",
      "prompt_template": "Create a professional impact assessment report about: {{TOPIC}}\n\nHTML STRUCTURE:\n- Header: Gradient banner with report title and date\n- Tab Navigation: <nav> with <button> elements for each major section. JavaScript click handlers toggle active class and show/hide tab panels.\n- Tab Panels: <div class=\"tab-panel\"> containers, only one visible at a time. First tab auto-activated on page load.\n- Executive Summary: Highlighted card at top with key findings in bullet points\n\nCONTENT SECTIONS (create tabs only for sections that match the provided content):\n- Executive Summary: Key findings, highlighted metrics, overall assessment\n- Analysis: Organized findings with <section> blocks, data tables where applicable\n- Recommendations: Numbered action items with priority badges (High/Medium/Low)\n- Risk Assessment: Risk cards with severity indicators using color-coded borders\n\nINTERACTIVE ELEMENTS:\n- Tab switching via JavaScript (addEventListener on buttons, toggle display of panels)\n- Status badges: Pill-shaped <span> elements (green for low risk, yellow for medium, red for high)\n- Solution comparison: Two-column layout for pros vs cons\n- Collapsible details sections using <details><summary> for lengthy analysis\n\nDo NOT force sections that don't match the provided content. Adapt the structure to fit the actual material."
    },
    {
      "id": "documentation",
      "name": "Technical Documentation",
      "category": "Technical",
      "description": "Documentation site with sidebar navigation, code examples, and collapsible sections",
      "prompt_template": "Create comprehensive technical documentation for: {{SYSTEM_NAME}}\n\nHTML STRUCTURE:\n- Fixed Sidebar: <aside> with nested <ul> navigation tree. Each <li> contains an <a> with href=\"#section-id\" for smooth scrolling.\n- Main Content: <main> with scroll-margin-top on each <section> to account for any fixed header.\n- Code Blocks: <pre><code> elements with dark background and monospace font. Use CSS to style keywords, strings, and comments in different colors.\n- Collapsible Sections: <details><summary> for FAQ items, troubleshooting steps, and optional deep-dives.\n\nCONTENT SECTIONS (include only those relevant to the provided material):\n- Overview / Getting Started: Introduction, prerequisites, quick start steps\n- Core Concepts: Key terminology and architecture explained\n- API Reference / Usage: Methods, endpoints, or procedures in definition lists (<dl><dt><dd>)\n- Code Examples: Inline examples in styled <pre> blocks\n- Troubleshooting / FAQ: Common issues in collapsible <details> elements\n\nDESIGN DETAILS:\n- Sidebar: 240px width, light background, sticky positioning, collapses to hamburger menu below 768px\n- Code blocks: Dark background (#1e1e1e or similar), 14px monospace font, horizontal scroll for long lines\n- Inline code: <code> tags with light blue background and slight padding\n- Section headings: Clear hierarchy (h1 > h2 > h3) with anchor links\n\nAdapt the documentation structure to fit the actual technical content provided."
    },
    {
      "id": "dashboard",
      "name": "Business Dashboard",
      "category": "Analytics",
      "description": "Interactive dashboard with KPI cards, SVG charts, and data tables",
      "prompt_template": "Create an interactive business dashboard for: {{METRICS_OR_DATA}}\n\nHTML STRUCTURE:\n- KPI Cards Row: CSS Grid row at top with 3-4 metric cards. Each card shows: large number, label text, and trend indicator (Unicode ▲ or ▼ with color).\n- Chart Section: <div> containers for SVG-based visualizations. Create charts using inline SVG elements (no external libraries).\n- Data Table: <table> with styled headers, alternating row colors, and numeric alignment.\n- Filter Bar: Visual filter controls at top (dropdown selects or button groups for time period). Functional interactivity is optional.\n\nCHART TYPES (choose based on the data provided):\n- Bar Chart: SVG <rect> elements with labels. Vertical bars for comparisons.\n- Line Chart: SVG <path> with smooth curves for trends over time. Include axis labels.\n- Pie/Donut Chart: SVG <circle> with stroke-dasharray for percentage splits. Legend below.\n- Sparklines: Tiny inline SVG paths embedded in table cells or KPI cards.\n\nDESIGN DETAILS:\n- KPI cards: White background, subtle shadow, large bold number (32px+), small label, colored trend arrow\n- Chart colors: Cycle through accent colors for data series (blue, teal, yellow, green)\n- Responsive grid: 3-4 columns desktop, 2 columns tablet, 1 column mobile\n- Hover effects: Cards lift slightly on hover, chart elements show tooltips via title attribute\n\nUse realistic placeholder data if the user provides general metrics. Adapt chart types to match the actual data structure provided."
    },
    {
      "id": "project-report",
      "name": "Project Report",
      "category": "Project Management",
      "description": "Track project progress with milestones, timelines, and team status",
      "prompt_template": "Create a comprehensive project report for: {{PROJECT_NAME}}\n\nHTML STRUCTURE:\n- Hero Section: Full-width banner with project name, overall status badge, and key dates (start, target completion).\n- Status Dashboard: Row of 4 KPI cards showing key metrics (e.g., % complete, tasks done, risks open, days remaining).\n- Timeline: Vertical milestone list with a connecting line (CSS border-left on a container). Each milestone shows date, title, description, and status icon (filled circle = complete, outlined = in progress, gray = future).\n- Updates Section: Chronological feed of recent updates with timestamp and description.\n\nSTATUS COMPONENTS:\n- Project status badge: Pill-shaped <span> with semantic color (green = On Track, yellow = At Risk, red = Delayed)\n- Progress bars: <div> with nested colored bar at width %. Show percentage label.\n- Milestone markers: Circles positioned on the timeline line using CSS (absolute positioning or flexbox)\n- Risk/issue tags: Small colored badges (red = high, yellow = medium, green = low)\n\nCONTENT SECTIONS (include only those that match the provided information):\n- Executive Summary: Key achievements and blockers in highlighted callout boxes\n- Milestones & Timeline: Visual timeline extracted from the provided dates and deliverables\n- Team Updates: Recent activity or status changes\n- Next Steps: Action items formatted as a checkbox list (Unicode ☐ / ☑)\n- Risks & Issues: Cards with severity, description, and mitigation\n\nDESIGN DETAILS:\n- Timeline line: 3px solid colored border, positioned to the left of milestone content\n- Hero banner: Gradient background with white text, 200px height\n- Update feed: Alternating subtle background colors for visual separation"
    },
    {
      "id": "process-documentation",
      "name": "Process Documentation",
      "category": "Operations",
      "description": "Step-by-step process guide with numbered steps, decision points, and role badges",
      "prompt_template": "Create detailed process documentation for: {{PROCESS_NAME}}\n\nHTML STRUCTURE:\n- Process Overview: Summary card with purpose, scope, and estimated duration.\n- Numbered Steps: <ol> with large styled step numbers. Each step is a card with: step number (large circle), title, description, and responsible role badge.\n- Decision Points: Highlighted <div> boxes with a diamond icon or shape to indicate branching logic (IF condition THEN path A ELSE path B).\n- Sub-steps: Nested <ul> within step cards for detailed instructions.\n- Prerequisites Section: Bulleted list of required tools, permissions, or prior knowledge.\n\nVISUAL COMPONENTS:\n- Step numbers: Large circle (48px) with colored background and white number text\n- Role badges: Small pill-shaped <span> showing who performs each step (e.g., \"Analyst\", \"Manager\", \"System\")\n- Decision boxes: Highlighted background with border, diamond or arrow icon, and branching paths described\n- Warning callouts: Yellow/orange background boxes with ⚠ icon for important notes\n- Tip callouts: Blue background boxes for best practice recommendations\n- Checklist items: Unicode checkbox (☐) before verification points\n\nCONTENT SECTIONS (adapt based on the material provided):\n- Overview: Purpose and scope\n- Prerequisites: Required tools, access, knowledge\n- Procedure: Numbered step-by-step sequence\n- Decision Trees: IF/THEN branching logic from the content\n- Troubleshooting: Common issues and resolutions\n- References: Related documents or systems\n\nDo NOT add steps or decisions not present in the user's material."
    },
    {
      "id": "presentation",
      "name": "Presentation Slides",
      "category": "Presentation",
      "description": "Slide presentation with keyboard navigation, slide counter, and professional layouts",
      "prompt_template": "Create an engaging slide presentation about: {{TOPIC}}\n\nHTML STRUCTURE:\n- Slide Container: Each slide is a full-viewport <div class=\"slide\"> element. Only one slide visible at a time.\n- Slide Counter: Fixed position element showing \"3 / 12\" format (current / total).\n- Navigation: Arrow buttons (left/right) fixed at viewport sides. JavaScript handles: button clicks, keyboard arrow keys, and slide counter updates.\n- Progress Bar: Fixed top bar whose width represents current position as percentage.\n\nSLIDE TYPES (organize content into appropriate types):\n- Title Slide: Large centered title, subtitle, author/date at bottom\n- Section Header: Full background color, large centered heading to introduce a new topic\n- Content Slide: Heading + 3-5 bullet points with adequate font size (24px+ for body)\n- Two-Column: Content split into left and right halves (text + visual, or two lists)\n- Quote Slide: Large centered quote text with citation below\n- Summary Slide: Key takeaways in a numbered or icon-based grid\n\nJAVASCRIPT REQUIREMENTS:\n- Track currentSlide index (starting at 0)\n- Show/hide slides by toggling display or transform\n- Arrow key listeners (ArrowLeft = prev, ArrowRight = next)\n- Update slide counter text and progress bar width on every navigation\n- Prevent navigation beyond first/last slide\n\nDESIGN DETAILS:\n- Slide aspect ratio: Full viewport width and height (100vw x 100vh)\n- Typography: Large headings (48px), readable body (24px), consistent across slides\n- Alternate backgrounds: White and light colored slides for visual rhythm\n- Transitions: Smooth CSS transform (translateX or opacity) between slides, 0.4s ease\n- Navigation arrows: Large semi-transparent circles (60px), enlarge on hover\n\nCreate 8-12 slides. Opening: title + agenda. Body: 1 topic per slide. Closing: summary + next steps."
    },
    {
      "id": "stakeholder-brief",
      "name": "Stakeholder Brief",
      "category": "Business Reports",
      "description": "Turn rough notes and loose documents into polished stakeholder-ready summaries",
      "prompt_template": "Create a polished stakeholder brief from the following content: {{CONTENT}}\n\nIMPORTANT: This template is designed for converting rough notes, bullet points, and loose documents into a well-organized professional summary. Analyze the content provided and create the most appropriate structure.\n\nHTML STRUCTURE:\n- Header: Clean banner with brief title (derived from content), date, and intended audience if apparent.\n- Adaptive Sections: Choose ONLY sections that match the actual content. Common sections include:\n  - Key Takeaways / Summary\n  - Current Status / Progress\n  - Decisions Made or Pending\n  - Recommendations\n  - Next Steps / Action Items\n  - Open Items / Risks\n  - Background / Context\n- If multiple distinct topics exist, use tab navigation (same pattern as Impact Assessment: <nav> with <button> tabs, <div> panels, JavaScript switching).\n- If content is a single topic, use a clean single-page layout with <section> elements.\n\nDESIGN COMPONENTS:\n- Callout boxes: Highlighted <div> with left border (4px colored) for critical items, decisions, or deadlines\n- Action items: Formatted as a list with owner name in bold and due date if provided\n- Status indicators: Pill-shaped badges (green = complete, yellow = in progress, red = blocked, gray = not started)\n- Summary cards: Key metrics or counts in small cards at the top if the content contains quantitative data\n\nCRITICAL INSTRUCTIONS:\n- Do NOT force sections that don't match the content. If there are no \"risks\" in the notes, don't create a risks section.\n- Do NOT add information beyond what the user provided. Organize and format only.\n- If the content is brief, create a brief output. Don't pad with boilerplate.\n- Preserve the user's intent and key points. This is about formatting, not rewriting."
    },
    {
      "id": "brd",
      "name": "Business Requirements Document",
      "category": "Business Reports",
      "description": "Structured requirements document with scope, objectives, and specifications",
      "prompt_template": "Create a Business Requirements Document (BRD) for: {{PROJECT_OR_INITIATIVE}}\n\nHTML STRUCTURE:\n- Document Header: Title, version number (1.0), date, author placeholder, status badge\n- Tab Navigation: <nav> with <button> tabs for major BRD sections. JavaScript click handlers toggle tab panels. First tab auto-activated.\n- Requirements Table: <table> with columns: ID, Description, Priority (High/Medium/Low), Status, and optional Notes. Alternate row shading.\n- Collapsible Details: <details><summary> elements for detailed specifications within each requirement.\n- Approval Section: Sign-off area at bottom with role, name placeholder, date, and signature line.\n\nBRD SECTIONS (use tabs, include only those relevant to the content):\n- Overview: Purpose, background, business objectives\n- Scope: In-scope items, out-of-scope items (clearly separated), assumptions, constraints\n- Requirements: Functional requirements in a numbered table. Non-functional requirements in a separate table or section.\n- Dependencies: External systems, teams, or prerequisites listed with status indicators\n- Timeline: Key milestones or phases if provided\n- Approvals: Sign-off table with columns for role, name, date, signature\n\nDESIGN COMPONENTS:\n- Requirement IDs: Auto-numbered format (e.g., FR-001, FR-002 for functional; NFR-001 for non-functional)\n- Priority badges: Pill-shaped colored badges (red = High, yellow = Medium, green = Low)\n- Status badges: (Draft, In Review, Approved, Deferred) with distinct colors\n- Scope boxes: Green-bordered box for in-scope, red-bordered for out-of-scope\n- Assumption/constraint cards: Small cards with icon and brief text\n\nCRITICAL INSTRUCTIONS:\n- Structure the BRD based on the information provided. If the user provides loose notes, organize them into proper BRD format.\n- Do NOT invent requirements. Only document what the user has provided.\n- If information for a section is missing, include the section header with a placeholder note like \"[To be determined]\".\n- Use formal, professional language appropriate for a business document."
    }
  ]
}
```

### Build Verification (Phase 3)
```bash
# Verify JSON is valid
python -c "import json; json.load(open('backend/app/config/builtin_templates.json'))"
```

---

## Phase 4: Sync Frontend Fallback (Frontend)

### Objective
Update the frontend hardcoded template data to match the new backend templates exactly.

### 4.1 Rewrite promptTemplates.ts

**File:** `frontend/src/data/promptTemplates.ts`

**Replace entire file with:**

```typescript
// Prompt Template Data Structure
export interface PromptTemplate {
  id: string;
  name: string;
  category: string;
  description: string;
  template: string;
}

export const promptTemplates: PromptTemplate[] = [
  {
    id: 'impact-assessment',
    name: 'Impact Assessment Report',
    category: 'Business Reports',
    description: 'Professional report with tabbed navigation, analysis sections, and risk assessment',
    template: `Create a professional impact assessment report about: {{TOPIC}}

HTML STRUCTURE:
- Header: Gradient banner with report title and date
- Tab Navigation: <nav> with <button> elements for each major section. JavaScript click handlers toggle active class and show/hide tab panels.
- Tab Panels: <div class="tab-panel"> containers, only one visible at a time. First tab auto-activated on page load.
- Executive Summary: Highlighted card at top with key findings in bullet points

CONTENT SECTIONS (create tabs only for sections that match the provided content):
- Executive Summary: Key findings, highlighted metrics, overall assessment
- Analysis: Organized findings with <section> blocks, data tables where applicable
- Recommendations: Numbered action items with priority badges (High/Medium/Low)
- Risk Assessment: Risk cards with severity indicators using color-coded borders

INTERACTIVE ELEMENTS:
- Tab switching via JavaScript (addEventListener on buttons, toggle display of panels)
- Status badges: Pill-shaped <span> elements (green for low risk, yellow for medium, red for high)
- Solution comparison: Two-column layout for pros vs cons
- Collapsible details sections using <details><summary> for lengthy analysis

Do NOT force sections that don't match the provided content. Adapt the structure to fit the actual material.`
  },
  {
    id: 'documentation',
    name: 'Technical Documentation',
    category: 'Technical',
    description: 'Documentation site with sidebar navigation, code examples, and collapsible sections',
    template: `Create comprehensive technical documentation for: {{SYSTEM_NAME}}

HTML STRUCTURE:
- Fixed Sidebar: <aside> with nested <ul> navigation tree. Each <li> contains an <a> with href="#section-id" for smooth scrolling.
- Main Content: <main> with scroll-margin-top on each <section> to account for any fixed header.
- Code Blocks: <pre><code> elements with dark background and monospace font. Use CSS to style keywords, strings, and comments in different colors.
- Collapsible Sections: <details><summary> for FAQ items, troubleshooting steps, and optional deep-dives.

CONTENT SECTIONS (include only those relevant to the provided material):
- Overview / Getting Started: Introduction, prerequisites, quick start steps
- Core Concepts: Key terminology and architecture explained
- API Reference / Usage: Methods, endpoints, or procedures in definition lists (<dl><dt><dd>)
- Code Examples: Inline examples in styled <pre> blocks
- Troubleshooting / FAQ: Common issues in collapsible <details> elements

DESIGN DETAILS:
- Sidebar: 240px width, light background, sticky positioning, collapses to hamburger menu below 768px
- Code blocks: Dark background (#1e1e1e or similar), 14px monospace font, horizontal scroll for long lines
- Inline code: <code> tags with light blue background and slight padding
- Section headings: Clear hierarchy (h1 > h2 > h3) with anchor links

Adapt the documentation structure to fit the actual technical content provided.`
  },
  {
    id: 'dashboard',
    name: 'Business Dashboard',
    category: 'Analytics',
    description: 'Interactive dashboard with KPI cards, SVG charts, and data tables',
    template: `Create an interactive business dashboard for: {{METRICS_OR_DATA}}

HTML STRUCTURE:
- KPI Cards Row: CSS Grid row at top with 3-4 metric cards. Each card shows: large number, label text, and trend indicator (Unicode ▲ or ▼ with color).
- Chart Section: <div> containers for SVG-based visualizations. Create charts using inline SVG elements (no external libraries).
- Data Table: <table> with styled headers, alternating row colors, and numeric alignment.
- Filter Bar: Visual filter controls at top (dropdown selects or button groups for time period). Functional interactivity is optional.

CHART TYPES (choose based on the data provided):
- Bar Chart: SVG <rect> elements with labels. Vertical bars for comparisons.
- Line Chart: SVG <path> with smooth curves for trends over time. Include axis labels.
- Pie/Donut Chart: SVG <circle> with stroke-dasharray for percentage splits. Legend below.
- Sparklines: Tiny inline SVG paths embedded in table cells or KPI cards.

DESIGN DETAILS:
- KPI cards: White background, subtle shadow, large bold number (32px+), small label, colored trend arrow
- Chart colors: Cycle through accent colors for data series (blue, teal, yellow, green)
- Responsive grid: 3-4 columns desktop, 2 columns tablet, 1 column mobile
- Hover effects: Cards lift slightly on hover, chart elements show tooltips via title attribute

Use realistic placeholder data if the user provides general metrics. Adapt chart types to match the actual data structure provided.`
  },
  {
    id: 'project-report',
    name: 'Project Report',
    category: 'Project Management',
    description: 'Track project progress with milestones, timelines, and team status',
    template: `Create a comprehensive project report for: {{PROJECT_NAME}}

HTML STRUCTURE:
- Hero Section: Full-width banner with project name, overall status badge, and key dates (start, target completion).
- Status Dashboard: Row of 4 KPI cards showing key metrics (e.g., % complete, tasks done, risks open, days remaining).
- Timeline: Vertical milestone list with a connecting line (CSS border-left on a container). Each milestone shows date, title, description, and status icon (filled circle = complete, outlined = in progress, gray = future).
- Updates Section: Chronological feed of recent updates with timestamp and description.

STATUS COMPONENTS:
- Project status badge: Pill-shaped <span> with semantic color (green = On Track, yellow = At Risk, red = Delayed)
- Progress bars: <div> with nested colored bar at width %. Show percentage label.
- Milestone markers: Circles positioned on the timeline line using CSS (absolute positioning or flexbox)
- Risk/issue tags: Small colored badges (red = high, yellow = medium, green = low)

CONTENT SECTIONS (include only those that match the provided information):
- Executive Summary: Key achievements and blockers in highlighted callout boxes
- Milestones & Timeline: Visual timeline extracted from the provided dates and deliverables
- Team Updates: Recent activity or status changes
- Next Steps: Action items formatted as a checkbox list (Unicode ☐ / ☑)
- Risks & Issues: Cards with severity, description, and mitigation

DESIGN DETAILS:
- Timeline line: 3px solid colored border, positioned to the left of milestone content
- Hero banner: Gradient background with white text, 200px height
- Update feed: Alternating subtle background colors for visual separation`
  },
  {
    id: 'process-documentation',
    name: 'Process Documentation',
    category: 'Operations',
    description: 'Step-by-step process guide with numbered steps, decision points, and role badges',
    template: `Create detailed process documentation for: {{PROCESS_NAME}}

HTML STRUCTURE:
- Process Overview: Summary card with purpose, scope, and estimated duration.
- Numbered Steps: <ol> with large styled step numbers. Each step is a card with: step number (large circle), title, description, and responsible role badge.
- Decision Points: Highlighted <div> boxes with a diamond icon or shape to indicate branching logic (IF condition THEN path A ELSE path B).
- Sub-steps: Nested <ul> within step cards for detailed instructions.
- Prerequisites Section: Bulleted list of required tools, permissions, or prior knowledge.

VISUAL COMPONENTS:
- Step numbers: Large circle (48px) with colored background and white number text
- Role badges: Small pill-shaped <span> showing who performs each step (e.g., "Analyst", "Manager", "System")
- Decision boxes: Highlighted background with border, diamond or arrow icon, and branching paths described
- Warning callouts: Yellow/orange background boxes with ⚠ icon for important notes
- Tip callouts: Blue background boxes for best practice recommendations
- Checklist items: Unicode checkbox (☐) before verification points

CONTENT SECTIONS (adapt based on the material provided):
- Overview: Purpose and scope
- Prerequisites: Required tools, access, knowledge
- Procedure: Numbered step-by-step sequence
- Decision Trees: IF/THEN branching logic from the content
- Troubleshooting: Common issues and resolutions
- References: Related documents or systems

Do NOT add steps or decisions not present in the user's material.`
  },
  {
    id: 'presentation',
    name: 'Presentation Slides',
    category: 'Presentation',
    description: 'Slide presentation with keyboard navigation, slide counter, and professional layouts',
    template: `Create an engaging slide presentation about: {{TOPIC}}

HTML STRUCTURE:
- Slide Container: Each slide is a full-viewport <div class="slide"> element. Only one slide visible at a time.
- Slide Counter: Fixed position element showing "3 / 12" format (current / total).
- Navigation: Arrow buttons (left/right) fixed at viewport sides. JavaScript handles: button clicks, keyboard arrow keys, and slide counter updates.
- Progress Bar: Fixed top bar whose width represents current position as percentage.

SLIDE TYPES (organize content into appropriate types):
- Title Slide: Large centered title, subtitle, author/date at bottom
- Section Header: Full background color, large centered heading to introduce a new topic
- Content Slide: Heading + 3-5 bullet points with adequate font size (24px+ for body)
- Two-Column: Content split into left and right halves (text + visual, or two lists)
- Quote Slide: Large centered quote text with citation below
- Summary Slide: Key takeaways in a numbered or icon-based grid

JAVASCRIPT REQUIREMENTS:
- Track currentSlide index (starting at 0)
- Show/hide slides by toggling display or transform
- Arrow key listeners (ArrowLeft = prev, ArrowRight = next)
- Update slide counter text and progress bar width on every navigation
- Prevent navigation beyond first/last slide

DESIGN DETAILS:
- Slide aspect ratio: Full viewport width and height (100vw x 100vh)
- Typography: Large headings (48px), readable body (24px), consistent across slides
- Alternate backgrounds: White and light colored slides for visual rhythm
- Transitions: Smooth CSS transform (translateX or opacity) between slides, 0.4s ease
- Navigation arrows: Large semi-transparent circles (60px), enlarge on hover

Create 8-12 slides. Opening: title + agenda. Body: 1 topic per slide. Closing: summary + next steps.`
  },
  {
    id: 'stakeholder-brief',
    name: 'Stakeholder Brief',
    category: 'Business Reports',
    description: 'Turn rough notes and loose documents into polished stakeholder-ready summaries',
    template: `Create a polished stakeholder brief from the following content: {{CONTENT}}

IMPORTANT: This template is designed for converting rough notes, bullet points, and loose documents into a well-organized professional summary. Analyze the content provided and create the most appropriate structure.

HTML STRUCTURE:
- Header: Clean banner with brief title (derived from content), date, and intended audience if apparent.
- Adaptive Sections: Choose ONLY sections that match the actual content. Common sections include:
  - Key Takeaways / Summary
  - Current Status / Progress
  - Decisions Made or Pending
  - Recommendations
  - Next Steps / Action Items
  - Open Items / Risks
  - Background / Context
- If multiple distinct topics exist, use tab navigation (same pattern as Impact Assessment: <nav> with <button> tabs, <div> panels, JavaScript switching).
- If content is a single topic, use a clean single-page layout with <section> elements.

DESIGN COMPONENTS:
- Callout boxes: Highlighted <div> with left border (4px colored) for critical items, decisions, or deadlines
- Action items: Formatted as a list with owner name in bold and due date if provided
- Status indicators: Pill-shaped badges (green = complete, yellow = in progress, red = blocked, gray = not started)
- Summary cards: Key metrics or counts in small cards at the top if the content contains quantitative data

CRITICAL INSTRUCTIONS:
- Do NOT force sections that don't match the content. If there are no "risks" in the notes, don't create a risks section.
- Do NOT add information beyond what the user provided. Organize and format only.
- If the content is brief, create a brief output. Don't pad with boilerplate.
- Preserve the user's intent and key points. This is about formatting, not rewriting.`
  },
  {
    id: 'brd',
    name: 'Business Requirements Document',
    category: 'Business Reports',
    description: 'Structured requirements document with scope, objectives, and specifications',
    template: `Create a Business Requirements Document (BRD) for: {{PROJECT_OR_INITIATIVE}}

HTML STRUCTURE:
- Document Header: Title, version number (1.0), date, author placeholder, status badge
- Tab Navigation: <nav> with <button> tabs for major BRD sections. JavaScript click handlers toggle tab panels. First tab auto-activated.
- Requirements Table: <table> with columns: ID, Description, Priority (High/Medium/Low), Status, and optional Notes. Alternate row shading.
- Collapsible Details: <details><summary> elements for detailed specifications within each requirement.
- Approval Section: Sign-off area at bottom with role, name placeholder, date, and signature line.

BRD SECTIONS (use tabs, include only those relevant to the content):
- Overview: Purpose, background, business objectives
- Scope: In-scope items, out-of-scope items (clearly separated), assumptions, constraints
- Requirements: Functional requirements in a numbered table. Non-functional requirements in a separate table or section.
- Dependencies: External systems, teams, or prerequisites listed with status indicators
- Timeline: Key milestones or phases if provided
- Approvals: Sign-off table with columns for role, name, date, signature

DESIGN COMPONENTS:
- Requirement IDs: Auto-numbered format (e.g., FR-001, FR-002 for functional; NFR-001 for non-functional)
- Priority badges: Pill-shaped colored badges (red = High, yellow = Medium, green = Low)
- Status badges: (Draft, In Review, Approved, Deferred) with distinct colors
- Scope boxes: Green-bordered box for in-scope, red-bordered for out-of-scope
- Assumption/constraint cards: Small cards with icon and brief text

CRITICAL INSTRUCTIONS:
- Structure the BRD based on the information provided. If the user provides loose notes, organize them into proper BRD format.
- Do NOT invent requirements. Only document what the user has provided.
- If information for a section is missing, include the section header with a placeholder note like "[To be determined]".
- Use formal, professional language appropriate for a business document.`
  }
];

export const getTemplatesByCategory = () => {
  const categories = new Map<string, PromptTemplate[]>();

  promptTemplates.forEach(template => {
    if (!categories.has(template.category)) {
      categories.set(template.category, []);
    }
    categories.get(template.category)!.push(template);
  });

  return categories;
};

export const getTemplateById = (id: string): PromptTemplate | undefined => {
  return promptTemplates.find(template => template.id === id);
};
```

### Build Verification (Phase 4)
```bash
cd frontend && npx tsc --noEmit
cd frontend && npm run build
```

---

## Phase 5: Update Tests (Backend)

### Objective
Update test expectations for new template IDs and add placeholder format validation.

### 5.1 Update Template ID Test

**File:** `backend/tests/test_templates_api.py`

**Current code (lines 67-77):**
```python
def test_builtin_templates_have_all_ids(client: TestClient) -> None:
    resp = client.get("/api/templates/builtin")
    ids = {t["id"] for t in resp.json()["templates"]}
    expected = {
        "impact-assessment",
        "documentation",
        "dashboard",
        "project-report",
        "process-documentation",
        "presentation",
        "meeting-notes",
        "data-report",
    }
    assert ids == expected
```

**Replace with:**
```python
def test_builtin_templates_have_all_ids(client: TestClient) -> None:
    resp = client.get("/api/templates/builtin")
    ids = {t["id"] for t in resp.json()["templates"]}
    expected = {
        "impact-assessment",
        "documentation",
        "dashboard",
        "project-report",
        "process-documentation",
        "presentation",
        "stakeholder-brief",
        "brd",
    }
    assert ids == expected
```

### 5.2 Add Placeholder Format Test

**File:** `backend/tests/test_templates_api.py`

**Add after `test_builtin_templates_have_all_ids`:**

```python
def test_builtin_templates_use_unified_placeholders(client: TestClient) -> None:
    """All templates must use {{PLACEHOLDER}} format, not old formats."""
    resp = client.get("/api/templates/builtin")
    for t in resp.json()["templates"]:
        prompt = t["prompt_template"]
        # Must contain {{PLACEHOLDER}} format
        assert "{{" in prompt and "}}" in prompt, (
            f"Template '{t['id']}' missing {{{{PLACEHOLDER}}}} token"
        )
        # Must NOT contain old formats
        assert "{USER_CONTENT}" not in prompt, (
            f"Template '{t['id']}' uses old {{USER_CONTENT}} format"
        )
```

### Build Verification (Phase 5)
```bash
cd backend && python -m pytest tests/test_templates_api.py -v
```

---

## Phase 6: Final Verification

### Automated Tests
```bash
# Backend
cd backend && python -m pytest tests/test_templates_api.py -v
cd backend && python -m pytest tests/ -v  # Full suite
ruff check backend/app/services/creator.py backend/app/config/
mypy backend/app/services/creator.py

# Frontend
cd frontend && npx tsc --noEmit
cd frontend && npm run build
```

### Manual Testing Checklist
- [ ] Click each of 8 template cards on empty state → verify `{{PLACEHOLDER}}` auto-selected in textarea
- [ ] Type replacement text over selected placeholder → verify it replaces cleanly
- [ ] Press Ctrl+Enter → verify document generates successfully
- [ ] Open Prompt Library modal → verify all 8 templates listed
- [ ] Select template in modal → preview shows `[Your content here]` in place of `{{PLACEHOLDER}}`
- [ ] Click "Use This Template" → verify correct text inserted in textarea
- [ ] Verify template descriptions clearly differentiate Project Report vs Stakeholder Brief
- [ ] Verify Stakeholder Brief generates adaptive sections (not forced structure)
- [ ] Verify BRD generates tabbed requirements document with proper ID numbering

### Expected Test Results
- Backend: 244+/245 tests passing (1 pre-existing failure: test_init_db_creates_file)
- Frontend: TypeScript clean, Vite build clean
- Ruff: Clean
- Mypy: Clean

---

## Sign-off Checklist

- [x] Phase 1: Placeholder handling fixed in ChatInput.tsx and PromptLibraryModal.tsx (including section header regex — see 1.3)
- [x] Phase 2: max_tokens bumped to 24000 in creator.py (4 occurrences) AND test_creator.py assertion (see 2.2)
- [x] Phase 3: All 8 templates rewritten in builtin_templates.json
- [x] Phase 4: Frontend fallback synced in promptTemplates.ts (8 templates)
- [x] Phase 5: Tests updated (new IDs + placeholder format test)
- [x] Phase 6: All automated tests pass (244/245, 1 pre-existing failure)
- [x] No changes to: CREATION_SYSTEM_PROMPT, EDIT_SYSTEM_PROMPT, chat.py, router.py, templates.py, template_service.py

---

## Rollback Plan

All changes are content-only (JSON, TypeScript, Python). No database migrations, no API changes, no new dependencies.

**If template content is poor:**
- Revert `builtin_templates.json` to previous version
- Revert `promptTemplates.ts` to previous version

**If placeholder fix breaks selection:**
- Revert `ChatInput.tsx` lines 102-121 to previous version
- Revert `PromptLibraryModal.tsx` lines 132-145 (includes preview replace AND section header regex)

**If token limit causes issues:**
- Revert `creator.py` max_tokens back to 16000 AND revert `test_creator.py` assertion to 16000

**Full rollback:**
- Single `git revert` of the commit (all changes are in one commit)

---

## Implementation Notes (Post-Completion)

### Files Actually Modified (7 total — plan originally specified 6)

| # | File | Change |
|---|------|--------|
| 1 | `frontend/src/components/ChatWindow/ChatInput.tsx` | Rewrote `handleTemplateSelect` (lines 102-121) |
| 2 | `frontend/src/components/ChatWindow/PromptLibraryModal.tsx` | Fixed preview `.replace` (line 133) + section header highlighting regex (lines 137-143) |
| 3 | `backend/app/services/creator.py` | `max_tokens` 16000→24000 (4 occurrences) |
| 4 | `backend/app/config/builtin_templates.json` | Replaced all 8 templates |
| 5 | `frontend/src/data/promptTemplates.ts` | Replaced all templates (6→8, synced with backend) |
| 6 | `backend/tests/test_templates_api.py` | Updated IDs + added placeholder format test |
| 7 | `backend/tests/test_creator.py` | Updated `max_tokens` assertion 16000→24000 **(not in original plan)** |

### Discrepancies Corrected From Plan Document (3 total)

1. **PromptLibraryModal section header highlighting (Phase 1.3):** Plan omitted that lines 137-143 had hardcoded `startsWith` checks for old header names (`DESIGN REQUIREMENTS:`, `CONTENT TO INCLUDE:`, etc.). New templates use different headers (`HTML STRUCTURE:`, `CONTENT SECTIONS:`, etc.), so these needed replacing with regex `/^[A-Z][A-Z _/&()-]+:/`.

2. **test_creator.py max_tokens assertion (Phase 2.2):** Plan omitted that `test_create_uses_correct_params` in `test_creator.py` asserts the exact `max_tokens` value. Changing `creator.py` without updating this test causes a failure (`assert 24000 == 16000`).

3. **Test count (Testing Rules):** Plan said "243/244, 1 pre-existing failure" but the correct count after adding the new placeholder format test is **244/245** (244 pass + 1 pre-existing failure: `test_init_db_creates_file`).

### Final Test Results
- Backend: **244/245 passing** (1 pre-existing failure: `test_init_db_creates_file`)
- Ruff: Clean
- Mypy: Clean (no issues in 1 source file)
- TypeScript: Clean (no errors)
- Vite build: Clean (built in ~8s)
