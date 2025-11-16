/**
 * JavaScript for AI Fine-tuning Command Admin Page
 * 
 * Handles template selection and JSON editing in Django admin.
 * Provides real-time JSON validation and template loading functionality.
 */

(function() {
  'use strict';
  
  /**
   * Default template configurations
   * @type {Object<string, Object>}
   */
  const DEFAULT_TEMPLATES = {
    'default_fine_tune': {
      model: 'gpt-3.5-turbo',
      hyperparameters: {
        learning_rate: 0.0001,
        batch_size: 4,
        n_epochs: 3
      },
      suffix: null,
      validation_file: null
    },
    'default_update_prompt': {
      prompt: 'You are a helpful research assistant specialized in statistical analysis and data interpretation.',
      temperature: 0.7,
      max_tokens: 2000
    },
    'default_add_context': {
      context_type: 'knowledge_base',
      embedding_model: 'text-embedding-ada-002',
      max_context_length: 4000
    },
    'default_test_model': {
      test_message: 'Hello, how are you?',
      temperature: 0.7,
      max_tokens: 150,
      top_p: 1.0,
      frequency_penalty: 0.0,
      presence_penalty: 0.0
    },
    'default_reset_model': {
      confirm_reset: true,
      backup_before_reset: true
    },
    'default_other': {
      parameters: {},
      options: {}
    }
  };
  
  /**
   * Template manager for admin page
   */
  const TemplateManager = {
    /**
     * Initialize template functionality
     */
    init: function() {
      const templateSelect = document.querySelector('.template-select');
      const commandDataField = document.querySelector('.command-data-json');
      
      if (!templateSelect || !commandDataField) {
        return;
      }
      
      const commandTypeSelect = document.getElementById('id_command_type');
      const savedTemplates = this._loadSavedTemplates();
      
      this._setupEventHandlers(
        templateSelect,
        commandTypeSelect,
        commandDataField,
        savedTemplates
      );
      
      this._initializeDefaults(commandTypeSelect, templateSelect, commandDataField);
    },
    
    /**
     * Load saved templates from page data
     * @returns {Object} Dictionary of saved templates
     */
    _loadSavedTemplates: function() {
      const templatesScript = document.querySelector('script[data-templates]');
      if (!templatesScript) {
        return {};
      }
      
      try {
        return JSON.parse(templatesScript.getAttribute('data-templates'));
      } catch (e) {
        console.error('Error parsing templates:', e);
        return {};
      }
    },
    
    /**
     * Setup event handlers for template functionality
     * @param {HTMLElement} templateSelect - Template dropdown element
     * @param {HTMLElement} commandTypeSelect - Command type dropdown element
     * @param {HTMLElement} commandDataField - Command data textarea
     * @param {Object} savedTemplates - Saved templates dictionary
     */
    _setupEventHandlers: function(templateSelect, commandTypeSelect, commandDataField, savedTemplates) {
      const self = this;
      
      templateSelect.addEventListener('change', function() {
        self._loadTemplate(this.value, commandDataField, savedTemplates);
      });
      
      if (commandTypeSelect) {
        commandTypeSelect.addEventListener('change', function() {
          self._handleCommandTypeChange(
            this.value,
            templateSelect,
            commandDataField,
            savedTemplates
          );
        });
      }
      
      commandDataField.addEventListener('input', function() {
        self._validateJson(this.value, commandDataField);
      });
    },
    
    /**
     * Initialize defaults on page load
     * @param {HTMLElement} commandTypeSelect - Command type dropdown
     * @param {HTMLElement} templateSelect - Template dropdown
     * @param {HTMLElement} commandDataField - Command data textarea
     */
    _initializeDefaults: function(commandTypeSelect, templateSelect, commandDataField) {
      if (!commandTypeSelect || !commandTypeSelect.value) {
        return;
      }
      
      this._filterTemplatesByCommandType(commandTypeSelect.value, templateSelect);
      this._generateDefaultForCommandType(
        commandTypeSelect.value,
        templateSelect,
        commandDataField
      );
      
      if (commandDataField.value) {
        this._validateJson(commandDataField.value, commandDataField);
      }
    },
    
    /**
     * Load template into command data field
     * @param {string} templateValue - Template value identifier
     * @param {HTMLElement} commandDataField - Command data textarea
     * @param {Object} savedTemplates - Saved templates dictionary
     */
    _loadTemplate: function(templateValue, commandDataField, savedTemplates) {
      if (!templateValue || templateValue === '') {
        commandDataField.value = '{}';
        this._validateJson('{}', commandDataField);
        return;
      }
      
      const templateData = this._getTemplateData(templateValue, savedTemplates);
      if (!templateData) {
        return;
      }
      
      try {
        const formattedJson = JSON.stringify(templateData, null, 2);
        commandDataField.value = formattedJson;
        this._validateJson(formattedJson, commandDataField);
      } catch (e) {
        // Show error in console and create user-friendly error message
        console.error('Error loading template:', e);
        const errorMsg = document.createElement('div');
        errorMsg.className = 'error-message';
        errorMsg.style.cssText = 'color: #ba2121; padding: 8px; margin-top: 5px; background: #fff3f3; border-left: 3px solid #ba2121;';
        errorMsg.textContent = 'Error loading template: ' + e.message;
        commandDataField.parentNode.insertBefore(errorMsg, commandDataField.nextSibling);
        setTimeout(function() {
          if (errorMsg.parentNode) {
            errorMsg.remove();
          }
        }, 5000);
      }
    },
    
    /**
     * Get template data by value
     * @param {string} templateValue - Template value identifier
     * @param {Object} savedTemplates - Saved templates dictionary
     * @returns {Object|null} Template data or null
     */
    _getTemplateData: function(templateValue, savedTemplates) {
      if (templateValue.startsWith('default_')) {
        return DEFAULT_TEMPLATES[templateValue] || null;
      }
      
      if (templateValue.startsWith('template_')) {
        const templateId = templateValue.replace('template_', '');
        return savedTemplates[templateId] || null;
      }
      
      return null;
    },
    
    /**
     * Validate JSON and show errors
     * @param {string} jsonString - JSON string to validate
     * @param {HTMLElement} commandDataField - Command data textarea
     * @returns {boolean} True if valid, false otherwise
     */
    _validateJson: function(jsonString, commandDataField) {
      this._clearJsonErrors(commandDataField);
      
      if (!jsonString || !jsonString.trim()) {
        return true;
      }
      
      try {
        JSON.parse(jsonString);
        this._showJsonSuccess(commandDataField);
        return true;
      } catch (e) {
        this._showJsonError(e.message, commandDataField);
        return false;
      }
    },
    
    /**
     * Clear JSON validation errors
     * @param {HTMLElement} commandDataField - Command data textarea
     */
    _clearJsonErrors: function(commandDataField) {
      commandDataField.style.borderColor = '';
      commandDataField.classList.remove('valid-json');
      const errorDiv = document.getElementById('json-error-message');
      if (errorDiv) {
        errorDiv.remove();
      }
    },
    
    /**
     * Show JSON validation error
     * @param {string} errorMessage - Error message to display
     * @param {HTMLElement} commandDataField - Command data textarea
     */
    _showJsonError: function(errorMessage, commandDataField) {
      commandDataField.style.borderColor = '#ba2121';
      commandDataField.classList.remove('valid-json');
      
      const errorDiv = document.createElement('div');
      errorDiv.id = 'json-error-message';
      errorDiv.textContent = 'Invalid JSON: ' + errorMessage;
      
      // Remove existing error message
      const existingError = commandDataField.parentNode.querySelector('#json-error-message');
      if (existingError) {
        existingError.remove();
      }
      
      commandDataField.parentNode.appendChild(errorDiv);
    },
    
    /**
     * Show JSON validation success
     * @param {HTMLElement} commandDataField - Command data textarea
     */
    _showJsonSuccess: function(commandDataField) {
      commandDataField.classList.add('valid-json');
    },
    
    /**
     * Filter templates by command type
     * @param {string} commandType - Command type to filter by
     * @param {HTMLElement} templateSelect - Template dropdown
     */
    _filterTemplatesByCommandType: function(commandType, templateSelect) {
      if (!commandType) {
        return;
      }
      
      const options = templateSelect.options;
      for (let i = 0; i < options.length; i++) {
        const option = options[i];
        const value = option.value;
        
        if (value === '') {
          option.style.display = 'block';
          continue;
        }
        
        if (value.startsWith('default_')) {
          const templateType = value.replace('default_', '');
          option.style.display = templateType === commandType ? 'block' : 'none';
        } else if (value.startsWith('template_')) {
          // Show all saved templates (could be filtered if we had command type data)
          option.style.display = 'block';
        }
      }
    },
    
    /**
     * Handle command type change
     * @param {string} commandType - New command type
     * @param {HTMLElement} templateSelect - Template dropdown
     * @param {HTMLElement} commandDataField - Command data textarea
     * @param {Object} savedTemplates - Saved templates dictionary
     */
    _handleCommandTypeChange: function(commandType, templateSelect, commandDataField, savedTemplates) {
      this._filterTemplatesByCommandType(commandType, templateSelect);
      
      if (!templateSelect.value || templateSelect.value === '') {
        this._generateDefaultForCommandType(commandType, templateSelect, commandDataField);
      }
    },
    
    /**
     * Generate default template for command type
     * @param {string} commandType - Command type
     * @param {HTMLElement} templateSelect - Template dropdown
     * @param {HTMLElement} commandDataField - Command data textarea
     */
    _generateDefaultForCommandType: function(commandType, templateSelect, commandDataField) {
      const defaultKey = 'default_' + commandType;
      if (DEFAULT_TEMPLATES[defaultKey]) {
        this._loadTemplate(defaultKey, commandDataField, {});
        templateSelect.value = defaultKey;
      }
    }
  };
  
  /**
   * Initialize when DOM is ready
   */
  function init() {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', function() {
        TemplateManager.init();
      });
    } else {
      TemplateManager.init();
    }
  }
  
  init();
})();
