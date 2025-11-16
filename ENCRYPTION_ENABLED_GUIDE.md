# Encryption Setup Guide

## ✅ Encryption Now Enabled

Your application now has encryption capabilities for both **files** and **sensitive database fields**.

## What's Encrypted

### 1. **Database Fields** (Automatic)
The following sensitive fields are now encrypted at rest:
- `UserProfile.stripe_customer_id` - Stripe customer IDs
- `UserProfile.stripe_subscription_id` - Stripe subscription IDs  
- `Payment.stripe_payment_intent_id` - Stripe payment intent IDs

These fields automatically encrypt/decrypt when saving/reading from the database.

### 2. **Uploaded Files** (Configurable)
Dataset files can be encrypted when uploaded. Controlled by `ENCRYPT_DATASETS` setting.

## Setup Instructions

### Step 1: Generate Encryption Key

**IMPORTANT**: Do this once and save the key securely!

```bash
python manage.py generate_encryption_key
```

This will output a long base64-encoded key. Copy it.

### Step 2: Configure Environment Variables

Add to your `.env` file:

```bash
# Encryption Key (REQUIRED for database field encryption)
ENCRYPTION_KEY=your-generated-key-here

# File Encryption (optional, defaults to False)
ENCRYPT_DATASETS=True  # Set to True to encrypt uploaded files
```

### Step 3: Database Migration

Since we added encrypted fields, you need to create and run a migration:

```bash
python manage.py makemigrations
python manage.py migrate
```

**Note**: Existing data in `stripe_customer_id`, `stripe_subscription_id`, and `stripe_payment_intent_id` will remain plaintext until you re-save those records (they'll be encrypted on next save).

## How It Works

### Database Field Encryption

- **Automatic**: Fields using `EncryptedCharField` or `EncryptedTextField` automatically encrypt on save and decrypt on read
- **Transparent**: Your code doesn't need to change - encryption happens at the model level
- **Backward Compatible**: If encryption is disabled, fields work as normal CharField/TextField

### File Encryption

- **Conditional**: Only encrypts if `ENCRYPT_DATASETS=True`
- **User-Specific**: Each user's files are encrypted with a user-specific key
- **Automatic**: Files are encrypted on upload and decrypted when accessed

## Security Features

✅ **AES-256-GCM** encryption (military-grade)
✅ **PBKDF2** key derivation (100,000 iterations)
✅ **User-specific keys** for file encryption
✅ **Authenticated encryption** (prevents tampering)
✅ **Automatic encryption/decryption** (no code changes needed)

## Privacy Compliance

This encryption implementation helps with:
- ✅ **PIPEDA** (Canada) - Encryption of personal information
- ✅ **CCPA/CPRA** (USA) - Protection of sensitive data
- ✅ **HIPAA** (USA) - Encryption requirements for health data
- ✅ **GDPR** (EU) - Encryption as security measure

## Testing

To test encryption:

```python
from engine.models import UserProfile
from django.contrib.auth.models import User

# Create a user profile with encrypted field
user = User.objects.get(username='testuser')
profile = UserProfile.objects.get(user=user)
profile.stripe_customer_id = "cus_test123"
profile.save()

# Read it back - should be automatically decrypted
print(profile.stripe_customer_id)  # Should print "cus_test123"
```

## Troubleshooting

### "Encryption failed" errors
- Make sure `ENCRYPTION_KEY` is set in your `.env` file
- Verify the key is the same one you generated (don't regenerate!)

### Existing data not encrypted
- Existing records will be encrypted on next save
- To encrypt all existing data, create a data migration script

### Files not encrypting
- Check `ENCRYPT_DATASETS=True` in your `.env` file
- Restart your Django server after changing settings

## Production Checklist

- [ ] Generate encryption key: `python manage.py generate_encryption_key`
- [ ] Add `ENCRYPTION_KEY` to `.env` file
- [ ] Set `ENCRYPT_DATASETS=True` for production
- [ ] Store encryption key securely (password manager, secrets manager)
- [ ] Run migrations: `python manage.py migrate`
- [ ] Test encryption with a sample record
- [ ] Backup encryption key in secure location

## Important Notes

⚠️ **DO NOT**:
- Regenerate the encryption key after you have encrypted data
- Commit the encryption key to version control
- Share the encryption key publicly

✅ **DO**:
- Store the key securely
- Use the same key across environments (or document which key is used where)
- Back up the key in multiple secure locations
- Test encryption before deploying to production

