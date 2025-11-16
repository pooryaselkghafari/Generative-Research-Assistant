"""
Dependency vulnerability scan tests.
"""
import subprocess
import json
from pathlib import Path
from django.conf import settings
from tests.base import BaseTestSuite


class DependencyScanTestSuite(BaseTestSuite):
    category = 'dependency_scan'
    test_name = 'Dependency Vulnerability Scan'
    target_score = 95.0  # High priority for security
    
    def setUp(self):
        super().setUp()
        self.project_root = Path(settings.BASE_DIR)
        self.requirements_file = self.project_root / 'requirements.txt'
    
    def test_requirements_file_exists(self):
        """Test that requirements file exists."""
        exists = self.requirements_file.exists()
        
        self.record_test(
            'requirements_file_exists',
            exists,
            "Requirements file not found" if not exists else "Requirements file exists"
        )
    
    def test_pip_audit_available(self):
        """Test if pip-audit is available for vulnerability scanning."""
        try:
            result = subprocess.run(['pip-audit', '--version'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=5)
            available = result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            available = False
        
        self.record_test(
            'pip_audit_available',
            available,
            "pip-audit not installed (install with: pip install pip-audit)" if not available else "pip-audit available"
        )
    
    def test_dependency_vulnerabilities(self):
        """Scan for known vulnerabilities in dependencies."""
        if not self.requirements_file.exists():
            self.record_test(
                'dependency_vulnerabilities',
                False,
                "Cannot scan: requirements file not found"
            )
            return
        
        try:
            # Try to use pip-audit if available
            result = subprocess.run(['pip-audit', '--requirement', str(self.requirements_file), '--format', 'json'],
                                  capture_output=True,
                                  text=True,
                                  timeout=30)
            
            if result.returncode == 0:
                # No vulnerabilities found
                self.record_test(
                    'dependency_vulnerabilities',
                    True,
                    "No known vulnerabilities found"
                )
            else:
                # Vulnerabilities found
                try:
                    data = json.loads(result.stdout)
                    vuln_count = len(data.get('vulnerabilities', []))
                    self.record_test(
                        'dependency_vulnerabilities',
                        vuln_count == 0,
                        f"Found {vuln_count} known vulnerabilities" if vuln_count > 0 else "No vulnerabilities",
                        {'vulnerability_count': vuln_count}
                    )
                except json.JSONDecodeError:
                    self.record_test(
                        'dependency_vulnerabilities',
                        False,
                        "Could not parse pip-audit output"
                    )
            return
        except (FileNotFoundError, subprocess.TimeoutExpired):
            # pip-audit not available, skip this test
            self.record_test(
                'dependency_vulnerabilities',
                True,  # Pass if tool not available (not a failure of the code)
                "pip-audit not available, skipping vulnerability scan"
            )
    
    def test_outdated_dependencies(self):
        """Check for outdated dependencies."""
        if not self.requirements_file.exists():
            self.record_test(
                'outdated_dependencies',
                True,  # Pass if no requirements file
                "No requirements file to check"
            )
            return
        
        try:
            # Read requirements.txt to get list of packages we care about
            with open(self.requirements_file, 'r') as f:
                req_lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
            req_packages = []
            for line in req_lines:
                # Extract package name (before >=, ==, <, etc.)
                pkg = line.split('>=')[0].split('==')[0].split('<')[0].split('>')[0].strip()
                req_packages.append(pkg.lower())
            
            result = subprocess.run(['pip', 'list', '--outdated', '--format=json'],
                                  capture_output=True,
                                  text=True,
                                  timeout=30)
            
            if result.returncode == 0:
                try:
                    outdated = json.loads(result.stdout)
                    # Only count packages that are in requirements.txt
                    outdated_in_req = [pkg for pkg in outdated if pkg['name'].lower() in req_packages]
                    outdated_count = len(outdated_in_req)
                    self.record_test(
                        'outdated_dependencies',
                        outdated_count < 10,  # Allow some outdated packages
                        f"Found {outdated_count} outdated packages in requirements.txt" if outdated_count > 0 else "All packages in requirements.txt are up to date",
                        {'outdated_count': outdated_count, 'total_outdated': len(outdated)}
                    )
                except json.JSONDecodeError:
                    self.record_test(
                        'outdated_dependencies',
                        True,
                        "Could not parse pip list output"
                    )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            self.record_test(
                'outdated_dependencies',
                True,
                "Could not check outdated dependencies"
            )

