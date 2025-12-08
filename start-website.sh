#!/bin/bash

# Start Website Script - Fixes common issues and starts all services

set -e

echo "🚀 Starting Website Services"
echo "============================="
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
        echo "   ⚠️  You should configure EMAIL_HOST_PASSWORD with your Resend API key"
        echo "   📝 Edit .env file to add your email credentials"
    else
        echo "✅ EMAIL_HOST is configured in .env"
    fi
else
    echo "❌ .env file not found!"
    echo "   Creating from env.example..."
    if [ -f env.example ]; then
        cp env.example .env
        echo "✅ Created .env from env.example"
        echo "   ⚠️  Please edit .env file with your actual configuration"
    else
        echo "❌ env.example not found. Cannot create .env file."
        exit 1
    fi
fi
echo ""

# Step 2: Stop any running containers
echo "🛑 Stopping existing containers..."
$DOCKER_COMPOSE down 2>/dev/null || true
echo ""

# Step 3: Start database and Redis first
echo "🗄️  Starting database and Redis..."
$DOCKER_COMPOSE up -d db redis
echo "⏳ Waiting for database to be ready..."
sleep 15

# Check database connectivity
MAX_RETRIES=10
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if $DOCKER_COMPOSE exec -T db pg_isready -U postgres &> /dev/null; then
        echo "✅ Database is ready"
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        echo "⏳ Waiting for database... ($RETRY_COUNT/$MAX_RETRIES)"
        sleep 2
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "⚠️  Database may not be fully ready, but continuing..."
fi
echo ""

# Step 4: Run migrations
echo "🔄 Running database migrations..."
$DOCKER_COMPOSE run --rm web python manage.py migrate --noinput || {
    echo "⚠️  Migrations failed, but continuing..."
}
echo ""

# Step 5: Collect static files
echo "📁 Collecting static files..."
$DOCKER_COMPOSE run --rm web python manage.py collectstatic --noinput || {
    echo "⚠️  Static collection failed, but continuing..."
}
echo ""

# Step 6: Start all services
echo "🚀 Starting all services..."
$DOCKER_COMPOSE up -d
echo ""

# Step 7: Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 15
echo ""

# Step 8: Check service status
echo "📊 Service Status:"
echo "-----------------"
$DOCKER_COMPOSE ps
echo ""

# Step 9: Check for errors in logs
echo "🔍 Checking for startup errors..."
echo ""

WEB_ERRORS=$($DOCKER_COMPOSE logs --tail=30 web 2>&1 | grep -i "error\|exception\|traceback" | head -5 || true)
NGINX_ERRORS=$($DOCKER_COMPOSE logs --tail=30 nginx 2>&1 | grep -i "error\|emerg\|crit" | head -5 || true)
DB_ERRORS=$($DOCKER_COMPOSE logs --tail=30 db 2>&1 | grep -i "error\|fatal" | head -5 || true)

if [ -n "$WEB_ERRORS" ]; then
    echo "⚠️  Web service errors:"
    echo "$WEB_ERRORS"
    echo ""
fi

if [ -n "$NGINX_ERRORS" ]; then
    echo "⚠️  Nginx errors:"
    echo "$NGINX_ERRORS"
    echo ""
fi

if [ -n "$DB_ERRORS" ]; then
    echo "⚠️  Database errors:"
    echo "$DB_ERRORS"
    echo ""
fi

# Step 10: Test connectivity
echo "🔌 Testing connectivity..."
echo ""

# Test Django
sleep 5
if curl -s -o /dev/null -w "Django (port 8000): HTTP %{http_code}\n" http://localhost:8000 --max-time 10 &> /dev/null; then
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000 --max-time 10)
    echo "✅ Django responding: HTTP $HTTP_CODE"
else
    echo "❌ Django NOT responding on port 8000"
    echo "   Checking web logs..."
    $DOCKER_COMPOSE logs --tail=20 web | tail -10
fi

# Test Nginx HTTP
if curl -s -o /dev/null -w "Nginx HTTP (port 80): HTTP %{http_code}\n" http://localhost:80 --max-time 10 &> /dev/null; then
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:80 --max-time 10)
    echo "✅ Nginx HTTP responding: HTTP $HTTP_CODE"
else
    echo "❌ Nginx NOT responding on port 80"
    echo "   Checking nginx logs..."
    $DOCKER_COMPOSE logs --tail=20 nginx | tail -10
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

# Final summary
echo "✅ Startup complete!"
echo ""
echo "📝 Next steps:"
echo "1. If services are running, your website should be accessible"
echo "2. If you see errors above, check logs: $DOCKER_COMPOSE logs -f [service_name]"
echo "3. Configure EMAIL_HOST_PASSWORD in .env if you want email functionality"
echo "4. Run ./diagnose-website.sh for detailed diagnostics"
echo ""
echo "🔗 Useful commands:"
echo "   View logs: $DOCKER_COMPOSE logs -f"
echo "   Restart: $DOCKER_COMPOSE restart"
echo "   Stop: $DOCKER_COMPOSE down"
echo ""
