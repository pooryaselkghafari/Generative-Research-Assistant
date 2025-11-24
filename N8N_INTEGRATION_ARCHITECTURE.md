# n8n Integration Architecture

## Overview

This document describes the architecture for integrating n8n (workflow automation) into the Generative Research Assistant application, enabling AI chatbot agents powered by n8n workflows.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Browser                            │
└──────────────┬──────────────────────────────┬─────────────────┘
               │                              │
               │ HTTPS                        │ HTTPS
               │                              │
    ┌──────────▼──────────┐      ┌───────────▼────────────┐
    │   Nginx Reverse     │      │   Nginx Reverse       │
    │   Proxy (Port 443)  │      │   Proxy (Port 443)   │
    │                     │      │                       │
    │  /whereadmingoeshere│      │  /n8n/                │
    │  /api/chat          │      │  (Admin only)         │
    └──────────┬──────────┘      └───────────┬───────────┘
               │                              │
               │                              │
    ┌──────────▼──────────┐      ┌───────────▼────────────┐
    │   Django Web App     │      │   n8n Service          │
    │   (Port 8000)        │      │   (Port 5678)         │
    │                      │      │                       │
    │  - Admin UI          │      │  - Workflow Editor    │
    │  - Agent Template    │      │  - Webhook Endpoints  │
    │    Manager           │      │  - Workflow Execution │
    │  - Chatbot API       │      │                       │
    │  - Database          │      │  - n8n Database       │
    └──────────┬──────────┘      └───────────┬───────────┘
               │                              │
               │                              │
               │  HTTP POST (Webhook)         │
               │  ────────────────────────────►
               │                              │
               │  JSON Response               │
               │  ◄───────────────────────────
               │                              │
    ┌──────────▼──────────────────────────────▼──────────────┐
    │              PostgreSQL Database                        │
    │  - AgentTemplate table                                  │
    │  - Application data                                     │
    └─────────────────────────────────────────────────────────┘
```

## Technology Stack

### Backend
- **Framework**: Django 5.2+ (existing)
- **Database**: PostgreSQL 15 (existing)
- **API**: Django REST Framework (to be added) or Django JSON views
- **Authentication**: Django session-based auth + admin checks

### Frontend
- **Admin UI**: Django admin with custom templates
- **Chatbot UI**: Existing JavaScript/HTML (to be extended)

### n8n Hosting
- **Container**: Docker (n8n official image)
- **Database**: SQLite (default) or PostgreSQL (optional)
- **Port**: 5678 (internal, not exposed)
- **Access**: Via Nginx reverse proxy at `/n8n/`

### Reverse Proxy
- **Server**: Nginx (existing)
- **SSL**: Let's Encrypt certificates (existing)
- **Security**: Session-based authentication check before proxying to n8n

### Testing & Quality
- **Unit Tests**: pytest
- **Integration Tests**: pytest + Django TestCase
- **API Tests**: pytest + Django TestClient
- **E2E Tests**: Playwright
- **Static Analysis**: mypy, ruff, bandit
- **Coverage**: pytest-cov
- **Dependency Scan**: pip-audit, safety
- **Monitoring**: Structured logging + Prometheus (optional)
- **Backup**: pg_dump scripts + cron
- **Cron**: systemd timers or Celery beat

## Data Flow

### 1. Admin Creates Agent Template
```
Admin → Django Admin UI → AgentTemplate Model → Database
```

### 2. Admin Configures n8n Workflow
```
Admin → Nginx → n8n GUI → Create Workflow → Save Webhook URL
```

### 3. User Uses Chatbot
```
User → Frontend → POST /api/chat → Django Backend
  → Lookup AgentTemplate → POST to n8n Webhook
  → n8n Executes Workflow → Returns JSON
  → Django Transforms Response → Return to Frontend
  → Display to User
