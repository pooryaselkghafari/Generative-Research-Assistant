"""
Coverage tests for validation services and edge cases.
"""
from django.test import Client, RequestFactory
from django.contrib.auth.models import User
from django.http import JsonResponse
from engine.models import Dataset, UserProfile
from engine.services.dataset_validation_service import DatasetValidationService
from engine.services.dataset_merge_service import DatasetMergeService
from tests.base import BaseTestSuite
import pandas as pd


class CoverageValidationTestSuite(BaseTestSuite):
    category = 'coverage'
    test_name = 'Coverage - Validation Services'
    target_score = 80.0
    
    def setUp(self):
        super().setUp()
        self.client = Client()
        self.factory = RequestFactory()
        self.user = User.objects.create_user('valuser', 'val@test.com', 'pass123')
        self.user.is_active = True
        self.user.save()
        profile, _ = UserProfile.objects.get_or_create(user=self.user, defaults={'subscription_type': 'free'})
        profile.subscription_type = 'free'
        profile.save()
    
    def test_dataset_validation_user_limits_dataset_count(self):
        """Test DatasetValidationService.check_user_limits with dataset count limit."""
        # Create datasets up to limit
        for i in range(5):
            Dataset.objects.create(
                user=self.user,
                name=f'Dataset {i}',
                file_path=f'/test/path{i}.csv'
            )
        
        # Update profile to have limit of 5 datasets
        profile = self.user.profile
        profile.subscription_type = 'free'
        profile.save()
        
        request = self.factory.post('/datasets/upload/')
        request.headers = {'X-Requested-With': 'XMLHttpRequest'}
        
        result = DatasetValidationService.check_user_limits(self.user, 1.0, request)
        self.record_test(
            'dataset_validation_user_limits_dataset_count',
            result is not None and result.status_code == 403,
            f"Should return error when dataset limit reached (got {result.status_code if result else None})"
        )
    
    def test_dataset_validation_user_limits_file_size(self):
        """Test DatasetValidationService.check_user_limits with file size limit."""
        request = self.factory.post('/datasets/upload/')
        request.headers = {'X-Requested-With': 'XMLHttpRequest'}
        
        # Free tier typically has 10MB limit
        result = DatasetValidationService.check_user_limits(self.user, 100.0, request)
        self.record_test(
            'dataset_validation_user_limits_file_size',
            result is not None and result.status_code == 403,
            f"Should return error when file size exceeds limit (got {result.status_code if result else None})"
        )
    
    def test_dataset_validation_user_limits_no_user(self):
        """Test DatasetValidationService.check_user_limits with no user."""
        request = self.factory.post('/datasets/upload/')
        result = DatasetValidationService.check_user_limits(None, 1.0, request)
        self.record_test(
            'dataset_validation_user_limits_no_user',
            result is None,
            "Should return None when no user provided"
        )
    
    def test_dataset_validation_session_limits(self):
        """Test DatasetValidationService.check_session_limits."""
        request = self.factory.post('/run/')
        request.headers = {'X-Requested-With': 'XMLHttpRequest'}
        
        result = DatasetValidationService.check_session_limits(self.user, request)
        # Should return None if no limit or limit not reached
        self.record_test(
            'dataset_validation_session_limits',
            result is None or result.status_code == 403,
            f"Should check session limits (got {result.status_code if result else None})"
        )
    
    def test_dataset_validation_session_limits_unauthenticated(self):
        """Test DatasetValidationService.check_session_limits with unauthenticated user."""
        request = self.factory.post('/run/')
        result = DatasetValidationService.check_session_limits(None, request)
        self.record_test(
            'dataset_validation_session_limits_unauthenticated',
            result is None,
            "Should return None for unauthenticated user"
        )
    
    def test_dataset_merge_validate_columns_missing_col1(self):
        """Test DatasetMergeService.validate_merge_columns with missing column in first dataset."""
        df1 = pd.DataFrame({'x': [1, 2, 3]})
        df2 = pd.DataFrame({'y': [1, 2, 3]})
        
        error = DatasetMergeService.validate_merge_columns(df1, df2, 'missing_col', 'y', 'Dataset2')
        self.record_test(
            'dataset_merge_validate_columns_missing_col1',
            error is not None and 'not found' in error.lower(),
            f"Should return error for missing column (got {error})"
        )
    
    def test_dataset_merge_validate_columns_missing_col2(self):
        """Test DatasetMergeService.validate_merge_columns with missing column in second dataset."""
        df1 = pd.DataFrame({'x': [1, 2, 3]})
        df2 = pd.DataFrame({'y': [1, 2, 3]})
        
        error = DatasetMergeService.validate_merge_columns(df1, df2, 'x', 'missing_col', 'Dataset2')
        self.record_test(
            'dataset_merge_validate_columns_missing_col2',
            error is not None and 'not found' in error.lower(),
            f"Should return error for missing column (got {error})"
        )
    
    def test_dataset_merge_validate_columns_type_mismatch(self):
        """Test DatasetMergeService.validate_merge_columns with type mismatch."""
        df1 = pd.DataFrame({'x': [1, 2, 3]})  # int64
        df2 = pd.DataFrame({'y': ['a', 'b', 'c']})  # object
        
        error = DatasetMergeService.validate_merge_columns(df1, df2, 'x', 'y', 'Dataset2')
        self.record_test(
            'dataset_merge_validate_columns_type_mismatch',
            error is not None and 'data type' in error.lower(),
            f"Should return error for type mismatch (got {error})"
        )
    
    def test_dataset_merge_validate_columns_valid(self):
        """Test DatasetMergeService.validate_merge_columns with valid columns."""
        df1 = pd.DataFrame({'x': [1, 2, 3]})
        df2 = pd.DataFrame({'y': [1, 2, 3]})
        
        error = DatasetMergeService.validate_merge_columns(df1, df2, 'x', 'y', 'Dataset2')
        self.record_test(
            'dataset_merge_validate_columns_valid',
            error is None,
            f"Should return None for valid columns (got {error})"
        )


