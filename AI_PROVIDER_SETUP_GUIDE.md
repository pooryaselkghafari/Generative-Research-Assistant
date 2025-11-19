# AI Provider Setup Guide

## Overview

The AI Provider module allows you to configure and manage AI service providers (OpenAI, Anthropic, Custom APIs) through the Django admin interface. All API keys are encrypted for security, and the system automatically uses the configured provider for fine-tuning operations.

## Quick Start

### 1. Access AI Provider Admin

1. Log in to Django admin: `/admin/`
2. Navigate to **Engine** → **AI Providers**
3. Click **Add AI Provider**

### 2. Configure Provider

Fill in the form:

- **Name**: Descriptive name (e.g., "Production OpenAI", "Development Claude")
- **Provider Type**: Select from:
  - OpenAI
  - Anthropic Claude
  - Custom API
- **API Key**: Your API key (will be encrypted automatically)
- **API Base URL**: Optional, uses provider default if not set
- **Base Model**: Model identifier (e.g., `gpt-3.5-turbo`, `claude-3-opus`)
- **Fine-tuned Model ID**: ID of your fine-tuned model (if available)
- **Organization ID**: For OpenAI (optional, encrypted)
- **Is Active**: Enable/disable this provider
- **Is Default**: Set as default provider (only one can be default)

### 3. Test Connection

1. Select the provider(s) in the list
2. Choose **Test connection** from the Actions dropdown
3. Click **Go**
4. Check the results - status will be updated automatically

### 4. Use Provider for Fine-tuning

Once configured, the AI fine-tuning commands will automatically use the active default provider (or first active provider if no default is set).

## Admin Actions

Available actions in the AI Provider list:

- **Test connection**: Test API credentials for selected providers
- **Set as default**: Set selected provider as default (select exactly one)
- **Activate selected providers**: Enable selected providers
- **Deactivate selected providers**: Disable selected providers

## Supported Providers

### OpenAI

- **API Key**: Get from https://platform.openai.com/account/api-keys
- **Base Models**: `gpt-3.5-turbo`, `gpt-4`, `gpt-4-turbo-preview`, etc.
- **Organization ID**: Optional, for team accounts

### Anthropic Claude

- **API Key**: Get from https://console.anthropic.com/
- **Base Models**: `claude-3-opus`, `claude-3-sonnet`, `claude-3-haiku`
- **Note**: Fine-tuning support may vary

### Custom API

- **API Base URL**: Your custom API endpoint
- **API Key**: Your authentication token
- **Format**: Expects REST API with `/fine-tune` and `/test` endpoints

## Security Features

- ✅ **Encrypted API Keys**: All API keys are encrypted using `EncryptedCharField`
- ✅ **Staff-only Access**: Only staff users can configure providers
- ✅ **Audit Trail**: Tracks who created each provider and when
- ✅ **Connection Testing**: Verify credentials before use

## Integration with Fine-tuning

The AI fine-tuning service automatically:

1. Retrieves the active provider
2. Uses provider's API key and configuration
3. Routes commands to the appropriate provider implementation
4. Handles errors gracefully

## Example Workflow

1. **Configure Provider**:
   - Go to Admin → AI Providers → Add
   - Enter OpenAI API key and settings
   - Set as default and active
   - Test connection

2. **Upload Training Files**:
   - Go to Admin → AI Fine-tuning Files
   - Upload your training data files

3. **Create Fine-tuning Command**:
   - Go to Admin → AI Fine-tuning Commands → Add
   - Select command type (e.g., "Fine-tune Model")
   - Select training files
   - Configure command data (hyperparameters, etc.)
   - Save

4. **Command Execution**:
   - The system automatically uses your configured provider
   - Status updates in real-time
   - Results are stored in the command

## Troubleshooting

### "No active AI provider configured"

- Ensure at least one provider is marked as **Is Active**
- Set one provider as **Is Default** for automatic selection

### Connection Test Fails

- Verify API key is correct
- Check API key has necessary permissions
- For OpenAI, ensure you have fine-tuning access
- Check network connectivity

### Fine-tuning Fails

- Verify provider is active and default
- Check training file format (JSONL for OpenAI)
- Ensure API key has sufficient credits/permissions
- Review error message in command result

## Test Coverage

The AI Provider system includes comprehensive tests covering:

- ✅ Security (encryption, authentication, SQL injection prevention)
- ✅ Database (integrity, indexes, constraints)
- ✅ Performance (query optimization)
- ✅ Unit (model methods, provider selection)
- ✅ Integration (complete workflows)
- ✅ API (service methods)
- ✅ E2E (end-to-end flows)
- ✅ Monitoring (status tracking)
- ✅ Frontend (admin templates)

**Total**: 25 tests, all passing ✅

## Files Created

- `engine/models.py` - AIProvider model
- `engine/admin.py` - AIProviderAdmin interface
- `engine/integrations/ai_provider.py` - AI service integration
- `engine/services/ai_finetuning_service.py` - Updated to use providers
- `tests/ai_provider/test_ai_provider_system.py` - Comprehensive tests

## Next Steps

1. Run migrations: `python manage.py migrate`
2. Access admin and configure your first provider
3. Test the connection
4. Start fine-tuning your models!

---

**Last Updated**: $(date)

