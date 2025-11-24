"""
Unit tests for n8n service.

Categories: Unit Tests, Security Tests
"""
import pytest
import json
from unittest.mock import patch, Mock
import requests
from engine.services.n8n_service import N8nService


class TestN8nService:
    """Test N8nService methods."""
    
    def test_sanitize_payload(self):
        """Test payload sanitization."""
        payload = {
            'key1': 'value1',
            'key2': None,
            'key3': 123,
            'key4': {'nested': 'data'}
        }
        sanitized = N8nService._sanitize_payload(payload)
        assert 'key1' in sanitized
        assert 'key2' not in sanitized  # None values removed
        assert sanitized['key3'] == 123
        assert sanitized['key4'] == {'nested': 'data'}
    
    def test_validate_response_valid(self):
        """Test response validation with valid response."""
        response = {
            'reply': 'Valid response',
            'metadata': {}
        }
        # Should not raise
        N8nService._validate_response(response)
    
    def test_validate_response_missing_reply(self):
        """Test response validation with missing reply."""
        response = {
            'metadata': {}
        }
        with pytest.raises(ValueError, match="reply"):
            N8nService._validate_response(response)
    
    def test_validate_response_alternative_fields(self):
        """Test that 'message' or 'response' fields are accepted."""
        # Test with 'message'
        response1 = {'message': 'Test message'}
        N8nService._validate_response(response1)
        assert response1['reply'] == 'Test message'
        
        # Test with 'response'
        response2 = {'response': 'Test response'}
        N8nService._validate_response(response2)
        assert response2['reply'] == 'Test response'
    
    def test_validate_response_not_dict(self):
        """Test validation fails for non-dict responses."""
        with pytest.raises(ValueError, match="JSON object"):
            N8nService._validate_response("not a dict")
    
    def test_build_chatbot_payload(self):
        """Test building chatbot payload."""
        payload = N8nService.build_chatbot_payload(
            user_id=123,
            message="Hello",
            template_id=456,
            mode_key="test_mode",
            conversation_id="conv_123",
            chat_history=[{'role': 'user', 'content': 'Previous'}],
            additional_parameters={'custom': 'value'}
        )
        assert payload['user_id'] == 123
        assert payload['message'] == "Hello"
        assert payload['template_id'] == 456
        assert payload['mode_key'] == "test_mode"
        assert payload['conversation_id'] == "conv_123"
        assert payload['chat_history'] == [{'role': 'user', 'content': 'Previous'}]
        assert payload['custom'] == 'value'
    
    @patch('requests.post')
    def test_call_webhook_success(self, mock_post):
        """Test successful webhook call."""
        mock_response = Mock()
        mock_response.json.return_value = {'reply': 'Success'}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        result = N8nService.call_webhook(
            'http://localhost:5678/webhook/test',
            {'message': 'Test'}
        )
        assert result['reply'] == 'Success'
        mock_post.assert_called_once()
    
    @patch('requests.post')
    def test_call_webhook_timeout(self, mock_post):
        """Test webhook timeout handling."""
        mock_post.side_effect = requests.exceptions.Timeout("Timeout")
        
        with pytest.raises(requests.exceptions.Timeout):
            N8nService.call_webhook(
                'http://localhost:5678/webhook/test',
                {'message': 'Test'}
            )
    
    @patch('requests.post')
    def test_call_webhook_invalid_url(self, mock_post):
        """Test validation of webhook URL."""
        with pytest.raises(ValueError, match="Invalid webhook URL"):
            N8nService.call_webhook(
                'not-a-url',
                {'message': 'Test'}
            )
    
    @patch('requests.post')
    def test_call_webhook_retry(self, mock_post):
        """Test webhook retry on failure."""
        # First call fails, second succeeds
        mock_post.side_effect = [
            requests.exceptions.RequestException("Error"),
            Mock(json=lambda: {'reply': 'Success'}, raise_for_status=Mock())
        ]
        
        result = N8nService.call_webhook(
            'http://localhost:5678/webhook/test',
            {'message': 'Test'},
            retries=1
        )
        assert result['reply'] == 'Success'
        assert mock_post.call_count == 2

