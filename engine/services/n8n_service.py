"""
Service for interacting with n8n webhooks.

This service handles calling n8n webhook endpoints, constructing payloads,
and parsing responses.
"""
import json
import logging
import requests
from typing import Dict, Any, Optional
from django.conf import settings

logger = logging.getLogger(__name__)


class N8nService:
    """Service for calling n8n webhook endpoints."""
    
    # Default timeout for n8n webhook calls (seconds)
    DEFAULT_TIMEOUT = int(getattr(settings, 'N8N_WEBHOOK_TIMEOUT', 30))
    
    # Maximum number of retries for failed requests
    MAX_RETRIES = int(getattr(settings, 'N8N_MAX_RETRIES', 2))
    
    @staticmethod
    def call_webhook(
        webhook_url: str,
        payload: Dict[str, Any],
        timeout: Optional[int] = None,
        retries: int = None
    ) -> Dict[str, Any]:
        """
        Call an n8n webhook endpoint with the given payload.
        
        Args:
            webhook_url: Full URL to the n8n webhook endpoint
            payload: Dictionary of data to send to the webhook
            timeout: Request timeout in seconds (defaults to DEFAULT_TIMEOUT)
            retries: Number of retry attempts (defaults to MAX_RETRIES)
            
        Returns:
            Dictionary containing the response from n8n
            
        Raises:
            requests.exceptions.RequestException: If the request fails after retries
            ValueError: If the response is invalid or missing required fields
        """
        if timeout is None:
            timeout = N8nService.DEFAULT_TIMEOUT
        if retries is None:
            retries = N8nService.MAX_RETRIES
        
        # Validate webhook URL
        if not webhook_url or not webhook_url.startswith(('http://', 'https://')):
            raise ValueError(f"Invalid webhook URL: {webhook_url}")
        
        # Sanitize payload (remove None values, ensure JSON-serializable)
        sanitized_payload = N8nService._sanitize_payload(payload)
        
        last_exception = None
        for attempt in range(retries + 1):
            try:
                logger.info(
                    f"Calling n8n webhook: {webhook_url} (attempt {attempt + 1}/{retries + 1})",
                    extra={
                        'webhook_url': webhook_url,
                        'attempt': attempt + 1,
                        'payload_keys': list(sanitized_payload.keys())
                    }
                )
                
                response = requests.post(
                    webhook_url,
                    json=sanitized_payload,
                    timeout=timeout,
                    headers={
                        'Content-Type': 'application/json',
                        'User-Agent': 'GRA-Chatbot/1.0'
                    }
                )
                
                # Raise an exception for bad status codes
                response.raise_for_status()
                
                # Parse JSON response
                try:
                    result = response.json()
                except json.JSONDecodeError as e:
                    logger.error(
                        f"Invalid JSON response from n8n webhook: {e}",
                        extra={'webhook_url': webhook_url, 'response_text': response.text[:500]}
                    )
                    raise ValueError(f"Invalid JSON response from n8n: {e}")
                
                # Validate response structure
                N8nService._validate_response(result)
                
                logger.info(
                    f"Successfully called n8n webhook: {webhook_url}",
                    extra={
                        'webhook_url': webhook_url,
                        'response_keys': list(result.keys()) if isinstance(result, dict) else None
                    }
                )
                
                return result
                
            except requests.exceptions.Timeout as e:
                last_exception = e
                logger.warning(
                    f"Timeout calling n8n webhook (attempt {attempt + 1}/{retries + 1}): {e}",
                    extra={'webhook_url': webhook_url, 'timeout': timeout}
                )
                if attempt < retries:
                    continue
                raise
                
            except requests.exceptions.RequestException as e:
                last_exception = e
                logger.error(
                    f"Error calling n8n webhook (attempt {attempt + 1}/{retries + 1}): {e}",
                    extra={'webhook_url': webhook_url, 'error': str(e)}
                )
                if attempt < retries:
                    continue
                raise
        
        # If we get here, all retries failed
        if last_exception:
            raise last_exception
        raise Exception("Failed to call n8n webhook: unknown error")
    
    @staticmethod
    def _sanitize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize payload by removing None values and ensuring JSON-serializable types.
        
        Args:
            payload: Raw payload dictionary
            
        Returns:
            Sanitized payload dictionary
        """
        sanitized = {}
        for key, value in payload.items():
            if value is None:
                continue
            if isinstance(value, (dict, list, str, int, float, bool)):
                sanitized[key] = value
            elif hasattr(value, '__dict__'):
                # Convert objects to dict
                sanitized[key] = str(value)
            else:
                # Convert other types to string
                sanitized[key] = str(value)
        return sanitized
    
    @staticmethod
    def _validate_response(response: Dict[str, Any]) -> None:
        """
        Validate that the n8n response has the expected structure.
        
        Args:
            response: Response dictionary from n8n
            
        Raises:
            ValueError: If response is invalid
        """
        if not isinstance(response, dict):
            raise ValueError("n8n response must be a JSON object")
        
        # Check for required 'reply' field (main chatbot message)
        if 'reply' not in response:
            # If no 'reply' field, check for common alternatives
            if 'message' in response:
                response['reply'] = response['message']
            elif 'response' in response:
                response['reply'] = response['response']
            else:
                raise ValueError(
                    "n8n response must contain 'reply', 'message', or 'response' field. "
                    f"Received keys: {list(response.keys())}"
                )
        
        # Ensure 'reply' is a string
        if not isinstance(response.get('reply'), str):
            raise ValueError(f"n8n response 'reply' field must be a string, got {type(response.get('reply'))}")
    
    @staticmethod
    def build_chatbot_payload(
        user_id: int,
        message: str,
        template_id: Optional[int] = None,
        mode_key: Optional[str] = None,
        conversation_id: Optional[str] = None,
        chat_history: Optional[list] = None,
        additional_parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Build a standardized payload for n8n webhook calls from chatbot requests.
        
        Args:
            user_id: ID of the user making the request
            message: User's message text
            template_id: ID of the agent template being used
            mode_key: Mode key of the agent template
            conversation_id: Optional conversation ID for context
            chat_history: Optional list of previous messages
            additional_parameters: Optional additional parameters to merge
            
        Returns:
            Dictionary payload ready to send to n8n
        """
        payload = {
            'user_id': user_id,
            'message': message,
            'timestamp': None,  # Will be set by n8n or can be set here
        }
        
        if template_id:
            payload['template_id'] = template_id
        if mode_key:
            payload['mode_key'] = mode_key
        if conversation_id:
            payload['conversation_id'] = conversation_id
        if chat_history:
            payload['chat_history'] = chat_history
        
        # Merge additional parameters
        if additional_parameters:
            payload.update(additional_parameters)
        
        return payload

