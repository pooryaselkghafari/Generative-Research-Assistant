# n8n Integration Setup Guide

## Quick Start

### 1. Environment Variables

Add to your `.env` file:

```bash
# n8n Configuration
N8N_HOST=0.0.0.0
N8N_PORT=5678
N8N_PROTOCOL=http
N8N_ENCRYPTION_KEY=$(openssl rand -base64 32)  # Generate once and reuse
N8N_WEBHOOK_TIMEOUT=30
N8N_MAX_RETRIES=2
```

### 2. Start Services

```bash
# Pull latest changes
git pull

# Start n8n service
docker-compose up -d n8n

# Run migrations
docker-compose exec web python manage.py migrate

# Restart nginx to pick up new config
docker-compose restart nginx
```

### 3. Access n8n

1. Log in to your admin panel: `https://yourdomain.com/whereadmingoeshere/`
2. Navigate to: `https://yourdomain.com/n8n/`
3. You should see the n8n workflow editor

### 4. Create Your First Workflow

1. In n8n, click "Add workflow"
2. Add a "Webhook" node (trigger)
3. Configure it:
   - HTTP Method: POST
   - Path: `/webhook/chatbot-test` (or any path you want)
   - Click "Listen for Test Event"
4. Add an "HTTP Request" node or "Code" node to process the request
5. Add a "Respond to Webhook" node to return the response:
   ```json
   {
     "reply": "Hello! This is a test response from n8n.",
     "metadata": {}
   }
   ```
6. Save the workflow
7. Copy the webhook URL (e.g., `http://localhost:5678/webhook/chatbot-test`)

### 5. Register Template in Admin

1. Go to: `https://yourdomain.com/whereadmingoeshere/engine/agenttemplate/`
2. Click "Add Agent Template"
3. Fill in:
   - **Name**: "Test Chatbot Agent"
   - **Description**: "A simple test agent"
   - **n8n Webhook URL**: `http://localhost:5678/webhook/chatbot-test` (use localhost since Django calls n8n directly)
   - **Status**: "Active"
   - **Visibility**: "Customer Facing"
   - **Mode Key**: (optional) "test_agent"
4. Click "Save"

### 6. Test the Integration

Use curl or your frontend:

```bash
curl -X POST https://yourdomain.com/api/chat \
  -H "Content-Type: application/json" \
  -H "Cookie: sessionid=YOUR_SESSION_ID" \
  -d '{
    "message": "Hello, test message",
    "mode_key": "test_agent"
  }'
```

Or use the "Test" button in the admin template detail page.

## Architecture Overview

```
User → Frontend → POST /api/chat → Django Backend
  → AgentTemplate lookup → n8n Webhook (http://localhost:5678/webhook/...)
  → n8n Workflow Execution → JSON Response
  → Django transforms → Return to Frontend
```

## Security

- n8n GUI is only accessible to authenticated admin users (via middleware)
- All webhook URLs must be registered in AgentTemplate
- Input validation on all user messages
- Output validation on n8n responses
- Rate limiting on chatbot endpoint

## Testing

Run all tests:

```bash
# Unit tests
pytest tests/agent_templates/test_models.py -v

# Integration tests
pytest tests/agent_templates/test_integration.py -v

# API tests
pytest tests/chatbot/test_endpoint.py -v

# E2E tests (requires Playwright)
pytest tests/e2e/test_chatbot_flow.py -v

# All tests with coverage
pytest --cov=engine --cov-report=html tests/
```

## Monitoring

Check logs:

```bash
# Django logs
docker-compose logs web | grep -i "n8n\|chatbot\|agent"

# n8n logs
docker-compose logs n8n
```

## Troubleshooting

### n8n not accessible

1. Check n8n is running: `docker-compose ps n8n`
2. Check nginx config: `docker-compose exec nginx nginx -t`
3. Check middleware is loaded in Django settings
4. Verify you're logged in as admin

### Webhook calls failing

1. Check n8n webhook URL is correct (use `http://localhost:5678/...` not `https://...`)
2. Check n8n workflow is active
3. Check n8n logs for errors
4. Test webhook directly with curl:
   ```bash
   curl -X POST http://localhost:5678/webhook/your-path \
     -H "Content-Type: application/json" \
     -d '{"message": "test"}'
   ```

### Template not found

1. Check template status is "Active"
2. Check visibility matches user type (internal vs customer_facing)
3. Check mode_key matches if using mode routing

