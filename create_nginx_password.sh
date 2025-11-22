#!/bin/bash
# Script to create Nginx basic auth password file
# Usage: ./create_nginx_password.sh [username]

set -e

USERNAME=${1:-admin}
PASSWORD_FILE="/etc/nginx/.htpasswd"

echo "Creating Nginx basic authentication password file..."
echo "Username: $USERNAME"
echo ""

# Check if htpasswd is available
if command -v htpasswd &> /dev/null; then
    echo "Using htpasswd..."
    if [ -f "$PASSWORD_FILE" ]; then
        echo "Password file exists. Adding/updating user..."
        sudo htpasswd "$PASSWORD_FILE" "$USERNAME"
    else
        echo "Creating new password file..."
        sudo htpasswd -c "$PASSWORD_FILE" "$USERNAME"
    fi
elif command -v openssl &> /dev/null; then
    echo "htpasswd not found. Using OpenSSL instead..."
    read -sp "Enter password for $USERNAME: " PASSWORD
    echo ""
    read -sp "Confirm password: " PASSWORD_CONFIRM
    echo ""
    
    if [ "$PASSWORD" != "$PASSWORD_CONFIRM" ]; then
        echo "Error: Passwords do not match!"
        exit 1
    fi
    
    if [ -f "$PASSWORD_FILE" ]; then
        echo "Password file exists. Appending user..."
        echo "$USERNAME:$(openssl passwd -apr1 "$PASSWORD")" | sudo tee -a "$PASSWORD_FILE"
    else
        echo "Creating new password file..."
        echo "$USERNAME:$(openssl passwd -apr1 "$PASSWORD")" | sudo tee "$PASSWORD_FILE"
    fi
else
    echo "Error: Neither htpasswd nor openssl is available!"
    echo "Please install one of them:"
    echo "  sudo apt install apache2-utils  # For htpasswd"
    echo "  sudo apt install openssl         # For openssl"
    exit 1
fi

# Set proper permissions
echo ""
echo "Setting file permissions..."
sudo chmod 600 "$PASSWORD_FILE"
sudo chown www-data:www-data "$PASSWORD_FILE" 2>/dev/null || sudo chown nginx:nginx "$PASSWORD_FILE" 2>/dev/null || true

echo ""
echo "✓ Password file created successfully at $PASSWORD_FILE"
echo ""
echo "Next steps:"
echo "1. Restart Nginx: sudo systemctl restart nginx"
echo "2. Or if using Docker: docker-compose restart nginx"
echo "3. Test access: https://yourdomain.com/whereadmingoeshere/"

