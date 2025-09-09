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
    template: `Create a professional impact assessment report for: {USER_CONTENT}

Organize into logical tabbed sections based on the actual content provided:
- Create tabs only for themes that exist in the material
- Use descriptive tab names that reflect the actual content
- Present analysis and insights derived solely from the provided information
- Include executive summary based on available data

Focus on clear organization of existing information rather than generating additional content.`
  },
  {
    id: 'documentation',
    name: 'Technical Documentation',
    category: 'Technical',
    description: 'Clean documentation site with sidebar navigation and code examples',
    template: `Create comprehensive technical documentation for: {USER_CONTENT}

Structure the technical information provided:
- Organize content with clear navigation based on available material
- Present procedures, code examples, and specifications as documented
- Include relevant sections that exist in the source content
- Focus on developer-friendly presentation of the provided information

Design for easy navigation and understanding of the documented technical content.`
  },
  {
    id: 'dashboard',
    name: 'Business Dashboard',
    category: 'Analytics',
    description: 'Interactive dashboard with charts, metrics, and data visualization',
    template: `Create an interactive business dashboard for: {USER_CONTENT}

Present the business data and metrics provided:
- Organize key performance indicators and metrics from the source material
- Create appropriate visualizations based on available data types
- Include relevant analytical components that match the provided information
- Focus on business stakeholder needs using the actual data available

Design for clear visual hierarchy and actionable insights from the provided business information.`
  },
  {
    id: 'project-report',
    name: 'Project Report',
    category: 'Project Management',
    description: 'Structured project report with status, milestones, and team updates',
    template: `Create a comprehensive project report for: {USER_CONTENT}

Organize the available project information into clear sections:
- Structure based on the actual data and updates provided
- Include relevant status indicators and progress metrics where available
- Present timeline and milestone information as provided
- Focus on stakeholder-relevant insights from the source material

Format for project stakeholders using the information available in the content.`
  },
  {
    id: 'process-documentation',
    name: 'Process Documentation',
    category: 'Operations',
    description: 'Step-by-step process guide with workflows and decision trees',
    template: `Create detailed process documentation for: {USER_CONTENT}

Organize the process information provided:
- Structure workflow steps and procedures as documented in the material
- Present roles and responsibilities based on available information
- Include decision points and requirements as specified
- Focus on operational clarity using the provided details

Design for easy-to-follow sequential understanding of the documented process.`
  },
  {
    id: 'presentation',
    name: 'Presentation Slides',
    category: 'Presentation',
    description: 'Clean slide presentation with navigation and professional styling',
    template: `Create an engaging slide presentation covering: {USER_CONTENT}

Design as professional slides:
- Organize content into logical slide sequence based on the material provided
- Create appropriate slide structure that matches the content flow
- Emphasize key points and insights from the source information
- Include navigation and presenter notes for effective delivery

Structure for business presentation with engaging visual storytelling of the provided content.`
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