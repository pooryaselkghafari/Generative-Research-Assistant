#!/bin/bash

# Start Website Only - Skip PostgreSQL and Supabase

set -e

echo "🚀 Starting Website Services (without PostgreSQL)"
echo "=================================================="
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

# Step 1: Fix .env file - add EMAIL_HOST if missing
echo "⚙️  Checking .env file..."
if [ -f .env ]; then
    if ! grep -q "^EMAIL_HOST=" .env; then
        echo "⚠️  EMAIL_HOST not found in .env, adding default value..."
        echo "" >> .env
        echo "# Email Settings (added automatically)" >> .env
        echo "EMAIL_HOST=smtp.resend.com" >> .env
        echo "EMAIL_PORT=465" >> .env
        echo "EMAIL_USE_SSL=True" >> .env
        echo "EMAIL_USE_TLS=False" >> .env
        echo "EMAIL_HOST_USER=resend" >> .env
        echo "EMAIL_HOST_PASSWORD=" >> .env
        echo "DEFAULT_FROM_EMAIL=noreply@generativera.com" >> .env
        echo "✅ Added default email settings to .env"
    else
        echo "✅ EMAIL_HOST is configured in .env"
    fi
else
    echo "❌ .env file not found!"
    exit 1
fi
echo ""

# Step 2: Stop any running containers (except db)
echo "🛑 Stopping existing containers..."
$DOCKER_COMPOSE stop web nginx redis n8n 2>/dev/null || true
echo ""

# Step 3: Start Redis first
echo "🔄 Starting Redis..."
$DOCKER_COMPOSE up -d redis
sleep 3
echo ""

# Step 4: Start web service (it will connect to existing PostgreSQL on host)
echo "🌐 Starting web service..."
echo "   (Assuming PostgreSQL is already running on localhost:5432)"
$DOCKER_COMPOSE up -d web
sleep 5
echo ""

# Step 5: Start n8n
echo "🔧 Starting n8n..."
$DOCKER_COMPOSE up -d n8n
sleep 3
echo ""

# Step 6: Start nginx (remove Supabase network dependency temporarily)
echo "📡 Starting nginx..."
# Temporarily remove Supabase network from nginx if it fails
$DOCKER_COMPOSE up -d nginx 2>&1 | grep -v "supabase_default" || {
    echo "⚠️  Nginx failed to start with Supabase network, trying without it..."
    # Create a temporary docker-compose override
    cat > docker-compose.override.yml <<EOF
services:
  nginx:
    networks:
      - default
EOF
    $DOCKER_COMPOSE up -d nginx
}
echo ""

# Step 7: Wait for services
echo "⏳ Waiting for services to start..."
sleep 10
echo ""

# Step 8: Check service status
echo "📊 Service Status:"
echo "-----------------"
$DOCKER_COMPOSE ps web nginx redis n8n
echo ""

# Step 9: Test connectivity
echo "🔌 Testing connectivity..."
echo ""

# Test Django
if curl -s -o /dev/null -w "Django (port 8000): HTTP %{http_code}\n" http://localhost:8000 --max-time 10 &> /dev/null; then
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000 --max-time 10)
    echo "✅ Django responding: HTTP $HTTP_CODE"
else
    echo "❌ Django NOT responding on port 8000"
    echo "   Checking web logs..."
    $DOCKER_COMPOSE logs --tail=10 web | tail -5
fi

# Test Nginx HTTP
if curl -s -o /dev/null -w "Nginx HTTP (port 80): HTTP %{http_code}\n" http://localhost:80 --max-time 10 &> /dev/null; then
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:80 --max-time 10)
    echo "✅ Nginx HTTP responding: HTTP $HTTP_CODE"
else
    echo "❌ Nginx NOT responding on port 80"
    echo "   Checking nginx logs..."
    $DOCKER_COMPOSE logs --tail=10 nginx | tail -5
fi

# Test Nginx HTTPS (if SSL is configured)
if [ -f ./ssl/cert.pem ] && [ -f ./ssl/key.pem ]; then
    if curl -s -o /dev/null -w "Nginx HTTPS (port 443): HTTP %{http_code}\n" https://localhost:443 --max-time 10 -k &> /dev/null; then
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://localhost:443 --max-time 10 -k)
        echo "✅ Nginx HTTPS responding: HTTP $HTTP_CODE"
    else
        echo "⚠️  Nginx HTTPS NOT responding (may be SSL configuration issue)"
    fi
fi

echo ""
echo "✅ Website services started!"
echo ""
echo "📝 Note: PostgreSQL container was skipped. Make sure PostgreSQL is running on localhost:5432"
echo "   If you need to check: sudo systemctl status postgresql"
echo ""
