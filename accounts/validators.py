"""
Custom password validators for strong password requirements.
"""
import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class ComplexityPasswordValidator:
    """
    Validate that the password contains uppercase letters and numbers.
    
    Requirements:
    - At least one uppercase letter (A-Z)
    - At least one number (0-9)
    """
    
    def validate(self, password, user=None):
        errors = []
        
        if not re.search(r'[A-Z]', password):
            errors.append('Password must contain at least one uppercase letter (A-Z).')
        if not re.search(r'\d', password):
            errors.append('Password must contain at least one number (0-9).')
        
        if errors:
            raise ValidationError(errors)
    
    def get_help_text(self):
        return (
            'Your password must contain at least: '
            'one uppercase letter and one number.'
        )

