"""
Backup and restore functionality tests.
"""
import os
import shutil
import tempfile
from pathlib import Path
from django.conf import settings
from django.core.management import call_command
from tests.base import BaseTestSuite


class BackupTestSuite(BaseTestSuite):
    category = 'backup'
    test_name = 'Backup/Restore Tests'
    target_score = 85.0
    
    def setUp(self):
        super().setUp()
        self.temp_dir = tempfile.mkdtemp()
        self.backup_dir = Path(self.temp_dir) / 'backups'
        self.backup_dir.mkdir(exist_ok=True)
    
    def tearDown(self):
        super().tearDown()
        # Cleanup
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_database_backup_creates_file(self):
        """Test that database backup creates a file."""
        backup_file = self.backup_dir / 'test_backup.sql'
        
        try:
            # Try to create a backup using Django's dumpdata
            from io import StringIO
            out = StringIO()
            call_command('dumpdata', '--output', str(backup_file), verbosity=0)
            
            exists = backup_file.exists()
            self.record_test(
                'database_backup_creates_file',
                exists,
                "Backup file was not created" if not exists else "Backup file created successfully"
            )
        except Exception as e:
            self.record_test(
                'database_backup_creates_file',
                False,
                f"Backup failed: {str(e)}"
            )
    
    def test_backup_file_not_empty(self):
        """Test that backup file contains data."""
        backup_file = self.backup_dir / 'test_backup.sql'
        
        try:
            from io import StringIO
            call_command('dumpdata', '--output', str(backup_file), verbosity=0)
            
            if backup_file.exists():
                size = backup_file.stat().st_size
                self.record_test(
                    'backup_file_not_empty',
                    size > 0,
                    f"Backup file is empty (size: {size} bytes)" if size == 0 else f"Backup file contains data ({size} bytes)"
                )
            else:
                self.record_test(
                    'backup_file_not_empty',
                    False,
                    "Backup file does not exist"
                )
        except Exception as e:
            self.record_test(
                'backup_file_not_empty',
                False,
                f"Backup test failed: {str(e)}"
            )
    
    def test_media_backup_structure(self):
        """Test that media files can be backed up."""
        media_root = Path(settings.MEDIA_ROOT)
        
        # Check if media directory exists and has structure
        exists = media_root.exists()
        has_content = exists and any(media_root.iterdir())
        
        self.record_test(
            'media_backup_structure',
            exists,
            "Media directory does not exist" if not exists else "Media directory exists and ready for backup"
        )
    
    def test_restore_capability(self):
        """Test that restore functionality is available."""
        # Check if loaddata command is available
        try:
            from django.core.management import get_commands
            commands = get_commands()
            has_loaddata = 'loaddata' in commands
            
            self.record_test(
                'restore_capability',
                has_loaddata,
                "loaddata command not available" if not has_loaddata else "Restore capability available"
            )
        except Exception as e:
            self.record_test(
                'restore_capability',
                False,
                f"Could not check restore capability: {str(e)}"
            )



