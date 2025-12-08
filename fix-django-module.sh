#!/bin/bash

# Fix Django module not found error

set -e

echo "🔧 Fixing Django Module Error"
echo "=============================="
echo ""

# Find project directory
if [ -d ~/GRA1 ]; then
    PROJECT_DIR=~/GRA1
elif [ -d ~/GRA ]; then
    PROJECT_DIR=~/GRA
elif [ -d /home/deploy/GRA1 ]; then
    PROJECT_DIR=/home/deploy/GRA1
elif [ -d /home/deploy/GRA ]; then
    PROJECT_DIR=/home/deploy/GRA
else
    echo "❌ Could not find project directory."
    exit 1
fi

cd "$PROJECT_DIR"

# Use docker compose (newer) or docker-compose (older)
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

echo "📋 Checking if statbox directory exists..."
if [ ! -d "statbox" ]; then
    echo "❌ statbox directory not found in $PROJECT_DIR"
    exit 1
fi

echo "✅ statbox directory exists"
echo ""

echo "🔍 Checking container contents..."
$DOCKER_COMPOSE exec web ls -la /app/ | head -20 || echo "Container not running, will check after restart"
echo ""

echo "🔍 Checking if statbox.wsgi exists in container..."
$DOCKER_COMPOSE exec web ls -la /app/statbox/wsgi.py 2>/dev/null || {
    echo "⚠️  statbox/wsgi.py not found in container"
    echo ""
    echo "🔄 Rebuilding container to ensure code is included..."
    $DOCKER_COMPOSE build web
    echo ""
}

echo "🔄 Restarting web container..."
$DOCKER_COMPOSE restart web
echo ""

echo "⏳ Waiting for container to start..."
sleep 5
echo ""

echo "📋 Checking web container logs..."
$DOCKER_COMPOSE logs --tail=20 web
echo ""

echo "✅ Fix attempt complete!"
echo ""
echo "💡 If still failing, try:"
echo "   1. Check if statbox directory exists: ls -la statbox/"
echo "   2. Rebuild container: $DOCKER_COMPOSE build web"
echo "   3. Check container contents: $DOCKER_COMPOSE exec web ls -la /app/"
