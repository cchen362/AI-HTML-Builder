import openai
import re
from typing import List, Dict, Any, Optional
import structlog
from ..core.config import settings
from ..models.schemas import Message

logger = structlog.get_logger()

class LLMService:
    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = "gpt-5-mini"  # Using GPT-5-mini as specified in docs
        
    async def generate_html(
        self,
        user_input: str,
        context: List[Dict[str, Any]],
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Generate HTML based on user input and conversation context
        """
        try:
            if not system_prompt:
                system_prompt = self._get_default_system_prompt()
            
            messages = self._build_messages(system_prompt, context, user_input)
            
            logger.info(
                "Generating HTML",
                input_length=len(user_input),
                context_messages=len(context),
                model=self.model
            )
            
            # Build input text from messages for GPT-5 Responses API
            input_text = self._build_input_from_messages(messages)
            
            # Determine reasoning effort based on content complexity
            reasoning_effort = "low"
            verbosity = "medium"
            
            # Analyze input complexity to adjust model parameters
            if self._is_complex_document(user_input, context):
                reasoning_effort = "medium"  # More reasoning for complex layouts
                verbosity = "high"  # More detailed HTML for complex content
                logger.info("Using enhanced parameters for complex document")
            
            response = await self.client.responses.create(
                model=self.model,
                input=input_text,
                reasoning={"effort": reasoning_effort},
                text={"verbosity": verbosity}
            )
            
            html_output = response.output_text.strip()
            
            logger.info(
                "HTML generated successfully",
                output_length=len(html_output),
                tokens_used=response.usage.total_tokens if hasattr(response, 'usage') and response.usage else 0
            )
            
            return html_output
            
        except Exception as e:
            logger.error("HTML generation failed", error=str(e))
            return self._get_fallback_html(user_input)
    
    def _get_default_system_prompt(self) -> str:
        """Enhanced system prompt for HTML generation with complex document handling"""
        return """You are an expert HTML/CSS developer creating single-file HTML documents with advanced layout capabilities.

CORE REQUIREMENTS:
1. Generate complete, valid HTML5 documents
2. All CSS must be inline in <style> tags
3. All JavaScript must be inline in <script> tags
4. No external dependencies or CDN links
5. Mobile-responsive by default using viewport meta tag
6. Use semantic HTML elements

ADVANCED DOCUMENT HANDLING:
- For complex documents (reports, assessments, multi-section content):
  * Use proper document structure with header, main, sections, and footer
  * Implement clear visual hierarchy with consistent spacing
  * Use appropriate typography scales for different content levels
  * Apply consistent margin/padding patterns throughout
  * Ensure content flows logically and is easy to scan

CONVERSATION HANDLING:
- If this is a follow-up request, carefully read the user's modification request
- Apply ONLY the requested changes to the existing design
- Maintain all existing content unless specifically asked to change it
- Pay close attention to specific details like URLs, text content, colors, layout changes
- Do NOT regenerate the entire page from scratch - modify the existing one

STYLING GUIDELINES:
- Colors: Navy blue (#003366), Light blue (#4A90E2), White (#FFFFFF), Grey (#E5E5E5)
- Font stack: 'Benton Sans', Arial, sans-serif
- Typography: Use proper heading hierarchy (h1-h6), readable line-height (1.5-1.6)
- Spacing: Consistent vertical rhythm with 1rem, 1.5rem, 2rem increments
- Layout: Use CSS Grid and Flexbox for complex layouts
- Interactive elements: Add subtle hover effects and transitions

COMPLEX DOCUMENT PATTERNS:
- Reports/Assessments: Use tabbed sections, expandable content, side navigation
- Lists/Tables: Proper styling with alternating row colors, responsive behavior
- Forms: Clear field grouping, validation styling, accessible labels
- Cards/Panels: Consistent shadow, border-radius, and spacing
- Navigation: Sticky headers, breadcrumbs for long documents

CSS FRAMEWORK DECISION:
- Use modern CSS features: Grid, Flexbox, CSS custom properties
- For complex components: Implement custom CSS rather than framework dependencies
- Ensure IE11+ compatibility while leveraging modern features progressively

PERFORMANCE OPTIMIZATION:
- Minimize CSS redundancy
- Use efficient selectors
- Optimize for fast rendering

OUTPUT FORMAT:
Return only the complete HTML document starting with <!DOCTYPE html>"""
    
    def _build_messages(
        self,
        system_prompt: str,
        context: List[Dict[str, Any]],
        user_input: str
    ) -> List[Dict[str, str]]:
        """Build message array for OpenAI API"""
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add context messages (keep last 8 messages to manage token usage)
        recent_context = context[-8:] if len(context) > 8 else context
        
        for msg in recent_context:
            if msg.get("sender") == "user" and msg.get("content"):
                content = msg.get("content", "").strip()
                if content:
                    messages.append({"role": "user", "content": content})
            elif msg.get("sender") == "assistant":
                # For assistant messages, provide a summary rather than full HTML
                if msg.get("html_output"):
                    # Extract key info from the HTML for context
                    html_summary = self._summarize_html_for_context(msg.get("html_output", ""))
                    messages.append({"role": "assistant", "content": html_summary})
        
        # Add current user input with explicit instruction for iteration
        if len(recent_context) > 0:
            enhanced_input = f"""Based on our previous conversation, {user_input}

Please modify the existing HTML accordingly. Make sure to incorporate the requested changes while maintaining the overall structure and styling."""
        else:
            enhanced_input = user_input
            
        messages.append({"role": "user", "content": enhanced_input})
        
        return messages
    
    def _build_input_from_messages(self, messages: List[Dict[str, str]]) -> str:
        """Convert messages array to input text for GPT-5 Responses API"""
        input_parts = []
        
        for message in messages:
            role = message.get("role", "")
            content = message.get("content", "")
            
            if role == "system":
                input_parts.append(f"System Instructions: {content}")
            elif role == "user":
                input_parts.append(f"User: {content}")
            elif role == "assistant":
                input_parts.append(f"Assistant: {content}")
        
        return "\n\n".join(input_parts)
    
    def _is_complex_document(self, user_input: str, context: List[Dict[str, Any]]) -> bool:
        """Determine if the document requires complex layout handling"""
        complexity_indicators = [
            # Document types
            'impact assessment', 'report', 'assessment', 'analysis', 'evaluation',
            'documentation', 'proposal', 'specification', 'requirements',
            
            # Layout complexity
            'table', 'chart', 'graph', 'tabs', 'sections', 'columns',
            'navigation', 'sidebar', 'dashboard', 'multi-page',
            
            # Content complexity
            'multiple sections', 'structured data', 'detailed layout',
            'complex formatting', 'professional document', 'technical document'
        ]
        
        # Check user input for complexity indicators
        input_lower = user_input.lower()
        complexity_score = sum(1 for indicator in complexity_indicators if indicator in input_lower)
        
        # Check context for existing complex content
        context_complexity = 0
        for msg in context[-3:]:  # Check last 3 messages
            if msg.get('html_output'):
                html_content = msg['html_output'].lower()
                # Look for complex HTML structures
                if any(tag in html_content for tag in ['<table>', '<nav>', '<section>', '<aside>', '<grid']):
                    context_complexity += 2
                if len(html_content) > 5000:  # Large HTML indicates complexity
                    context_complexity += 1
        
        # Determine complexity
        total_complexity = complexity_score + context_complexity
        is_complex = total_complexity >= 2
        
        if is_complex:
            logger.info(f"Complex document detected: score={complexity_score}, context={context_complexity}")
        
        return is_complex
    
    def _summarize_html_for_context(self, html_content: str) -> str:
        """Create a summary of HTML content for context without including the full HTML"""
        if not html_content:
            return "Generated basic HTML page"
        
        # Extract title
        title_match = re.search(r'<title>(.*?)</title>', html_content, re.IGNORECASE)
        title = title_match.group(1) if title_match else "Untitled"
        
        # Count major elements
        sections = len(re.findall(r'<(section|div|article)', html_content, re.IGNORECASE))
        headings = len(re.findall(r'<h[1-6]', html_content, re.IGNORECASE))
        
        # Determine page type
        if "business card" in html_content.lower():
            page_type = "business card"
        elif "landing" in html_content.lower():
            page_type = "landing page"
        elif "portfolio" in html_content.lower():
            page_type = "portfolio page"
        else:
            page_type = "webpage"
            
        return f"Created a {page_type} titled '{title}' with {sections} sections and {headings} headings. Ready for modifications."
    
    def _get_fallback_html(self, user_input: str) -> str:
        """Fallback HTML when API fails"""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Generated HTML</title>
    <style>
        body {{
            font-family: 'Benton Sans', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #ffffff;
        }}
        .header {{
            background: linear-gradient(135deg, #003366, #4A90E2);
            color: white;
            padding: 2rem;
            border-radius: 8px;
            margin-bottom: 2rem;
        }}
        .content {{
            background: #f8f9fa;
            padding: 2rem;
            border-radius: 8px;
            border-left: 4px solid #4A90E2;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>AI HTML Builder</h1>
        <p>Generated content based on your request</p>
    </div>
    <div class="content">
        <p><strong>Your request:</strong> {user_input}</p>
        <p>We're processing your request. Please try again if this wasn't what you expected.</p>
    </div>
</body>
</html>"""
    
    async def process_file_content(self, file_content: str, filename: str) -> str:
        """Process uploaded file content into HTML"""
        try:
            file_prompt = f"""Convert the following document content into structured HTML:
- Preserve headings as <h1> to <h6> tags
- Convert lists to <ul> or <ol>
- Maintain paragraph structure
- Convert tables to HTML tables
- Apply default styling per system requirements

File: {filename}
Content: {file_content}"""
            
            return await self.generate_html(file_prompt, [])
            
        except Exception as e:
            logger.error("File processing failed", filename=filename, error=str(e))
            return self._get_fallback_html(f"Processed content from {filename}")
    
    def get_template_html(self, template_name: str) -> str:
        """Get predefined template HTML"""
        templates = {
            "Landing Page": self._get_landing_page_template(),
            "Impact Assessment": self._get_impact_assessment_template(),
            "Newsletter": self._get_newsletter_template(),
            "Documentation": self._get_documentation_template()
        }
        
        return templates.get(template_name, self._get_landing_page_template())
    
    def _get_landing_page_template(self) -> str:
        """Landing page template"""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Professional Landing Page</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Benton Sans', Arial, sans-serif; line-height: 1.6; color: #333; }
        .hero { background: linear-gradient(135deg, #003366, #4A90E2); color: white; padding: 4rem 2rem; text-align: center; }
        .hero h1 { font-size: 3rem; margin-bottom: 1rem; }
        .hero p { font-size: 1.2rem; margin-bottom: 2rem; }
        .btn { background: #4A90E2; color: white; padding: 1rem 2rem; border: none; border-radius: 5px; font-size: 1rem; cursor: pointer; }
        .features { padding: 4rem 2rem; max-width: 1200px; margin: 0 auto; }
        .feature-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 2rem; }
        .feature { background: #f8f9fa; padding: 2rem; border-radius: 8px; text-align: center; }
    </style>
</head>
<body>
    <section class="hero">
        <h1>Welcome to Our Service</h1>
        <p>Transform your business with our innovative solutions</p>
        <button class="btn">Get Started</button>
    </section>
    <section class="features">
        <div class="feature-grid">
            <div class="feature">
                <h3>Feature One</h3>
                <p>Description of your first key feature</p>
            </div>
            <div class="feature">
                <h3>Feature Two</h3>
                <p>Description of your second key feature</p>
            </div>
            <div class="feature">
                <h3>Feature Three</h3>
                <p>Description of your third key feature</p>
            </div>
        </div>
    </section>
</body>
</html>"""
    
    def _get_impact_assessment_template(self) -> str:
        """Impact assessment template with tabbed navigation"""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Impact Assessment Report</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Benton Sans', Arial, sans-serif; line-height: 1.6; color: #333; background: #f5f5f5; }
        .header { background: linear-gradient(135deg, #003366, #4A90E2); color: white; padding: 2rem; text-align: center; }
        .container { max-width: 1200px; margin: 2rem auto; padding: 0 1rem; }
        .tabs { display: flex; background: white; border-radius: 8px 8px 0 0; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .tab { flex: 1; padding: 1rem; background: #e5e5e5; border: none; cursor: pointer; font-weight: bold; }
        .tab.active { background: #4A90E2; color: white; }
        .tab-content { background: white; padding: 2rem; border-radius: 0 0 8px 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .solution-card { background: #f8f9fa; padding: 1.5rem; margin: 1rem 0; border-radius: 8px; border-left: 4px solid #4A90E2; }
        .risk-item { padding: 1rem; margin: 0.5rem 0; border: 2px solid #e5e5e5; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Impact Assessment Report</h1>
        <p>Comprehensive Analysis & Recommendations</p>
    </div>
    <div class="container">
        <div class="tabs">
            <button class="tab active" onclick="showTab('problem')">Problem Statement</button>
            <button class="tab" onclick="showTab('solutions')">Technical Solutions</button>
            <button class="tab" onclick="showTab('risks')">Risk Analysis</button>
            <button class="tab" onclick="showTab('recommendations')">Recommendations</button>
        </div>
        <div id="problem" class="tab-content">
            <h2>Problem Statement</h2>
            <p>Detailed analysis of the current challenges and issues.</p>
        </div>
        <div id="solutions" class="tab-content" style="display:none;">
            <h2>Technical Solutions</h2>
            <div class="solution-card">
                <h3>Solution A</h3>
                <p><strong>Pros:</strong> Benefits and advantages</p>
                <p><strong>Cons:</strong> Limitations and drawbacks</p>
            </div>
        </div>
        <div id="risks" class="tab-content" style="display:none;">
            <h2>Risk Analysis</h2>
            <div class="risk-item">
                <h4>Risk Item 1</h4>
                <p>Description and mitigation strategies</p>
            </div>
        </div>
        <div id="recommendations" class="tab-content" style="display:none;">
            <h2>Executive Recommendations</h2>
            <p>Key recommendations based on the analysis.</p>
        </div>
    </div>
    <script>
        function showTab(tabName) {
            const contents = document.querySelectorAll('.tab-content');
            const tabs = document.querySelectorAll('.tab');
            contents.forEach(content => content.style.display = 'none');
            tabs.forEach(tab => tab.classList.remove('active'));
            document.getElementById(tabName).style.display = 'block';
            event.target.classList.add('active');
        }
    </script>
</body>
</html>"""
    
    def _get_newsletter_template(self) -> str:
        """Newsletter template"""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Newsletter</title>
    <style>
        body { font-family: 'Benton Sans', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; }
        .header { background: #003366; color: white; padding: 2rem; text-align: center; }
        .article { padding: 2rem; border-bottom: 1px solid #e5e5e5; }
        .footer { background: #f8f9fa; padding: 2rem; text-align: center; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Newsletter Title</h1>
        <p>Your monthly update</p>
    </div>
    <div class="article">
        <h2>Article Title</h2>
        <p>Newsletter content goes here...</p>
    </div>
    <div class="footer">
        <p>© 2025 Your Company</p>
    </div>
</body>
</html>"""
    
    def _get_documentation_template(self) -> str:
        """Documentation template"""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Documentation</title>
    <style>
        body { font-family: 'Benton Sans', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; }
        .sidebar { width: 250px; background: #003366; color: white; height: 100vh; position: fixed; padding: 1rem; }
        .sidebar ul { list-style: none; }
        .sidebar a { color: #4A90E2; text-decoration: none; }
        .content { margin-left: 270px; padding: 2rem; }
    </style>
</head>
<body>
    <nav class="sidebar">
        <h2>Documentation</h2>
        <ul>
            <li><a href="#intro">Introduction</a></li>
            <li><a href="#guide">User Guide</a></li>
            <li><a href="#api">API Reference</a></li>
        </ul>
    </nav>
    <main class="content">
        <h1 id="intro">Introduction</h1>
        <p>Welcome to the documentation.</p>
        <h1 id="guide">User Guide</h1>
        <p>How to use this system.</p>
        <h1 id="api">API Reference</h1>
        <p>API documentation.</p>
    </main>
</body>
</html>"""

# Global LLM service instance
llm_service = LLMService()