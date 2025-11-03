# Quick Encryption Setup Guide

## One-Time Setup (Do This Once)

### 1. Generate Your Encryption Key

Run this command **ONCE** when you first set up the application:

```bash
python manage.py generate_encryption_key
```

**Output will look like:**
```
============================================================
ENCRYPTION KEY GENERATED
============================================================
aBc123XyZ789... (long base64 string)
```

### 2. Save It to Your .env File

Copy the generated key and add it to your `.env` file:

```bash
# .env file
ENCRYPTION_KEY=aBc123XyZ789...your-generated-key-here
ENCRYPT_DATASETS=False  # Set to True when ready to enable encryption
```

### 3. That's It!

✅ **You're done!** The app will automatically use this key for all encryption/decryption.

## Important Notes

### ❌ DON'T Do This:
- Generate a new key each time you run the app
- Change the key after you have encrypted data (you'll lose access!)
- Commit the key to git/version control

### ✅ DO This:
- Generate once and reuse
- Store the key securely (environment variable, secrets manager)
- Back up the key in a secure location
- Use the same key across all environments (dev/staging/prod) OR use different keys per environment (but keep them consistent)

## Development vs Production

### Development (Local Testing)
```bash
# Optional: Disable encryption for faster development
ENCRYPT_DATASETS=False
```

### Production
```bash
# Enable encryption
ENCRYPT_DATASETS=True
ENCRYPTION_KEY=your-production-key
```

## What Happens Automatically

Once configured:
- ✅ Files are encrypted when uploaded (if `ENCRYPT_DATASETS=True`)
- ✅ Files are decrypted automatically when accessed
- ✅ No code changes needed - it's transparent!

## If You Lose Your Key

⚠️ **Warning**: If you lose your encryption key, you **cannot** decrypt your data. 

**Prevention**:
- Store key in multiple secure locations
- Use a password manager
- Use cloud secrets manager (AWS Secrets Manager, etc.)
- Document key location in secure team documentation

## Testing Encryption

To test that encryption works:

```bash
# 1. Enable encryption
ENCRYPT_DATASETS=True

# 2. Upload a test dataset

# 3. Check that file on disk is encrypted (look for .encrypted extension)

# 4. Verify you can still access/read the dataset normally
```

---

**TL;DR**: Generate the key once, save it to `.env`, and forget about it. The app handles everything automatically!


