"""
Base test class with result tracking.
"""
import time
import json
from django.test import TestCase
from django.db import connection
from engine.models import TestResult


class BaseTestSuite(TestCase):
    """Base class for all test suites with result tracking."""
    
    category = None  # Override in subclasses
    test_name = None  # Override in subclasses
    target_score = 80.0  # Minimum passing score
    
    # Class-level storage for results (to save after all tests)
    _all_suite_results = {}
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls_name = cls.__name__
        cls._all_suite_results[cls_name] = {
            'category': cls.category,
            'test_name': cls.test_name,
            'target_score': cls.target_score,
            'test_results': [],
            'start_time': time.time(),
            'query_count_start': 0
        }
    
    @classmethod
    def tearDownClass(cls):
        # Save results after all tests in the suite complete
        cls_name = cls.__name__
        suite_results = cls._all_suite_results.get(cls_name, {})
        
        if suite_results.get('test_results'):
            execution_time = time.time() - suite_results['start_time']
            total = len(suite_results['test_results'])
            passed = sum(1 for r in suite_results['test_results'] if r['passed'])
            score = (passed / total * 100) if total > 0 else 0
            
            # Save to database
            # Note: Django TestCase wraps tests in transactions that are rolled back,
            # so we can't save to DB during tests. File save (below) works as a backup.
            # For production/test runs outside TestCase, database saves will work.
            try:
                from django.db import transaction
                # Check if we're in an atomic block
                if connection.in_atomic_block:
                    # Can't save during transaction - file save will handle it
                    pass
                else:
                    TestResult.objects.create(
                        category=suite_results['category'],
                        test_name=suite_results['test_name'],
                        passed=score >= suite_results['target_score'],
                        score=score,
                        total_tests=total,
                        passed_tests=passed,
                        failed_tests=total - passed,
                        execution_time=execution_time,
                        details={
                            'test_results': suite_results['test_results'],
                        }
                    )
            except Exception as e:
                # Silently fail - file save below will handle persistence
                pass
            
            # Also save to file as backup
            import json
            from pathlib import Path
            results_dir = Path(__file__).parent.parent / 'test_results'
            results_dir.mkdir(exist_ok=True)
            result_file = results_dir / f"{suite_results['category']}_{int(time.time())}.json"
            with open(result_file, 'w') as f:
                json.dump({
                    'category': suite_results['category'],
                    'test_name': suite_results['test_name'],
                    'score': score,
                    'passed': score >= suite_results['target_score'],
                    'total_tests': total,
                    'passed_tests': passed,
                    'failed_tests': total - passed,
                    'execution_time': execution_time,
                    'test_results': suite_results['test_results'],
                }, f, indent=2)
        
        super().tearDownClass()
    
    def setUp(self):
        super().setUp()
        self.start_time = time.time()
        self.test_results = []
        self.query_count_start = len(connection.queries)
    
    def tearDown(self):
        super().tearDown()
        # Add this test's results to suite results
        cls_name = self.__class__.__name__
        if cls_name in BaseTestSuite._all_suite_results:
            BaseTestSuite._all_suite_results[cls_name]['test_results'].extend(self.test_results)
    
    def record_test(self, test_name, passed, message="", details=None):
        """Record individual test result."""
        self.test_results.append({
            'test_name': test_name,
            'passed': passed,
            'message': message,
            'details': details or {}
        })
        # Don't fail immediately - let all tests run and record results
        # The tearDownClass will calculate the score based on all recorded tests

