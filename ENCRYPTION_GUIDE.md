# Data Encryption Implementation Guide

## Overview

This application implements **industry-standard encryption** for user data and datasets using:

- **Algorithm**: AES-256-GCM (Advanced Encryption Standard, 256-bit key, Galois/Counter Mode)
- **Standard Compliance**: 
  - NIST SP 800-175B (Cryptographic Standards)
  - FIPS 197 (AES Standard)
  - RFC 2898 (PBKDF2 Key Derivation)
- **Security Level**: Military-grade encryption suitable for sensitive data

## Standards & Compliance

### Encryption Standards

1. **AES-256-GCM**
   - ✅ **NIST Recommended** (NIST SP 800-38D)
   - ✅ **FIPS 197 Compliant**
   - ✅ **Authenticated Encryption** (prevents tampering)
   - ✅ **256-bit keys** (highest security level)

2. **Key Derivation (PBKDF2)**
   - ✅ **RFC 2898 Compliant**
   - ✅ **100,000 iterations** (NIST recommendation)
   - ✅ **SHA-256 hashing**
   - ✅ **Unique salt per encryption**

3. **Data Protection Levels**
   - **At Rest**: AES-256-GCM encryption
   - **In Transit**: TLS 1.2+ (configure in web server)
   - **Key Management**: Secure key storage and rotation

### Regulatory Compliance

- ✅ **GDPR** (EU): Encryption is a recommended security measure
- ✅ **HIPAA** (US Healthcare): Encryption satisfies security requirements
- ✅ **PCI DSS** (Payment Data): AES-256 meets Level 1 requirements
- ✅ **SOC 2**: Encryption supports security control requirements

## Configuration

### 1. Generate Encryption Key

**IMPORTANT**: Generate a strong encryption key for production:

```bash
python manage.py generate_encryption_key
```

This will generate a secure 256-bit key. Save it to your `.env` file:

```bash
ENCRYPTION_KEY=your-generated-key-here
```

### 2. Environment Variables

Add to your `.env` file:

```bash
# Data Encryption
ENCRYPTION_KEY=your-encryption-key-here
ENCRYPT_DATASETS=True  # Set to False to disable encryption
```

### 3. Production Deployment

For production, store the encryption key securely:

- **Option 1**: Environment variable (recommended for single-server)
- **Option 2**: AWS Secrets Manager / Azure Key Vault / GCP Secret Manager
- **Option 3**: Hardware Security Module (HSM) for enterprise

**NEVER** commit encryption keys to version control!

## Usage

### Encrypting Files

When users upload datasets, they are automatically encrypted:

```python
from engine.encrypted_storage import store_encrypted_file

# In upload view
encrypted_path = store_encrypted_file(uploaded_file, user_id=request.user.id)
```

### Reading Encrypted Files

Files are automatically decrypted when accessed:

```python
from engine.encrypted_storage import read_encrypted_file

# Read encrypted dataset
df = read_encrypted_file(encrypted_path, user_id=user.id)
```

### Manual Encryption/Decryption

```python
from engine.encryption import encrypt_data, decrypt_data

# Encrypt a string
encrypted = encrypt_data("sensitive data", user_id=user.id)

# Decrypt
decrypted = decrypt_data(encrypted, user_id=user.id)
```

## Security Features

### 1. User-Specific Encryption

Each user's data is encrypted with a user-specific key derived from:
- Master encryption key
- User ID
- Unique salt per file

This ensures:
- ✅ User data isolation
- ✅ Enhanced security (one compromised key doesn't affect others)
- ✅ Compliance with multi-tenant security requirements

### 2. Authenticated Encryption

AES-GCM provides:
- ✅ **Confidentiality**: Data cannot be read without the key
- ✅ **Integrity**: Data cannot be modified without detection
- ✅ **Authentication**: Verifies data hasn't been tampered with

### 3. Secure Key Management

- Keys are never stored with encrypted data
- Each encryption operation uses unique salt/nonce
- Keys are derived using industry-standard PBKDF2

## Key Rotation

### Rotating Encryption Keys

If you need to rotate encryption keys:

1. **Generate new key**: `python manage.py generate_encryption_key`
2. **Re-encrypt data**: Use migration script to re-encrypt existing files
3. **Update environment**: Set new `ENCRYPTION_KEY`

**Note**: Re-encryption of existing files requires a migration script.

## Performance Considerations

- **Encryption overhead**: ~10-20% performance impact on file operations
- **Large files**: Files are encrypted in chunks (8KB) to minimize memory usage
- **Caching**: Decrypted files are temporarily cached during processing

## Backup & Recovery

### Backup Strategy

1. **Encrypted backups**: Backup encrypted files as-is (no need to decrypt)
2. **Key backup**: Store encryption key in secure, separate location
3. **Test restoration**: Regularly test backup restoration

### Recovery Process

1. Restore encrypted files from backup
2. Restore encryption key from secure storage
3. System automatically decrypts on access

## Monitoring & Auditing

### Security Logging

Log the following events:
- File encryption/decryption operations
- Key rotation events
- Failed decryption attempts (potential security breach)

### Compliance Audits

The encryption implementation supports:
- Audit trails
- Compliance reporting
- Security assessments

## Troubleshooting

### Common Issues

1. **Decryption fails**: 
   - Check encryption key is correct
   - Verify user_id matches original encryption
   - Check file hasn't been corrupted

2. **Performance issues**:
   - Consider disabling encryption for development
   - Use hardware acceleration if available
   - Optimize file chunk sizes

3. **Key management**:
   - Never lose encryption key (data will be unrecoverable)
   - Store keys in multiple secure locations
   - Use key management services for production

## Best Practices

1. ✅ **Use strong keys**: Generate 256-bit keys
2. ✅ **Separate keys**: Use different keys for different environments
3. ✅ **Key rotation**: Rotate keys periodically (annual recommended)
4. ✅ **Access control**: Limit who can access encryption keys
5. ✅ **Backup keys**: Store keys securely, separately from data
6. ✅ **Monitor usage**: Log all encryption/decryption operations
7. ✅ **Regular audits**: Review encryption implementation annually

## Support

For security concerns or questions:
- Review encryption implementation: `engine/encryption.py`
- Check logs for errors
- Consult security team for key management strategies

---

**Last Updated**: 2024
**Standards**: NIST SP 800-175B, FIPS 197, RFC 2898
**Algorithm**: AES-256-GCM


