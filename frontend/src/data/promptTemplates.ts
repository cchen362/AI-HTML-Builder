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
    description: 'Professional report with tabbed navigation and analysis sections',
    template: `Create a professional impact assessment report with the following specifications:

DESIGN REQUIREMENTS:
- Deep blue (#00175A) header with bright blue (#006FCF) accents and light blue (#66A9E2) highlights
- Tabbed navigation system (Problem Statement, Technical Solutions, Risk Analysis, Recommendations)
- Solution cards with pros/cons sections in white (#FFFFFF) containers with charcoal (#152835) text
- Highlighted problem areas with yellow (#FFB900) accent borders
- Professional typography with clear hierarchy using charcoal (#152835) for headings
- Interactive JavaScript for seamless tab switching

CONTENT TO INCLUDE:
{USER_CONTENT}

STRUCTURE REQUIREMENTS:
- Deep blue (#00175A) to bright blue (#006FCF) gradient header with report title
- Four main tabs with organized content sections using light blue (#66A9E2) active states
- Card-based layout for solutions and recommendations with sky blue (#B4EEFF) backgrounds
- Risk items with forest green (#006469) for low risk, yellow (#FFB900) for medium, wine red (#7D1941) for high risk
- Mobile-responsive design with collapsible sections
- Professional color coding: success (green #28CD6E), warning (yellow #FFB900), error (wine #7D1941)`
  },
  {
    id: 'documentation',
    name: 'Technical Documentation',
    category: 'Technical',
    description: 'Clean documentation site with sidebar navigation and code examples',
    template: `Create a professional technical documentation site with these specifications:

DESIGN REQUIREMENTS:
- Deep blue (#00175A) sidebar with bright blue (#006FCF) active states and light blue (#66A9E2) hover effects
- Clean white (#FFFFFF) content area with powder blue (#F6F0FA) code blocks
- Sticky navigation with smooth scrolling using charcoal (#152835) text
- Syntax highlighting for code examples with sky blue (#B4EEFF) backgrounds
- Search-friendly heading structure (H1-H6) using charcoal (#152835) for headings
- Interactive table of contents with yellow (#FFB900) accent indicators

CONTENT TO INCLUDE:
{USER_CONTENT}

FEATURES REQUIRED:
- Collapsible sidebar navigation with light blue (#66A9E2) borders
- Code syntax highlighting with copy buttons styled in bright blue (#006FCF)
- Breadcrumb navigation using gray 6 (#A7A8AA) separators
- Mobile hamburger menu with deep blue (#00175A) background
- Print-friendly styles maintaining brand colors
- Modern typography with proper spacing and charcoal (#152835) text
- Professional color scheme: info (bright blue #006FCF), success (green #28CD6E), warning (yellow #FFB900)`
  },
  {
    id: 'dashboard',
    name: 'Business Dashboard',
    category: 'Analytics',
    description: 'Interactive dashboard with charts, metrics, and data visualization',
    template: `Create a modern business dashboard with the following specifications:

DESIGN REQUIREMENTS:
- Deep blue (#00175A) header and sidebar with bright blue (#006FCF) accent elements
- Light blue (#66A9E2) accent colors for charts and metrics with sky blue (#B4EEFF) data visualizations
- Card-based layout with white (#FFFFFF) backgrounds and charcoal (#152835) text with subtle shadows
- Interactive chart placeholders with yellow (#FFB900) highlight effects on hover
- Responsive grid system for different screen sizes using powder blue (#F6F0FA) section backgrounds
- Modern metric cards with icons and trend indicators using green (#28CD6E) for positive trends

CONTENT TO INCLUDE:
{USER_CONTENT}

INTERACTIVE FEATURES:
- Animated counters for key metrics with bright blue (#006FCF) number highlights
- Hover effects on chart elements using light blue (#66A9E2) overlays
- Collapsible sidebar navigation with deep blue (#00175A) background
- Filter buttons with active states using yellow (#FFB900) selection indicators
- Responsive table with sorting capabilities and gray 6 (#A7A8AA) borders
- Loading states and smooth transitions with sky blue (#B4EEFF) progress indicators
- Status indicators: success (green #28CD6E), warning (yellow #FFB900), error (wine #7D1941), info (bright blue #006FCF)`
  },
  {
    id: 'project-report',
    name: 'Project Report',
    category: 'Project Management',
    description: 'Structured project report with status, milestones, and team updates',
    template: `Create a professional project report with these specifications:

DESIGN REQUIREMENTS:
- Deep blue (#00175A) header with project title and status indicators using bright blue (#006FCF) accents
- Light blue (#66A9E2) section headers and progress bars with sky blue (#B4EEFF) fill indicators
- Clean white (#FFFFFF) content sections with organized information and charcoal (#152835) text
- Status indicators: on-track (green #28CD6E), at-risk (yellow #FFB900), delayed (wine #7D1941)
- Timeline visualization for milestones using powder blue (#F6F0FA) backgrounds
- Team member cards with roles and responsibilities using gray 6 (#A7A8AA) borders

CONTENT TO INCLUDE:
{USER_CONTENT}

REPORT SECTIONS:
- Executive summary with key highlights using yellow (#FFB900) accent callouts
- Project status and progress indicators with bright blue (#006FCF) completion percentages
- Milestone timeline with dates using light blue (#66A9E2) milestone markers
- Risk assessment and mitigation plans with forest green (#006469) for low risk items
- Team updates and resource allocation using charcoal (#152835) headings
- Next steps and action items with yellow (#FFB900) priority indicators
- Professional formatting with clear hierarchy and consistent brand colors`
  },
  {
    id: 'process-documentation',
    name: 'Process Documentation',
    category: 'Operations',
    description: 'Step-by-step process guide with workflows and decision trees',
    template: `Create a comprehensive process documentation with the following specifications:

DESIGN REQUIREMENTS:
- Deep blue (#00175A) header with process title and bright blue (#006FCF) process category badges
- Light blue (#66A9E2) step numbers and decision points with yellow (#FFB900) highlights
- Clean white (#FFFFFF) workflow sections with visual flow indicators and powder blue (#F6F0FA) backgrounds
- Numbered steps with clear action items using charcoal (#152835) text
- Decision tree diagrams with yes/no branches using green (#28CD6E) for yes, wine (#7D1941) for no
- Responsibility matrix for different roles with gray 6 (#A7A8AA) grid lines

CONTENT TO INCLUDE:
{USER_CONTENT}

WORKFLOW FEATURES:
- Step-by-step process flow with visual indicators using sky blue (#B4EEFF) connectors
- Decision points with clear branching paths highlighted in yellow (#FFB900)
- Role-based responsibility assignments with bright blue (#006FCF) role indicators
- Input/output specifications for each step with forest green (#006469) input markers
- Exception handling and escalation procedures with wine (#7D1941) alert styling
- Mobile-friendly collapsible sections with light blue (#66A9E2) section headers
- Print-optimized layout maintaining brand colors for reference`
  },
  {
    id: 'presentation',
    name: 'Presentation Slides',
    category: 'Presentation',
    description: 'Clean slide presentation with navigation and professional styling',
    template: `Create a modern slide presentation with the following specifications:

DESIGN REQUIREMENTS:
- Deep blue (#00175A) backgrounds with white (#FFFFFF) text and bright blue (#006FCF) accent elements
- Light blue (#66A9E2) accent colors for highlights with yellow (#FFB900) emphasis points
- Clean slide transitions and navigation controls using sky blue (#B4EEFF) indicators
- Professional slide layouts (title, content, comparison) with powder blue (#F6F0FA) content backgrounds
- Slide counter and progress indicator using charcoal (#152835) text
- Full-screen presentation mode with deep blue (#00175A) speaker view

CONTENT TO INCLUDE:
{USER_CONTENT}

INTERACTIVE FEATURES:
- Keyboard navigation (arrow keys, space) with yellow (#FFB900) navigation hints
- Slide thumbnails in sidebar with light blue (#66A9E2) borders and bright blue (#006FCF) active states
- Smooth slide transitions with sky blue (#B4EEFF) loading animations
- Mobile swipe navigation with gray 6 (#A7A8AA) touch indicators
- Professional presenter notes section with white (#FFFFFF) backgrounds
- Print-friendly version for handouts maintaining brand colors
- Clear visual hierarchy: titles (charcoal #152835), highlights (yellow #FFB900), success (green #28CD6E)`
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