```

## Security Model

### n8n Access Control
- **Path**: `/n8n/` (only accessible to authenticated admin users)
- **Method**: Nginx checks Django session cookie before proxying
- **Fallback**: Django middleware can also check admin status
- **Network**: n8n only accessible via reverse proxy (not directly exposed)

### Webhook Security
- **Validation**: All webhook URLs must be registered in AgentTemplate
- **Input Validation**: Sanitize user input before sending to n8n
- **Output Validation**: Validate n8n responses before returning to user
- **Rate Limiting**: Apply rate limits to chatbot endpoint
- **Logging**: Log all webhook calls with user_id and template_id

## Component Details

### AgentTemplate Model
- Stores metadata about n8n workflows
- Links chatbot modes to specific workflows
- Tracks active/inactive status
- Stores default parameters per template

### Template Manager UI
- List all templates
- Create/edit templates
- Test templates (send sample payload)
- Activate/deactivate templates
- View template usage stats

### Chatbot Integration
- Endpoint: `POST /api/chat`
- Determines which template to use
- Calls n8n webhook with structured payload
- Handles errors and timeouts
- Returns formatted response

### n8n Workflow Structure
- **Trigger**: Webhook node (receives POST from Django)
- **Processing**: LLM nodes, RAG nodes, tool nodes, etc.
- **Output**: Return JSON with `reply` field

## File Structure

```
GRA/
├── docker-compose.yml          # Add n8n service
├── nginx.conf                  # Add /n8n/ location
├── engine/
│   ├── models.py               # Add AgentTemplate model
│   ├── admin.py                # Add AgentTemplateAdmin
│   ├── views/
│   │   ├── agent_templates.py  # Template Manager APIs
│   │   └── chatbot.py          # Chatbot endpoint
│   ├── services/
│   │   └── n8n_service.py      # n8n webhook client
│   ├── templates/
│   │   └── admin/
│   │       └── agent_template/ # Custom admin templates
│   └── migrations/
│       └── XXXX_add_agent_template.py
├── tests/
│   ├── agent_templates/
│   │   ├── test_models.py
│   │   ├── test_views.py
│   │   └── test_integration.py
│   ├── chatbot/
│   │   ├── test_endpoint.py
│   │   └── test_n8n_integration.py
│   └── e2e/
│       └── test_chatbot_flow.py
└── scripts/
    ├── backup_n8n.sh
    └── health_check_n8n.sh
```

## Environment Variables

```bash
# n8n Configuration
N8N_HOST=0.0.0.0
N8N_PORT=5678
N8N_PROTOCOL=http
N8N_BASIC_AUTH_ACTIVE=false
N8N_BASIC_AUTH_USER=
N8N_BASIC_AUTH_PASSWORD=
N8N_ENCRYPTION_KEY=  # Generate with: openssl rand -base64 32

# n8n Database (optional - uses SQLite by default)
N8N_DB_TYPE=postgresdb
N8N_DB_POSTGRESDB_HOST=db
N8N_DB_POSTGRESDB_PORT=5432
N8N_DB_POSTGRESDB_DATABASE=n8n
N8N_DB_POSTGRESDB_USER=postgres
N8N_DB_POSTGRESDB_PASSWORD=${DB_PASSWORD}

# Django n8n Integration
N8N_WEBHOOK_TIMEOUT=30  # seconds
N8N_MAX_RETRIES=2
```

## Testing Strategy

### Unit Tests
- AgentTemplate model methods
- Template selection logic
- Payload construction
- Response parsing

### Integration Tests
- Template CRUD operations
- Chatbot → n8n webhook flow (with mocked n8n)
- Admin authentication checks

### API Tests
- All admin endpoints
- Chatbot endpoint with various scenarios
- Error handling

### E2E Tests
- Admin creates template
- User uses chatbot with template
- Template activation/deactivation

### Security Tests
- Unauthorized access attempts
- Input validation
- SQL injection attempts
- XSS attempts

### Performance Tests
- Response time under load
- Concurrent webhook calls
- Database query optimization

### Static Analysis
- Type checking (mypy)
- Code quality (ruff)
- Security scanning (bandit)

### Coverage
- Target: 80% coverage for new code
- Exclude migrations and admin boilerplate

## Deployment Steps

1. **Add n8n to Docker Compose**
2. **Update Nginx configuration**
3. **Run migrations for AgentTemplate**
4. **Configure n8n environment variables**
5. **Start services**: `docker-compose up -d`
6. **Access n8n**: `https://yourdomain.com/n8n/` (admin only)
7. **Create first workflow in n8n**
8. **Register workflow in Template Manager**
9. **Test chatbot integration**

## Monitoring & Maintenance

### Logging
- All n8n webhook calls logged with:
  - User ID
  - Template ID
  - Request/response size
  - Duration
  - Success/failure

### Health Checks
- n8n service health endpoint
- Webhook endpoint availability
- Database connectivity

### Backups
- AgentTemplate database table
- n8n workflow definitions (exported as JSON)
- n8n database (if using PostgreSQL)

### Cron Jobs
- Daily health check of n8n webhooks
- Weekly backup of AgentTemplate data
- Monthly backup of n8n workflows

