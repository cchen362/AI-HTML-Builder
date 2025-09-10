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

Organize into logical tabbed sections based on the actual content provided:
- Create tabs only for themes that exist in the material
- Use descriptive tab names that reflect the actual content
- Present analysis and insights derived solely from the provided information
- Include executive summary based on available data

Focus on clear organization of existing information rather than generating additional content.
```

### 2. Technical Documentation
**ID**: `documentation`
**Category**: Technical
**Description**: Clean documentation site with sidebar navigation and code examples

```
Create comprehensive technical documentation for: {USER_CONTENT}

Structure the technical information provided:
- Organize content with clear navigation based on available material
- Present procedures, code examples, and specifications as documented
- Include relevant sections that exist in the source content
- Focus on developer-friendly presentation of the provided information

Design for easy navigation and understanding of the documented technical content.
```

### 3. Business Dashboard
**ID**: `dashboard`
**Category**: Analytics
**Description**: Interactive dashboard with charts, metrics, and data visualization

```
Create an interactive business dashboard for: {USER_CONTENT}

Present the business data and metrics provided:
- Organize key performance indicators and metrics from the source material
- Create appropriate visualizations based on available data types
- Include relevant analytical components that match the provided information
- Focus on business stakeholder needs using the actual data available

Design for clear visual hierarchy and actionable insights from the provided business information.
```

### 4. Project Report
**ID**: `project-report`
**Category**: Project Management
**Description**: Structured project report with status, milestones, and team updates

```
Create a comprehensive project report for: {USER_CONTENT}

Organize the available project information into clear sections:
- Structure based on the actual data and updates provided
- Include relevant status indicators and progress metrics where available
- Present timeline and milestone information as provided
- Focus on stakeholder-relevant insights from the source material

Format for project stakeholders using the information available in the content.
```

### 5. Process Documentation
**ID**: `process-documentation`
**Category**: Operations
**Description**: Step-by-step process guide with workflows and decision trees

```
Create detailed process documentation for: {USER_CONTENT}

Organize the process information provided:
- Structure workflow steps and procedures as documented in the material
- Present roles and responsibilities based on available information
- Include decision points and requirements as specified
- Focus on operational clarity using the provided details

Design for easy-to-follow sequential understanding of the documented process.
```

### 6. Presentation Slides
**ID**: `presentation`
**Category**: Presentation
**Description**: Clean slide presentation with navigation and professional styling

```
Create an engaging slide presentation covering: {USER_CONTENT}

Design as professional slides:
- Organize content into logical slide sequence based on the material provided
- Create appropriate slide structure that matches the content flow
- Emphasize key points and insights from the source information
- Include navigation and presenter notes for effective delivery

Structure for business presentation with engaging visual storytelling of the provided content.
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