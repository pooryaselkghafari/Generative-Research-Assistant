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
    
    # Create temporary file for decrypted data
    with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp_file:
        tmp_path = tmp_file.name
    
    try:
        # Decrypt the file
        enc.decrypt_file(encrypted_path, tmp_path, user_id)
        
        if as_dataframe:
            # Determine file type from original path
            original_ext = os.path.splitext(encrypted_path.replace('.encrypted', ''))[1].lower()
            
            # Read as DataFrame based on extension
            if original_ext in ['.xlsx', '.xls', '.xlsm']:
                df = pd.read_excel(tmp_path, **kwargs)
            elif original_ext == '.csv' or original_ext == '':
                df = pd.read_csv(tmp_path, **kwargs)
            else:
                # Try CSV first, then Excel
                try:
                    df = pd.read_csv(tmp_path, **kwargs)
                except:
                    df = pd.read_excel(tmp_path, **kwargs)
            
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
    """
    enc = get_encryption()
    
    # Create temporary file
    original_ext = os.path.splitext(encrypted_path.replace('.encrypted', ''))[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=original_ext) as tmp_file:
        tmp_path = tmp_file.name
    
    # Decrypt to temporary location
    enc.decrypt_file(encrypted_path, tmp_path, user_id)
    
    return tmp_path


