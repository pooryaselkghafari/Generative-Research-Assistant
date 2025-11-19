"""
Service for handling AI fine-tuning operations.

This service encapsulates all business logic for fine-tuning the AI model,
including file management, command processing, and integration with AI providers.
"""
from typing import Dict, Any, List, Optional, Tuple
from django.utils import timezone
from engine.models import AIFineTuningFile, AIFineTuningCommand


class AIFineTuningService:
    """Service for managing AI fine-tuning operations."""
    
    @staticmethod
    def process_fine_tune_command(command: AIFineTuningCommand) -> Dict[str, Any]:
        """
        Process a fine-tuning command.
        
        Args:
            command: The AIFineTuningCommand instance to process
            
        Returns:
            dict with 'success' (bool) and 'message' (str)
        """
        command.status = AIFineTuningCommand.STATUS_PROCESSING
        command.save()
        
        try:
            result = AIFineTuningService._route_command(command)
            command.status = (
                AIFineTuningCommand.STATUS_COMPLETED
                if result['success']
                else AIFineTuningCommand.STATUS_FAILED
            )
            command.result = result['message']
            command.completed_at = timezone.now()
            command.save()
            return result
        except Exception as e:
            command.status = AIFineTuningCommand.STATUS_FAILED
            command.result = f"Error: {str(e)}"
            command.completed_at = timezone.now()
            command.save()
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def _route_command(command: AIFineTuningCommand) -> Dict[str, Any]:
        """
        Route command to appropriate handler based on type.
        
        Args:
            command: The command to process
            
        Returns:
            dict with 'success' and 'message'
        """
        handlers = {
            AIFineTuningCommand.COMMAND_TYPE_FINE_TUNE: (
                AIFineTuningService._process_fine_tune
            ),
            AIFineTuningCommand.COMMAND_TYPE_UPDATE_PROMPT: (
                AIFineTuningService._process_update_prompt
            ),
            AIFineTuningCommand.COMMAND_TYPE_ADD_CONTEXT: (
                AIFineTuningService._process_add_context
            ),
            AIFineTuningCommand.COMMAND_TYPE_TEST_MODEL: (
                AIFineTuningService._process_test_model
            ),
            AIFineTuningCommand.COMMAND_TYPE_RESET_MODEL: (
                AIFineTuningService._process_reset_model
            ),
        }
        
        handler = handlers.get(command.command_type)
        if not handler:
            return {
                'success': False,
                'message': f'Unknown command type: {command.command_type}'
            }
        
        files = command.files.all()
        return handler(files, command.command_data)
    
    @staticmethod
    def _process_fine_tune(
        files: List[AIFineTuningFile],
        command_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process fine-tuning with files.
        
        Args:
            files: List of AIFineTuningFile objects
            command_data: Additional command parameters
            
        Returns:
            dict with 'success' and 'message'
        """
        if not files:
            return {
                'success': False,
                'message': 'No files provided for fine-tuning'
            }
        
        # Integrate with AI provider
        from engine.integrations.ai_provider import AIService
        result = AIService.fine_tune(files, command_data)
        return result
    
    @staticmethod
    def _process_update_prompt(
        files: List[AIFineTuningFile],
        command_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update system prompt.
        
        Args:
            files: Not used for this command type
            command_data: Must contain 'prompt' key
            
        Returns:
            dict with 'success' and 'message'
        """
        prompt = command_data.get('prompt', '')
        if not prompt:
            return {'success': False, 'message': 'No prompt provided'}
        
        # Integrate with AI provider to update system prompt
        from engine.integrations.ai_provider import AIService
        result = AIService.update_system_prompt(prompt)
        return result
    
    @staticmethod
    def _process_add_context(
        files: List[AIFineTuningFile],
        command_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Add context data from files.
        
        Args:
            files: List of AIFineTuningFile objects
            command_data: Additional command parameters
            
        Returns:
            dict with 'success' and 'message'
        """
        if not files:
            return {'success': False, 'message': 'No files provided'}
        
        # Integrate with AI provider to add context
        from engine.integrations.ai_provider import AIService
        result = AIService.add_context(files, command_data)
        return result
    
    @staticmethod
    def _process_test_model(
        files: List[AIFineTuningFile],
        command_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Test the current model.
        
        Args:
            files: Not used for this command type
            command_data: May contain 'test_message' key
            
        Returns:
            dict with 'success' and 'message'
        """
        test_message = command_data.get('test_message', 'Hello, how are you?')
        
        # Integrate with AI provider to test model
        from engine.integrations.ai_provider import AIService
        result = AIService.test_model(test_message)
        if result.get('success'):
            response_text = result.get('response', 'No response')
            return {'success': True, 'message': f'Test response: {response_text}'}
        return result
    
    @staticmethod
    def _process_reset_model(
        files: List[AIFineTuningFile],
        command_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Reset model to default state.
        
        Args:
            files: Not used for this command type
            command_data: Not used for this command type
            
        Returns:
            dict with 'success' and 'message'
        """
        # Integrate with AI provider to reset model
        from engine.integrations.ai_provider import AIService
        result = AIService.reset_model()
        return result
    
    @staticmethod
    def get_active_files() -> List[AIFineTuningFile]:
        """
        Get all active fine-tuning files.
        
        Returns:
            QuerySet of active AIFineTuningFile objects
        """
        return list(
            AIFineTuningFile.objects.filter(is_active=True)
            .select_related('uploaded_by')
            .order_by('-uploaded_at')
        )
    
    @staticmethod
    def get_recent_commands(limit: int = 10) -> List[AIFineTuningCommand]:
        """
        Get recent fine-tuning commands.
        
        Args:
            limit: Maximum number of commands to return
            
        Returns:
            List of AIFineTuningCommand objects
        """
        return list(
            AIFineTuningCommand.objects.all()
            .select_related('created_by')
            .prefetch_related('files')
            .order_by('-created_at')[:limit]
        )
