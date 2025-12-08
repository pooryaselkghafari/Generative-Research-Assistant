#!/bin/bash

# Verify container setup and fix issues

set -e

echo "🔍 Verifying Container Setup"
echo "============================"
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

echo "1️⃣ Checking if statbox/wsgi.py exists on host..."
if [ -f "statbox/wsgi.py" ]; then
    echo "✅ statbox/wsgi.py exists on host"
else
    echo "❌ statbox/wsgi.py NOT found on host!"
    echo "   Pulling latest from git..."
    git pull origin main
    if [ -f "statbox/wsgi.py" ]; then
        echo "✅ File pulled successfully"
    else
        echo "❌ File still not found after git pull"
        exit 1
    fi
fi
echo ""

echo "2️⃣ Checking container status..."
if $DOCKER_COMPOSE ps | grep -q "web.*Up"; then
    echo "✅ Web container is running"
else
    echo "⚠️  Web container is not running"
    echo "   Starting web container..."
    $DOCKER_COMPOSE up -d web
    sleep 5
fi
echo ""

echo "3️⃣ Checking if statbox/wsgi.py exists in container..."
if $DOCKER_COMPOSE exec web test -f /app/statbox/wsgi.py 2>/dev/null; then
    echo "✅ statbox/wsgi.py exists in container"
else
    echo "❌ statbox/wsgi.py NOT found in container!"
    echo ""
    echo "📋 Listing /app/statbox/ contents:"
    $DOCKER_COMPOSE exec web ls -la /app/statbox/ 2>/dev/null || echo "   Cannot list directory"
    echo ""
    echo "🔄 Restarting container to remount volumes..."
    $DOCKER_COMPOSE restart web
    sleep 5
    if $DOCKER_COMPOSE exec web test -f /app/statbox/wsgi.py 2>/dev/null; then
        echo "✅ File now exists after restart"
    else
        echo "❌ File still not found. Checking volume mount..."
        echo ""
        echo "📋 Checking /app directory in container:"
        $DOCKER_COMPOSE exec web ls -la /app/ | head -10
        echo ""
        echo "💡 The volume mount might not be working. Try rebuilding:"
        echo "   $DOCKER_COMPOSE down"
        echo "   $DOCKER_COMPOSE build web"
        echo "   $DOCKER_COMPOSE up -d web"
    fi
fi
echo ""

echo "4️⃣ Testing Python import..."
if $DOCKER_COMPOSE exec web python -c "import statbox.wsgi" 2>/dev/null; then
    echo "✅ Python can import statbox.wsgi"
else
    echo "❌ Python cannot import statbox.wsgi"
    echo ""
    echo "📋 Error details:"
    $DOCKER_COMPOSE exec web python -c "import statbox.wsgi" 2>&1 || true
    echo ""
    echo "📋 Checking Python path:"
    $DOCKER_COMPOSE exec web python -c "import sys; print('\n'.join(sys.path))"
fi
echo ""

echo "✅ Verification complete!"
