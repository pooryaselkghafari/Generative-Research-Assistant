"""
Encrypted file storage utilities for datasets.
Handles transparent encryption/decryption of dataset files.
"""

import os
import tempfile
from .encryption import get_encryption
from django.conf import settings


def store_encrypted_file(uploaded_file, user_id=None):
    """
    Store an uploaded file in encrypted format.
    
    Args:
        uploaded_file: Django UploadedFile object
        user_id: User ID for user-specific encryption
        
    Returns:
        str: Path to the encrypted file
    """
    # Get encryption instance
    enc = get_encryption()
    
    # Create temporary file for original upload
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        # Write uploaded file to temporary location
        for chunk in uploaded_file.chunks():
            tmp_file.write(chunk)
        tmp_path = tmp_file.name
    
    try:
        # Determine encrypted file path (add .encrypted extension)
        encrypted_path = tmp_path + '.encrypted'
        
        # Encrypt the file
        enc.encrypt_file(tmp_path, encrypted_path, user_id)
        
        return encrypted_path
    finally:
        # Clean up temporary unencrypted file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


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
    original_ext = os.path.splitext(encrypted_path.replace('.encrypted', ''))[1].lower()
    
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
    original_ext = os.path.splitext(encrypted_path.replace('.encrypted', ''))[1]
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
    except Exception as e:
        # Clean up temp file on error
        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except:
                pass
        raise ValueError(f"Failed to decrypt file {encrypted_path}: {e}") from e


