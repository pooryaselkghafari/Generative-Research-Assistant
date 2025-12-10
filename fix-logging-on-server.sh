#!/bin/bash

# Quick fix for logging error on server
# This script fixes the settings.py file directly on the server

echo "🔧 Fixing logging configuration in settings.py..."
echo ""

SETTINGS_FILE="statbox/settings.py"

if [ ! -f "$SETTINGS_FILE" ]; then
    echo "❌ Error: $SETTINGS_FILE not found!"
    echo "   Make sure you're in the project root directory"
    exit 1
fi

# Backup original file
cp "$SETTINGS_FILE" "${SETTINGS_FILE}.backup"
echo "✅ Created backup: ${SETTINGS_FILE}.backup"

# Check if fix is already applied
if grep -q "can_write_logs = False" "$SETTINGS_FILE"; then
    echo "✅ Logging fix already applied in settings.py"
    echo "   The issue might be permissions. Fixing logs directory..."
    mkdir -p logs
    chmod 755 logs
    touch logs/django.log 2>/dev/null && chmod 644 logs/django.log || echo "⚠️  Could not create django.log"
    exit 0
fi

echo "📝 Applying logging fix..."

# Create a Python script to fix the settings
python3 << 'PYTHON_SCRIPT'
import re

settings_file = "statbox/settings.py"

with open(settings_file, 'r') as f:
    content = f.read()

# Check if already fixed
if "can_write_logs = False" in content:
    print("✅ Fix already applied")
    exit(0)

# Find the LOGGING configuration section
# We need to find where LOGGING is defined and modify it

# Pattern 1: Find the LOGGING dict definition
logging_pattern = r"(# Logging Configuration.*?LOGGING = \{.*?'handlers': \{.*?'file': \{.*?\},)"

# Try to find and replace the file handler references
# First, let's add the permission check before LOGGING

# Find where LOGGING starts
logging_start = content.find("# Logging Configuration")
if logging_start == -1:
    logging_start = content.find("LOGGING = {")

if logging_start == -1:
    print("❌ Could not find LOGGING configuration")
    exit(1)

# Insert permission check before LOGGING
permission_check = """# Ensure logs directory exists and check permissions BEFORE configuring logging
import os
logs_dir = BASE_DIR / 'logs'
logs_file = logs_dir / 'django.log'
can_write_logs = False

try:
    os.makedirs(logs_dir, exist_ok=True)
    # Test if we can write to the logs directory by trying to create a test file
    test_file = logs_dir / '.test_write'
    try:
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        can_write_logs = True
    except (PermissionError, OSError):
        can_write_logs = False
except (PermissionError, OSError):
    can_write_logs = False

# Logging Configuration (conditional based on write permissions)
"""

# Check if permission check already exists
if "can_write_logs = False" not in content:
    # Insert before LOGGING
    content = content[:logging_start] + permission_check + content[logging_start:]

# Now modify LOGGING to conditionally include file handler
# Remove 'file' from handlers dict initially
content = re.sub(
    r"'handlers': \{(\s*)'file': \{.*?\},(\s*)'console':",
    r"'handlers': {\1'console':",
    content,
    flags=re.DOTALL
)

# Remove 'file' from root handlers
content = re.sub(
    r"'handlers': \[.*?'file'.*?\]",
    r"'handlers': ['console']",
    content
)

# Remove 'file' from logger handlers
content = re.sub(
    r"'handlers': \[.*?'file'.*?\]",
    r"'handlers': ['console']",
    content
)

# Add conditional file handler after LOGGING dict closes
logging_end = content.find("}", content.find("LOGGING = {"))
if logging_end != -1:
    # Find the closing brace of LOGGING dict
    brace_count = 0
    start_pos = content.find("LOGGING = {")
    pos = start_pos
    while pos < len(content) and brace_count >= 0:
        if content[pos] == '{':
            brace_count += 1
        elif content[pos] == '}':
            brace_count -= 1
            if brace_count == 0:
                logging_end = pos
                break
        pos += 1
    
    # Insert conditional file handler code after LOGGING
    conditional_handler = """
# Only add file handler if we can write to logs directory
if can_write_logs:
    LOGGING['handlers']['file'] = {
        'level': 'INFO',
        'class': 'logging.FileHandler',
        'filename': str(logs_file),
        'formatter': 'verbose',
    }
    # Add file handler to root and loggers
    LOGGING['root']['handlers'].append('file')
    for logger_name in ['django', 'engine', 'accounts']:
        if logger_name in LOGGING['loggers']:
            LOGGING['loggers'][logger_name]['handlers'].append('file')
"""
    
    # Insert after the closing brace of LOGGING
    insert_pos = content.find('\n', logging_end) + 1
    content = content[:insert_pos] + conditional_handler + content[insert_pos:]

# Write back
with open(settings_file, 'w') as f:
    f.write(content)

print("✅ Settings.py updated successfully")
PYTHON_SCRIPT

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Logging configuration fixed!"
    echo ""
    echo "📋 Next steps:"
    echo "1. Fix logs directory permissions:"
    echo "   mkdir -p logs && chmod 755 logs"
    echo ""
    echo "2. Restart web container:"
    echo "   docker-compose restart web"
    echo ""
    echo "3. Check if it's working:"
    echo "   docker-compose logs --tail=20 web"
    echo "   curl http://localhost:8000/health/"
else
    echo ""
    echo "⚠️  Automatic fix failed. Applying manual fix..."
    echo ""
    echo "Please manually edit statbox/settings.py and:"
    echo "1. Find the LOGGING configuration"
    echo "2. Remove 'file' from all handlers lists"
    echo "3. Or run: ./fix-logs-permission.sh to fix permissions instead"
fi
