# AI HTML Builder 🤖✨

> Transform ideas into professional HTML documents through intelligent conversation

[![AI Powered](https://img.shields.io/badge/AI-Claude%20Sonnet%204-blue)](https://www.anthropic.com/)
[![Tech Stack](https://img.shields.io/badge/Stack-React%2019%20%2B%20FastAPI%20%2B%20Redis-green)](https://github.com/)
[![Deploy](https://img.shields.io/badge/Deploy-Podman%20Ready-orange)](https://podman.io/)

AI HTML Builder is a cutting-edge web application that enables users to generate beautiful, responsive HTML documents through natural language conversations. Powered by Anthropic's Claude Sonnet 4, it transforms user ideas into professionally crafted single-file HTML outputs with live preview and real-time editing capabilities.

## 🚀 Features

### 🎯 Core Functionality
- **AI-Powered Generation**: Leverages Claude Sonnet 4 for superior HTML/CSS creation
- **Natural Language Interface**: Chat-based interaction for intuitive document creation
- **Live Preview**: Real-time rendering with toggle between preview and code view
- **Single-File Output**: Complete HTML documents with inlined CSS/JS (no external dependencies)
- **File Upload Support**: Process .txt, .docx, .md files up to 50MB
- **Smart Editing**: Semantic targeting system for precise modifications without content recreation

### 📊 Admin Dashboard & Analytics
- **Secure Admin Access**: JWT-based authentication with session management
- **Real-Time Analytics**: Response times, token usage, session tracking
- **Usage Metrics**: Output type classification, success rates, user engagement
- **Data Export**: CSV exports with date filtering for business intelligence
- **Session Management**: Monitor active sessions and system performance

### 🎨 Professional Design Templates
- **Impact Assessment Reports**: Tabbed navigation with analysis sections
- **Technical Documentation**: Clean docs with sidebar navigation
- **Business Dashboards**: Interactive charts and data visualization
- **Project Reports**: Structured reports with status tracking
- **Process Documentation**: Step-by-step guides with workflows
- **Presentation Slides**: Professional slide presentations

### 🔧 Advanced Technical Features
- **Semantic Targeting**: Claude Artifacts-inspired precise editing
- **150K Context Window**: Handle large documents and complex iterations
- **WebSocket Communication**: Real-time bidirectional communication
- **Redis Integration**: Session persistence with graceful memory fallback
- **Mobile-Responsive**: Optimized for all device sizes
- **Accessibility Compliant**: WCAG guidelines and ARIA attributes

## 🛠 Technology Stack

### Frontend (React 19)
- **React**: 19.1.1 with enhanced concurrent rendering
- **TypeScript**: 5.8.3 for type safety
- **Vite**: 7.1.2 for fast development and builds
- **React Router**: 7.8.2 for client-side routing

### Backend (FastAPI)
- **FastAPI**: 0.111.0+ with async support
- **Python**: 3.11+ (3.13 compatible)
- **WebSockets**: 12.0+ for real-time communication
- **Redis**: 5.0.0+ for session management and caching

### AI Integration
- **Anthropic Claude Sonnet 4**: Primary AI model for HTML generation
- **Advanced Context Management**: 150K character optimization
- **Semantic Analysis**: Multi-phase request understanding

## ⚡ Quick Start

### Prerequisites
- **Node.js** 18+ (for frontend development)
- **Python** 3.11+ (for backend development)
- **Podman** or Docker (for deployment)
- **Anthropic API Key** (required)
- **Redis** (optional, falls back to memory)

### 🏃‍♂️ Development Setup

```bash
# Clone the repository
git clone <your-repository-url>
cd AI-HTML-Builder

# Frontend setup
cd frontend
npm install
npm run dev    # Starts on http://localhost:5173

# Backend setup (new terminal)
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Anthropic API key

# Start backend
uvicorn app.main:app --reload  # Starts on http://localhost:8000
```

### 🐳 Production Deployment with Podman

```bash
# Quick deployment
podman-compose -f docker-compose.prod.yml up -d

# Or manual setup
podman build -t ai-html-builder .
podman run -d -p 8080:8000 --env-file .env.prod ai-html-builder
```

**Access Your Application:**
- **Main App**: http://localhost:8080
- **Admin Dashboard**: http://localhost:8080/admin
- **API Documentation**: http://localhost:8080/docs

## 🎮 Usage Guide

### Creating Your First HTML Document

1. **Start a Chat**: Open the application and begin typing your request
2. **Describe Your Vision**: Use natural language to describe what you want to create
   - "Create a professional landing page for a tech startup"
   - "Build a documentation site with navigation and code examples" 
   - "Design a dashboard with charts and metrics"

3. **Iterate and Refine**: Make changes through conversation
   - "Change the header color to navy blue"
   - "Add a contact form in the footer"
   - "Make the layout more mobile-friendly"

4. **Export and Use**: Download as a complete HTML file or open in fullscreen

### Example Prompts

```
🏢 Business Use Cases:
"Create an impact assessment report with tabs for problem analysis, technical solutions, and recommendations"

📚 Documentation:
"Build a technical documentation site with a sidebar menu, search, and code syntax highlighting"

📊 Analytics:
"Design a business dashboard with KPI cards, charts, and a data table"

📄 Reports:
"Generate a project status report with timeline, milestones, and team updates"
```

## 🔐 Admin Dashboard

Access advanced analytics and management features:

### Authentication
- Navigate to `/admin`
- Use admin credentials (see `.env.prod` configuration)
- JWT-based session with 8-hour timeout

### Analytics Features
- **Performance Metrics**: Response times, token usage, processing efficiency
- **Usage Analytics**: Session counts, iteration patterns, success rates
- **Content Classification**: Automatic categorization of generated outputs
- **Export Capabilities**: CSV downloads with custom date ranges

## 🏗 Architecture Overview

```
┌─────────────────┐    WebSocket/HTTP    ┌─────────────────┐
│   React 19      │ ←──────────────────→ │   FastAPI       │
│   Frontend      │                      │   Backend       │
└─────────────────┘                      └─────────────────┘
                                                   ↓
                                         ┌─────────────────┐
                                         │ Claude Sonnet 4 │
                                         │ + Redis Cache   │
                                         └─────────────────┘
```

### Key Components
- **Chat Interface**: Natural language processing with Claude integration
- **HTML Viewer**: Live preview with code/preview toggle
- **Session Management**: Redis-based with memory fallback
- **Semantic Targeting**: Precise editing without content recreation
- **Admin Dashboard**: Analytics, monitoring, and user management

## 📝 Environment Configuration

### Development (.env)
```bash
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
REDIS_URL=redis://localhost:6379
ENVIRONMENT=development
LOG_LEVEL=debug
MAX_UPLOAD_SIZE=52428800
SESSION_TIMEOUT=3600
```

### Production (.env.prod)
```bash
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
ENVIRONMENT=production
LOG_LEVEL=info
REDIS_URL=redis://redis:6379
JWT_SECRET=your-secure-jwt-secret
ADMIN_PASSWORD=your-secure-admin-password
```

## 🚀 Deployment Guide

### System Requirements
- **Memory**: 2GB RAM minimum, 4GB recommended
- **CPU**: 2 cores minimum
- **Storage**: 10GB available space
- **Network**: Internet access for AI API calls

### Performance Specifications
- **Concurrent Users**: Up to 8 simultaneous sessions
- **Response Time**: < 10 seconds for HTML generation
- **File Upload Limit**: 50MB per file
- **Session Duration**: 1 hour timeout
- **Context Window**: 150K characters (optimized for Claude Sonnet 4)

### Production Deployment

1. **Configure Environment**
   ```bash
   # Copy and configure production environment
   cp .env.example .env.prod
   # Edit with your production settings
   ```

2. **Deploy with Podman**
   ```bash
   # Build and deploy
   podman-compose -f docker-compose.prod.yml up -d
   
   # Monitor deployment
   podman logs -f ai-html-builder-app
   ```

3. **Health Checks**
   ```bash
   # Verify application health
   curl http://localhost:8080/api/health
   
   # Check Redis connectivity
   podman exec ai-html-builder-redis redis-cli ping
   ```

### Scaling and Monitoring

```bash
# Monitor resource usage
podman stats

# View application logs
podman logs -f ai-html-builder-app

# Access admin analytics
curl -H "Authorization: Bearer TOKEN" http://localhost:8080/api/admin/stats
```

## 🔧 Development

### Project Structure
```
AI-HTML-Builder/
├── frontend/          # React 19 application
│   ├── src/
│   │   ├── components/   # UI components
│   │   ├── hooks/        # Custom React hooks
│   │   ├── pages/        # Route components
│   │   └── types/        # TypeScript definitions
│   └── dist/            # Built frontend assets
├── backend/           # FastAPI application
│   ├── app/
│   │   ├── api/          # REST endpoints
│   │   ├── services/     # Business logic
│   │   ├── models/       # Data models
│   │   └── core/         # Configuration
│   └── requirements.txt
├── Dockerfile         # Multi-stage container build
├── docker-compose.prod.yml  # Production deployment
└── DEPLOYMENT.md      # Detailed deployment guide
```

### Adding New Features

1. **Frontend Components**: Add to `frontend/src/components/`
2. **API Endpoints**: Create in `backend/app/api/endpoints/`
3. **Services**: Implement in `backend/app/services/`
4. **Types**: Define in `frontend/src/types/`

### Code Quality
```bash
# Frontend linting
cd frontend && npm run lint

# Backend linting  
ruff check backend/

# Type checking
mypy backend/
```

## 🔒 Security Features

### Data Protection
- **No External Dependencies**: All CSS/JS inlined for security
- **Input Validation**: File type/size validation and XSS prevention
- **API Key Protection**: Environment variables only, never exposed to client
- **Session Security**: UUID v4 generation with automatic cleanup

### Admin Security
- **JWT Authentication**: Secure token-based authentication
- **Password Protection**: Configurable admin credentials
- **Rate Limiting**: 30 requests/minute per session
- **CORS Configuration**: Restricted origins for production

## 📊 Analytics & Monitoring

### Tracked Metrics
- ⏱️ **Performance**: Response times, processing duration
- 🎯 **Usage**: Token consumption, iteration counts
- 📊 **Content**: Output type classification, success rates
- 👥 **Users**: Session analytics, engagement patterns

### Export Capabilities
- **CSV Exports**: Detailed analytics with date filtering
- **Session Summaries**: High-level performance metrics
- **Custom Reports**: Flexible data analysis options

## 🐛 Troubleshooting

### Common Issues

**Redis Connection Warning** ✅
- This is expected behavior - the app gracefully falls back to memory storage
- In production, Redis will be available via docker-compose
- No action needed for development

**WebSocket Connection Failed**
```bash
# Check backend is running
curl http://localhost:8000/api/health

# Verify WebSocket endpoint
wscat -c ws://localhost:8000/ws/test-session-id
```

**Admin Dashboard Access Issues**
- Verify JWT_SECRET is configured
- Check admin password in .env.prod
- Clear browser cookies and try again

### Performance Optimization
- **Context Management**: App uses 150K character optimization for large documents
- **Semantic Caching**: Analysis results cached for similar requests
- **Connection Pooling**: Redis connections managed efficiently

## 🤝 Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

### Development Guidelines
- Follow existing code style
- Add TypeScript types for new features
- Include tests for new functionality
- Update documentation as needed

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

### Getting Help
- **Documentation**: Check `/docs` endpoint for API documentation
- **Health Check**: Monitor `/api/health` for system status
- **Admin Dashboard**: Use `/admin` for detailed analytics
- **Logs**: Check container logs for debugging

### System Requirements
- **Browser**: Modern browsers with WebSocket support
- **Network**: Stable internet for AI API calls
- **Resources**: Minimum 2GB RAM, 2 CPU cores

---

**🚀 Ready to Launch?** Follow the deployment guide in `DEPLOYMENT.md` for detailed production setup instructions.

**Built with ❤️ using Claude Sonnet 4, React 19, FastAPI, and modern web technologies.**