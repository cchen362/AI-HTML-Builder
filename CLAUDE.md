# AI HTML Builder - Claude Assistant Documentation

## Project Overview

This is an AI-powered web application that enables users to generate styled HTML/CSS documents through natural language chat interactions and file uploads. The system uses OpenAI's latest GPT models to transform user inputs into professionally formatted, single-file HTML outputs with real-time preview and editing capabilities.

## Quick Start Commands

### Development Setup
```bash
# Clone/setup project
git init
git add .
git commit -m "Initial project setup"

# Frontend setup (React 19)
cd frontend
npm install
npm run dev

# Backend setup (Python 3.11+)
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Redis (via Podman/Docker)
podman run -d -p 6379:6379 --name redis redis:7-alpine
```

### Testing & Quality
```bash
# Run all tests
npm run test          # Frontend tests
pytest backend/tests  # Backend tests

# Linting & Type checking
npm run lint         # Frontend linting
npm run typecheck    # TypeScript checking
ruff check backend/  # Python linting
mypy backend/       # Python type checking

# Build & Deploy
npm run build                        # Frontend build
podman build -t ai-html-builder .   # Container build
podman-compose up -d                # Deploy with compose
```

## Technology Stack (Latest Versions - 2024/2025)

### Frontend
- **React**: 19.1.0 (latest with enhanced concurrent rendering)
- **TypeScript**: 5.4+ (latest type safety features)
- **Vite**: 5.2+ (fast build tool)
- **Node.js**: 22 LTS "Jod" (recommended for 2025, supported until April 2027)

### Backend
- **FastAPI**: Latest 2024 version with enhanced async features
- **Python**: 3.11+ (balance of features and stability, 3.13 supported)
- **Redis**: 7.4+ (latest stable with hash field expiration)
- **OpenAI SDK**: Latest with GPT-4.1/GPT-5 support

### Deployment
- **Podman**: Container orchestration (preferred over Docker)
- **Redis**: 7.4+ with persistence enabled

## Architecture Overview

```
Frontend (React 19) ←→ WebSocket/HTTP ←→ Backend (FastAPI)
                                              ↓
                                        Redis + OpenAI API
```

### Key Components
1. **Chat Interface**: Natural language processing for HTML generation
2. **HTML Viewer**: Live preview with toggle between rendered/code views  
3. **File Upload**: Process .txt, .docx, .md files (50MB limit)
4. **Session Management**: Redis-based isolation (1-hour timeout)
5. **Export System**: Single-file HTML with inlined CSS/JS

## System Requirements & Constraints

### Performance Targets
- **Concurrent Users**: Maximum 8 simultaneous sessions
- **Response Time**: < 10 seconds for HTML generation
- **Session Duration**: 1 hour timeout on inactivity
- **Chat Iterations**: Maximum 15 per session
- **File Size Limit**: 50MB per upload

