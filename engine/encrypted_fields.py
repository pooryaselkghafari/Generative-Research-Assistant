"""
Encrypted field types for Django models.

Provides encrypted CharField and TextField that automatically
encrypt/decrypt data at rest in the database.
"""
from django.db import models
from django.conf import settings


class EncryptedCharField(models.CharField):
    """
    Encrypted CharField that automatically encrypts data before saving
    and decrypts when reading.
    
    Usage:
        stripe_customer_id = EncryptedCharField(max_length=100, blank=True, null=True)
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize encrypted field."""
        # Store original max_length for decryption
        self._original_max_length = kwargs.get('max_length', 255)
        # Increase max_length to accommodate encrypted data (base64 encoding increases size by ~33%)
        if 'max_length' in kwargs:
            kwargs['max_length'] = int(kwargs['max_length'] * 1.5) + 100  # Add buffer for encryption overhead
        super().__init__(*args, **kwargs)
    
    def from_db_value(self, value, expression, connection):
        """Decrypt value when reading from database."""
        if value is None:
            return value
        
        # Check if encryption is enabled
        if not getattr(settings, 'ENCRYPT_DB_FIELDS', False):
            return value
        
        try:
            from .encryption import get_encryption
            enc = get_encryption()
            # Try to decrypt (if it's encrypted)
            decrypted = enc.decrypt(value)
            return decrypted.decode('utf-8') if isinstance(decrypted, bytes) else decrypted
        except Exception:
            # If decryption fails, assume it's plaintext (for backward compatibility)
            return value
    
    def to_python(self, value):
        """Convert value to Python string."""
        if value is None:
            return value
        if isinstance(value, str):
            return value
        return str(value)
    
    def get_prep_value(self, value):
        """Encrypt value before saving to database."""
        if value is None or value == '':
            return value
        
        # Check if encryption is enabled
        if not getattr(settings, 'ENCRYPT_DB_FIELDS', False):
            return value
        
        # Don't encrypt if already encrypted (check for base64 pattern)
        if isinstance(value, str) and len(value) > 50 and value.replace('+', '').replace('/', '').replace('=', '').isalnum():
            # Might be encrypted, try to decrypt first
            try:
                from .encryption import get_encryption
                enc = get_encryption()
                enc.decrypt(value)  # Test if it's encrypted
                return value  # Already encrypted
            except:
                pass  # Not encrypted, continue to encrypt
        
        # Encrypt the value
        try:
            from .encryption import get_encryption
            enc = get_encryption()
            encrypted = enc.encrypt(value)
            return encrypted
        except Exception as e:
            # If encryption fails, log and return plaintext (shouldn't happen)
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Encryption failed: {e}")
            return value


class EncryptedTextField(models.TextField):
    """
    Encrypted TextField that automatically encrypts data before saving
    and decrypts when reading.
    
    Usage:
        sensitive_data = EncryptedTextField(blank=True, null=True)
    """
    
    def from_db_value(self, value, expression, connection):
        """Decrypt value when reading from database."""
        if value is None:
            return value
        
        # Check if encryption is enabled
        if not getattr(settings, 'ENCRYPT_DB_FIELDS', False):
            return value
        
        try:
            from .encryption import get_encryption
            enc = get_encryption()
            # Try to decrypt (if it's encrypted)
            decrypted = enc.decrypt(value)
            return decrypted.decode('utf-8') if isinstance(decrypted, bytes) else decrypted
        except Exception:
            # If decryption fails, assume it's plaintext (for backward compatibility)
            return value
    
    def to_python(self, value):
        """Convert value to Python string."""
        if value is None:
            return value
        if isinstance(value, str):
            return value
        return str(value)
    
    def get_prep_value(self, value):
        """Encrypt value before saving to database."""
        if value is None or value == '':
            return value
        
        # Check if encryption is enabled
        if not getattr(settings, 'ENCRYPT_DB_FIELDS', False):
            return value
        
        # Don't encrypt if already encrypted (check for base64 pattern)
        if isinstance(value, str) and len(value) > 50 and value.replace('+', '').replace('/', '').replace('=', '').isalnum():
            # Might be encrypted, try to decrypt first
            try:
                from .encryption import get_encryption
                enc = get_encryption()
                enc.decrypt(value)  # Test if it's encrypted
                return value  # Already encrypted
            except:
                pass  # Not encrypted, continue to encrypt
        
        # Encrypt the value
        try:
            from .encryption import get_encryption
            enc = get_encryption()
            encrypted = enc.encrypt(value)
            return encrypted
        except Exception as e:
            # If encryption fails, log and return plaintext (shouldn't happen)
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Encryption failed: {e}")
            return value
