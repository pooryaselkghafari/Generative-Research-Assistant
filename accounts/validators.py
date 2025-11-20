"""
Custom password validators for strong password requirements.
"""
import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class ComplexityPasswordValidator:
    """
    Validate that the password contains uppercase, lowercase, numbers, and special characters.
    
    Requirements:
    - At least one uppercase letter (A-Z)
    - At least one lowercase letter (a-z)
    - At least one number (0-9)
    - At least one special character (!@#$%^&*()_+-=[]{}|;:,.<>/?)
    """
    
    def validate(self, password, user=None):
        errors = []
        
        if not re.search(r'[A-Z]', password):
            errors.append('Password must contain at least one uppercase letter (A-Z).')
        if not re.search(r'[a-z]', password):
            errors.append('Password must contain at least one lowercase letter (a-z).')
        if not re.search(r'\d', password):
            errors.append('Password must contain at least one number (0-9).')
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]', password):
            errors.append('Password must contain at least one special character (!@#$%^&*()_+-=[]{}|;:,.<>/?).')
        
        if errors:
            raise ValidationError(errors)
    
    def get_help_text(self):
        return (
            'Your password must contain at least: '
            'one uppercase letter, one lowercase letter, one number, and one special character.'
        )

