#!/bin/bash

# Website Diagnostic Script for DigitalOcean Server
# This script checks all services and identifies why the website isn't loading

set -e

echo "🔍 Website Diagnostic Tool"
echo "=========================="
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

# Check if docker-compose.yml exists
if [ ! -f docker-compose.yml ]; then
    echo "❌ docker-compose.yml not found in $PROJECT_DIR"
    exit 1
fi

# 1. Check Docker and Docker Compose
echo "🐳 Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed"
    exit 1
fi

if ! docker ps &> /dev/null; then
    echo "❌ Docker daemon is not running or user doesn't have permissions"
    echo "   Try: sudo systemctl start docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not installed"
    exit 1
fi

# Use docker compose (newer) or docker-compose (older)
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

echo "✅ Docker is running"
echo ""

# 2. Check container status
echo "📊 Container Status:"
echo "-------------------"
$DOCKER_COMPOSE ps
echo ""

# Check each service
SERVICES=("web" "nginx" "db" "redis" "n8n")
ALL_RUNNING=true

for service in "${SERVICES[@]}"; do
    if $DOCKER_COMPOSE ps | grep -q "$service.*Up"; then
        echo "✅ $service is running"
    else
        echo "❌ $service is NOT running"
        ALL_RUNNING=false
    fi
done

echo ""

# 3. Check ports
echo "🌐 Port Status:"
echo "---------------"
if sudo ss -tlnp 2>/dev/null | grep -q ":80"; then
    echo "✅ Port 80 is in use"
    sudo ss -tlnp | grep ":80" | head -1
else
    echo "❌ Port 80 is NOT in use - nginx may not be running"
fi

if sudo ss -tlnp 2>/dev/null | grep -q ":443"; then
    echo "✅ Port 443 is in use"
    sudo ss -tlnp | grep ":443" | head -1
else
    echo "❌ Port 443 is NOT in use - nginx may not be running"
fi

if ss -tlnp 2>/dev/null | grep -q ":8000"; then
    echo "✅ Port 8000 is in use (Django/Gunicorn)"
    ss -tlnp | grep ":8000" | head -1
else
    echo "❌ Port 8000 is NOT in use - Django/Gunicorn may not be running"
fi

echo ""

# 4. Check nginx logs
echo "📋 Nginx Logs (last 20 lines):"
echo "-------------------------------"
if $DOCKER_COMPOSE ps | grep -q "nginx.*Up"; then
    $DOCKER_COMPOSE logs --tail=20 nginx 2>&1 | tail -20
else
    echo "⚠️  Nginx container is not running, cannot check logs"
fi
echo ""

# 5. Check web (Django) logs
echo "📋 Web Service Logs (last 20 lines):"
echo "-------------------------------------"
if $DOCKER_COMPOSE ps | grep -q "web.*Up"; then
    $DOCKER_COMPOSE logs --tail=20 web 2>&1 | tail -20
else
    echo "⚠️  Web container is not running, cannot check logs"
fi
echo ""

# 6. Check database connectivity
echo "🗄️  Database Status:"
echo "-------------------"
if $DOCKER_COMPOSE ps | grep -q "db.*Up"; then
    if $DOCKER_COMPOSE exec -T db pg_isready -U postgres &> /dev/null; then
        echo "✅ Database is ready and accepting connections"
    else
        echo "❌ Database is running but not accepting connections"
    fi
else
    echo "❌ Database container is not running"
fi
echo ""

# 7. Check SSL certificates
echo "🔒 SSL Certificate Status:"
echo "-------------------------"
if [ -d ./ssl ]; then
    if [ -f ./ssl/cert.pem ] && [ -f ./ssl/key.pem ]; then
        echo "✅ SSL certificates found in ./ssl/"
        if command -v openssl &> /dev/null; then
            CERT_EXPIRY=$(openssl x509 -enddate -noout -in ./ssl/cert.pem 2>/dev/null | cut -d= -f2)
            if [ -n "$CERT_EXPIRY" ]; then
                echo "   Certificate expires: $CERT_EXPIRY"
            fi
        fi
    else
        echo "⚠️  SSL directory exists but certificates are missing"
    fi
else
    echo "⚠️  SSL directory not found - HTTPS may not work"
fi
echo ""

# 8. Test local connectivity
echo "🔌 Local Connectivity Tests:"
echo "----------------------------"
if curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://localhost:8000 --max-time 5 &> /dev/null; then
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000 --max-time 5)
    echo "✅ Django/Gunicorn responding on localhost:8000 (HTTP $HTTP_CODE)"
else
    echo "❌ Django/Gunicorn NOT responding on localhost:8000"
fi

if curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://localhost:80 --max-time 5 &> /dev/null; then
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:80 --max-time 5)
    echo "✅ Nginx responding on localhost:80 (HTTP $HTTP_CODE)"
else
    echo "❌ Nginx NOT responding on localhost:80"
fi

if curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" https://localhost:443 --max-time 5 -k &> /dev/null; then
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://localhost:443 --max-time 5 -k)
    echo "✅ Nginx responding on localhost:443 (HTTP $HTTP_CODE)"
else
    echo "❌ Nginx NOT responding on localhost:443"
fi
echo ""

# 9. Check .env file
echo "⚙️  Environment Configuration:"
echo "------------------------------"
if [ -f .env ]; then
    echo "✅ .env file exists"
    if grep -q "DEBUG=True" .env; then
        echo "⚠️  WARNING: DEBUG is set to True (should be False in production)"
    fi
    if ! grep -q "ALLOWED_HOSTS" .env || grep -q "ALLOWED_HOSTS=$" .env; then
        echo "⚠️  WARNING: ALLOWED_HOSTS may not be configured"
    fi
else
    echo "❌ .env file not found - configuration is missing"
fi
echo ""

# 10. Check disk space
echo "💾 Disk Space:"
echo "-------------"
df -h / | tail -1
echo ""

# 11. Check memory
echo "🧠 Memory Usage:"
echo "--------------"
free -h
echo ""

# Summary and recommendations
echo "📝 Summary and Recommendations:"
echo "================================"
echo ""

if [ "$ALL_RUNNING" = false ]; then
    echo "❌ Some services are not running. Try:"
    echo "   $DOCKER_COMPOSE up -d"
    echo ""
fi

if ! ss -tlnp 2>/dev/null | grep -q ":80\|:443"; then
    echo "❌ Nginx is not listening on ports 80/443. Try:"
    echo "   $DOCKER_COMPOSE restart nginx"
    echo "   $DOCKER_COMPOSE logs nginx"
    echo ""
fi

if ! ss -tlnp 2>/dev/null | grep -q ":8000"; then
    echo "❌ Django/Gunicorn is not listening on port 8000. Try:"
    echo "   $DOCKER_COMPOSE restart web"
    echo "   $DOCKER_COMPOSE logs web"
    echo ""
fi

echo "🔧 Quick Fix Commands:"
echo "---------------------"
echo "# Restart all services:"
echo "  $DOCKER_COMPOSE restart"
echo ""
echo "# View all logs:"
echo "  $DOCKER_COMPOSE logs --tail=50"
echo ""
echo "# Start services if stopped:"
echo "  $DOCKER_COMPOSE up -d"
echo ""
echo "# Rebuild and restart:"
echo "  $DOCKER_COMPOSE down"
echo "  $DOCKER_COMPOSE build"
echo "  $DOCKER_COMPOSE up -d"
echo ""

echo "✅ Diagnostic complete!"
