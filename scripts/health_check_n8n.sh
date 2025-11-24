#!/bin/bash
# Health check script for n8n webhooks

set -e

N8N_URL="${N8N_URL:-http://localhost:5678}"
HEALTH_ENDPOINT="${N8N_URL}/healthz"
TIMEOUT=5

echo "Checking n8n health at: $HEALTH_ENDPOINT"

# Check if n8n is responding
if curl -f -s --max-time "$TIMEOUT" "$HEALTH_ENDPOINT" > /dev/null; then
    echo "✓ n8n is healthy"
    exit 0
else
    echo "✗ n8n health check failed"
    exit 1
fi

