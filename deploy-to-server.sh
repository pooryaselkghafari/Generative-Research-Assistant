#!/bin/bash

# Quick deployment script for Digital Ocean server
# This script helps you deploy to server 147.182.153.228

set -e

SERVER_IP="147.182.153.228"
SERVER_USER="root"  # Change to your SSH user if different
REPO_URL="https://github.com/pooryaselkghafari/GRA2.git"
PROJECT_DIR="statbox"

echo "🚀 StatBox Deployment Script for Digital Ocean"
echo "=============================================="
echo ""
echo "Server IP: $SERVER_IP"
echo "Repository: $REPO_URL"
echo ""

# Check if we're on the server or local machine
if [ "$HOSTNAME" != "$SERVER_IP" ] && [ "$SSH_CONNECTION" == "" ]; then
    echo "📋 This script should be run ON THE SERVER, not locally."
    echo ""
    echo "To deploy:"
    echo "1. First, push your code to GitHub:"
    echo "   git add ."
    echo "   git commit -m 'Deploy to production'"
    echo "   git push origin main"
    echo ""
    echo "2. Then SSH to your server:"
    echo "   ssh $SERVER_USER@$SERVER_IP"
    echo ""
    echo "3. On the server, run:"
    echo "   cd ~"
    echo "   git clone $REPO_URL $PROJECT_DIR"
    echo "   cd $PROJECT_DIR"
    echo "   chmod +x deploy.sh"
    echo "   ./deploy.sh"
    echo ""
    exit 1
fi

# If we're here, we're on the server
echo "✅ Running on server. Starting deployment..."
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found!"
    echo "📝 Creating .env from env.example..."
    cp env.example .env
    echo ""
    echo "⚠️  IMPORTANT: You must edit .env file with your production settings!"
    echo "   Run: nano .env"
    echo ""
    echo "   Required settings:"
    echo "   - SECRET_KEY (generate with: python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')"
    echo "   - DEBUG=False"
    echo "   - ALLOWED_HOSTS=147.182.153.228,your-domain.com"
    echo "   - DB_PASSWORD (strong password)"
    echo "   - Email settings"
    echo ""
    read -p "Press Enter after you've configured .env file..."
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed!"
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
fi

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed!"
    echo "Installing Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

# Run the main deploy script
if [ -f deploy.sh ]; then
    echo "📦 Running main deployment script..."
    chmod +x deploy.sh
    ./deploy.sh
else
    echo "❌ deploy.sh not found!"
    exit 1
fi

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🌍 Your application should be accessible at:"
echo "   - http://$SERVER_IP"
echo "   - Admin: http://$SERVER_IP/whereadmingoeshere"
echo "   - Default credentials: admin/admin123"
echo ""
echo "⚠️  IMPORTANT: Change the admin password immediately!"
echo "   Run: docker-compose exec web python manage.py changepassword admin"
echo ""
