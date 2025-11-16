"""
Test Runner with Scheduling and Result Tracking
Usage:
    python manage.py test_runner security          # Run security tests
    python manage.py test_runner all               # Run all tests
    python manage.py test_runner --schedule        # Run scheduled tests
    python manage.py test_runner --report          # Show test report
"""
from django.core.management.base import BaseCommand
from django.test.utils import get_runner
from django.conf import settings
from datetime import datetime, timedelta
from engine.models import TestResult


class Command(BaseCommand):
    help = 'Run test suites with scheduling and result tracking'
    
    SCHEDULE = {
        'security': {
            'interval': 'daily',
            'time': '02:00',
            'priority': 'high'
        },
        'database': {
            'interval': 'daily',
            'time': '03:00',
            'priority': 'high'
        },
        'performance': {
            'interval': 'daily',
            'time': '04:00',
            'priority': 'medium'
        },
        'unit': {
            'interval': 'on_commit',
            'priority': 'high'
        },
        'integration': {
            'interval': 'daily',
            'time': '05:00',
            'priority': 'medium'
        },
        'api': {
            'interval': 'daily',
            'time': '06:00',
            'priority': 'medium'
        },
        'e2e': {
            'interval': 'weekly',
            'time': '02:00',
            'day': 'sunday',
            'priority': 'low'
        },
        'static_analysis': {
            'interval': 'on_commit',
            'priority': 'high'
        },
        'dependency_scan': {
            'interval': 'weekly',
            'time': '03:00',
            'day': 'sunday',
            'priority': 'high'
        },
        'coverage': {
            'interval': 'on_commit',
            'priority': 'high'
        },
        'backup': {
            'interval': 'weekly',
            'time': '04:00',
            'day': 'sunday',
            'priority': 'high'
        },
        'monitoring': {
            'interval': 'daily',
            'time': '07:00',
            'priority': 'high'
        },
        'cron': {
            'interval': 'daily',
            'time': '08:00',
            'priority': 'medium'
        },
        'frontend': {
            'interval': 'on_commit',
            'priority': 'medium'
        }
    }
    
    TARGET_SCORES = {
        'security': 95.0,
        'database': 85.0,
        'performance': 80.0,
        'unit': 80.0,
        'integration': 75.0,
        'api': 80.0,
        'e2e': 70.0,
        'static_analysis': 80.0,
        'dependency_scan': 95.0,
        'coverage': 80.0,
        'backup': 85.0,
        'monitoring': 85.0,
        'cron': 80.0,
        'frontend': 75.0,
    }
    
    def add_arguments(self, parser):
        parser.add_argument('categories', nargs='*', default=['all'],
                          help='Test categories to run (security, database, performance, etc.)')
        parser.add_argument('--schedule', action='store_true',
                          help='Run only scheduled tests')
        parser.add_argument('--report', action='store_true',
                          help='Show test report')
    
    def handle(self, *args, **options):
        if options['report']:
            self.print_report()
            return
        
        test_runner = get_runner(settings)()
        
        if options['schedule']:
            categories = self.get_scheduled_tests()
            if not categories:
                self.stdout.write("No scheduled tests to run.")
                return
        else:
            categories = options['categories']
            if 'all' in categories:
                categories = list(self.SCHEDULE.keys())
        
        results = {}
        for category in categories:
            if category not in self.SCHEDULE:
                self.stdout.write(self.style.WARNING(f"⚠️  Unknown category: {category}"))
                continue
            
            self.stdout.write(f"\n{'='*60}")
            self.stdout.write(f"Running {category.upper()} tests...")
            self.stdout.write(f"{'='*60}")
            
            try:
                # Run tests - handle different test file names
                test_paths = {
                    'unit': 'tests.unit.test_services',
                    'security': 'tests.security.test_security',
                    'database': 'tests.database.test_database',
                    'performance': 'tests.performance.test_performance',
                    'integration': 'tests.integration.test_integration',
                    'api': 'tests.api.test_api',
                    'e2e': 'tests.e2e.test_e2e',
                    'static_analysis': 'tests.static_analysis.test_static_analysis',
                    'dependency_scan': 'tests.dependency_scan.test_dependency_scan',
                    'coverage': 'tests.coverage.test_coverage',
                    'backup': 'tests.backup.test_backup',
                    'monitoring': 'tests.monitoring.test_monitoring',
                    'cron': 'tests.cron.test_cron',
                    'frontend': 'tests.frontend.test_frontend',
                }
                test_path = test_paths.get(category, f'tests.{category}.test_{category}')
                test_runner.run_tests([test_path], verbosity=2)
                
                # Try to get result from file first (more reliable in test environment)
                import json
                from pathlib import Path
                from datetime import datetime
                import time
                import os
                # Wait a moment for file to be written
                time.sleep(0.5)
                
                # Get project root (where manage.py is)
                project_root = Path(__file__).parent.parent.parent.parent
                results_dir = project_root / 'test_results'
                result_files = sorted(results_dir.glob(f'{category}_*.json'), reverse=True) if results_dir.exists() else []
                
                latest_result = None
                if result_files:
                    # Get most recent result file
                    try:
                        with open(result_files[0], 'r') as f:
                            file_result = json.load(f)
                        
                        # Create result object from file
                        class FileResult:
                            def __init__(self, data):
                                self.passed = data['passed']
                                self.score = data['score']
                                self.total_tests = data['total_tests']
                                self.passed_tests = data['passed_tests']
                                self.failed_tests = data['failed_tests']
                                self.execution_time = data['execution_time']
                                self.created_at = datetime.now()
                        
                        latest_result = FileResult(file_result)
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"Could not read result file: {e}"))
                
                # Also try to get from database (if not found in file)
                if not latest_result:
                    latest_result = TestResult.objects.filter(
                        category=category
                    ).order_by('-created_at').first()
                
                if latest_result:
                    results[category] = {
                        'passed': latest_result.passed,
                        'score': latest_result.score,
                        'target': self.TARGET_SCORES[category],
                        'total': latest_result.total_tests,
                        'passed_count': latest_result.passed_tests,
                        'failed_count': latest_result.failed_tests,
                        'execution_time': latest_result.execution_time,
                    }
                    
                    status = "✅ PASS" if latest_result.passed else "❌ FAIL"
                    self.stdout.write(
                        self.style.SUCCESS(f"\n{status} - Score: {latest_result.score:.1f}% "
                                         f"(Target: {self.TARGET_SCORES[category]}%)")
                        if latest_result.passed
                        else self.style.ERROR(f"\n{status} - Score: {latest_result.score:.1f}% "
                                             f"(Target: {self.TARGET_SCORES[category]}%)")
                    )
                else:
                    results[category] = {'error': 'No results recorded'}
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error running {category} tests: {e}"))
                results[category] = {'error': str(e)}
        
        self.print_summary(results)
    
    def get_scheduled_tests(self):
        """Get tests that should run based on schedule."""
        now = datetime.now()
        scheduled = []
        
        for category, schedule in self.SCHEDULE.items():
            if schedule['interval'] == 'on_commit':
                continue
            
            last_run = TestResult.objects.filter(
                category=category
            ).order_by('-created_at').first()
            
            should_run = False
            
            if schedule['interval'] == 'daily':
                if not last_run or (now - last_run.created_at) > timedelta(days=1):
                    should_run = True
            elif schedule['interval'] == 'weekly':
                if not last_run or (now - last_run.created_at) > timedelta(weeks=1):
                    should_run = True
            elif schedule['interval'] == 'monthly':
                if not last_run or (now - last_run.created_at) > timedelta(days=30):
                    should_run = True
            
            if should_run:
                scheduled.append(category)
        
        return scheduled
    
    def print_summary(self, results):
        """Print test summary."""
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write("TEST SUMMARY")
        self.stdout.write(f"{'='*60}\n")
        
        for category, result in results.items():
            if 'error' in result:
                self.stdout.write(self.style.WARNING(
                    f"{category.upper():15} ❌ ERROR: {result['error']}"
                ))
                continue
            
            status = "✅" if result['passed'] else "❌"
            style = self.style.SUCCESS if result['passed'] else self.style.ERROR
            self.stdout.write(style(
                f"{category.upper():15} {status} {result['score']:.1f}% "
                f"({result['passed_count']}/{result['total']} passed) "
                f"Time: {result['execution_time']:.2f}s"
            ))
        
        # Overall score
        if results:
            valid_results = [r for r in results.values() if 'score' in r]
            if valid_results:
                avg_score = sum(r['score'] for r in valid_results) / len(valid_results)
                self.stdout.write(f"\n{'OVERALL':15} 📊 {avg_score:.1f}% average score")
    
    def print_report(self):
        """Print test results report."""
        import json
        from pathlib import Path
        from datetime import datetime
        
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write("TEST RESULTS REPORT")
        self.stdout.write(f"{'='*60}\n")
        
        # Get project root
        project_root = Path(__file__).parent.parent.parent.parent
        results_dir = project_root / 'test_results'
        
        for category in ['security', 'database', 'performance', 'unit', 'integration', 'api', 'e2e', 
                         'static_analysis', 'dependency_scan', 'coverage', 'backup', 'monitoring', 'cron', 'frontend']:
            # Try database first
            latest = TestResult.objects.filter(category=category).order_by('-created_at').first()
            
            # If not in database, try file
            if not latest and results_dir.exists():
                result_files = sorted(results_dir.glob(f'{category}_*.json'), reverse=True)
                if result_files:
                    try:
                        with open(result_files[0], 'r') as f:
                            file_result = json.load(f)
                        # Create a mock object
                        class FileResult:
                            def __init__(self, data):
                                self.passed = data['passed']
                                self.score = data['score']
                                self.created_at = datetime.fromtimestamp(int(result_files[0].stem.split('_')[-1]))
                        latest = FileResult(file_result)
                    except:
                        pass
            
            if latest:
                status = "✅" if latest.passed else "❌"
                style = self.style.SUCCESS if latest.passed else self.style.ERROR
                self.stdout.write(style(
                    f"{category.upper():15} {status} {latest.score:.1f}% "
                    f"({latest.created_at.strftime('%Y-%m-%d %H:%M')})"
                ))
            else:
                self.stdout.write(self.style.WARNING(
                    f"{category.upper():15} ⚠️  Not run yet"
                ))

