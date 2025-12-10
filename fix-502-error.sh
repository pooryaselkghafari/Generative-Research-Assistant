#!/bin/bash

# Fix 502 Bad Gateway Error
# This script diagnoses and fixes common causes of 502 errors

echo "🔍 Diagnosing 502 Bad Gateway Error..."
echo ""

# Check if web container is running
echo "1. Checking web container status..."
if docker-compose ps web 2>/dev/null | grep -q "Up"; then
    echo "✅ Web container is running"
else
    echo "❌ Web container is NOT running!"
    echo ""
    echo "Checking logs..."
    docker-compose logs --tail=50 web
    echo ""
    echo "Attempting to start web container..."
    docker-compose up -d web
    sleep 5
    docker-compose ps web
fi
echo ""

# Check if Django is listening on port 8000
echo "2. Checking if Django is listening on port 8000..."
if ss -tlnp 2>/dev/null | grep -q ":8000" || netstat -tlnp 2>/dev/null | grep -q ":8000"; then
    echo "✅ Port 8000 is in use (Django/Gunicorn is running)"
    ss -tlnp 2>/dev/null | grep ":8000" || netstat -tlnp 2>/dev/null | grep ":8000"
else
    echo "❌ Port 8000 is NOT in use - Django/Gunicorn is not running"
    echo ""
    echo "Checking web container logs for errors..."
    docker-compose logs --tail=30 web
fi
echo ""

# Check nginx status
echo "3. Checking nginx container status..."
if docker-compose ps nginx 2>/dev/null | grep -q "Up"; then
    echo "✅ Nginx container is running"
else
    echo "❌ Nginx container is NOT running!"
    echo "Starting nginx..."
    docker-compose up -d nginx
fi
echo ""

# Check nginx logs
echo "4. Checking nginx error logs..."
docker-compose logs --tail=20 nginx 2>/dev/null | grep -i error || echo "No recent errors in nginx logs"
echo ""

# Check if logs directory has permission issues
echo "5. Checking logs directory permissions..."
if [ -d "logs" ]; then
    if [ -w "logs" ]; then
        echo "✅ Logs directory is writable"
    else
        echo "❌ Logs directory is NOT writable!"
        echo "Fixing permissions..."
        mkdir -p logs
        chmod 755 logs
        touch logs/django.log 2>/dev/null && chmod 644 logs/django.log || echo "Could not create django.log"
    fi
else
    echo "⚠️  Logs directory doesn't exist, creating it..."
    mkdir -p logs
    chmod 755 logs
fi
echo ""

# Check database connection
echo "6. Checking database connection..."
if docker-compose ps db 2>/dev/null | grep -q "Up"; then
    echo "✅ Database container is running"
    if docker-compose exec -T db pg_isready -U postgres &>/dev/null; then
        echo "✅ Database is accepting connections"
    else
        echo "⚠️  Database is running but may not be ready"
    fi
else
    echo "❌ Database container is NOT running!"
    echo "Starting database..."
    docker-compose up -d db
    echo "Waiting for database to be ready..."
    sleep 10
fi
echo ""

# Summary and recommendations
echo "📋 Summary and Recommendations:"
echo "================================"
echo ""

# Check all services
ALL_RUNNING=true
if ! docker-compose ps web 2>/dev/null | grep -q "Up"; then
    echo "❌ Web container needs to be started"
    ALL_RUNNING=false
fi
if ! docker-compose ps db 2>/dev/null | grep -q "Up"; then
    echo "❌ Database container needs to be started"
    ALL_RUNNING=false
fi
if ! docker-compose ps nginx 2>/dev/null | grep -q "Up"; then
    echo "❌ Nginx container needs to be started"
    ALL_RUNNING=false
fi

if [ "$ALL_RUNNING" = true ]; then
    echo "✅ All containers are running"
    echo ""
    echo "If you still see 502 error, try:"
    echo "1. Restart all services:"
    echo "   docker-compose restart"
    echo ""
    echo "2. Check web container logs for Django errors:"
    echo "   docker-compose logs -f web"
    echo ""
    echo "3. Test Django directly:"
    echo "   curl http://localhost:8000/health/"
    echo ""
    echo "4. Check nginx configuration:"
    echo "   docker-compose exec nginx nginx -t"
else
    echo ""
    echo "🔧 Attempting to start all services..."
    docker-compose up -d
    echo ""
    echo "Waiting 10 seconds for services to start..."
    sleep 10
    echo ""
    echo "Checking status again..."
    docker-compose ps
fi

echo ""
echo "📝 Next steps if error persists:"
echo "1. Check web container logs: docker-compose logs web"
echo "2. Check nginx logs: docker-compose logs nginx"
echo "3. Verify .env file is configured correctly"
echo "4. Make sure database migrations are run: docker-compose exec web python manage.py migrate"
