"""
Additional coverage tests for helper functions, exception paths, and edge cases.
These tests target low-coverage areas to raise overall coverage to 70%+.
"""
from django.test import Client, TestCase
from django.contrib.auth.models import User
from django.http import JsonResponse
from engine.models import Dataset, AnalysisSession, UserProfile
from engine.helpers.analysis_helpers import (
    count_equations, count_dependent_variables, _validate_equation,
    _prepare_options, _determine_template
)
from engine.views.sessions import _list_context
from tests.base import BaseTestSuite
import pandas as pd


class CoverageHelpersTestSuite(BaseTestSuite):
    category = 'coverage'
    test_name = 'Coverage - Helper Functions'
    target_score = 80.0
    
    def setUp(self):
        super().setUp()
        self.client = Client()
        self.user = User.objects.create_user('covuser', 'cov@test.com', 'pass123')
        self.user.is_active = True
        self.user.save()
        profile, _ = UserProfile.objects.get_or_create(user=self.user, defaults={'subscription_type': 'free'})
        profile.subscription_type = 'free'
        profile.save()
        self.client.login(username='covuser', password='pass123')
        
        # Create test dataset
        self.dataset = Dataset.objects.create(
            user=self.user,
            name='Coverage Test Dataset',
            file_path='/test/coverage.csv'
        )
        
        # Create test dataframe
        self.df = pd.DataFrame({
            'y1': [1, 2, 3, 4, 5],
            'y2': [2, 3, 4, 5, 6],
            'x1': [1, 1, 2, 2, 3],
            'x2': [2, 3, 4, 5, 6]
        })
    
    def test_count_equations_empty(self):
        """Test count_equations with empty string."""
        result = count_equations('')
        self.record_test(
            'count_equations_empty',
            result == 0,
            f"Empty string should return 0 equations (got {result})"
        )
    
    def test_count_equations_whitespace(self):
        """Test count_equations with whitespace only."""
        result = count_equations('   \n  \t  ')
        self.record_test(
            'count_equations_whitespace',
            result == 0,
            f"Whitespace-only string should return 0 equations (got {result})"
        )
    
    def test_count_equations_single(self):
        """Test count_equations with single equation."""
        result = count_equations('y ~ x1 + x2')
        self.record_test(
            'count_equations_single',
            result == 1,
            f"Single equation should return 1 (got {result})"
        )
    
    def test_count_equations_multi(self):
        """Test count_equations with multiple equations."""
        result = count_equations('y1 ~ x1 + x2\ny2 ~ x1 + x3')
        self.record_test(
            'count_equations_multi',
            result == 2,
            f"Two equations should return 2 (got {result})"
        )
    
    def test_count_equations_with_comments(self):
        """Test count_equations with lines without ~."""
        result = count_equations('y ~ x1\n# comment\nx2')
        self.record_test(
            'count_equations_with_comments',
            result == 1,
            f"Should only count lines with ~ (got {result})"
        )
    
    def test_count_dependent_variables_empty(self):
        """Test count_dependent_variables with empty string."""
        result = count_dependent_variables('')
        self.record_test(
            'count_dependent_variables_empty',
            result == 0,
            f"Empty string should return 0 DVs (got {result})"
        )
    
    def test_count_dependent_variables_single(self):
        """Test count_dependent_variables with single DV."""
        result = count_dependent_variables('y ~ x1 + x2')
        self.record_test(
            'count_dependent_variables_single',
            result == 1,
            f"Single DV should return 1 (got {result})"
        )
    
    def test_count_dependent_variables_multiple(self):
        """Test count_dependent_variables with multiple DVs."""
        result = count_dependent_variables('y1 + y2 ~ x1 + x2')
        self.record_test(
            'count_dependent_variables_multiple',
            result == 2,
            f"Two DVs should return 2 (got {result})"
        )
    
    def test_count_dependent_variables_multi_equation(self):
        """Test count_dependent_variables with multiple equations."""
        result = count_dependent_variables('y1 ~ x1\ny2 ~ x2')
        self.record_test(
            'count_dependent_variables_multi_equation',
            result == 2,
            f"Two equations with one DV each should return 2 (got {result})"
        )
    
    def test_validate_equation_no_dv(self):
        """Test _validate_equation with no dependent variable."""
        request = self.client.request()
        request.user = self.user
        request.method = 'POST'
        
        result = _validate_equation(request, '~ x1 + x2', 'regression', self.df, _list_context)
        self.record_test(
            'validate_equation_no_dv',
            result is not None,  # Should return error response
            "Should return error when no dependent variable"
        )
    
    def test_validate_equation_varx_insufficient_dvs(self):
        """Test _validate_equation for VARX with insufficient DVs."""
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.post('/run/')
        request.user = self.user
        
        result = _validate_equation(request, 'y1 ~ x1 + x2', 'varx', self.df, _list_context)
        self.record_test(
            'validate_equation_varx_insufficient_dvs',
            result is not None,  # Should return error response
            "Should return error when VARX has < 2 DVs"
        )
    
    def test_validate_equation_varx_multiple_equations(self):
        """Test _validate_equation for VARX with multiple equations."""
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.post('/run/')
        request.user = self.user
        
        result = _validate_equation(request, 'y1 ~ x1\ny2 ~ x2', 'varx', self.df, _list_context)
        self.record_test(
            'validate_equation_varx_multiple_equations',
            result is not None,  # Should return error response
            "Should return error when VARX has multiple equations"
        )
    
    def test_validate_equation_non_regression_multiple_dvs(self):
        """Test _validate_equation for non-regression with multiple DVs."""
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.post('/run/')
        request.user = self.user
        
        result = _validate_equation(request, 'y1 + y2 ~ x1 + x2', 'anova', self.df, _list_context)
        self.record_test(
            'validate_equation_non_regression_multiple_dvs',
            result is not None,  # Should return error response
            "Should return error when non-regression model has multiple DVs"
        )
    
    def test_validate_equation_multi_equation_non_regression(self):
        """Test _validate_equation with multiple equations for non-regression."""
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.post('/run/')
        request.user = self.user
        
        result = _validate_equation(request, 'y1 ~ x1\ny2 ~ x2', 'anova', self.df, _list_context)
        self.record_test(
            'validate_equation_multi_equation_non_regression',
            result is not None,  # Should return error response
            "Should return error when non-regression model has multiple equations"
        )
    
    def test_validate_equation_multi_equation_multiple_dvs_per_line(self):
        """Test _validate_equation with multiple DVs in multi-equation regression."""
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.post('/run/')
        request.user = self.user
        
        result = _validate_equation(request, 'y1 + y2 ~ x1\ny3 ~ x2', 'regression', self.df, _list_context)
        self.record_test(
            'validate_equation_multi_equation_multiple_dvs_per_line',
            result is not None,  # Should return error response
            "Should return error when multi-equation regression has multiple DVs per line"
        )
    
    def test_validate_equation_valid_single(self):
        """Test _validate_equation with valid single equation."""
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.post('/run/')
        request.user = self.user
        
        result = _validate_equation(request, 'y1 ~ x1 + x2', 'regression', self.df, _list_context)
        self.record_test(
            'validate_equation_valid_single',
            result is None,  # Should pass validation
            "Should pass validation for valid single equation"
        )
    
    def test_validate_equation_valid_varx(self):
        """Test _validate_equation with valid VARX equation."""
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.post('/run/')
        request.user = self.user
        
        result = _validate_equation(request, 'y1 + y2 ~ x1 + x2', 'varx', self.df, _list_context)
        self.record_test(
            'validate_equation_valid_varx',
            result is None,  # Should pass validation
            "Should pass validation for valid VARX equation"
        )
    
    def test_validate_equation_valid_multi_equation(self):
        """Test _validate_equation with valid multi-equation regression."""
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.post('/run/')
        request.user = self.user
        
        result = _validate_equation(request, 'y1 ~ x1\ny2 ~ x2', 'regression', self.df, _list_context)
        self.record_test(
            'validate_equation_valid_multi_equation',
            result is None,  # Should pass validation
            "Should pass validation for valid multi-equation regression"
        )
    
    def test_prepare_options_basic(self):
        """Test _prepare_options with basic request."""
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.post('/run/', {
            'formula': 'y1 ~ x1 + x2',
            'show_ci': 'true',
            'show_se': 'true'
        })
        
        options = _prepare_options(request, 'y1 ~ x1 + x2', self.df)
        self.record_test(
            'prepare_options_basic',
            isinstance(options, dict) and 'show_ci' in options,
            "Should return options dictionary with request parameters"
        )
    
    def test_determine_template_multi_equation(self):
        """Test _determine_template for multi-equation results."""
        results = {
            'is_multi_equation': True,
            'dependent_vars': ['y1', 'y2'],
            'rhs_vars': ['x1', 'x2'],
            'grid_data': {},
            'equation_results': []
        }
        template = _determine_template(results, '', 'frequentist')
        self.record_test(
            'determine_template_multi_equation',
            template == 'engine/results_multi_regression.html',
            f"Should return multi-regression template (got {template})"
        )
    
    def test_determine_template_override(self):
        """Test _determine_template with template override."""
        results = {'has_results': True}
        template = _determine_template(results, 'custom_template', 'frequentist')
        self.record_test(
            'determine_template_override',
            template == 'engine/custom_template.html',
            f"Should return override template (got {template})"
        )
    
    def test_determine_template_bayesian(self):
        """Test _determine_template for Bayesian analysis."""
        results = {'has_results': True}
        template = _determine_template(results, '', 'bayesian')
        self.record_test(
            'determine_template_bayesian',
            template == 'engine/bayesian_results.html',
            f"Should return Bayesian template (got {template})"
        )
    
    def test_determine_template_default(self):
        """Test _determine_template default case."""
        results = {'has_results': True}
        template = _determine_template(results, '', 'frequentist')
        self.record_test(
            'determine_template_default',
            template == 'engine/results.html',
            f"Should return default template (got {template})"
        )

