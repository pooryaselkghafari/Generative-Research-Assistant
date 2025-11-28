"""
Monitoring and logging tests.
"""
import logging
from django.conf import settings
from django.test import override_settings
from tests.base import BaseTestSuite


class MonitoringTestSuite(BaseTestSuite):
    category = 'monitoring'
    test_name = 'Monitoring/Logging Tests'
    target_score = 85.0
    
    def setUp(self):
        super().setUp()
        self.logger = logging.getLogger('django')
    
    def test_logging_configured(self):
        """Test that logging is properly configured."""
        configured = hasattr(settings, 'LOGGING') and settings.LOGGING
        
        self.record_test(
            'logging_configured',
            configured,
            "Logging not configured in settings" if not configured else "Logging is configured"
        )
    
    def test_logger_available(self):
        """Test that logger is available and functional."""
        try:
            self.logger.info("Test log message")
            available = True
        except Exception as e:
            available = False
        
        self.record_test(
            'logger_available',
            available,
            "Logger not available or not functional" if not available else "Logger is available and functional"
        )
    
    def test_error_logging(self):
        """Test that errors are properly logged."""
        try:
            self.logger.error("Test error message")
            error_logging_works = True
        except Exception:
            error_logging_works = False
        
        self.record_test(
            'error_logging',
            error_logging_works,
            "Error logging not working" if not error_logging_works else "Error logging works"
        )
    
    def test_debug_logging(self):
        """Test that debug logging works (when DEBUG=True)."""
        try:
            self.logger.debug("Test debug message")
            debug_logging_works = True
        except Exception:
            debug_logging_works = False
        
        # Debug logging should work when DEBUG=True
        debug_enabled = settings.DEBUG
        self.record_test(
            'debug_logging',
            debug_logging_works or not debug_enabled,
            "Debug logging not working" if debug_logging_works and not debug_enabled else "Debug logging works"
        )
    
    def test_log_levels(self):
        """Test that different log levels work."""
        levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        working_levels = []
        
        for level_name in levels:
            try:
                level = getattr(logging, level_name)
                self.logger.log(level, f"Test {level_name} message")
                working_levels.append(level_name)
            except Exception:
                pass
        
        self.record_test(
            'log_levels',
            len(working_levels) >= 3,  # At least 3 levels should work
            f"Working log levels: {', '.join(working_levels)}" if working_levels else "No log levels working",
            {'working_levels': working_levels}
        )



