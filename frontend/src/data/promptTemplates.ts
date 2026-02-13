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
- KPI Cards Row: CSS Grid row at top with 3-4 metric cards. Each card shows: large number, label text, and trend indicator (Unicode \u25b2 or \u25bc with color).
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
- Next Steps: Action items formatted as a checkbox list (Unicode \u2610 / \u2611)
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
- Warning callouts: Yellow/orange background boxes with \u26a0 icon for important notes
- Tip callouts: Blue background boxes for best practice recommendations
- Checklist items: Unicode checkbox (\u2610) before verification points

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

