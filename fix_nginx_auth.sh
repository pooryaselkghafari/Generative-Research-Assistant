#!/bin/bash
# Script to fix Nginx basic auth for admin

set -e

PASSWORD_FILE="/etc/nginx/.htpasswd"
ADMIN_PATH="whereadmingoeshere"

echo "=========================================="
echo "NGINX BASIC AUTH SETUP"
echo "=========================================="
echo ""

# Check if password file exists
if [ -f "$PASSWORD_FILE" ]; then
    echo "✓ Password file exists at $PASSWORD_FILE"
    echo ""
    echo "Current users in password file:"
    cut -d: -f1 "$PASSWORD_FILE" 2>/dev/null || echo "  (could not read file)"
    echo ""
    read -p "Do you want to add/update a user? (y/n): " update
    if [ "$update" != "y" ]; then
        echo "Skipping password file update."
        exit 0
    fi
fi

# Get username
read -p "Enter username for Nginx basic auth [admin]: " username
username=${username:-admin}

# Get password
read -sp "Enter password for $username: " password
echo ""
read -sp "Confirm password: " password_confirm
echo ""

if [ "$password" != "$password_confirm" ]; then
    echo "Error: Passwords do not match!"
    exit 1
fi

# Create password file
echo ""
echo "Creating password file..."

if command -v htpasswd &> /dev/null; then
    echo "Using htpasswd..."
    if [ -f "$PASSWORD_FILE" ]; then
        echo "$password" | sudo htpasswd -i "$PASSWORD_FILE" "$username"
    else
        echo "$password" | sudo htpasswd -ci "$PASSWORD_FILE" "$username"
    fi
elif command -v openssl &> /dev/null; then
    echo "Using OpenSSL..."
    if [ -f "$PASSWORD_FILE" ]; then
        echo "$username:$(openssl passwd -apr1 "$password")" | sudo tee -a "$PASSWORD_FILE" > /dev/null
    else
        echo "$username:$(openssl passwd -apr1 "$password")" | sudo tee "$PASSWORD_FILE" > /dev/null
    fi
else
    echo "Error: Neither htpasswd nor openssl is available!"
    exit 1
fi

# Set permissions
echo "Setting file permissions..."
sudo chmod 600 "$PASSWORD_FILE"
sudo chown www-data:www-data "$PASSWORD_FILE" 2>/dev/null || \
sudo chown nginx:nginx "$PASSWORD_FILE" 2>/dev/null || true

echo ""
echo "✓ Password file created/updated successfully!"
echo ""
echo "Next steps:"
echo "1. Restart Nginx: sudo systemctl restart nginx"
echo "   Or if using Docker: docker-compose restart nginx"
echo "2. Test access: https://yourdomain.com/$ADMIN_PATH/?token=YOUR_TOKEN"
echo "3. You'll be prompted for:"
echo "   - Nginx Basic Auth: username=$username, password=(what you just set)"
echo "   - Django Admin: your Django superuser credentials"

