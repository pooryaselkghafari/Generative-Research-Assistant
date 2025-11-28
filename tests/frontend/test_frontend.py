"""
Frontend tests for JavaScript, CSS, and templates.
"""
from pathlib import Path
from django.conf import settings
from django.test import Client
from tests.base import BaseTestSuite


class FrontendTestSuite(BaseTestSuite):
    category = 'frontend'
    test_name = 'Frontend Tests'
    target_score = 75.0
    
    def setUp(self):
        super().setUp()
        self.client = Client()
        self.project_root = Path(settings.BASE_DIR)
    
    def test_static_files_exist(self):
        """Test that static files directory exists."""
        static_root = Path(settings.STATIC_ROOT)
        static_exists = static_root.exists() or Path(settings.BASE_DIR / 'static').exists()
        
        self.record_test(
            'static_files_exist',
            static_exists,
            "Static files directory not found" if not static_exists else "Static files directory exists"
        )
    
    def test_template_files_exist(self):
        """Test that template files exist."""
        template_dirs = getattr(settings, 'TEMPLATES', [{}])[0].get('DIRS', [])
        templates_exist = False
        
        for template_dir in template_dirs:
            if Path(template_dir).exists():
                templates_exist = True
                break
        
        # Also check app template directories
        if not templates_exist:
            engine_templates = self.project_root / 'engine' / 'templates'
            templates_exist = engine_templates.exists()
        
        self.record_test(
            'template_files_exist',
            templates_exist,
            "Template directories not found" if not templates_exist else "Template directories exist"
        )
    
    def test_javascript_files_valid(self):
        """Test that JavaScript files exist and are readable."""
        js_files = list(self.project_root.rglob('*.js'))
        # Filter out node_modules and other excluded directories
        js_files = [f for f in js_files if not any(skip in str(f) for skip in ['node_modules', '__pycache__', '.venv', 'venv'])]
        
        valid_files = 0
        for js_file in js_files[:10]:  # Check first 10 files
            try:
                with open(js_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Basic syntax check (has content, no obvious errors)
                    if len(content) > 0:
                        valid_files += 1
            except Exception:
                pass
        
        self.record_test(
            'javascript_files_valid',
            valid_files > 0,
            f"Found {valid_files} valid JavaScript files" if valid_files > 0 else "No valid JavaScript files found",
            {'js_file_count': len(js_files), 'valid_count': valid_files}
        )
    
    def test_css_files_exist(self):
        """Test that CSS files exist."""
        css_files = list(self.project_root.rglob('*.css'))
        css_files = [f for f in css_files if not any(skip in str(f) for skip in ['node_modules', '__pycache__', '.venv', 'venv'])]
        
        self.record_test(
            'css_files_exist',
            len(css_files) > 0,
            f"Found {len(css_files)} CSS files" if len(css_files) > 0 else "No CSS files found",
            {'css_file_count': len(css_files)}
        )
    
    def test_templates_render(self):
        """Test that key templates can be rendered."""
        from django.contrib.auth.models import User
        from engine.models import UserProfile
        
        # Create test user
        user = User.objects.create_user('frontend_test', 'test@test.com', 'pass123')
        user.is_active = True
        user.save()
        profile, _ = UserProfile.objects.get_or_create(user=user, defaults={'subscription_type': 'free'})
        
        self.client.login(username='frontend_test', password='pass123')
        
        # Test landing page
        try:
            response = self.client.get('/')
            landing_works = response.status_code == 200
        except Exception:
            landing_works = False
        
        # Test app page
        try:
            response = self.client.get('/app/')
            app_works = response.status_code == 200
        except Exception:
            app_works = False
        
        self.record_test(
            'templates_render',
            landing_works and app_works,
            f"Templates render: landing={landing_works}, app={app_works}",
            {'landing': landing_works, 'app': app_works}
        )



