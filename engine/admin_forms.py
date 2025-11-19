"""
Custom admin forms for AI fine-tuning.

This module provides custom Django admin forms with enhanced functionality
for managing AI fine-tuning commands, including template selection and
JSON validation.
"""
import json
from typing import Dict, Any, List, Tuple, Optional
from django import forms
from engine.models import AIFineTuningCommand, AIFineTuningTemplate, AIProvider


class AIFineTuningCommandAdminForm(forms.ModelForm):
    """
    Custom form for AI Fine-tuning Command with template selection.
    
    Provides a template selector dropdown and JSON validation for
    the command_data field.
    """
    
    template_select = forms.ChoiceField(
        required=False,
        label='Load Template',
        choices=[],
        widget=forms.Select(attrs={
            'class': 'template-select',
        })
    )
    
    provider = forms.ModelChoiceField(
        queryset=AIProvider.objects.filter(is_active=True),
        required=False,
        label='AI Provider',
        help_text='Select which AI provider to use for this command. Leave empty to use the default provider.',
        widget=forms.Select(attrs={
            'class': 'provider-select',
        })
    )
    
    class Meta:
        """Form metadata configuration."""
        model = AIFineTuningCommand
        fields = '__all__'
        widgets = {
            'provider': forms.Select(attrs={
                'class': 'provider-select',
            }),
        }
        widgets = {
            'command_data': forms.Textarea(attrs={
                'rows': 18,
                'cols': 80,
                'placeholder': '{\n  "key": "value"\n}',
                'class': 'command-data-json'
            }),
            'description': forms.Textarea(attrs={
                'rows': 3,
                'cols': 80,
                'style': 'width: 100%;'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        """
        Initialize form with template choices and provider options.
        
        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments
        """
        super().__init__(*args, **kwargs)
        
        command_type = self._get_command_type()
        template_choices = self._build_template_choices(command_type)
        self.fields['template_select'].choices = template_choices
        
        # Update provider queryset to show active providers
        try:
            self.fields['provider'].queryset = AIProvider.objects.filter(is_active=True).order_by('-is_default', 'name')
        except Exception:
            # If AIProvider table doesn't exist yet, use empty queryset
            self.fields['provider'].queryset = AIProvider.objects.none()
        
        self._format_existing_command_data()
    
    def _get_command_type(self) -> Optional[str]:
        """
        Extract command type from form data or instance.
        
        Returns:
            Optional[str]: Command type or None
        """
        if self.instance and self.instance.pk:
            return self.instance.command_type
        
        if 'command_type' in self.initial:
            return self.initial['command_type']
        
        if 'command_type' in self.data:
            return self.data['command_type']
        
        return None
    
    def _build_template_choices(self, command_type: Optional[str]) -> List[Tuple[str, str]]:
        """
        Build template choices list.
        
        Args:
            command_type: Optional command type to filter templates
            
        Returns:
            List of (value, label) tuples for template choices
        """
        choices = [('', '-- No Template (Start Fresh) --')]
        choices.extend(self._get_default_template_choices())
        choices.extend(self._get_saved_template_choices(command_type))
        return choices
    
    def _get_default_template_choices(self) -> List[Tuple[str, str]]:
        """
        Get default template choices.
        
        Returns:
            List of (value, label) tuples for default templates
        """
        default_templates = self._get_default_templates()
        return [
            (f'default_{key}', f'[Default] {value["name"]}')
            for key, value in default_templates.items()
        ]
    
    def _get_saved_template_choices(self, command_type: Optional[str]) -> List[Tuple[str, str]]:
        """
        Get saved template choices from database.
        
        Args:
            command_type: Optional command type to filter by
            
        Returns:
            List of (value, label) tuples for saved templates
        """
        choices = []
        
        # Try to query templates, gracefully handle if table doesn't exist
        try:
            if command_type:
                templates = AIFineTuningTemplate.objects.filter(
                    command_type=command_type,
                    is_active=True
                ).order_by('name')
                for template in templates:
                    choices.append((f'template_{template.id}', template.name))
            else:
                templates = AIFineTuningTemplate.objects.filter(
                    is_active=True
                ).order_by('command_type', 'name')
                for template in templates:
                    display_name = f'{template.name} ({template.get_command_type_display()})'
                    choices.append((f'template_{template.id}', display_name))
        except Exception:
            # If query fails (table doesn't exist), return empty list
            # This allows the form to work even if migration hasn't run
            pass
        
        return choices
    
    def _format_existing_command_data(self) -> None:
        """Format existing command_data as JSON for editing."""
        if not (self.instance and self.instance.pk and self.instance.command_data):
            return
        
        try:
            formatted_json = json.dumps(self.instance.command_data, indent=2)
            self.initial['command_data'] = formatted_json
        except (TypeError, ValueError):
            # If formatting fails, leave as is
            pass
    
    @staticmethod
    def _get_default_templates() -> Dict[str, Dict[str, Any]]:
        """
        Get default template configurations.
        
        Returns:
            Dictionary mapping command types to template data
        """
        return {
            'fine_tune': {
                'name': 'Fine-tune Model (Default)',
                'data': {
                    'model': 'gpt-3.5-turbo',
                    'hyperparameters': {
                        'learning_rate': 0.0001,
                        'batch_size': 4,
                        'n_epochs': 3
                    },
                    'suffix': None,
                    'validation_file': None
                }
            },
            'update_prompt': {
                'name': 'Update System Prompt (Default)',
                'data': {
                    'prompt': (
                        'You are a helpful research assistant specialized in '
                        'statistical analysis and data interpretation.'
                    ),
                    'temperature': 0.7,
                    'max_tokens': 2000
                }
            },
            'add_context': {
                'name': 'Add Context Data (Default)',
                'data': {
                    'context_type': 'knowledge_base',
                    'embedding_model': 'text-embedding-ada-002',
                    'max_context_length': 4000
                }
            },
            'test_model': {
                'name': 'Test Model (Default)',
                'data': {
                    'test_message': 'Hello, how are you?',
                    'temperature': 0.7,
                    'max_tokens': 150,
                    'top_p': 1.0,
                    'frequency_penalty': 0.0,
                    'presence_penalty': 0.0
                }
            },
            'reset_model': {
                'name': 'Reset Model (Default)',
                'data': {
                    'confirm_reset': True,
                    'backup_before_reset': True
                }
            },
            'other': {
                'name': 'Other (Default)',
                'data': {
                    'parameters': {},
                    'options': {}
                }
            }
        }
    
    def clean_command_data(self) -> Dict[str, Any]:
        """
        Validate and parse JSON command data.
        
        Returns:
            Parsed JSON as dictionary
            
        Raises:
            forms.ValidationError: If JSON is invalid
        """
        data = self.cleaned_data.get('command_data', '')
        
        if not data or (isinstance(data, str) and data.strip() == ''):
            return {}
        
        if isinstance(data, dict):
            return data
        
        try:
            parsed = json.loads(data)
            return parsed
        except (json.JSONDecodeError, TypeError) as e:
            raise forms.ValidationError(f'Invalid JSON: {str(e)}')
    
    def clean(self) -> Dict[str, Any]:
        """
        Clean form data.
        
        Returns:
            Cleaned form data dictionary
        """
        cleaned_data = super().clean()
        # template_select is not a model field, used only for UI
        return cleaned_data
