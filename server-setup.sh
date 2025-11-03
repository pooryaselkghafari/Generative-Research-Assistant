#!/bin/bash

# StatBox DigitalOcean Server Initial Setup Script
# Run this script on a fresh Ubuntu 22.04 server as root

set -e

echo "🚀 Starting StatBox server setup..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Please run as root (use sudo)"
    exit 1
fi

# Update system
echo "📦 Updating system packages..."
export DEBIAN_FRONTEND=noninteractive
# Keep existing configuration files (important for SSH config)
apt update && apt-get upgrade -y -o Dpkg::Options::="--force-confold"

# Install essential packages
echo "📦 Installing essential packages..."
apt install -y \
    curl \
    wget \
    git \
    nano \
    ufw \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release

# Create deploy user
echo "👤 Creating deploy user..."
if id "deploy" &>/dev/null; then
    echo "User 'deploy' already exists, skipping..."
else
    adduser --disabled-password --gecos "" deploy
    usermod -aG sudo deploy
    echo "User 'deploy' created successfully"
fi

# Configure firewall
echo "🔥 Configuring firewall..."
ufw --force enable
ufw allow OpenSSH
ufw allow 80
ufw allow 443
echo "Firewall configured"

# Install Docker
echo "🐳 Installing Docker..."
if command -v docker &> /dev/null; then
    echo "Docker already installed, skipping..."
else
    # Add Docker's official GPG key
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg

    # Add Docker repository
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Install Docker
    apt update
    apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    
    # Add deploy user to docker group
    usermod -aG docker deploy
    
    echo "Docker installed successfully"
fi

# Install Docker Compose (standalone)
echo "🐳 Installing Docker Compose..."
if command -v docker-compose &> /dev/null; then
    echo "Docker Compose already installed, skipping..."
else
    DOCKER_COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d\" -f4)
    curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    echo "Docker Compose installed successfully"
fi

# Install Certbot
echo "🔒 Installing Certbot..."
apt install -y certbot python3-certbot-nginx

# Set up swap file (2GB)
echo "💾 Setting up swap file..."
if [ -f /swapfile ]; then
    echo "Swap file already exists, skipping..."
else
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    echo "Swap file created (2GB)"
fi

# Display system information
echo ""
echo "✅ Server setup complete!"
echo ""
echo "📊 System Information:"
echo "   OS: $(lsb_release -d | cut -f2)"
echo "   Docker: $(docker --version | cut -d' ' -f3 | cut -d',' -f1)"
echo "   Docker Compose: $(docker-compose --version | cut -d' ' -f4 | cut -d',' -f1)"
echo "   Swap: $(free -h | grep Swap | awk '{print $2}')"
echo ""
echo "🔐 Next steps:"
echo "   1. Switch to deploy user: su - deploy"
echo "   2. Clone your repository: git clone <your-repo> statbox"
echo "   3. Configure .env file with your settings"
echo "   4. Run: ./deploy.sh"
echo ""
echo "📖 See DIGITALOCEAN_DEPLOYMENT.md for detailed instructions"
echo ""

