# AI HTML Builder - Prompt Templates

This file contains all prompt templates used in the prompt library feature. Each template is designed to generate specific output styles while maintaining consistent branding and modern design principles.

## Template Structure

Each template follows this structure:
- **ID**: Unique identifier for the template
- **Name**: Display name in the UI
- **Category**: Group classification (Document, Report, etc.)
- **Description**: Brief explanation of the template's purpose
- **Template**: The actual prompt with placeholder for user content

## Brand Guidelines

All templates should specify:
- **Primary Colors**: Deep Blue (#00175A), Bright Blue (#006FCF), Light Blue (#66A9E2), Charcoal (#152835), Gray 6 (#A7A8AA), White (#FFFFFF)
- **Accent Colors**: Sky Blue (#B4EEFF), Powder Blue (#F6F0FA), Yellow (#FFB900), Forest (#006469), Green (#28CD6E)  
- **Fonts**: 'Benton Sans' (primary), Arial (fallback)
- **Style**: Clean, minimal UI with proper spacing
- **Interactive**: Modern, responsive design elements

---

## Template Library

### 1. Impact Assessment Report
**ID**: `impact-assessment`
**Category**: Business Reports
**Description**: Professional report with tabbed navigation and analysis sections

```
Create a professional impact assessment report for: {USER_CONTENT}

Structure with tabbed sections:
- Problem Statement & Current State
- Technical Solutions & Options Analysis
- Risk Assessment & Mitigation Strategies  
- Recommendations & Next Steps

Include executive summary, detailed analysis with pros/cons for each solution, risk ratings (low/medium/high), and actionable recommendations with clear priorities.
```

### 2. Technical Documentation
**ID**: `documentation`
**Category**: Technical
**Description**: Clean documentation site with sidebar navigation and code examples

```
Create comprehensive technical documentation for: {USER_CONTENT}

Structure with:
- Table of contents with sidebar navigation
- Clear section hierarchy with proper headings
- Code examples with syntax highlighting
- Step-by-step procedures and explanations
- API references or technical specifications
- Troubleshooting and FAQ sections

Focus on developer-friendly layout with searchable content and easy navigation between sections.
```

### 3. Business Dashboard
**ID**: `dashboard`
**Category**: Analytics
**Description**: Interactive dashboard with charts, metrics, and data visualization

```
Create an interactive business dashboard for: {USER_CONTENT}

Include key components:
- Executive summary with top-level KPI cards
- Interactive charts and data visualizations
- Filtering and sorting capabilities
- Performance metrics with trend indicators
- Data tables with key business insights
- Status indicators and alerts for critical items

Design for business stakeholders with clear visual hierarchy and actionable insights at a glance.
```

### 4. Project Report
**ID**: `project-report`
**Category**: Project Management
**Description**: Structured project report with status, milestones, and team updates

```
Create a comprehensive project report for: {USER_CONTENT}

Include sections covering:
- Executive summary with project overview and key achievements
- Current status with progress indicators and completion percentages
- Milestone timeline with major deliverables and dates
- Team performance and resource allocation updates
- Risk assessment with mitigation strategies
- Budget status and resource utilization
- Next steps and action items with priorities

Format for project stakeholders with clear status indicators and actionable insights.
```

### 5. Process Documentation
**ID**: `process-documentation`
**Category**: Operations
**Description**: Step-by-step process guide with workflows and decision trees

```
Create detailed process documentation for: {USER_CONTENT}

Structure with:
- Process overview and objectives
- Step-by-step workflow with numbered actions
- Decision points and branching logic
- Role responsibilities and ownership matrix
- Input requirements and expected outputs
- Exception handling and escalation procedures
- Quality checkpoints and validation steps

Focus on operational clarity with visual workflow indicators and easy-to-follow sequential steps.
```

### 6. Presentation Slides
**ID**: `presentation`
**Category**: Presentation
**Description**: Clean slide presentation with navigation and professional styling

```
Create an engaging slide presentation covering: {USER_CONTENT}

Design as professional slides with:
- Title slide with agenda overview
- Content slides with clear section headers
- Key points with visual emphasis
- Summary slide with conclusions and next steps
- Navigation between slides and presenter notes

Structure for business presentation with logical flow and engaging visual storytelling.
```

---

## Usage Guidelines

### Adding New Templates
1. Create new template following the structure above
2. Add unique ID and descriptive name
3. Include brand color specifications
4. Test template with various content types
5. Update this file with the new template

### Template Maintenance
- Review templates quarterly for content effectiveness
- Ensure templates complement system prompt without duplication
- Test templates with various content types for consistency
- Keep templates focused on content structure, not visual design
- Maintain ~200 characters or less per template for optimal token usage

### Content Placeholder
All templates use `{USER_CONTENT}` as the placeholder where users will paste their content. This should be clearly marked in the UI as the area where users add their specific information.

---

**Last Updated**: January 2025
**Version**: 1.0.0