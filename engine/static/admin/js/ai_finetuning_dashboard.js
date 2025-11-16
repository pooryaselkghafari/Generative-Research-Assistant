/**
 * JavaScript for AI Fine-tuning Dashboard
 * 
 * Handles drag-and-drop file uploads, form submissions, and UI interactions.
 * Uses modular, maintainable code structure.
 */

(function() {
  'use strict';
  
  /**
   * Main dashboard controller object
   */
  const AIFineTuningDashboard = {
    /**
     * Initialize the dashboard
     */
    init: function() {
      this.setupDragAndDrop();
      this.setupFileInput();
      this.setupCommandForm();
      this.setupCommandTypeHandler();
    },
    
    /**
     * Setup drag and drop functionality
     */
    setupDragAndDrop: function() {
      const dropZone = document.getElementById('dropZone');
      const fileInput = document.getElementById('fileInput');
      
      if (!dropZone || !fileInput) {
        return;
      }
      
      dropZone.addEventListener('click', () => fileInput.click());
      dropZone.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          fileInput.click();
        }
      });
      
      dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
      });
      
      dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('drag-over');
      });
      
      dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
          fileInput.files = files;
          this.handleFileUpload();
        }
      });
    },
    
    /**
     * Setup file input change handler
     */
    setupFileInput: function() {
      const fileInput = document.getElementById('fileInput');
      if (fileInput) {
        fileInput.addEventListener('change', () => {
          this.handleFileUpload();
        });
      }
    },
    
    /**
     * Setup command form submission
     */
    setupCommandForm: function() {
      const form = document.getElementById('commandForm');
      if (form) {
        form.addEventListener('submit', (e) => {
          e.preventDefault();
          this.handleCommandSubmit();
        });
      }
    },
    
    /**
     * Setup command type change handler
     */
    setupCommandTypeHandler: function() {
      const commandType = document.getElementById('commandType');
      const promptGroup = document.getElementById('promptGroup');
      const testMessageGroup = document.getElementById('testMessageGroup');
      const templateSelect = document.getElementById('templateSelect');
      
      if (commandType) {
        commandType.addEventListener('change', () => {
          const type = commandType.value;
          if (promptGroup) {
            promptGroup.style.display = type === 'update_prompt' ? 'block' : 'none';
          }
          if (testMessageGroup) {
            testMessageGroup.style.display = type === 'test_model' ? 'block' : 'none';
          }
          
          // Filter templates by command type
          this.filterTemplatesByCommandType(type);
          
          // Reset template selection if current template doesn't match
          if (templateSelect && templateSelect.value) {
            const selectedOption = templateSelect.options[templateSelect.selectedIndex];
            if (selectedOption.dataset.commandType !== type) {
              templateSelect.value = '';
            }
          }
          
          // Generate default template for the command type
          this.generateDefaultTemplate(type);
        });
      }
      
      // Setup template selector
      if (templateSelect) {
        templateSelect.addEventListener('change', () => {
          this.handleTemplateSelection();
        });
      }
      
      // Setup JSON validation for command data
      const commandData = document.getElementById('commandData');
      if (commandData) {
        commandData.addEventListener('input', () => {
          this.validateJson(commandData.value);
        });
      }
    },
    
    /**
     * Filter templates by command type
     */
    filterTemplatesByCommandType: function(commandType) {
      const templateSelect = document.getElementById('templateSelect');
      if (!templateSelect) {
        return;
      }
      
      const options = templateSelect.options;
      for (let i = 0; i < options.length; i++) {
        const option = options[i];
        if (option.value === '') {
          // Always show the "No Template" option
          option.style.display = 'block';
        } else {
          // Show/hide based on command type match
          option.style.display = option.dataset.commandType === commandType ? 'block' : 'none';
        }
      }
    },
    
    /**
     * Handle template selection
     */
    handleTemplateSelection: function() {
      const templateSelect = document.getElementById('templateSelect');
      const commandData = document.getElementById('commandData');
      
      if (!templateSelect || !commandData) {
        return;
      }
      
      const selectedOption = templateSelect.options[templateSelect.selectedIndex];
      const templateId = selectedOption.value;
      
      if (templateId === '') {
        // No template selected, generate default for current command type
        const commandType = document.getElementById('commandType');
        if (commandType) {
          this.generateDefaultTemplate(commandType.value);
        } else {
          this.resetCommandData();
        }
        return;
      }
      
      // Get template data from window.AIFineTuningTemplates
      if (!window.AIFineTuningTemplates) {
        this.showAlert('Templates data not available', 'error');
        return;
      }
      
      const template = window.AIFineTuningTemplates.find(t => t.id === parseInt(templateId));
      if (!template) {
        this.showAlert('Template not found', 'error');
        return;
      }
      
      try {
        // template_data is already a JavaScript object (dict)
        const templateData = template.template_data;
        const formattedJson = JSON.stringify(templateData, null, 2);
        commandData.value = formattedJson;
        this.validateJson(formattedJson);
      } catch (e) {
        this.showAlert('Error loading template: ' + e.message, 'error');
      }
    },
    
    /**
     * Reset command data to empty JSON
     */
    resetCommandData: function() {
      const commandData = document.getElementById('commandData');
      if (commandData) {
        commandData.value = '{}';
        this.validateJson('{}');
      }
    },
    
    /**
     * Generate default template JSON based on command type
     */
    generateDefaultTemplate: function(commandType) {
      const commandData = document.getElementById('commandData');
      const templateSelect = document.getElementById('templateSelect');
      
      if (!commandData) {
        return;
      }
      
      // If a template is selected, don't override
      if (templateSelect && templateSelect.value) {
        return;
      }
      
      // Generate default template based on command type
      let defaultTemplate = {};
      
      switch (commandType) {
        case 'fine_tune':
          defaultTemplate = {
            model: 'gpt-3.5-turbo',
            hyperparameters: {
              learning_rate: 0.0001,
              batch_size: 4,
              n_epochs: 3
            },
            suffix: null,
            validation_file: null
          };
          break;
          
        case 'update_prompt':
          defaultTemplate = {
            prompt: 'You are a helpful research assistant specialized in statistical analysis and data interpretation.',
            temperature: 0.7,
            max_tokens: 2000
          };
          break;
          
        case 'add_context':
          defaultTemplate = {
            context_type: 'knowledge_base',
            embedding_model: 'text-embedding-ada-002',
            max_context_length: 4000
          };
          break;
          
        case 'test_model':
          defaultTemplate = {
            test_message: 'Hello, how are you?',
            temperature: 0.7,
            max_tokens: 150,
            top_p: 1.0,
            frequency_penalty: 0.0,
            presence_penalty: 0.0
          };
          break;
          
        case 'reset_model':
          defaultTemplate = {
            confirm_reset: true,
            backup_before_reset: true
          };
          break;
          
        case 'other':
        default:
          defaultTemplate = {
            parameters: {},
            options: {}
          };
          break;
      }
      
      // Format and set the template
      const formattedJson = JSON.stringify(defaultTemplate, null, 2);
      commandData.value = formattedJson;
      this.validateJson(formattedJson);
    },
    
    /**
     * Validate JSON and show errors
     */
    validateJson: function(jsonString) {
      const jsonError = document.getElementById('jsonError');
      const commandData = document.getElementById('commandData');
      
      if (!jsonError || !commandData) {
        return true;
      }
      
      // Remove error styling
      commandData.style.borderColor = '#ddd';
      jsonError.style.display = 'none';
      jsonError.textContent = '';
      
      if (!jsonString.trim()) {
        return true;
      }
      
      try {
        JSON.parse(jsonString);
        return true;
      } catch (e) {
        // Show error
        commandData.style.borderColor = '#ba2121';
        jsonError.style.display = 'block';
        jsonError.textContent = 'Invalid JSON: ' + e.message;
        return false;
      }
    },
    
    /**
     * Handle file upload
     */
    handleFileUpload: function() {
      const fileInput = document.getElementById('fileInput');
      const files = fileInput.files;
      
      if (files.length === 0) {
        return;
      }
      
      const fileName = document.getElementById('fileName').value || files[0].name;
      const fileDescription = document.getElementById('fileDescription').value;
      const fileType = document.getElementById('fileType').value;
      
      const formData = new FormData();
      formData.append('file', files[0]);
      formData.append('name', fileName);
      formData.append('description', fileDescription);
      formData.append('file_type', fileType);
      
      this.sendRequest('/admin/ai-finetuning/upload-file/', {
        method: 'POST',
        body: formData,
      })
      .then((data) => {
        if (data.success) {
          this.showAlert('File uploaded successfully!', 'success');
          this.resetFileForm();
          setTimeout(() => location.reload(), 1000);
        } else {
          this.showAlert('Error: ' + (data.error || 'Failed to upload file'), 'error');
        }
      })
      .catch((error) => {
        this.showAlert('Error: ' + error.message, 'error');
      });
    },
    
    /**
     * Handle command form submission
     */
    handleCommandSubmit: function() {
      const submitBtn = document.getElementById('submitBtn');
      const commandType = document.getElementById('commandType').value;
      const description = document.getElementById('commandDescription').value;
      const commandDataField = document.getElementById('commandData');
      
      if (!description) {
        this.showAlert('Please provide a description', 'error');
        return;
      }
      
      // Validate JSON before submission
      if (commandDataField && !this.validateJson(commandDataField.value)) {
        this.showAlert('Please fix JSON errors before submitting', 'error');
        return;
      }
      
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="spinner"></span> Sending...';
      
      const fileCheckboxes = document.querySelectorAll('input[name="file_ids"]:checked');
      const fileIds = Array.from(fileCheckboxes).map(cb => parseInt(cb.value));
      
      // Parse command data from JSON field
      let commandData = {};
      if (commandDataField && commandDataField.value.trim()) {
        try {
          commandData = JSON.parse(commandDataField.value);
        } catch (e) {
          this.showAlert('Invalid JSON in command data: ' + e.message, 'error');
          submitBtn.disabled = false;
          submitBtn.innerHTML = 'Send Command';
          return;
        }
      }
      
      // Merge with prompt/test message if applicable
      if (commandType === 'update_prompt') {
        const promptText = document.getElementById('promptText');
        if (promptText && promptText.value) {
          commandData.prompt = promptText.value;
        }
      } else if (commandType === 'test_model') {
        const testMessage = document.getElementById('testMessage');
        if (testMessage && testMessage.value) {
          commandData.test_message = testMessage.value;
        }
      }
      
      this.sendRequest('/admin/ai-finetuning/execute-command/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          command_type: commandType,
          description: description,
          command_data: commandData,
          file_ids: fileIds,
        }),
      })
      .then((data) => {
        if (data.success) {
          this.showAlert('Command sent successfully!', 'success');
          document.getElementById('commandForm').reset();
          document.getElementById('promptGroup').style.display = 'none';
          document.getElementById('testMessageGroup').style.display = 'none';
          setTimeout(() => location.reload(), 2000);
        } else {
          this.showAlert('Error: ' + (data.error || 'Failed to send command'), 'error');
        }
      })
      .catch((error) => {
        this.showAlert('Error: ' + error.message, 'error');
      })
      .finally(() => {
        submitBtn.disabled = false;
        submitBtn.innerHTML = 'Send Command';
      });
    },
    
    /**
     * Toggle file active status
     */
    toggleFile: function(fileId) {
      this.sendRequest(`/admin/ai-finetuning/toggle-file/${fileId}/`, {
        method: 'POST',
      })
      .then((data) => {
        if (data.success) {
          this.showAlert('File status updated!', 'success');
          setTimeout(() => location.reload(), 1000);
        } else {
          this.showAlert('Error: ' + (data.error || 'Failed to update file'), 'error');
        }
      })
      .catch((error) => {
        this.showAlert('Error: ' + error.message, 'error');
      });
    },
    
    /**
     * Delete a file
     */
    deleteFile: function(fileId) {
      if (!confirm('Are you sure you want to delete this file?')) {
        return;
      }
      
      this.sendRequest(`/admin/ai-finetuning/delete-file/${fileId}/`, {
        method: 'POST',
      })
      .then((data) => {
        if (data.success) {
          this.showAlert('File deleted!', 'success');
          setTimeout(() => location.reload(), 1000);
        } else {
          this.showAlert('Error: ' + (data.error || 'Failed to delete file'), 'error');
        }
      })
      .catch((error) => {
        this.showAlert('Error: ' + error.message, 'error');
      });
    },
    
    /**
     * Send HTTP request with CSRF token
     */
    sendRequest: function(url, options) {
      const defaultOptions = {
        headers: {
          'X-CSRFToken': this.getCsrfToken(),
        },
      };
      
      const mergedOptions = {
        ...defaultOptions,
        ...options,
        headers: {
          ...defaultOptions.headers,
          ...(options.headers || {}),
        },
      };
      
      return fetch(url, mergedOptions)
        .then((response) => {
          if (!response.ok) {
            return response.json().then((data) => {
              throw new Error(data.error || 'Request failed');
            });
          }
          return response.json();
        });
    },
    
    /**
     * Get CSRF token from cookies
     */
    getCsrfToken: function() {
      const name = 'csrftoken';
      let cookieValue = null;
      
      if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
          const cookie = cookies[i].trim();
          if (cookie.substring(0, name.length + 1) === (name + '=')) {
            cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
            break;
          }
        }
      }
      
      return cookieValue;
    },
    
    /**
     * Show alert message
     */
    showAlert: function(message, type) {
      const container = document.getElementById('alertContainer');
      if (!container) {
        return;
      }
      
      const alert = document.createElement('div');
      alert.className = `alert alert-${type}`;
      alert.innerHTML = `
        <span>${this.escapeHtml(message)}</span>
        <button onclick="this.parentElement.remove()" style="margin-left: auto; background: none; border: none; cursor: pointer; font-size: 18px;">&times;</button>
      `;
      container.appendChild(alert);
      
      setTimeout(() => {
        if (alert.parentNode) {
          alert.remove();
        }
      }, 5000);
    },
    
    /**
     * Reset file upload form
     */
    resetFileForm: function() {
      const fileInput = document.getElementById('fileInput');
      const fileName = document.getElementById('fileName');
      const fileDescription = document.getElementById('fileDescription');
      
      if (fileInput) {
        fileInput.value = '';
      }
      if (fileName) {
        fileName.value = '';
      }
      if (fileDescription) {
        fileDescription.value = '';
      }
    },
    
    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml: function(text) {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    },
  };
  
      // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      AIFineTuningDashboard.init();
      // Filter templates and generate default on initial load
      const commandType = document.getElementById('commandType');
      if (commandType) {
        AIFineTuningDashboard.filterTemplatesByCommandType(commandType.value);
        AIFineTuningDashboard.generateDefaultTemplate(commandType.value);
      }
    });
  } else {
    AIFineTuningDashboard.init();
    // Filter templates and generate default on initial load
    const commandType = document.getElementById('commandType');
    if (commandType) {
      AIFineTuningDashboard.filterTemplatesByCommandType(commandType.value);
      AIFineTuningDashboard.generateDefaultTemplate(commandType.value);
    }
  }
  
  // Export to window for onclick handlers
  window.AIFineTuningDashboard = AIFineTuningDashboard;
})();

