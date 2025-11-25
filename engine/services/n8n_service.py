"""
Service for interacting with n8n webhooks.

This service handles calling n8n webhook endpoints, constructing payloads,
and parsing responses.
"""
import json
import logging
import requests
import re
from typing import Dict, Any, Optional
from django.conf import settings

logger = logging.getLogger(__name__)


class N8nService:
    """Service for calling n8n webhook endpoints."""
    
    # Default timeout for n8n webhook calls (seconds)
    DEFAULT_TIMEOUT = int(getattr(settings, 'N8N_WEBHOOK_TIMEOUT', 30))
    
    # Maximum number of retries for failed requests
    MAX_RETRIES = int(getattr(settings, 'N8N_MAX_RETRIES', 2))
    
    # n8n base URL for direct calls (when Django calls n8n from backend)
    # Use localhost since both containers are on host network
    N8N_DIRECT_URL = getattr(settings, 'N8N_DIRECT_URL', 'http://127.0.0.1:5678')
    
    @staticmethod
    def _normalize_webhook_url(webhook_url: str) -> str:
        """
        Convert public webhook URL to direct localhost URL for backend calls.
        
        Converts URLs like:
        - https://generativera.com/n8n/webhook/abc123 -> http://127.0.0.1:5678/webhook/abc123
        - http://localhost:5678/webhook/abc123 -> http://127.0.0.1:5678/webhook/abc123 (no change)
        
        Important: n8n webhooks should be called at /webhook/ID (not /n8n/webhook/ID)
        when calling directly from backend.
        
        Args:
            webhook_url: Original webhook URL (public or direct)
            
        Returns:
            Normalized URL for direct backend calls (removes /n8n/ prefix if present)
        """
        if not webhook_url:
            return webhook_url
        
        # Extract webhook ID from URL
        # Pattern: https://domain.com/n8n/webhook/ID or /n8n/webhook/ID or /webhook/ID
        match = re.search(r'/webhook/([^/?]+)', webhook_url)
        if match:
            webhook_id = match.group(1)
            # Build direct URL - use /webhook/ID (NOT /n8n/webhook/ID)
            # n8n expects webhooks at /webhook/ID when called directly
            return f"{N8nService.N8N_DIRECT_URL}/webhook/{webhook_id}"
        
        # If already a direct URL or doesn't match pattern, return as-is
        return webhook_url
    
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
        
        # Normalize webhook URL (convert public URL to direct localhost URL)
        normalized_url = N8nService._normalize_webhook_url(webhook_url)
        
        # Validate webhook URL
        if not normalized_url or not normalized_url.startswith(('http://', 'https://')):
            raise ValueError(f"Invalid webhook URL: {normalized_url} (original: {webhook_url})")
        
        # Log URL conversion for debugging
        if normalized_url != webhook_url:
            logger.debug(
                f"Converted webhook URL: {webhook_url} -> {normalized_url}",
                extra={'original_url': webhook_url, 'normalized_url': normalized_url}
            )
        
        # Sanitize payload (remove None values, ensure JSON-serializable)
        sanitized_payload = N8nService._sanitize_payload(payload)
        
        last_exception = None
        for attempt in range(retries + 1):
            try:
                logger.info(
                    f"Calling n8n webhook: {normalized_url} (attempt {attempt + 1}/{retries + 1})",
                    extra={
                        'webhook_url': normalized_url,
                        'original_url': webhook_url,
                        'attempt': attempt + 1,
                        'payload_keys': list(sanitized_payload.keys())
                    }
                )
                
                response = requests.post(
                    normalized_url,
                    json=sanitized_payload,
                    timeout=timeout,
                    headers={
                        'Content-Type': 'application/json',
                        'User-Agent': 'GRA-Chatbot/1.0'
                    }
                )
                
                # Check for error status codes and provide detailed error info
                if not response.ok:
                    error_body = response.text[:1000] if response.text else "(empty response)"
                    logger.error(
                        f"n8n webhook returned error status {response.status_code}",
                        extra={
                            'webhook_url': normalized_url,
                            'original_url': webhook_url,
                            'status_code': response.status_code,
                            'response_text': error_body,
                            'payload_keys': list(sanitized_payload.keys())
                        }
                    )
                    # Try to parse error message from response
                    try:
                        error_json = response.json()
                        error_message = error_json.get('message') or error_json.get('error') or str(error_json)
                    except:
                        error_message = error_body
                    
                    raise requests.exceptions.HTTPError(
                        f"{response.status_code} Server Error: {error_message} for url: {normalized_url}",
                        response=response
                    )
                
                # Raise an exception for any other bad status codes
                response.raise_for_status()
                
                # Check if response is empty
                if not response.text or not response.text.strip():
                    logger.error(
                        f"Empty response from n8n webhook",
                        extra={
                            'webhook_url': normalized_url,
                            'original_url': webhook_url,
                            'status_code': response.status_code,
                            'headers': dict(response.headers)
                        }
                    )
                    raise ValueError(
                        "Empty response from n8n webhook. "
                        "Make sure your n8n workflow has a 'Respond to Webhook' node that returns JSON with a 'reply' field."
                    )
                
                # Parse JSON response
                try:
                    result = response.json()
                except json.JSONDecodeError as e:
                    response_preview = response.text[:500] if response.text else "(empty)"
                    logger.error(
                        f"Invalid JSON response from n8n webhook: {e}",
                        extra={
                            'webhook_url': normalized_url,
                            'original_url': webhook_url,
                            'status_code': response.status_code,
                            'content_type': response.headers.get('Content-Type', 'unknown'),
                            'response_text': response_preview
                        }
                    )
                    raise ValueError(
                        f"Invalid JSON response from n8n: {e}. "
                        f"Response was: {response_preview}. "
                        "Make sure your n8n workflow returns valid JSON with a 'reply' field."
                    )
                
                # Validate response structure
                N8nService._validate_response(result)
                
                logger.info(
                    f"Successfully called n8n webhook: {normalized_url}",
                    extra={
                        'webhook_url': normalized_url,
                        'original_url': webhook_url,
                        'response_keys': list(result.keys()) if isinstance(result, dict) else None
                    }
                )
                
                return result
                
            except requests.exceptions.Timeout as e:
                last_exception = e
                logger.warning(
                    f"Timeout calling n8n webhook (attempt {attempt + 1}/{retries + 1}): {e}",
                    extra={'webhook_url': normalized_url, 'original_url': webhook_url, 'timeout': timeout}
                )
                if attempt < retries:
                    continue
                raise
                
            except requests.exceptions.RequestException as e:
                last_exception = e
                logger.error(
                    f"Error calling n8n webhook (attempt {attempt + 1}/{retries + 1}): {e}",
                    extra={'webhook_url': normalized_url, 'original_url': webhook_url, 'error': str(e)}
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
            elif 'output' in response:
                # Handle n8n's default output format
                output = response['output']
                # If output is a string, use it directly
                if isinstance(output, str):
                    response['reply'] = output
                # If output is a list, extract message from first item
                elif isinstance(output, list) and len(output) > 0:
                    first_item = output[0]
                    # If first item is a dict, try to extract message/content
                    if isinstance(first_item, dict):
                        # Try common OpenAI response structures
                        if 'choices' in first_item and isinstance(first_item['choices'], list) and len(first_item['choices']) > 0:
                            choice = first_item['choices'][0]
                            if isinstance(choice, dict) and 'message' in choice:
                                message = choice['message']
                                if isinstance(message, dict):
                                    response['reply'] = message.get('content') or message.get('text') or str(message)
                                else:
                                    response['reply'] = str(message)
                            else:
                                response['reply'] = str(choice)
                        # Try direct message/content fields
                        else:
                            response['reply'] = (
                                first_item.get('message') or 
                                first_item.get('content') or 
                                first_item.get('text') or
                                first_item.get('response') or
                                str(first_item)
                            )
                    # If first item is a string, use it
                    elif isinstance(first_item, str):
                        response['reply'] = first_item
                    # Otherwise convert to string
                    else:
                        response['reply'] = str(first_item)
                # If output is a dict, try to extract message/content
                elif isinstance(output, dict):
                    # Try OpenAI structure first
                    if 'choices' in output and isinstance(output['choices'], list) and len(output['choices']) > 0:
                        choice = output['choices'][0]
                        if isinstance(choice, dict) and 'message' in choice:
                            message = choice['message']
                            if isinstance(message, dict):
                                response['reply'] = message.get('content') or message.get('text') or str(message)
                            else:
                                response['reply'] = str(message)
                        else:
                            response['reply'] = str(choice)
                    # Try direct fields
                    else:
                        response['reply'] = (
                            output.get('message') or 
                            output.get('content') or 
                            output.get('text') or 
                            output.get('response') or
                            str(output)
                        )
                else:
                    response['reply'] = str(output)
            else:
                raise ValueError(
                    "n8n response must contain 'reply', 'message', 'response', or 'output' field. "
                    f"Received keys: {list(response.keys())}"
                )
        
        # Ensure 'reply' is a string (convert if needed)
        reply = response.get('reply')
        if not isinstance(reply, str):
            # Try to extract string from list/dict structures
            if isinstance(reply, list) and len(reply) > 0:
                # Get first item from list
                first_item = reply[0]
                if isinstance(first_item, dict):
                    # Try to extract message/content from dict
                    reply = (
                        first_item.get('message') or 
                        first_item.get('content') or 
                        first_item.get('text') or
                        first_item.get('response') or
                        str(first_item)
                    )
                else:
                    reply = str(first_item)
            elif isinstance(reply, dict):
                # Try to extract message from dict
                reply = (
                    reply.get('message') or 
                    reply.get('content') or 
                    reply.get('text') or
                    reply.get('response') or
                    str(reply)
                )
            else:
                # Convert to string as last resort
                reply = str(reply) if reply is not None else ''
            
            # Update response with converted reply
            response['reply'] = reply
        
        # Final check - ensure it's a string
        if not isinstance(response.get('reply'), str):
            raise ValueError(f"n8n response 'reply' field must be a string after conversion, got {type(response.get('reply'))}")
    
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

