#!/bin/bash

# Quick Fix Script for Website Issues
# This script attempts to fix common issues that prevent the website from loading

set -e

echo "🔧 Website Quick Fix Tool"
echo "========================="
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
    echo "❌ Could not find project directory. Please run this script from the project directory."
    exit 1
fi

cd "$PROJECT_DIR"
echo "📁 Project directory: $PROJECT_DIR"
echo ""

# Use docker compose (newer) or docker-compose (older)
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

# Step 1: Stop all services
echo "🛑 Stopping all services..."
$DOCKER_COMPOSE down
echo ""

# Step 2: Start database and Redis first
echo "🗄️  Starting database and Redis..."
$DOCKER_COMPOSE up -d db redis
echo "⏳ Waiting for database to be ready..."
sleep 10
echo ""

# Step 3: Check database connectivity
echo "🔍 Checking database connection..."
if $DOCKER_COMPOSE exec -T db pg_isready -U postgres &> /dev/null; then
    echo "✅ Database is ready"
else
    echo "⚠️  Database may not be ready yet, continuing anyway..."
fi
echo ""

# Step 4: Run migrations (if needed)
echo "🔄 Running database migrations..."
$DOCKER_COMPOSE run --rm web python manage.py migrate --noinput || echo "⚠️  Migrations failed, continuing..."
echo ""

# Step 5: Collect static files
echo "📁 Collecting static files..."
$DOCKER_COMPOSE run --rm web python manage.py collectstatic --noinput || echo "⚠️  Static collection failed, continuing..."
echo ""

# Step 6: Start all services
echo "🚀 Starting all services..."
$DOCKER_COMPOSE up -d
echo ""

# Step 7: Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 10
echo ""

# Step 8: Check service status
echo "📊 Service Status:"
echo "-----------------"
$DOCKER_COMPOSE ps
echo ""

# Step 9: Test connectivity
echo "🔌 Testing connectivity..."
echo ""

# Test Django
if curl -s -o /dev/null -w "Django (port 8000): HTTP %{http_code}\n" http://localhost:8000 --max-time 5 &> /dev/null; then
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000 --max-time 5)
    echo "✅ Django responding: HTTP $HTTP_CODE"
else
    echo "❌ Django NOT responding on port 8000"
    echo "   Checking logs..."
    $DOCKER_COMPOSE logs --tail=20 web
fi

# Test Nginx HTTP
if curl -s -o /dev/null -w "Nginx HTTP (port 80): HTTP %{http_code}\n" http://localhost:80 --max-time 5 &> /dev/null; then
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:80 --max-time 5)
    echo "✅ Nginx HTTP responding: HTTP $HTTP_CODE"
else
    echo "❌ Nginx NOT responding on port 80"
    echo "   Checking logs..."
    $DOCKER_COMPOSE logs --tail=20 nginx
fi

# Test Nginx HTTPS (if SSL is configured)
if [ -f ./ssl/cert.pem ] && [ -f ./ssl/key.pem ]; then
    if curl -s -o /dev/null -w "Nginx HTTPS (port 443): HTTP %{http_code}\n" https://localhost:443 --max-time 5 -k &> /dev/null; then
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://localhost:443 --max-time 5 -k)
        echo "✅ Nginx HTTPS responding: HTTP $HTTP_CODE"
    else
        echo "⚠️  Nginx HTTPS NOT responding (may be SSL configuration issue)"
    fi
fi

echo ""

# Step 10: Show recent errors
echo "📋 Recent Errors (if any):"
echo "--------------------------"
echo "Web service errors:"
$DOCKER_COMPOSE logs --tail=10 web 2>&1 | grep -i error || echo "  No errors found"
echo ""
echo "Nginx errors:"
$DOCKER_COMPOSE logs --tail=10 nginx 2>&1 | grep -i error || echo "  No errors found"
echo ""

echo "✅ Fix attempt complete!"
echo ""
echo "📝 Next steps:"
echo "1. Run ./diagnose-website.sh for detailed diagnostics"
echo "2. Check logs: $DOCKER_COMPOSE logs -f"
echo "3. If issues persist, check firewall: sudo ufw status"
echo "4. Verify domain DNS is pointing to this server"
echo ""
