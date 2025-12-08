#!/bin/bash

# Fix all current issues: Django module and nginx upstream

set -e

echo "🔧 Fixing All Issues"
echo "===================="
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

echo "1️⃣ Fixing nginx.conf upstream..."
if [ -f nginx.conf ]; then
    # Fix any web:8000 references to 127.0.0.1:8000
    sed -i 's|web:8000|127.0.0.1:8000|g' nginx.conf
    sed -i 's|server web:8000|server 127.0.0.1:8000|g' nginx.conf
    echo "✅ Updated nginx.conf"
else
    echo "❌ nginx.conf not found!"
    exit 1
fi
echo ""

echo "2️⃣ Verifying statbox/wsgi.py exists..."
if [ ! -f "statbox/wsgi.py" ]; then
    echo "❌ statbox/wsgi.py not found! Creating it..."
    mkdir -p statbox
    cat > statbox/wsgi.py <<'EOF'
import os
from django.core.wsgi import get_wsgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'statbox.settings')
application = get_wsgi_application()
EOF
    echo "✅ Created statbox/wsgi.py"
else
    echo "✅ statbox/wsgi.py exists"
fi
echo ""

echo "3️⃣ Stopping all containers..."
$DOCKER_COMPOSE down
echo ""

echo "4️⃣ Rebuilding web container..."
$DOCKER_COMPOSE build web
echo ""

echo "5️⃣ Starting all services..."
$DOCKER_COMPOSE up -d redis web n8n nginx
echo ""

echo "⏳ Waiting for services to start..."
sleep 10
echo ""

echo "6️⃣ Checking service status..."
$DOCKER_COMPOSE ps
echo ""

echo "7️⃣ Testing connectivity..."
if curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:8000 --max-time 5 2>/dev/null; then
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000 --max-time 5)
    echo "✅ Django responding: HTTP $HTTP_CODE"
else
    echo "❌ Django still not responding"
    echo "   Checking logs..."
    $DOCKER_COMPOSE logs --tail=10 web
fi

if curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:80 --max-time 5 2>/dev/null; then
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:80 --max-time 5)
    echo "✅ Nginx responding: HTTP $HTTP_CODE"
else
    echo "❌ Nginx still not responding"
    echo "   Checking logs..."
    $DOCKER_COMPOSE logs --tail=10 nginx
fi
echo ""

echo "✅ Fix complete!"
