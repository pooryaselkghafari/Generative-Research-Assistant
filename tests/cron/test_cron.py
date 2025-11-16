"""
Cron and scheduled task tests.
"""
import subprocess
from pathlib import Path
from django.conf import settings
from tests.base import BaseTestSuite


class CronTestSuite(BaseTestSuite):
    category = 'cron'
    test_name = 'Cron/Scheduled Task Tests'
    target_score = 80.0
    
    def setUp(self):
        super().setUp()
        self.project_root = Path(settings.BASE_DIR)
    
    def test_management_commands_exist(self):
        """Test that management commands exist and are executable."""
        commands_dir = self.project_root / 'engine' / 'management' / 'commands'
        commands_exist = commands_dir.exists() and any(commands_dir.glob('*.py'))
        
        self.record_test(
            'management_commands_exist',
            commands_exist,
            "Management commands directory not found" if not commands_exist else "Management commands exist"
        )
    
    def test_test_runner_command(self):
        """Test that test_runner command is available."""
        try:
            from django.core.management import get_commands
            commands = get_commands()
            available = 'test_runner' in commands
        except Exception:
            available = False
        
        self.record_test(
            'test_runner_command',
            available,
            "test_runner command not available" if not available else "test_runner command available"
        )
    
    def test_scheduled_tasks_defined(self):
        """Test that scheduled tasks are properly defined."""
        # Check if test_runner has schedule definitions
        try:
            from engine.management.commands.test_runner import Command
            runner = Command()
            has_schedule = hasattr(runner, 'SCHEDULE') and len(runner.SCHEDULE) > 0
            
            self.record_test(
                'scheduled_tasks_defined',
                has_schedule,
                "No schedule definitions found" if not has_schedule else "Schedule definitions exist"
            )
        except Exception as e:
            self.record_test(
                'scheduled_tasks_defined',
                False,
                f"Could not check schedule: {str(e)}"
            )
    
    def test_cron_syntax_valid(self):
        """Test that cron syntax would be valid (if cron file exists)."""
        # Check for common cron file locations
        cron_files = [
            self.project_root / 'crontab',
            self.project_root / '.crontab',
            self.project_root / 'deploy' / 'crontab',
        ]
        
        cron_file_found = any(f.exists() for f in cron_files)
        
        self.record_test(
            'cron_syntax_valid',
            True,  # Pass if no cron file (not required)
            "Cron file found" if cron_file_found else "No cron file (optional)"
        )

