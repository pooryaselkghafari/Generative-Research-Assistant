#!/bin/bash

# StatBox Deployment Script

set -e

echo "🚀 Starting StatBox deployment..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please copy env.example to .env and configure it."
    exit 1
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Build and start services
echo "📦 Building Docker containers..."
docker-compose build

echo "🗄️ Starting database and Redis..."
docker-compose up -d db redis

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
sleep 10

# Run migrations
echo "🔄 Running database migrations..."
docker-compose run --rm web python manage.py migrate

# Create superuser (optional)
echo "👤 Creating superuser..."
docker-compose run --rm web python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Superuser created: admin/admin123')
else:
    print('Superuser already exists')
"

# Collect static files
echo "📁 Collecting static files..."
docker-compose run --rm web python manage.py collectstatic --noinput

# Start all services
echo "🌐 Starting all services..."
docker-compose up -d

echo "✅ Deployment complete!"
echo "🌍 Your StatBox application is running at:"
echo "   - HTTP: http://localhost"
echo "   - Admin: http://localhost/admin"
echo "   - API: http://localhost/api/"

echo ""
echo "📋 Next steps:"
echo "1. Configure your domain in nginx.conf"
echo "2. Set up SSL certificates in ./ssl/"
echo "3. Configure Stripe webhooks"
echo "4. Set up monitoring and backups"
