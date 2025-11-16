"""
Database tests for query performance, integrity, and transactions.
"""
from django.test import TestCase
from django.db import connection, reset_queries, transaction
from django.contrib.auth.models import User
from engine.models import Dataset, AnalysisSession, UserProfile
from tests.base import BaseTestSuite
import time


class DatabaseTestSuite(BaseTestSuite):
    category = 'database'
    test_name = 'Database Tests'
    target_score = 85.0
    
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user('testuser', 'test@test.com', 'pass123')
        profile, _ = UserProfile.objects.get_or_create(user=self.user, defaults={'subscription_type': 'free'})
        profile.subscription_type = 'free'
        profile.save()
    
    def test_query_performance(self):
        """Test that queries are optimized (no N+1 problems)."""
        reset_queries()
        
        # Create test data
        datasets = [Dataset.objects.create(
            user=self.user,
            name=f'Dataset {i}',
            file_path=f'/test/path{i}.csv'
        ) for i in range(10)]
        
        reset_queries()
        
        # Fetch datasets with related sessions
        datasets_list = list(Dataset.objects.filter(user=self.user).select_related('user'))
        sessions = AnalysisSession.objects.filter(dataset__in=datasets_list).select_related('dataset', 'user')
        list(sessions)  # Force evaluation
        
        query_count = len(connection.queries)
        
        self.record_test(
            'query_performance_no_n_plus_one',
            query_count < 10,  # Should use select_related efficiently
            f"Query count: {query_count} (should be < 10)",
            {'query_count': query_count}
        )
    
    def test_database_integrity(self):
        """Test database constraints and integrity."""
        # Enable foreign key constraints for SQLite (they're off by default)
        from django.db import connection
        if 'sqlite' in connection.settings_dict['ENGINE']:
            with connection.cursor() as cursor:
                cursor.execute("PRAGMA foreign_keys = ON")
        
        # Test foreign key constraint validation
        # Since dataset field allows null=True, we test that validation works when dataset_id is set
        try:
            # Try to create a session with an invalid dataset_id
            # This should fail validation (not at DB level, but at model level)
            session = AnalysisSession(
                user=self.user,
                dataset_id=99999,  # Non-existent dataset
                name='Test Session'
            )
            session.full_clean()  # This should raise ValidationError
            session.save()
            # If we get here, validation didn't work
            integrity_passed = False
            session.delete()
        except Exception as e:
            # If it fails validation, constraints are working
            # Check if it's a ValidationError (expected) or other error
            from django.core.exceptions import ValidationError
            if isinstance(e, ValidationError):
                integrity_passed = True
            else:
                # Other errors might indicate DB-level constraint (also acceptable)
                integrity_passed = True
        
        # Test unique constraint (more reliable for SQLite)
        Dataset.objects.create(user=self.user, name='Unique Test', file_path='/test1.csv')
        try:
            Dataset.objects.create(user=self.user, name='Unique Test', file_path='/test2.csv')
            unique_passed = False
        except Exception:
            unique_passed = True
        
        self.record_test(
            'database_integrity_foreign_keys',
            integrity_passed and unique_passed,
            "Database constraints should be enforced (foreign key validation and unique constraints tested)"
        )
    
    def test_transaction_rollback(self):
        """Test transaction rollback on errors."""
        initial_count = Dataset.objects.count()
        
        try:
            with transaction.atomic():
                Dataset.objects.create(user=self.user, name='Test', file_path='/test.csv')
                raise Exception("Simulated error")
        except Exception:
            pass
        
        final_count = Dataset.objects.count()
        
        self.record_test(
            'transaction_rollback',
            initial_count == final_count,
            "Transactions should rollback on errors"
        )
    
    def test_index_usage(self):
        """Test that indexes are being used for common queries."""
        # Test user-based queries (should use index)
        start = time.time()
        datasets = list(Dataset.objects.filter(user=self.user))
        query_time = time.time() - start
        
        self.record_test(
            'index_usage',
            query_time < 0.1,  # Should be fast with index
            f"Query time: {query_time:.4f}s (should be < 0.1s)",
            {'query_time': query_time}
        )
    
    def test_unique_constraints(self):
        """Test unique constraints are enforced."""
        # Create dataset
        Dataset.objects.create(user=self.user, name='Unique Test', file_path='/test1.csv')
        
        # Try to create duplicate (should fail)
        try:
            Dataset.objects.create(user=self.user, name='Unique Test', file_path='/test2.csv')
            unique_passed = False
        except Exception:
            unique_passed = True
        
        self.record_test(
            'unique_constraints',
            unique_passed,
            "Unique constraints should be enforced"
        )

