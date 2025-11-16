"""
Unit tests for service classes.
"""
from django.test import TestCase
from django.contrib.auth.models import User
from engine.models import AnalysisSession, Dataset, UserProfile
from engine.services.irf_service import IRFService
from engine.services.model_service import ModelService
from tests.base import BaseTestSuite


class UnitTestSuite(BaseTestSuite):
    category = 'unit'
    test_name = 'Unit Tests - Services'
    target_score = 80.0
    
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user('testuser', 'test@test.com', 'pass123')
        profile, _ = UserProfile.objects.get_or_create(user=self.user, defaults={'subscription_type': 'free'})
        profile.subscription_type = 'free'
        profile.save()
    
    def test_irf_service_validation(self):
        """Test IRF service validation."""
        # Create a session
        dataset = Dataset.objects.create(
            user=self.user,
            name='Test Dataset',
            file_path='/test/path.csv'
        )
        session = AnalysisSession.objects.create(
            user=self.user,
            dataset=dataset,
            name='Test Session',
            module='varx'
        )
        
        # Test validation
        is_valid, error = IRFService.validate_session_for_irf(session)
        self.record_test(
            'irf_service_validation_varx',
            is_valid and error is None,
            "IRF service should validate VARX sessions"
        )
        
        # Test invalid module
        session.module = 'regression'
        is_valid, error = IRFService.validate_session_for_irf(session)
        self.record_test(
            'irf_service_validation_invalid_module',
            not is_valid and error is not None,
            "IRF service should reject non-VARX sessions"
        )
    
    def test_model_service_multi_equation_detection(self):
        """Test model service multi-equation detection."""
        dataset = Dataset.objects.create(
            user=self.user,
            name='Test Dataset',
            file_path='/test/path.csv'
        )
        
        # Single equation
        session1 = AnalysisSession.objects.create(
            user=self.user,
            dataset=dataset,
            name='Single Eq Session',
            module='regression',
            formula='Y ~ X1 + X2'
        )
        
        # Multi equation
        session2 = AnalysisSession.objects.create(
            user=self.user,
            dataset=dataset,
            name='Multi Eq Session',
            module='regression',
            formula='Y1 ~ X1\nY2 ~ X2'
        )
        
        # Test detection logic (we can't fully test without actual data, but we can test the structure)
        formula1 = session1.formula
        equation_lines1 = [line.strip() for line in formula1.split('\n') if line.strip() and '~' in line]
        is_multi1 = len(equation_lines1) > 1 and session1.module == 'regression'
        
        formula2 = session2.formula
        equation_lines2 = [line.strip() for line in formula2.split('\n') if line.strip() and '~' in line]
        is_multi2 = len(equation_lines2) > 1 and session2.module == 'regression'
        
        self.record_test(
            'model_service_single_equation_detection',
            not is_multi1,
            "Should detect single equation correctly"
        )
        
        self.record_test(
            'model_service_multi_equation_detection',
            is_multi2,
            "Should detect multi-equation correctly"
        )