### Design Guidelines
- **Colors**: Navy blue (#003366), Light blue (#4A90E2), White, Grey (#E5E5E5)
- **Fonts**: 'Benton Sans' (primary), Arial (fallback)
- **Mobile-first**: Responsive design with viewport meta tag
- **No external dependencies**: All CSS/JS must be inline

## Default Templates

### Available Templates
1. **Landing Page**: Professional landing page with hero section, features, and CTA
2. **Impact Assessment**: Professional report with tabbed navigation, solution cards, risk analysis
3. **Newsletter**: Responsive email newsletter template  
4. **Documentation**: Technical documentation with sidebar navigation

### Impact Assessment Template Structure
- Blue gradient header design
- Tabbed navigation (Problem Statement, Technical Solutions, Risk Analysis, Recommendation)
- Solution cards with pros/cons sections
- Highlighted problem areas and bordered risk items
- Interactive JavaScript for tab switching
- Mobile-responsive card-based layout

## Security Best Practices

### Input Validation
- File type/size validation
- XSS prevention for text input
- HTML output sanitization
- Content Security Policy headers

### API Security
- Rate limiting: 30 requests/minute per session
- API key protection (environment variables only)
- CORS configuration with restricted origins
- No API keys exposed to client

### Session Security
- UUID v4 session generation
- Redis key prefixing for isolation
- Automatic cleanup after 1 hour
- No persistent user data storage

## Development Workflow

### Git Branch Strategy
```
main
├── develop
│   ├── feature/chat-interface
│   ├── feature/html-viewer
│   └── feature/websocket
└── release/v1.0.0
```

### Code Quality Standards
- **Frontend**: ESLint + Prettier, React best practices
- **Backend**: Ruff + MyPy, FastAPI conventions  
- **Testing**: 80%+ coverage for unit tests
- **Documentation**: Inline comments for complex logic only

### Environment Configuration
```bash
# .env file structure
OPENAI_API_KEY=sk-...                    # Your OpenAI API key
REDIS_URL=redis://localhost:6379         # Redis connection
ENVIRONMENT=development|production       # Environment mode
LOG_LEVEL=info                          # Logging level
MAX_UPLOAD_SIZE=52428800                # 50MB in bytes
SESSION_TIMEOUT=3600                    # 1 hour in seconds
RATE_LIMIT_REQUESTS=30                  # Per minute
RATE_LIMIT_WINDOW=60                    # Time window
CORS_ORIGINS=["http://localhost:3000"]  # Allowed origins
```

## System Prompts & LLM Configuration

### Primary System Prompt Template
```markdown
You are an expert HTML/CSS developer creating single-file HTML documents.

REQUIREMENTS:
1. Generate complete, valid HTML5 documents
2. All CSS must be inline in <style> tags  
3. All JavaScript must be inline in <script> tags
4. No external dependencies or CDN links
5. Mobile-responsive with viewport meta tag
6. Use semantic HTML elements

DEFAULT STYLING (unless specified otherwise):
- Colors: Navy blue (#003366), Light blue (#4A90E2), White, Grey
- Font: 'Benton Sans', Arial, sans-serif  
- Clean, minimal UI with proper spacing
- Professional typography with readable line heights

OUTPUT: Return only complete HTML starting with <!DOCTYPE html>
```

## API Documentation

### REST Endpoints
- `POST /api/upload` - File upload with validation
- `POST /api/export` - HTML export functionality  
- `GET /api/health` - System health check

### WebSocket Protocol
- Connection: `/ws/{session_id}`
- Messages: JSON format with type, payload, timestamp
- Events: chat, update, error, status

## Monitoring & Observability

### Health Checks
- Application: `/api/health` endpoint
- Redis connectivity: Ping every 30s
- OpenAI API: Rate limit monitoring
- Disk space: Check `/tmp` usage

### Key Metrics
- Request count and duration
- Active sessions and WebSocket connections
- Error rates and response times
- Token usage and API costs

## Troubleshooting

### Common Issues
1. **WebSocket disconnections**: Automatic reconnection with exponential backoff
2. **LLM API errors**: Fallback to simpler prompts, retry logic
3. **File upload failures**: Size/type validation, clear error messages
4. **Rate limiting**: Queue management with user feedback
5. **Session expiration**: Graceful handling with new session creation

### Performance Optimization
- Code splitting for faster initial loads
- Debouncing for editor changes (500ms)
- Virtual scrolling for long message lists
- Connection pooling for Redis (size: 20)
- Response streaming via WebSocket

## Deployment Commands

### Local Development
```bash
# Start Redis
podman run -d -p 6379:6379 --name redis redis:7-alpine

# Start backend
cd backend && uvicorn app.main:app --reload

# Start frontend  
cd frontend && npm run dev
```

### Production Deployment
```bash
# Build container
podman build -t ai-html-builder .

# Deploy with compose
podman-compose up -d

# Health check
curl http://localhost:8000/api/health

# View logs
podman logs -f ai-html-builder
```

## Research & Updates

Claude is encouraged to:
- Research latest versions and best practices online
- Stay updated with technology changes and security updates
- Verify compatibility between different technology versions
- Look up current OpenAI model capabilities and pricing
- Check for breaking changes in dependencies

## Support & Maintenance

### Regular Maintenance Tasks
- Update dependencies monthly
- Review security patches
- Monitor API usage and costs  
- Clean up temporary files
- Backup Redis data (if persistence needed)

### Performance Monitoring
- P95 response time < 10 seconds
- Error rate < 1%
- 99% uptime target
- Session success rate > 90%

---

## Project Status

✅ **Completed**: Technical design document review and structure initialization
⏳ **In Progress**: Development environment setup
🔄 **Next Steps**: Component implementation and testing setup

**Last Updated**: January 2025
**Claude Version**: Sonnet 4 (claude-sonnet-4-20250514)