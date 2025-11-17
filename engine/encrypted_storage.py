"""
Encrypted file storage utilities for datasets.
Handles transparent encryption/decryption of dataset files.
"""

import os
import tempfile
from .encryption import get_encryption
from django.conf import settings


def store_encrypted_file(uploaded_file, user_id=None, destination_path=None):
    """
    Store an uploaded file in encrypted format.
    
    Args:
        uploaded_file: Django UploadedFile object
        user_id: User ID for user-specific encryption
        destination_path: Optional destination path (without .encrypted extension)
                          If provided, encrypted file will be saved at destination_path + '.encrypted'
                          If not provided, uses a temporary file location
        
    Returns:
        str: Path to the encrypted file (with .encrypted extension)
    """
    # Get encryption instance
    enc = get_encryption()
    
    # Extract original file extension from uploaded file name
    original_name = uploaded_file.name
    original_ext = os.path.splitext(original_name)[1] if original_name else ''
    
    # Create temporary file for original upload (preserve extension for better debugging)
    if destination_path:
        # Use provided destination path
        tmp_path = destination_path
        encrypted_path = destination_path + '.encrypted'
    else:
        # Use temporary file with original extension
        with tempfile.NamedTemporaryFile(delete=False, suffix=original_ext) as tmp_file:
            tmp_path = tmp_file.name
        encrypted_path = tmp_path + '.encrypted'
    
    try:
        # Write uploaded file to temporary location
        with open(tmp_path, 'wb') as tmp_file:
            for chunk in uploaded_file.chunks():
                tmp_file.write(chunk)
        
        # Get original file size before encryption
        original_size = os.path.getsize(tmp_path) if os.path.exists(tmp_path) else 0
        
        # Encrypt the file
        enc.encrypt_file(tmp_path, encrypted_path, user_id)
        
        # Verify encrypted file was created and has reasonable size
        if not os.path.exists(encrypted_path):
            raise ValueError(f"Encryption failed: encrypted file was not created at {encrypted_path}")
        
        encrypted_size = os.path.getsize(encrypted_path)
        
        # Encrypted file should be at least: salt (16) + nonce (12) + auth tag (16) = 44 bytes minimum
        min_encrypted_size = 44
        if encrypted_size < min_encrypted_size:
            raise ValueError(
                f"Encryption failed: encrypted file is too small ({encrypted_size} bytes). "
                f"Minimum expected: {min_encrypted_size} bytes. File may be corrupted."
            )
        
        # For files larger than 1KB, encrypted size should be roughly original + overhead
        # (salt + nonce + auth tags add overhead, so encrypted should be >= original)
        if original_size > 1024 and encrypted_size < original_size:
            raise ValueError(
                f"Encryption failed: encrypted file ({encrypted_size} bytes) is smaller than "
                f"original ({original_size} bytes). This should not happen."
            )
        
        return encrypted_path
    finally:
        # Clean up temporary unencrypted file
        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


def read_encrypted_file(encrypted_path, user_id=None, as_dataframe=True, **kwargs):
    """
    Read and decrypt an encrypted dataset file.
    
    Args:
        encrypted_path: Path to encrypted file
        user_id: User ID for decryption
        as_dataframe: If True, return pandas DataFrame; if False, return file path
        **kwargs: Additional arguments passed to pandas read functions
        
    Returns:
        pandas.DataFrame or str: Decrypted data or path to decrypted file
    """
    import pandas as pd
    
    # Get encryption instance
    enc = get_encryption()
    
    # Determine file type from original path BEFORE creating temp file
    # Remove .encrypted extension to get original extension
    path_without_encrypted = encrypted_path.replace('.encrypted', '')
    original_ext = os.path.splitext(path_without_encrypted)[1].lower()
    
    # Create temporary file with correct extension for proper format detection
    # Use original extension so pandas can detect the format correctly
    suffix = original_ext if original_ext else '.csv'
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
        tmp_path = tmp_file.name
    
    try:
        # Decrypt the file
        enc.decrypt_file(encrypted_path, tmp_path, user_id)
        
        if as_dataframe:
            
            # Read as DataFrame based on extension
            if original_ext in ['.xlsx', '.xlsm']:
                df = pd.read_excel(tmp_path, engine='openpyxl', **kwargs)
            elif original_ext == '.xls':
                # Try openpyxl first, then xlrd for legacy .xls files
                try:
                    df = pd.read_excel(tmp_path, engine='openpyxl', **kwargs)
                except Exception:
                    df = pd.read_excel(tmp_path, engine='xlrd', **kwargs)
            elif original_ext == '.csv' or original_ext == '':
                df = pd.read_csv(tmp_path, **kwargs)
            else:
                # Try CSV first, then Excel
                try:
                    df = pd.read_csv(tmp_path, **kwargs)
                except:
                    # Try Excel with openpyxl engine
                    try:
                        df = pd.read_excel(tmp_path, engine='openpyxl', **kwargs)
                    except Exception:
                        df = pd.read_excel(tmp_path, engine='xlrd', **kwargs)
            
            return df
        else:
            return tmp_path
    finally:
        # Clean up temporary decrypted file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def is_encrypted_file(file_path):
    """Check if a file is encrypted (has .encrypted extension)."""
    return file_path.endswith('.encrypted')


def get_decrypted_path(encrypted_path, user_id=None):
    """
    Get a temporary decrypted file path for processing.
    WARNING: This creates a temporary file that must be cleaned up by caller.
    
    Args:
        encrypted_path: Path to encrypted file
        user_id: User ID for decryption
        
    Returns:
        str: Path to temporary decrypted file
        
    Raises:
        FileNotFoundError: If encrypted file doesn't exist
        ValueError: If decryption fails
    """
    if not os.path.exists(encrypted_path):
        raise FileNotFoundError(f"Encrypted file not found: {encrypted_path}")
    
    enc = get_encryption()
    
    # Create temporary file with correct extension
    # Remove .encrypted extension to get original extension
    path_without_encrypted = encrypted_path.replace('.encrypted', '')
    original_ext = os.path.splitext(path_without_encrypted)[1]
    if not original_ext:
        # Default to .csv if no extension found
        original_ext = '.csv'
    with tempfile.NamedTemporaryFile(delete=False, suffix=original_ext) as tmp_file:
        tmp_path = tmp_file.name
    
    try:
        # Decrypt to temporary location
        enc.decrypt_file(encrypted_path, tmp_path, user_id)
        
        # Verify decrypted file exists and has content
        if not os.path.exists(tmp_path):
            raise ValueError("Decryption failed: output file was not created")
        if os.path.getsize(tmp_path) == 0:
            raise ValueError("Decryption failed: output file is empty")
        
        return tmp_path
    except FileNotFoundError as e:
        # Clean up temp file on error
        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except:
                pass
        raise FileNotFoundError(f"Encrypted file not found: {encrypted_path}") from e
    except Exception as e:
        # Clean up temp file on error
        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except:
                pass
        # Provide more context about the error
        error_msg = str(e)
        if "InvalidTag" in str(type(e).__name__) or "decryption" in error_msg.lower():
            raise ValueError(
                f"Failed to decrypt file {encrypted_path}. "
                f"This usually means: (1) wrong encryption key (check ENCRYPTION_KEY in .env), "
                f"(2) wrong user_id (file was encrypted with different user), "
                f"or (3) file is corrupted. Original error: {error_msg}"
            ) from e
        else:
            raise ValueError(f"Failed to decrypt file {encrypted_path}: {error_msg}") from e


