#!/bin/bash

# Quick status check for all services

set -e

echo "🔍 Quick Service Status Check"
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

echo "📊 Container Status:"
echo "-------------------"
$DOCKER_COMPOSE ps
echo ""

echo "🌐 Port Status:"
echo "---------------"
echo "Port 80:"
sudo ss -tlnp | grep ":80" || echo "  ❌ Port 80 not in use"
echo ""
echo "Port 443:"
sudo ss -tlnp | grep ":443" || echo "  ❌ Port 443 not in use"
echo ""
echo "Port 8000:"
ss -tlnp | grep ":8000" || echo "  ❌ Port 8000 not in use"
echo ""

echo "🔌 Local Connectivity:"
echo "---------------------"
if curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:8000 --max-time 3 2>/dev/null; then
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000 --max-time 3)
    echo "✅ Django (localhost:8000): HTTP $HTTP_CODE"
else
    echo "❌ Django NOT responding on localhost:8000"
fi

if curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:80 --max-time 3 2>/dev/null; then
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:80 --max-time 3)
    echo "✅ Nginx (localhost:80): HTTP $HTTP_CODE"
else
    echo "❌ Nginx NOT responding on localhost:80"
fi
echo ""

echo "📋 Recent Errors:"
echo "----------------"
echo "Web service (last 10 lines):"
$DOCKER_COMPOSE logs --tail=10 web 2>&1 | grep -i "error\|exception\|failed" || echo "  No errors found"
echo ""
echo "Nginx (last 10 lines):"
$DOCKER_COMPOSE logs --tail=10 nginx 2>&1 | grep -i "error\|emerg\|crit" || echo "  No errors found"
echo ""

echo "✅ Status check complete!"
