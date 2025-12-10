#!/bin/bash

# Fix Port 80 Already in Use Error for Certbot
# This script identifies and stops the process using port 80

echo "🔍 Checking what's using port 80..."
echo ""

# Method 1: Check with lsof
echo "Method 1: Using lsof"
echo "-------------------"
if command -v lsof &> /dev/null; then
    sudo lsof -i :80
else
    echo "lsof not installed, trying alternative methods..."
fi
echo ""

# Method 2: Check with ss
echo "Method 2: Using ss"
echo "------------------"
if command -v ss &> /dev/null; then
    sudo ss -tulpn | grep :80
else
    echo "ss not installed"
fi
echo ""

# Method 3: Check with netstat
echo "Method 3: Using netstat"
echo "-----------------------"
if command -v netstat &> /dev/null; then
    sudo netstat -tulpn | grep :80
else
    echo "netstat not installed"
fi
echo ""

# Check for common services
echo "🔍 Checking for common services..."
echo ""

# Check Apache
if systemctl is-active --quiet apache2 2>/dev/null; then
    echo "⚠️  Apache is running!"
    echo "   Stopping Apache..."
    sudo systemctl stop apache2
    sudo systemctl disable apache2
    echo "✅ Apache stopped and disabled"
else
    echo "✅ Apache is not running"
fi
echo ""

# Check Nginx (on host, not Docker)
if systemctl is-active --quiet nginx 2>/dev/null; then
    echo "⚠️  Nginx (host service) is running!"
    echo "   Stopping Nginx..."
    sudo systemctl stop nginx
    sudo systemctl disable nginx
    echo "✅ Nginx stopped and disabled"
else
    echo "✅ Nginx (host service) is not running"
fi
echo ""

# Check Docker containers
echo "🐳 Checking Docker containers..."
if command -v docker &> /dev/null; then
    echo "Running containers:"
    docker ps --format "table {{.Names}}\t{{.Ports}}" | grep -E "80|NAME"
    
    # Check if nginx container is running
    if docker ps | grep -q nginx; then
        echo ""
        echo "⚠️  Nginx Docker container is running!"
        echo "   Stopping nginx container..."
        docker stop nginx 2>/dev/null || docker-compose stop nginx 2>/dev/null
        echo "✅ Nginx container stopped"
    fi
else
    echo "Docker not found"
fi
echo ""

# Final check - verify port 80 is free
echo "🔍 Final check - verifying port 80 is free..."
echo ""

if sudo lsof -i :80 2>/dev/null | grep -q LISTEN; then
    echo "❌ Port 80 is still in use!"
    echo ""
    echo "Process details:"
    sudo lsof -i :80
    echo ""
    echo "To manually stop the process:"
    echo "1. Find the PID from above"
    echo "2. Run: sudo kill <PID>"
    echo "   Or: sudo kill -9 <PID> (force kill)"
else
    echo "✅ Port 80 is now free!"
    echo ""
    echo "You can now run certbot:"
    echo "sudo certbot certonly --standalone -d generativera.com -d www.generativera.com"
fi
