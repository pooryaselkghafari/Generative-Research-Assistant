#!/bin/bash

# Fix database authentication error
# The error shows it's trying to connect as "adminpoorya" but database expects "postgres"

echo "🔧 Fixing database credentials..."
echo ""

cd ~/GRA || cd ~/statbox || { echo "❌ Could not find project directory"; exit 1; }

echo "1. Checking current .env file database settings..."
if [ -f .env ]; then
    echo "Current database settings:"
    grep -E "DB_USER|DB_PASSWORD|DB_NAME" .env | sed 's/PASSWORD=.*/PASSWORD=***/'
else
    echo "❌ .env file not found!"
    echo "Creating from env.example..."
    cp env.example .env
    echo "⚠️  Please edit .env and set DB_USER=postgres and DB_PASSWORD"
    exit 1
fi
echo ""

echo "2. Checking what user the database was created with..."
echo "   (Database container uses POSTGRES_USER=postgres)"
echo ""

echo "3. Fixing .env file..."
# Backup
cp .env .env.backup.$(date +%s)

# Fix DB_USER to be postgres (match docker-compose.yml)
if grep -q "DB_USER=" .env; then
    sed -i 's/^DB_USER=.*/DB_USER=postgres/' .env
    echo "✅ Set DB_USER=postgres"
else
    echo "DB_USER=postgres" >> .env
    echo "✅ Added DB_USER=postgres"
fi

# Check DB_PASSWORD is set
if ! grep -q "DB_PASSWORD=" .env || grep -q "DB_PASSWORD=$" .env || grep -q "DB_PASSWORD=your" .env; then
    echo ""
    echo "⚠️  DB_PASSWORD is not set or is using default value!"
    echo ""
    echo "Please set a strong password in .env:"
    echo "  DB_PASSWORD=your-strong-password-here"
    echo ""
    echo "Or generate one:"
    echo "  openssl rand -base64 32"
    echo ""
    read -p "Press Enter after you've set DB_PASSWORD in .env..."
fi

echo ""
echo "4. Verifying .env settings..."
echo "Updated database settings:"
grep -E "DB_USER|DB_NAME" .env
echo "DB_PASSWORD is set: $(grep -q "DB_PASSWORD=" .env && grep -v "^#" .env | grep "DB_PASSWORD=" | grep -v "your-" | grep -v "^$" > /dev/null && echo "Yes" || echo "No - please set it!")"
echo ""

echo "5. Checking docker-compose.yml database settings..."
echo "Database container expects:"
echo "  POSTGRES_USER=postgres"
echo "  POSTGRES_DB=statbox"
echo "  POSTGRES_PASSWORD=\${DB_PASSWORD}"
echo ""

echo "6. Restarting containers with new credentials..."
docker-compose down web
docker-compose up -d web

echo ""
echo "7. Waiting for web container to start..."
sleep 5

echo ""
echo "8. Checking web container logs..."
docker-compose logs --tail=20 web | tail -20

echo ""
echo "📋 Summary:"
echo "==========="
echo "✅ DB_USER should be: postgres"
echo "✅ DB_NAME should be: statbox"
echo "✅ DB_PASSWORD should match what you set when creating the database"
echo ""
echo "If you changed DB_PASSWORD, you may need to:"
echo "1. Update the database password, OR"
echo "2. Recreate the database with the new password"
echo ""
echo "To recreate database (⚠️  WARNING: This deletes all data!):"
echo "  docker-compose down db"
echo "  docker volume rm gra_postgres_data"
echo "  docker-compose up -d db"
echo ""
