#!/bin/bash

# Fix git pull conflict with docker-compose.yml

set -e

echo "🔧 Fixing git pull conflict..."
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
echo "📁 Project directory: $PROJECT_DIR"
echo ""

# Backup existing docker-compose.yml
if [ -f docker-compose.yml ]; then
    echo "💾 Backing up existing docker-compose.yml..."
    cp docker-compose.yml docker-compose.yml.backup
    echo "✅ Backed up to docker-compose.yml.backup"
    echo ""
fi

# Remove the conflicting file
echo "🗑️  Removing conflicting docker-compose.yml..."
rm -f docker-compose.yml
echo "✅ Removed"
echo ""

# Pull latest changes
echo "⬇️  Pulling latest changes from git..."
git pull origin main
echo ""

# Check if we need to merge any local changes
if [ -f docker-compose.yml.backup ]; then
    echo "📋 Comparing backup with new version..."
    if ! diff -q docker-compose.yml.backup docker-compose.yml > /dev/null 2>&1; then
        echo "⚠️  Your local docker-compose.yml had differences"
        echo "   Backup saved as: docker-compose.yml.backup"
        echo "   New version is now active"
    else
        echo "✅ No differences found"
        rm docker-compose.yml.backup
    fi
fi

echo ""
echo "✅ Git pull complete!"
echo ""
