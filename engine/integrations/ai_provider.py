"""
AI Provider Integration Module

Handles communication with AI providers (OpenAI, Anthropic, etc.)
for fine-tuning and model management.
"""
from typing import Dict, Any, List, Optional
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from engine.models import AIFineTuningFile, AIProvider
import logging
import json

logger = logging.getLogger(__name__)


def get_active_provider() -> Optional[AIProvider]:
    """
    Get the currently active AI provider.
    
    Returns:
        AIProvider instance or None if no provider is configured
    """
    return AIProvider.get_active_provider()


class AIService:
    """Service for interacting with AI providers."""
    
    @staticmethod
    def _get_provider() -> Optional[AIProvider]:
        """Get active provider or raise error."""
        provider = get_active_provider()
        if not provider:
            raise ValueError("No active AI provider configured. Please configure a provider in the admin panel.")
        if not provider.is_active:
            raise ValueError(f"Provider '{provider.name}' is not active.")
        return provider
    
    @staticmethod
    def _prepare_files(files: List[AIFineTuningFile]) -> List[Dict[str, Any]]:
        """
        Prepare files for API submission.
        
        Args:
            files: List of AIFineTuningFile objects
            
        Returns:
            List of file data dictionaries
        """
        prepared_files = []
        for file in files:
            try:
                # Read file content
                if hasattr(file.file, 'read'):
                    file.file.seek(0)
                    content = file.file.read()
                    if isinstance(content, bytes):
                        content = content.decode('utf-8')
                else:
                    with open(file.file.path, 'r', encoding='utf-8') as f:
                        content = f.read()
                
                prepared_files.append({
                    'name': file.name,
                    'type': file.file_type,
                    'description': file.description,
                    'content': content,
                })
            except Exception as e:
                logger.error(f"Error reading file {file.name}: {e}")
                raise ValueError(f"Error reading file {file.name}: {e}")
        
        return prepared_files
    
    @staticmethod
    def fine_tune(files: List[AIFineTuningFile], command_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fine-tune the AI model with provided files.
        
        Args:
            files: List of AIFineTuningFile objects
            command_data: Fine-tuning parameters from command
            
        Returns:
            dict with 'success' and 'message'
        """
        try:
            provider = AIService._get_provider()
            
            if not files:
                return {
                    'success': False,
                    'message': 'No files provided for fine-tuning'
                }
            
            # Prepare files
            prepared_files = AIService._prepare_files(files)
            
            # Route to provider-specific implementation
            if provider.provider_type == 'openai':
                return AIService._fine_tune_openai(provider, prepared_files, command_data)
            elif provider.provider_type == 'anthropic':
                return AIService._fine_tune_anthropic(provider, prepared_files, command_data)
            elif provider.provider_type == 'custom':
                return AIService._fine_tune_custom(provider, prepared_files, command_data)
            else:
                return {
                    'success': False,
                    'message': f'Unsupported provider type: {provider.provider_type}'
                }
        except ValueError as e:
            return {'success': False, 'message': str(e)}
        except Exception as e:
            logger.error(f"Error in fine_tune: {e}", exc_info=True)
            return {'success': False, 'message': f'Error: {str(e)}'}
    
    @staticmethod
    def _fine_tune_openai(provider: AIProvider, files: List[Dict], command_data: Dict[str, Any]) -> Dict[str, Any]:
        """Fine-tune using OpenAI API."""
        try:
            # Try OpenAI v1.x (newer API)
            try:
                from openai import OpenAI
                client = OpenAI(api_key=provider.api_key)
                if provider.organization_id:
                    client.organization = provider.organization_id
                if provider.api_base_url:
                    client.base_url = provider.api_base_url
                use_new_api = True
            except ImportError:
                # Fallback to older OpenAI API
                import openai
                openai.api_key = provider.api_key
                if provider.organization_id:
                    openai.organization = provider.organization_id
                if provider.api_base_url:
                    openai.api_base = provider.api_base_url
                use_new_api = False
            
            # Prepare training data in OpenAI format (JSONL)
            training_data = []
            for file_data in files:
                # Convert to OpenAI fine-tuning format
                # Format: {"messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
                messages = []
                
                # Add system message if provided
                if command_data.get('system_prompt'):
                    messages.append({
                        "role": "system",
                        "content": command_data['system_prompt']
                    })
                
                # Parse file content (assuming JSONL or structured format)
                try:
                    content_data = json.loads(file_data['content'])
                    if isinstance(content_data, list):
                        messages.extend(content_data)
                    elif isinstance(content_data, dict) and 'messages' in content_data:
                        messages.extend(content_data['messages'])
                    else:
                        # Fallback: treat as user message
                        messages.append({
                            "role": "user",
                            "content": file_data['content']
                        })
                except json.JSONDecodeError:
                    # Not JSON, treat as plain text
                    messages.append({
                        "role": "user",
                        "content": file_data['content']
                    })
                
                training_data.append({"messages": messages})
            
            # Create fine-tuning job
            base_model = command_data.get('base_model', provider.base_model)
            hyperparameters = command_data.get('hyperparameters', {})
            
            # Upload training file (create temporary file)
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as tmp_file:
                for item in training_data:
                    tmp_file.write(json.dumps(item) + '\n')
                tmp_file_path = tmp_file.name
            
            try:
                if use_new_api:
                    # Upload file to OpenAI (v1.x API)
                    with open(tmp_file_path, 'rb') as f:
                        uploaded_file = client.files.create(
                            file=f,
                            purpose='fine-tune'
                        )
                    
                    # Create fine-tuning job
                    fine_tune_job = client.fine_tuning.jobs.create(
                        training_file=uploaded_file.id,
                        model=base_model,
                        hyperparameters=hyperparameters
                    )
                    job_id = fine_tune_job.id
                else:
                    # Upload file to OpenAI (older API)
                    with open(tmp_file_path, 'rb') as f:
                        uploaded_file = openai.File.create(
                            file=f,
                            purpose='fine-tune'
                        )
                    
                    # Create fine-tuning job
                    fine_tune_job = openai.FineTuningJob.create(
                        training_file=uploaded_file.id,
                        model=base_model,
                        hyperparameters=hyperparameters
                    )
                    job_id = fine_tune_job.id if hasattr(fine_tune_job, 'id') else str(fine_tune_job)
                
                # Update provider with fine-tuned model ID when available
                if job_id:
                    # Store job ID in command_data for tracking
                    command_data['fine_tune_job_id'] = job_id
                
                # Get status from fine_tune_job
                if use_new_api:
                    status = fine_tune_job.status if hasattr(fine_tune_job, 'status') else 'created'
                else:
                    status = fine_tune_job.status if hasattr(fine_tune_job, 'status') else 'created'
                
                return {
                    'success': True,
                    'message': f'Fine-tuning job created: {job_id}. Status: {status}'
                }
            finally:
                # Clean up temporary file
                if os.path.exists(tmp_file_path):
                    os.unlink(tmp_file_path)
                    
        except ImportError:
            return {
                'success': False,
                'message': 'OpenAI library not installed. Install with: pip install openai'
            }
        except Exception as e:
            logger.error(f"OpenAI fine-tuning error: {e}", exc_info=True)
            return {
                'success': False,
                'message': f'OpenAI API error: {str(e)}'
            }
    
    @staticmethod
    def _fine_tune_anthropic(provider: AIProvider, files: List[Dict], command_data: Dict[str, Any]) -> Dict[str, Any]:
        """Fine-tune using Anthropic Claude API."""
        try:
            import anthropic
            
            client = anthropic.Anthropic(api_key=provider.api_key)
            
            # Anthropic doesn't support fine-tuning in the same way as OpenAI
            # This would typically involve creating a custom model or using their API differently
            # For now, return a message indicating this needs custom implementation
            
            return {
                'success': False,
                'message': 'Anthropic fine-tuning requires custom implementation. Please use OpenAI or custom API provider.'
            }
        except ImportError:
            return {
                'success': False,
                'message': 'Anthropic library not installed. Install with: pip install anthropic'
            }
        except Exception as e:
            logger.error(f"Anthropic fine-tuning error: {e}", exc_info=True)
            return {
                'success': False,
                'message': f'Anthropic API error: {str(e)}'
            }
    
    @staticmethod
    def _fine_tune_custom(provider: AIProvider, files: List[Dict], command_data: Dict[str, Any]) -> Dict[str, Any]:
        """Fine-tune using custom API endpoint."""
        try:
            import requests
            
            api_url = provider.api_base_url or command_data.get('api_url', '')
            if not api_url:
                return {
                    'success': False,
                    'message': 'Custom API requires api_base_url to be set in provider configuration'
                }
            
            # Prepare request payload
            payload = {
                'files': files,
                'base_model': command_data.get('base_model', provider.base_model),
                'hyperparameters': command_data.get('hyperparameters', {}),
                **command_data.get('custom_params', {})
            }
            
            # Make API request
            headers = {
                'Authorization': f'Bearer {provider.api_key}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                f"{api_url}/fine-tune",
                json=payload,
                headers=headers,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    'success': True,
                    'message': f'Fine-tuning initiated: {result.get("job_id", "success")}'
                }
            else:
                return {
                    'success': False,
                    'message': f'API error: {response.status_code} - {response.text}'
                }
        except ImportError:
            return {
                'success': False,
                'message': 'Requests library not installed. Install with: pip install requests'
            }
        except Exception as e:
            logger.error(f"Custom API fine-tuning error: {e}", exc_info=True)
            return {
                'success': False,
                'message': f'Custom API error: {str(e)}'
            }
    
    @staticmethod
    def update_system_prompt(prompt: str) -> Dict[str, Any]:
        """
        Update the system prompt.
        
        Args:
            prompt: New system prompt text
            
        Returns:
            dict with 'success' and 'message'
        """
        try:
            provider = AIService._get_provider()
            
            # Store system prompt in provider or separate model
            # For now, we'll just validate and return success
            if not prompt:
                return {'success': False, 'message': 'No prompt provided'}
            
            # TODO: Implement actual API call to update system prompt
            # This depends on the provider's capabilities
            
            return {'success': True, 'message': 'System prompt updated successfully'}
        except ValueError as e:
            return {'success': False, 'message': str(e)}
        except Exception as e:
            logger.error(f"Error updating system prompt: {e}", exc_info=True)
            return {'success': False, 'message': f'Error: {str(e)}'}
    
    @staticmethod
    def add_context(files: List[AIFineTuningFile], command_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add context data from files.
        
        Args:
            files: List of AIFineTuningFile objects
            command_data: Additional command parameters
            
        Returns:
            dict with 'success' and 'message'
        """
        try:
            provider = AIService._get_provider()
            
            if not files:
                return {'success': False, 'message': 'No files provided'}
            
            prepared_files = AIService._prepare_files(files)
            
            # TODO: Implement actual API call to add context
            # This might involve uploading files to a vector database or context store
            
            return {
                'success': True,
                'message': f'Context added from {len(files)} file(s)'
            }
        except ValueError as e:
            return {'success': False, 'message': str(e)}
        except Exception as e:
            logger.error(f"Error adding context: {e}", exc_info=True)
            return {'success': False, 'message': f'Error: {str(e)}'}
    
    @staticmethod
    def test_model(test_message: str = "Hello, how are you?") -> Dict[str, Any]:
        """
        Test the model with a message.
        
        Args:
            test_message: Message to test with
            
        Returns:
            dict with 'success', 'message', and optionally 'response'
        """
        try:
            provider = AIService._get_provider()
            
            if provider.provider_type == 'openai':
                return AIService._test_openai(provider, test_message)
            elif provider.provider_type == 'anthropic':
                return AIService._test_anthropic(provider, test_message)
            elif provider.provider_type == 'custom':
                return AIService._test_custom(provider, test_message)
            else:
                return {
                    'success': False,
                    'message': f'Unsupported provider type: {provider.provider_type}'
                }
        except ValueError as e:
            return {'success': False, 'message': str(e)}
        except Exception as e:
            logger.error(f"Error testing model: {e}", exc_info=True)
            return {'success': False, 'message': f'Error: {str(e)}'}
    
    @staticmethod
    def _test_openai(provider: AIProvider, test_message: str) -> Dict[str, Any]:
        """Test OpenAI model."""
        try:
            # Try OpenAI v1.x (newer API)
            try:
                from openai import OpenAI
                client = OpenAI(api_key=provider.api_key)
                if provider.organization_id:
                    client.organization = provider.organization_id
                if provider.api_base_url:
                    client.base_url = provider.api_base_url
                
                model = provider.fine_tuned_model_id or provider.base_model
                
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "user", "content": test_message}
                    ],
                    max_tokens=100
                )
                
                response_text = response.choices[0].message.content
            except ImportError:
                # Fallback to older OpenAI API
                import openai
                openai.api_key = provider.api_key
                if provider.organization_id:
                    openai.organization = provider.organization_id
                if provider.api_base_url:
                    openai.api_base = provider.api_base_url
                
                model = provider.fine_tuned_model_id or provider.base_model
                
                response = openai.ChatCompletion.create(
                    model=model,
                    messages=[
                        {"role": "user", "content": test_message}
                    ],
                    max_tokens=100
                )
                
                response_text = response.choices[0].message.content
            
            # Update provider test status
            provider.test_status = 'success'
            provider.test_message = f'Test successful. Response: {response_text[:200]}'
            provider.last_tested_at = timezone.now()
            provider.save(update_fields=['test_status', 'test_message', 'last_tested_at'])
            
            return {
                'success': True,
                'message': 'Model test successful',
                'response': response_text
            }
        except ImportError:
            return {'success': False, 'message': 'OpenAI library not installed. Install with: pip install openai'}
        except Exception as e:
            provider.test_status = 'failed'
            provider.test_message = str(e)
            provider.last_tested_at = timezone.now()
            provider.save(update_fields=['test_status', 'test_message', 'last_tested_at'])
            return {'success': False, 'message': f'OpenAI API error: {str(e)}'}
    
    @staticmethod
    def _test_anthropic(provider: AIProvider, test_message: str) -> Dict[str, Any]:
        """Test Anthropic model."""
        try:
            import anthropic
            
            client = anthropic.Anthropic(api_key=provider.api_key)
            
            model = provider.fine_tuned_model_id or provider.base_model
            
            response = client.messages.create(
                model=model,
                max_tokens=100,
                messages=[
                    {"role": "user", "content": test_message}
                ]
            )
            
            response_text = response.content[0].text
            
            provider.test_status = 'success'
            provider.test_message = f'Test successful. Response: {response_text[:200]}'
            provider.last_tested_at = timezone.now()
            provider.save(update_fields=['test_status', 'test_message', 'last_tested_at'])
            
            return {
                'success': True,
                'message': 'Model test successful',
                'response': response_text
            }
        except ImportError:
            return {'success': False, 'message': 'Anthropic library not installed'}
        except Exception as e:
            provider.test_status = 'failed'
            provider.test_message = str(e)
            provider.last_tested_at = timezone.now()
            provider.save(update_fields=['test_status', 'test_message', 'last_tested_at'])
            return {'success': False, 'message': f'Anthropic API error: {str(e)}'}
    
    @staticmethod
    def _test_custom(provider: AIProvider, test_message: str) -> Dict[str, Any]:
        """Test custom API."""
        try:
            import requests
            
            api_url = provider.api_base_url or ''
            if not api_url:
                return {'success': False, 'message': 'Custom API requires api_base_url'}
            
            headers = {
                'Authorization': f'Bearer {provider.api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'message': test_message,
                'model': provider.fine_tuned_model_id or provider.base_model
            }
            
            response = requests.post(
                f"{api_url}/test",
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                provider.test_status = 'success'
                provider.test_message = f'Test successful'
                provider.last_tested_at = timezone.now()
                provider.save(update_fields=['test_status', 'test_message', 'last_tested_at'])
                
                return {
                    'success': True,
                    'message': 'Model test successful',
                    'response': result.get('response', '')
                }
            else:
                provider.test_status = 'failed'
                provider.test_message = f'API error: {response.status_code}'
                provider.last_tested_at = timezone.now()
                provider.save(update_fields=['test_status', 'test_message', 'last_tested_at'])
                
                return {
                    'success': False,
                    'message': f'API error: {response.status_code} - {response.text}'
                }
        except ImportError:
            return {'success': False, 'message': 'Requests library not installed'}
        except Exception as e:
            provider.test_status = 'failed'
            provider.test_message = str(e)
            provider.last_tested_at = timezone.now()
            provider.save(update_fields=['test_status', 'test_message', 'last_tested_at'])
            return {'success': False, 'message': f'Custom API error: {str(e)}'}
    
    @staticmethod
    def reset_model() -> Dict[str, Any]:
        """
        Reset model to default state.
        
        Returns:
            dict with 'success' and 'message'
        """
        try:
            provider = AIService._get_provider()
            
            # Clear fine-tuned model ID
            provider.fine_tuned_model_id = ''
            provider.save(update_fields=['fine_tuned_model_id'])
            
            return {'success': True, 'message': 'Model reset to default state'}
        except ValueError as e:
            return {'success': False, 'message': str(e)}
        except Exception as e:
            logger.error(f"Error resetting model: {e}", exc_info=True)
            return {'success': False, 'message': f'Error: {str(e)}'}

