(function () {
  const root = document.documentElement;
  const key = "sb-theme";
  const saved = localStorage.getItem(key);
  if (saved) {
    root.setAttribute("data-theme", saved);
  }
  const toggle = document.getElementById("themeToggle");
  if (toggle) {
    toggle.addEventListener("click", () => {
      const current = root.getAttribute("data-theme") || "dark";
      const next = current === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      localStorage.setItem(key, next);
    });
  }

  // lightweight list filter
  window.sbFilterList = function (input, selector) {
    const q = (input.value || "").toLowerCase();
    document.querySelectorAll(selector + " > li").forEach(li => {
      const text = li.textContent.toLowerCase();
      li.style.display = text.includes(q) ? "" : "none";
    });
  };

  // Enhanced session filtering with multi-selection support
  window.filterSessions = function(input) {
    const q = (input.value || "").toLowerCase();
    const sessionItems = document.querySelectorAll('#sessionList > li.session-item');
    const clearBtn = document.getElementById('searchClear');
    let visibleCount = 0;
    
    sessionItems.forEach(li => {
      const text = li.textContent.toLowerCase();
      const isVisible = text.includes(q);
      li.style.display = isVisible ? "" : "none";
      
      if (isVisible) {
        visibleCount++;
      }
    });
    
    // Show/hide clear button based on input value
    if (clearBtn) {
      clearBtn.style.display = q.length > 0 ? 'flex' : 'none';
    }
    
    // Update selection UI based on visible items
    updateSelectionUI();
  };

  // Global variables for dataset column types
  window.datasetColumnTypes = {};

  // Multi-selection functionality
  window.updateSelectionUI = function() {
    const checkboxes = document.querySelectorAll('.session-checkbox:not([style*="display: none"])');
    const checkedBoxes = document.querySelectorAll('.session-checkbox:checked:not([style*="display: none"])');
    const selectAllBtn = document.getElementById('selectAllBtn');
    const bulkDeleteBtn = document.getElementById('bulkDeleteBtn');
    
    if (checkboxes.length === 0) {
      selectAllBtn.style.display = 'none';
      bulkDeleteBtn.style.display = 'none';
      return;
    }
    
    // Show/hide buttons based on whether there are visible sessions
    const hasVisibleSessions = checkboxes.length > 0;
    selectAllBtn.style.display = hasVisibleSessions ? 'inline-block' : 'none';
    bulkDeleteBtn.style.display = checkedBoxes.length > 0 ? 'inline-block' : 'none';
    
    // Update select all button text
    if (checkedBoxes.length === checkboxes.length && checkboxes.length > 0) {
      selectAllBtn.textContent = 'Deselect All';
    } else {
      selectAllBtn.textContent = 'Select All';
    }
  };

  window.toggleSelectAll = function() {
    const checkboxes = document.querySelectorAll('.session-checkbox:not([style*="display: none"])');
    const selectAllBtn = document.getElementById('selectAllBtn');
    const allChecked = Array.from(checkboxes).every(cb => cb.checked);
    
    checkboxes.forEach(checkbox => {
      checkbox.checked = !allChecked;
    });
    
    updateSelectionUI();
  };

  window.bulkDeleteSessions = function() {
    const checkedBoxes = document.querySelectorAll('.session-checkbox:checked');
    const sessionIds = Array.from(checkedBoxes).map(cb => cb.value);
    
    if (sessionIds.length === 0) {
      showNotification('No sessions selected', 'warning');
      return;
    }
    
    const sessionNames = Array.from(checkedBoxes).map(cb => {
      const row = cb.closest('.session-item');
      const link = row.querySelector('.link');
      return link ? link.textContent.trim() : 'Unknown';
    });
    
    // Show modern confirmation modal
    showDeleteConfirmation(sessionIds, sessionNames);
  };

  // Modern confirmation modal for bulk delete
  function showDeleteConfirmation(sessionIds, sessionNames) {
    // Create modal backdrop
    const backdrop = document.createElement('div');
    backdrop.className = 'modal-backdrop';
    backdrop.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0, 0, 0, 0.5);
      z-index: 1000;
      display: flex;
      align-items: center;
      justify-content: center;
      backdrop-filter: blur(4px);
    `;

    // Create modal content
    const modal = document.createElement('div');
    modal.style.cssText = `
      background: white;
      border-radius: 12px;
      padding: 0;
      max-width: 500px;
      width: 90%;
      max-height: 80vh;
      overflow: hidden;
      box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
      transform: scale(0.95);
      transition: transform 0.2s ease-out;
    `;

    // Create header
    const header = document.createElement('div');
    header.style.cssText = `
      padding: 24px 24px 16px 24px;
      border-bottom: 1px solid #e5e7eb;
      display: flex;
      align-items: center;
      gap: 12px;
    `;

    const icon = document.createElement('div');
    icon.style.cssText = `
      width: 40px;
      height: 40px;
      background: #fef2f2;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #dc2626;
      font-size: 20px;
    `;
    icon.innerHTML = '⚠️';

    const title = document.createElement('h3');
    title.style.cssText = `
      margin: 0;
      font-size: 18px;
      font-weight: 600;
      color: #111827;
    `;
    title.textContent = 'Delete Sessions';

    header.appendChild(icon);
    header.appendChild(title);

    // Create body
    const body = document.createElement('div');
    body.style.cssText = `
      padding: 16px 24px;
    `;

    const message = document.createElement('p');
    message.style.cssText = `
      margin: 0 0 16px 0;
      color: #6b7280;
      line-height: 1.5;
    `;
    message.textContent = `Are you sure you want to delete ${sessionIds.length} session${sessionIds.length > 1 ? 's' : ''}? This action cannot be undone.`;

    // Create session list
    const sessionList = document.createElement('div');
    sessionList.style.cssText = `
      max-height: 200px;
      overflow-y: auto;
      border: 1px solid #e5e7eb;
      border-radius: 8px;
      padding: 12px;
      background: #f9fafb;
    `;

    sessionNames.forEach(name => {
      const item = document.createElement('div');
      item.style.cssText = `
        padding: 8px 0;
        border-bottom: 1px solid #e5e7eb;
        color: #374151;
        font-size: 14px;
        display: flex;
        align-items: center;
        gap: 8px;
      `;
      item.innerHTML = `
        <span style="color: #dc2626;">•</span>
        <span>${name}</span>
      `;
      sessionList.appendChild(item);
    });

    body.appendChild(message);
    body.appendChild(sessionList);

    // Create footer
    const footer = document.createElement('div');
    footer.style.cssText = `
      padding: 16px 24px 24px 24px;
      display: flex;
      gap: 12px;
      justify-content: flex-end;
      border-top: 1px solid #e5e7eb;
      background: #f9fafb;
    `;

    const cancelBtn = document.createElement('button');
    cancelBtn.style.cssText = `
      padding: 8px 16px;
      border: 1px solid #d1d5db;
      background: white;
      color: #374151;
      border-radius: 6px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s;
    `;
    cancelBtn.textContent = 'Cancel';
    cancelBtn.onmouseover = () => {
      cancelBtn.style.background = '#f9fafb';
      cancelBtn.style.borderColor = '#9ca3af';
    };
    cancelBtn.onmouseout = () => {
      cancelBtn.style.background = 'white';
      cancelBtn.style.borderColor = '#d1d5db';
    };

    const deleteBtn = document.createElement('button');
    deleteBtn.style.cssText = `
      padding: 8px 16px;
      border: none;
      background: #dc2626;
      color: white;
      border-radius: 6px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s;
    `;
    deleteBtn.textContent = 'Delete Sessions';
    deleteBtn.onmouseover = () => {
      deleteBtn.style.background = '#b91c1c';
    };
    deleteBtn.onmouseout = () => {
      deleteBtn.style.background = '#dc2626';
    };

    footer.appendChild(cancelBtn);
    footer.appendChild(deleteBtn);

    // Assemble modal
    modal.appendChild(header);
    modal.appendChild(body);
    modal.appendChild(footer);
    backdrop.appendChild(modal);

    // Add to DOM
    document.body.appendChild(backdrop);

    // Animate in
    setTimeout(() => {
      modal.style.transform = 'scale(1)';
    }, 10);

    // Event handlers
    const closeModal = () => {
      modal.style.transform = 'scale(0.95)';
      setTimeout(() => {
        document.body.removeChild(backdrop);
      }, 200);
    };

    cancelBtn.onclick = closeModal;
    backdrop.onclick = (e) => {
      if (e.target === backdrop) closeModal();
    };

    deleteBtn.onclick = () => {
      closeModal();
      performBulkDelete(sessionIds);
    };

    // Handle escape key
    const handleEscape = (e) => {
      if (e.key === 'Escape') {
        closeModal();
        document.removeEventListener('keydown', handleEscape);
      }
    };
    document.addEventListener('keydown', handleEscape);
  }

  // Perform the actual bulk delete
  function performBulkDelete(sessionIds) {
    // Show loading state
    const deleteBtn = document.getElementById('bulkDeleteBtn');
    const originalText = deleteBtn.textContent;
    deleteBtn.textContent = 'Deleting...';
    deleteBtn.disabled = true;

    // Create form to submit multiple deletions
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = '/sessions/bulk-delete/';
    
    // Add CSRF token
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
    if (csrfToken) {
      const csrfInput = document.createElement('input');
      csrfInput.type = 'hidden';
      csrfInput.name = 'csrfmiddlewaretoken';
      csrfInput.value = csrfToken.value;
      form.appendChild(csrfInput);
    }
    
    // Add session IDs
    sessionIds.forEach(id => {
      const input = document.createElement('input');
      input.type = 'hidden';
      input.name = 'session_ids';
      input.value = id;
      form.appendChild(input);
    });
    
    document.body.appendChild(form);
    form.submit();
  }

  // Single session delete confirmation
  window.showSingleDeleteConfirmation = function(sessionId, sessionName) {
    // Create modal backdrop
    const backdrop = document.createElement('div');
    backdrop.className = 'modal-backdrop';
    backdrop.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0, 0, 0, 0.5);
      z-index: 1000;
      display: flex;
      align-items: center;
      justify-content: center;
      backdrop-filter: blur(4px);
    `;

    // Create modal content
    const modal = document.createElement('div');
    modal.style.cssText = `
      background: white;
      border-radius: 12px;
      padding: 0;
      max-width: 400px;
      width: 90%;
      box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
      transform: scale(0.95);
      transition: transform 0.2s ease-out;
    `;

    // Create header
    const header = document.createElement('div');
    header.style.cssText = `
      padding: 24px 24px 16px 24px;
      border-bottom: 1px solid #e5e7eb;
      display: flex;
      align-items: center;
      gap: 12px;
    `;

    const icon = document.createElement('div');
    icon.style.cssText = `
      width: 40px;
      height: 40px;
      background: #fef2f2;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #dc2626;
      font-size: 20px;
    `;
    icon.innerHTML = '⚠️';

    const title = document.createElement('h3');
    title.style.cssText = `
      margin: 0;
      font-size: 18px;
      font-weight: 600;
      color: #111827;
    `;
    title.textContent = 'Delete Session';

    header.appendChild(icon);
    header.appendChild(title);

    // Create body
    const body = document.createElement('div');
    body.style.cssText = `
      padding: 16px 24px;
    `;

    const message = document.createElement('p');
    message.style.cssText = `
      margin: 0 0 16px 0;
      color: #6b7280;
      line-height: 1.5;
    `;
    message.textContent = `Are you sure you want to delete the session "${sessionName}"? This action cannot be undone.`;

    body.appendChild(message);

    // Create footer
    const footer = document.createElement('div');
    footer.style.cssText = `
      padding: 16px 24px 24px 24px;
      display: flex;
      gap: 12px;
      justify-content: flex-end;
      border-top: 1px solid #e5e7eb;
      background: #f9fafb;
    `;

    const cancelBtn = document.createElement('button');
    cancelBtn.style.cssText = `
      padding: 8px 16px;
      border: 1px solid #d1d5db;
      background: white;
      color: #374151;
      border-radius: 6px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s;
    `;
    cancelBtn.textContent = 'Cancel';
    cancelBtn.onmouseover = () => {
      cancelBtn.style.background = '#f9fafb';
      cancelBtn.style.borderColor = '#9ca3af';
    };
    cancelBtn.onmouseout = () => {
      cancelBtn.style.background = 'white';
      cancelBtn.style.borderColor = '#d1d5db';
    };

    const deleteBtn = document.createElement('button');
    deleteBtn.style.cssText = `
      padding: 8px 16px;
      border: none;
      background: #dc2626;
      color: white;
      border-radius: 6px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s;
    `;
    deleteBtn.textContent = 'Delete Session';
    deleteBtn.onmouseover = () => {
      deleteBtn.style.background = '#b91c1c';
    };
    deleteBtn.onmouseout = () => {
      deleteBtn.style.background = '#dc2626';
    };

    footer.appendChild(cancelBtn);
    footer.appendChild(deleteBtn);

    // Assemble modal
    modal.appendChild(header);
    modal.appendChild(body);
    modal.appendChild(footer);
    backdrop.appendChild(modal);

    // Add to DOM
    document.body.appendChild(backdrop);

    // Animate in
    setTimeout(() => {
      modal.style.transform = 'scale(1)';
    }, 10);

    // Event handlers
    const closeModal = () => {
      modal.style.transform = 'scale(0.95)';
      setTimeout(() => {
        document.body.removeChild(backdrop);
      }, 200);
    };

    cancelBtn.onclick = closeModal;
    backdrop.onclick = (e) => {
      if (e.target === backdrop) closeModal();
    };

    deleteBtn.onclick = () => {
      closeModal();
      performSingleDelete(sessionId);
    };

    // Handle escape key
    const handleEscape = (e) => {
      if (e.key === 'Escape') {
        closeModal();
        document.removeEventListener('keydown', handleEscape);
      }
    };
    document.addEventListener('keydown', handleEscape);
  };

  // Perform single session delete
  function performSingleDelete(sessionId) {
    // Create form to submit deletion
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = `/session/delete/${sessionId}/`;
    
    // Add CSRF token
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
    if (csrfToken) {
      const csrfInput = document.createElement('input');
      csrfInput.type = 'hidden';
      csrfInput.name = 'csrfmiddlewaretoken';
      csrfInput.value = csrfToken.value;
      form.appendChild(csrfInput);
    }
    
    document.body.appendChild(form);
    form.submit();
  }

  // Notification system
  function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      padding: 12px 16px;
      border-radius: 8px;
      color: white;
      font-weight: 500;
      z-index: 1001;
      transform: translateX(100%);
      transition: transform 0.3s ease-out;
    `;

    const colors = {
      info: '#3b82f6',
      success: '#10b981',
      warning: '#f59e0b',
      error: '#ef4444'
    };

    notification.style.background = colors[type] || colors.info;
    notification.textContent = message;

    document.body.appendChild(notification);

    // Animate in
    setTimeout(() => {
      notification.style.transform = 'translateX(0)';
    }, 10);

    // Auto remove
    setTimeout(() => {
      notification.style.transform = 'translateX(100%)';
      setTimeout(() => {
        if (document.body.contains(notification)) {
          document.body.removeChild(notification);
        }
      }, 300);
    }, 3000);
  }
})();
(function () {
  // Toggle advanced controls based on module
  function toggleAdvanced() {
    const sel = document.getElementById("moduleSelect");
    const adv = document.getElementById("module-regression");
    if (!sel || !adv) return;
    adv.style.display = (sel.value === "regression") ? "" : "none";
  }
  document.addEventListener("change", (e) => {
    if (e.target && e.target.id === "moduleSelect") toggleAdvanced();
  });
  document.addEventListener("DOMContentLoaded", toggleAdvanced);

  // Auto-resize equation box & Cmd/Ctrl+Enter to run
  function autoSize(el) {
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.max(el.scrollHeight, 220) + "px";
  }
  document.addEventListener("input", (e) => {
    if (e.target && e.target.id === "equationBox") autoSize(e.target);
  });
  document.addEventListener("DOMContentLoaded", () => {
    const box = document.getElementById("equationBox");
    autoSize(box);
    if (box) {
      box.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
          e.preventDefault();
          const run = document.getElementById("runBtn");
          if (run) run.click();
        }
      });
      // Live-update the equation when dataset variables are renamed in the editor
      window.addEventListener('dataset-variables-renamed', (evt) => {
        try {
          const renameMap = (evt && evt.detail && evt.detail.renameMap) || {};
          if (!renameMap || Object.keys(renameMap).length === 0) return;
          let current = box.value || '';
          for (const [oldName, newName] of Object.entries(renameMap)) {
            const pattern = new RegExp('(?<![A-Za-z0-9_])' + oldName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '(?![A-Za-z0-9_])', 'g');
            current = current.replace(pattern, newName);
          }
          if (current !== box.value) {
            box.value = current;
            autoSize(box);
            // Re-validate run/visualize buttons
            if (typeof window.validateRun === 'function') window.validateRun();
          }
        } catch (e) {
          console.warn('Failed to live-update equation after rename', e);
        }
      });
    }
  });
})();
(function () {
  function autoSize(el) {
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.max(el.scrollHeight, 260) + "px";
  }

  function toggleAdvanced() {
    const sel = document.getElementById("moduleSelect");
    const adv = document.getElementById("module-regression");
    if (!sel || !adv) return;
    const v = (sel.value || "").trim();
    // Show only when a concrete model “regression” is chosen
    adv.style.display = (v === "regression") ? "" : "none";
  }

  function validateRun() {
    const run = document.getElementById("runBtn");
    const visualize = document.getElementById("visualizeBtn");
    const mod = document.getElementById("moduleSelect");
    const ds  = document.getElementById("datasetSelect");
    const eqn = document.getElementById("equationBox");
    const analysisType = document.querySelector('input[name="analysis_type"]:checked');
    if (!run || !mod || !ds || !eqn) return;

    const hasModel = (mod.value || "").trim().length > 0;
    const hasData  = (ds.value || "").trim().length > 0;
    const hasEqn   = (eqn.value || "").trim().length > 0;
    
    // Allow run button to be enabled when all required fields are filled
    const ok = hasModel && hasData && hasEqn;
    run.disabled = !ok;
    run.title = ok ? "Run analysis" : "Select model & dataset, then type an equation";
    
    // Enable/disable visualize button with same conditions
    if (visualize) {
      visualize.disabled = !ok;
      visualize.title = ok ? "Visualize data" : "Select model & dataset, then type an equation to visualize";
    }
  }

  // Make validateRun globally available
  window.validateRun = validateRun;
  
  // Form submission validation
  window.validateFormSubmission = function() {
    const equationBox = document.getElementById('equationBox');
    const datasetSelect = document.getElementById('datasetSelect');
    const moduleSelect = document.getElementById('moduleSelect');
    
    if (!equationBox || !datasetSelect || !moduleSelect) {
      return true; // Let form submit if elements not found
    }
    
    const hasModel = (moduleSelect.value || "").trim().length > 0;
    const hasData = (datasetSelect.value || "").trim().length > 0;
    const hasEqn = (equationBox.value || "").trim().length > 0;
    
    if (!hasModel) {
      alert('Please select a model');
      return false;
    }
    
    if (!hasData) {
      alert('Please select a dataset');
      return false;
    }
    
    if (!hasEqn) {
      alert('Please enter an equation');
      return false;
    }
    
    // Check for errors and show popup instead of preventing submission
    if (window.equationValidator) {
      const errorAnalysis = analyzeEquationErrors(equationBox.value.trim());
      if (errorAnalysis.hasErrors) {
        showErrorFixModal(errorAnalysis);
        return false; // Prevent form submission
      }
    }
    
    // Intercept form submission to handle large dataset warnings
    const form = document.getElementById('analysisForm');
    if (form) {
      form.addEventListener('submit', handleFormSubmission);
    }
    
    return true;
  };

  // Handle form submission with large dataset warnings
  function handleFormSubmission(event) {
    event.preventDefault();
    
    const form = event.target;
    const formData = new FormData(form);
    
    // Check for Bayesian regression with non-numeric DV before submitting
    const moduleValue = formData.get('module');
    const analysisType = formData.get('analysis_type');
    const formula = formData.get('formula');
    
    if (moduleValue === 'regression' && analysisType === 'bayesian' && formula) {
      // Extract dependent variable from equation
      if (formula.includes('~')) {
        const lhs = formula.split('~')[0].trim();
        const dv = lhs.split('+')[0].trim(); // Get first dependent variable
        
        // Check if DV is numeric
        if (window.datasetColumnTypes && window.datasetColumnTypes[dv]) {
          const dvType = window.datasetColumnTypes[dv];
          if (dvType !== 'numeric') {
            // Stop any running progress simulation
            if (window.hideBayesianLoadingModal) {
              window.hideBayesianLoadingModal();
            }
            // Show error modal instead of submitting
            showBayesianDVErrorModal(dvType);
            return;
          }
        }
      }
    }
    
    fetch('/run/', {
      method: 'POST',
      body: formData,
      headers: {
        'X-CSRFToken': formData.get('csrfmiddlewaretoken')
      }
    })
    .then(response => response.json())
    .then(data => {
      if (data.success === false && data.suggestion) {
        // Show large dataset warning modal
        showLargeDatasetModal(data);
      } else {
        // Redirect to results page
        window.location.href = data.redirect_url || '/';
      }
    })
    .catch(error => {
      console.error('Error:', error);
      // Fallback to normal form submission
      form.submit();
    });
  }

  // Show large dataset warning modal
  function showLargeDatasetModal(data) {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.style.cssText = 'display: block; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5);';
    
    modal.innerHTML = `
      <div class="modal-content" style="background-color: white; margin: 10% auto; padding: 20px; border-radius: 8px; width: 80%; max-width: 500px;">
        <div class="modal-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
          <h3>Large Dataset Warning</h3>
          <button type="button" onclick="closeLargeDatasetModal()" style="background: none; border: none; font-size: 24px; cursor: pointer;">×</button>
        </div>
        <div class="modal-body">
          <p style="margin-bottom: 15px;">
            <strong>Dataset Size:</strong> ${data.total_rows.toLocaleString()} rows
          </p>
          <p style="margin-bottom: 15px;">
            ${data.error}
          </p>
          <p style="margin-bottom: 20px;">
            ${data.suggestion}
          </p>
          <div style="display: flex; gap: 10px; justify-content: flex-end;">
            <button type="button" class="btn btn-ghost" onclick="closeLargeDatasetModal()">Cancel</button>
            <button type="button" class="btn" onclick="runWithSample(${data.sample_size})">Use Sample (${data.sample_size.toLocaleString()} rows)</button>
            <button type="button" class="btn btn-primary" onclick="runWithFullDataset()">Use Full Dataset</button>
          </div>
        </div>
      </div>
    `;
    
    document.body.appendChild(modal);
    window.currentModal = modal;
  }

  // Close large dataset modal
  function closeLargeDatasetModal() {
    if (window.currentModal) {
      window.currentModal.remove();
      window.currentModal = null;
    }
  }

  // Show Bayesian DV error modal
  function showBayesianDVErrorModal(dvType) {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.style.cssText = 'display: block; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5);';
    
    modal.innerHTML = `
      <div class="modal-content" style="background-color: white; margin: 15% auto; padding: 24px; border-radius: 12px; width: 80%; max-width: 500px; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);">
        <div class="modal-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
          <h3 style="margin: 0; color: #dc2626; font-size: 1.25rem;">Bayesian Regression Not Supported</h3>
          <button type="button" onclick="closeBayesianDVErrorModal()" style="background: none; border: none; font-size: 24px; cursor: pointer; color: #6b7280;">×</button>
        </div>
        <div class="modal-body">
          <div style="display: flex; align-items: center; margin-bottom: 16px; padding: 12px; background-color: #fef2f2; border-radius: 8px; border-left: 4px solid #dc2626;">
            <div style="margin-right: 12px;">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#dc2626" stroke-width="2">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="15" y1="9" x2="9" y2="15"></line>
                <line x1="9" y1="9" x2="15" y2="15"></line>
              </svg>
            </div>
            <div>
              <p style="margin: 0; font-weight: 600; color: #dc2626;">Analysis Type Not Available</p>
            </div>
          </div>
          <p style="margin-bottom: 16px; color: #374151; line-height: 1.6;">
            Bayesian regression with <strong>${dvType}</strong> dependent variables is not yet supported in this version of the application.
          </p>
          <p style="margin-bottom: 20px; color: #6b7280; line-height: 1.6;">
            For categorical outcomes (binary, ordinal, multinomial), please use <strong>Frequentist Regression</strong> instead, which provides excellent results for these analysis types.
          </p>
          <div style="display: flex; gap: 12px; justify-content: flex-end;">
            <button type="button" class="btn btn-ghost" onclick="closeBayesianDVErrorModal()">Cancel</button>
            <button type="button" class="btn btn-primary" onclick="switchToFrequentist()">Switch to Frequentist</button>
          </div>
        </div>
      </div>
    `;
    
    document.body.appendChild(modal);
    window.currentModal = modal;
  }

  // Close Bayesian DV error modal
  function closeBayesianDVErrorModal() {
    if (window.currentModal) {
      window.currentModal.remove();
      window.currentModal = null;
    }
  }

  // Switch to frequentist analysis
  function switchToFrequentist() {
    const frequentistRadio = document.querySelector('input[name="analysis_type"][value="frequentist"]');
    if (frequentistRadio) {
      frequentistRadio.checked = true;
      // Trigger change event to update UI
      frequentistRadio.dispatchEvent(new Event('change'));
    }
    closeBayesianDVErrorModal();
  }

  // Run analysis with sample
  function runWithSample(sampleSize) {
    const form = document.getElementById('analysisForm');
    const formData = new FormData(form);
    formData.set('use_sample', 'true');
    
    fetch('/run/', {
      method: 'POST',
      body: formData,
      headers: {
        'X-CSRFToken': formData.get('csrfmiddlewaretoken')
      }
    })
    .then(response => response.json())
    .then(data => {
      closeLargeDatasetModal();
      if (data.redirect_url) {
        window.location.href = data.redirect_url;
      } else {
        window.location.reload();
      }
    })
    .catch(error => {
      console.error('Error:', error);
      closeLargeDatasetModal();
      window.location.reload();
    });
  }

  // Run analysis with full dataset
  function runWithFullDataset() {
    closeLargeDatasetModal();
    const form = document.getElementById('analysisForm');
    form.submit();
  }

  document.addEventListener("DOMContentLoaded", () => {
    toggleAdvanced();
    validateRun();

    const box = document.getElementById("equationBox");
    autoSize(box);

    // autosize + Cmd/Ctrl+Enter submit
    if (box) {
      box.addEventListener("input", () => { autoSize(box); validateRun(); });
      box.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
          const run = document.getElementById("runBtn");
          if (run && !run.disabled) {
            e.preventDefault();
            run.click();
          }
        }
      });
    }

    // react to selector changes
    const mod = document.getElementById("moduleSelect");
    const ds  = document.getElementById("datasetSelect");
    if (mod) mod.addEventListener("change", () => { toggleAdvanced(); validateRun(); });
    if (ds)  ds.addEventListener("change", validateRun);
    
    // react to analysis type changes
    const analysisTypeRadios = document.querySelectorAll('input[name="analysis_type"]');
    analysisTypeRadios.forEach(radio => {
      radio.addEventListener("change", validateRun);
    });
  });
})();

(function () {
  // Mark selects with empty value as "placeholder" to tint the text
  function updateSelectPlaceholderState(sel) {
    const isEmpty = (sel.value || "").trim() === "";
    if (isEmpty) sel.classList.add("is-placeholder");
    else sel.classList.remove("is-placeholder");
  }

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("select.input").forEach(sel => {
      updateSelectPlaceholderState(sel);
      sel.addEventListener("change", () => updateSelectPlaceholderState(sel));
    });
  });
})();

(function () {
  function renderPlot(containerId, dataScriptId) {
    const el = document.getElementById(containerId);
    const dataEl = document.getElementById(dataScriptId);
    if (!el || !dataEl) return;
    try {
      const fig = JSON.parse(dataEl.textContent);
      const layout = fig.layout || {};
      const opts = {responsive: true, displaylogo: false}; // keeps modebar minimal
      Plotly.newPlot(el, fig.data || [], layout, opts);
    } catch (e) {
      console.warn("Plotly JSON parse error:", e);
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    renderPlot("plot-spotlight", "plot-spotlight-data");

    // Optional: tiny UX—click a table header to sort ascending/descending
    const tbl = document.getElementById("regTable");
    if (tbl) {
      const ths = tbl.querySelectorAll("thead th");
      ths.forEach((th, colIdx) => {
        th.style.cursor = "pointer";
        th.addEventListener("click", () => {
          const tbody = tbl.querySelector("tbody");
          const rows = Array.from(tbody.querySelectorAll("tr"));
          const asc = th.getAttribute("data-sort") !== "asc";
          ths.forEach(h => h.removeAttribute("data-sort"));
          th.setAttribute("data-sort", asc ? "asc" : "desc");
          rows.sort((a, b) => {
            const ta = a.children[colIdx].innerText;
            const tb = b.children[colIdx].innerText;
            const na = parseFloat(ta.replace(/[^\d.\-]/g, ""));
            const nb = parseFloat(tb.replace(/[^\d.\-]/g, ""));
            if (!isNaN(na) && !isNaN(nb)) return asc ? na - nb : nb - na;
            return asc ? ta.localeCompare(tb) : tb.localeCompare(ta);
          });
          rows.forEach(r => tbody.appendChild(r));
        });
      });
    }
  });
})();

// Equation validation and autocomplete system
(function() {
  window.datasetVariables = [];
  let currentDatasetId = null;
  let autocompleteVisible = false;
  let selectedAutocompleteIndex = -1;
  let equationValidator = null;

  // Initialize equation validator
  function initEquationValidator() {
    const equationBox = document.getElementById('equationBox');
    const statusDiv = document.getElementById('equationStatus');
    const datasetSelect = document.getElementById('datasetSelect');
    
    if (!equationBox || !statusDiv || !datasetSelect) return;

    equationValidator = {
      variables: [],
      errors: [],
      
      setVariables(vars) {
        this.variables = vars;
        this.validate();
      },
      
      validate() {
        const equation = equationBox.value.trim();
        this.errors = [];
        
        if (!equation) {
          this.updateStatus('', '');
          return true;
        }
        
        // Use new parsing logic for validation
        const parseResult = parseEquation(equation);
        
        if (parseResult.hasErrors) {
          // Collect all error messages
          const allErrors = [];
          if (parseResult.syntaxErrors.length > 0) {
            allErrors.push(...parseResult.syntaxErrors);
          }
          if (parseResult.unknownVars.length > 0) {
            allErrors.push(`Unknown variables: ${parseResult.unknownVars.join(', ')}`);
          }
          if (parseResult.invalidElements.length > 0) {
            allErrors.push(...parseResult.invalidElements);
          }
          
          this.errors = allErrors;
          this.updateStatus(allErrors.join('; '), 'error');
        } else {
          // Count valid terms for success message
          const rhs = equation.split('~')[1];
          if (rhs) {
            const terms = rhs.split('+').map(t => t.trim()).filter(t => t);
            this.updateStatus(`✓ All variables valid (${terms.length} terms)`, 'success');
          } else {
            this.updateStatus('', '');
          }
        }
        
        // Always return true to allow popup to be shown
        return true;
      },
      
      updateStatus(message, type) {
        statusDiv.textContent = message;
        statusDiv.className = `equation-status ${type}`;
        
        // Update equation box styling
        if (type === 'error') {
          equationBox.classList.add('has-errors');
        } else {
          equationBox.classList.remove('has-errors');
        }
      },
      
      isValid() {
        return this.errors.length === 0;
      }
    };
    
    window.equationValidator = equationValidator;
  }

  // Load dataset variables
  window.loadDatasetVariables = function(datasetId) {
    console.log('Loading dataset variables for ID:', datasetId);
    
    if (!datasetId) {
      window.datasetVariables = [];
      window.datasetColumnTypes = {};
      currentDatasetId = null;
      if (equationValidator) {
        equationValidator.setVariables([]);
      }
      return;
    }
    
    fetch(`/api/dataset/${datasetId}/variables/`)
      .then(response => {
        console.log('Dataset variables response status:', response.status);
        return response.json();
      })
      .then(data => {
        console.log('Dataset variables data:', data);
        if (data.success) {
          window.datasetVariables = data.variables;
          window.datasetColumnTypes = data.column_types || {};
          currentDatasetId = datasetId;
          console.log('Loaded variables:', window.datasetVariables);
          console.log('Loaded column types:', window.datasetColumnTypes);
          
          if (equationValidator) {
            equationValidator.setVariables(window.datasetVariables);
          }
          
          // Enable equation box
          const equationBox = document.getElementById('equationBox');
          if (equationBox) {
            equationBox.disabled = false;
            equationBox.placeholder = `Type your equation(s) like a chat message…

Examples
  y ~ x1 + x2 + x1:x2
  y1 + y2 ~ x + z
  y ~ x * m        (shorthand for x + m + x:m)`;
            console.log('Equation box enabled');
          } else {
            console.error('Equation box not found');
          }
        } else {
          console.error('Failed to load dataset variables:', data.error);
        }
      })
      .catch(error => {
        console.error('Error loading dataset variables:', error);
      });
  }

  // Show autocomplete dropdown
  window.showAutocomplete = function(query, cursorPosition) {
    console.log('showAutocomplete called with query:', query, 'cursorPosition:', cursorPosition);
    console.log('Available variables:', window.datasetVariables);
    
    if (!query || query.length < 1) {
      console.log('Query too short, hiding autocomplete');
      hideAutocomplete();
      return;
    }
    
    const matches = window.datasetVariables.filter(variable => 
      variable.toLowerCase().includes(query.toLowerCase())
    ).slice(0, 10); // Limit to 10 suggestions
    
    console.log('Filtered matches:', matches);
    
    if (matches.length === 0) {
      console.log('No matches found, hiding autocomplete');
      hideAutocomplete();
      return;
    }
    
    const dropdown = document.getElementById('autocompleteDropdown');
    if (!dropdown) {
      return;
    }
    
    // Calculate position based on cursor position
    const equationBox = document.getElementById('equationBox');
    const textBeforeCursor = equationBox.value.substring(0, cursorPosition);
    
    // Create a temporary element to measure text width
    const tempDiv = document.createElement('div');
    tempDiv.style.position = 'absolute';
    tempDiv.style.visibility = 'hidden';
    tempDiv.style.whiteSpace = 'pre-wrap';
    tempDiv.style.font = window.getComputedStyle(equationBox).font;
    tempDiv.style.padding = window.getComputedStyle(equationBox).padding;
    tempDiv.style.border = window.getComputedStyle(equationBox).border;
    tempDiv.style.width = equationBox.offsetWidth + 'px';
    tempDiv.textContent = textBeforeCursor;
    
    document.body.appendChild(tempDiv);
    
    // Get the position of the cursor
    const textHeight = tempDiv.offsetHeight;
    const textWidth = tempDiv.offsetWidth;
    
    // Find the last newline before cursor
    const lastNewline = textBeforeCursor.lastIndexOf('\n');
    const lineStart = lastNewline + 1;
    const currentLine = textBeforeCursor.substring(lineStart);
    
    // Create another temp element for just the current line
    const lineDiv = document.createElement('div');
    lineDiv.style.position = 'absolute';
    lineDiv.style.visibility = 'hidden';
    lineDiv.style.whiteSpace = 'pre';
    lineDiv.style.font = window.getComputedStyle(equationBox).font;
    lineDiv.textContent = currentLine;
    document.body.appendChild(lineDiv);
    
    const lineWidth = lineDiv.offsetWidth;
    const lineHeight = lineDiv.offsetHeight;
    
    // Clean up temp elements
    document.body.removeChild(tempDiv);
    document.body.removeChild(lineDiv);
    
    // Calculate position relative to the textarea
    const textareaRect = equationBox.getBoundingClientRect();
    const containerRect = equationBox.parentElement.getBoundingClientRect();
    
    // Position the dropdown
    const leftOffset = lineWidth + 10; // 10px offset from the text
    const topOffset = (lastNewline === -1 ? 0 : (lastNewline + 1) * lineHeight) + lineHeight;
    
    dropdown.style.position = 'absolute';
    dropdown.style.left = leftOffset + 'px';
    dropdown.style.top = topOffset + 'px';
    dropdown.style.width = '200px'; // Fixed width for better appearance
    dropdown.style.maxWidth = (equationBox.offsetWidth - leftOffset) + 'px';
    
    dropdown.innerHTML = '';
    console.log('Creating dropdown items for matches:', matches);
    
    matches.forEach((variable, index) => {
      const item = document.createElement('div');
      item.className = 'autocomplete-item';
      item.textContent = variable;
      item.addEventListener('click', () => selectAutocompleteItem(variable, cursorPosition));
      dropdown.appendChild(item);
      console.log('Added item:', variable);
    });
    
    dropdown.style.display = 'block';
    autocompleteVisible = true;
    selectedAutocompleteIndex = 0;
    updateAutocompleteSelection();
    console.log('Dropdown should now be visible');
  }

  // Hide autocomplete dropdown
  window.hideAutocomplete = function() {
    console.log('hideAutocomplete called');
    const dropdown = document.getElementById('autocompleteDropdown');
    if (dropdown) {
      dropdown.style.display = 'none';
      autocompleteVisible = false;
      selectedAutocompleteIndex = -1;
    } else {
      console.error('Autocomplete dropdown not found');
    }
  }

  // Update autocomplete selection highlighting
  function updateAutocompleteSelection() {
    const items = document.querySelectorAll('.autocomplete-item');
    items.forEach((item, index) => {
      item.classList.toggle('highlighted', index === selectedAutocompleteIndex);
    });
  }

  // Select an autocomplete item
  window.selectAutocompleteItem = function(variable, cursorPosition) {
    const equationBox = document.getElementById('equationBox');
    const value = equationBox.value;
    const beforeCursor = value.substring(0, cursorPosition);
    const afterCursor = value.substring(cursorPosition);
    
    // Find the start of the current word
    const wordStart = beforeCursor.search(/\b[a-zA-Z_][a-zA-Z0-9_]*$/);
    const startPos = wordStart >= 0 ? wordStart : cursorPosition;
    
    // Replace the current word with the selected variable
    const newValue = value.substring(0, startPos) + variable + afterCursor;
    equationBox.value = newValue;
    
    // Set cursor position after the inserted variable
    const newCursorPos = startPos + variable.length;
    equationBox.setSelectionRange(newCursorPos, newCursorPos);
    
    hideAutocomplete();
    equationBox.focus();
    
    // Trigger validation
    if (equationValidator) {
      equationValidator.validate();
    }
    validateRun();
  }

  // Handle keyboard navigation in autocomplete
  window.handleAutocompleteKeydown = function(event) {
    if (!autocompleteVisible) return;
    
    const items = document.querySelectorAll('.autocomplete-item');
    
    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault();
        selectedAutocompleteIndex = Math.min(selectedAutocompleteIndex + 1, items.length - 1);
        updateAutocompleteSelection();
        break;
      case 'ArrowUp':
        event.preventDefault();
        selectedAutocompleteIndex = Math.max(selectedAutocompleteIndex - 1, 0);
        updateAutocompleteSelection();
        break;
      case 'Enter':
        event.preventDefault();
        if (selectedAutocompleteIndex >= 0 && items[selectedAutocompleteIndex]) {
          items[selectedAutocompleteIndex].click();
        }
        break;
      case 'Escape':
        hideAutocomplete();
        break;
    }
  }

  // Test function for debugging autocomplete
  window.testAutocomplete = function() {
    console.log('Testing autocomplete...');
    console.log('Dataset variables:', window.datasetVariables);
    console.log('Equation box:', document.getElementById('equationBox'));
    console.log('Autocomplete dropdown:', document.getElementById('autocompleteDropdown'));
    
    if (window.datasetVariables.length > 0) {
      showAutocomplete('a', 0);
    } else {
      console.log('No variables loaded, trying to load dataset 18...');
      loadDatasetVariables(18);
    }
  };

  // Auto-upload functionality
  function initAutoUpload() {
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('fileInput');
    const uploadForm = document.querySelector('.upload-form');
    const uploadProgress = document.getElementById('uploadProgress');
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    const dropzoneContent = document.querySelector('.dropzone-content');

    if (!dropzone || !fileInput || !uploadForm) return;

    // Handle file selection
    fileInput.addEventListener('change', (e) => {
      if (e.target.files.length > 0) {
        uploadFile(e.target.files[0]);
      }
    });

    // Handle drag and drop
    dropzone.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropzone.classList.add('drag-over');
    });

    dropzone.addEventListener('dragleave', (e) => {
      e.preventDefault();
      dropzone.classList.remove('drag-over');
    });

    dropzone.addEventListener('drop', (e) => {
      e.preventDefault();
      dropzone.classList.remove('drag-over');
      
      const files = e.dataTransfer.files;
      if (files.length > 0) {
        uploadFile(files[0]);
      }
    });

    function uploadFile(file) {
      // Validate file type
      const allowedTypes = ['.csv', '.xlsx', '.xls'];
      const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
      
      if (!allowedTypes.includes(fileExtension)) {
        alert('Please select a CSV, XLSX, or XLS file.');
        return;
      }

      // Show progress
      showUploadProgress();
      
      // Create FormData
      const formData = new FormData();
      formData.append('dataset', file);
      formData.append('dataset_name', document.querySelector('input[name="dataset_name"]').value);
      formData.append('csrfmiddlewaretoken', document.querySelector('[name=csrfmiddlewaretoken]').value);

      // Upload file
      const xhr = new XMLHttpRequest();
      
      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
          const percentComplete = (e.loaded / e.total) * 100;
          updateProgress(percentComplete);
        }
      });

      xhr.addEventListener('load', () => {
        if (xhr.status === 200) {
          // Success - redirect to the new dataset
          const response = JSON.parse(xhr.responseText);
          if (response.dataset_id) {
            window.location.href = `/app/?dataset_id=${response.dataset_id}`;
          } else {
            window.location.reload();
          }
        } else {
          hideUploadProgress();
          alert('Upload failed. Please try again.');
        }
      });

      xhr.addEventListener('error', () => {
        hideUploadProgress();
        alert('Upload failed. Please try again.');
      });

      xhr.open('POST', '/datasets/upload/');
      xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
      xhr.send(formData);
    }

    function showUploadProgress() {
      dropzoneContent.style.opacity = '0.3';
      uploadProgress.style.display = 'block';
      progressFill.style.width = '0%';
      progressText.textContent = 'Uploading...';
    }

    function updateProgress(percent) {
      progressFill.style.width = percent + '%';
      progressText.textContent = `Uploading... ${Math.round(percent)}%`;
    }

    function hideUploadProgress() {
      dropzoneContent.style.opacity = '1';
      uploadProgress.style.display = 'none';
    }
  }

  // Initialize everything when DOM is loaded
  document.addEventListener('DOMContentLoaded', () => {
    initEquationValidator();
    initAutoUpload();
    
    const equationBox = document.getElementById('equationBox');
    const datasetSelect = document.getElementById('datasetSelect');
    
    if (equationBox && datasetSelect) {
      // Handle dataset selection
      datasetSelect.addEventListener('change', (e) => {
        const datasetId = e.target.value;
        loadDatasetVariables(datasetId);
        validateRun();
      });
      
      // Handle equation input
      equationBox.addEventListener('input', (e) => {
        if (equationValidator) {
          equationValidator.validate();
        }
        validateRun();
        
        // Handle autocomplete
        const cursorPosition = e.target.selectionStart;
        const value = e.target.value;
        const beforeCursor = value.substring(0, cursorPosition);
        
        console.log('Input event - cursorPosition:', cursorPosition, 'value:', value, 'beforeCursor:', beforeCursor);
        console.log('Available variables:', window.datasetVariables);
        
        // Find the current word being typed
        const wordMatch = beforeCursor.match(/\b[a-zA-Z_][a-zA-Z0-9_]*$/);
        console.log('Word match:', wordMatch);
        
        // Also try a simpler approach - just get the last word
        const words = beforeCursor.trim().split(/\s+/);
        const lastWord = words[words.length - 1] || '';
        console.log('Last word (simple):', lastWord);
        
        if (wordMatch && window.datasetVariables.length > 0) {
          console.log('Calling showAutocomplete with:', wordMatch[0]);
          showAutocomplete(wordMatch[0], cursorPosition);
        } else if (lastWord && window.datasetVariables.length > 0 && lastWord.length >= 1) {
          console.log('Calling showAutocomplete with last word:', lastWord);
          showAutocomplete(lastWord, cursorPosition);
        } else {
          console.log('Hiding autocomplete - wordMatch:', wordMatch, 'lastWord:', lastWord, 'variables length:', window.datasetVariables.length);
          hideAutocomplete();
        }
      });
      
      // Handle keyboard events for autocomplete
      equationBox.addEventListener('keydown', (e) => {
        handleAutocompleteKeydown(e);
        
        // Handle Ctrl/Cmd+Enter to run
        if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
          const run = document.getElementById('runBtn');
          if (run && !run.disabled) {
            e.preventDefault();
            run.click();
          }
        }
      });
      
      // Hide autocomplete when clicking outside
      document.addEventListener('click', (e) => {
        if (!e.target.closest('.equation-container')) {
          hideAutocomplete();
        }
      });
      
      // Load variables if dataset is already selected
      if (datasetSelect.value) {
        loadDatasetVariables(datasetSelect.value);
        // Enable equation box if dataset is already selected
        equationBox.disabled = false;
        equationBox.placeholder = `Type your equation(s) like a chat message…

Examples
  y ~ x1 + x2 + x1:x2
  y1 + y2 ~ x + z
  y ~ x * m        (shorthand for x + m + x:m)`;
      }
      
      // Auto-select dataset if specified in URL
      const urlParams = new URLSearchParams(window.location.search);
      const autoSelectDatasetId = urlParams.get('dataset_id');
      if (autoSelectDatasetId && !datasetSelect.value) {
        datasetSelect.value = autoSelectDatasetId;
        loadDatasetVariables(autoSelectDatasetId);
        // Enable equation box
        equationBox.disabled = false;
        equationBox.placeholder = `Type your equation(s) like a chat message…

Examples
  y ~ x1 + x2 + x1:x2
  y1 + y2 ~ x + z
  y ~ x * m        (shorthand for x + m + x:m)`;
        validateRun();
        
        // Clean up URL by removing the parameter
        const newUrl = new URL(window.location);
        newUrl.searchParams.delete('dataset_id');
        window.history.replaceState({}, '', newUrl);
      }
    }
  });
})();

// Error Analysis and Fix Modal System
(function() {
  let currentErrorAnalysis = null;
  
  // Analyze equation for syntax and variable errors using new parsing logic
  window.analyzeEquationErrors = function(equation) {
    const analysis = {
      hasErrors: false,
      hasSyntaxErrors: false,
      hasUnknownVars: false,
      hasInvalidElements: false,
      syntaxErrors: [],
      unknownVars: [],
      invalidElements: [],
      fixedEquation: equation,
      originalEquation: equation
    };
    
    if (!equation.trim()) {
      return analysis;
    }
    
    // Parse equation using new logic
    const parseResult = parseEquation(equation);
    
    if (parseResult.hasErrors) {
      analysis.hasErrors = true;
      analysis.hasSyntaxErrors = parseResult.hasSyntaxErrors;
      analysis.hasUnknownVars = parseResult.hasUnknownVars;
      analysis.hasInvalidElements = parseResult.hasInvalidElements;
      analysis.syntaxErrors = parseResult.syntaxErrors;
      analysis.unknownVars = parseResult.unknownVars;
      analysis.invalidElements = parseResult.invalidElements;
      analysis.fixedEquation = parseResult.fixedEquation;
    }
    
    return analysis;
  };
  
  // New parsing logic based on equation structure
  window.parseEquation = function(equation) {
    const result = {
      hasErrors: false,
      hasSyntaxErrors: false,
      hasUnknownVars: false,
      hasInvalidElements: false,
      syntaxErrors: [],
      unknownVars: [],
      invalidElements: [],
      fixedEquation: equation,
      originalEquation: equation
    };
    
    if (!equation.trim()) {
      return result;
    }
    
    // Split equation by ~ to separate LHS and RHS
    const parts = equation.split('~');
    if (parts.length !== 2) {
      result.hasErrors = true;
      result.hasSyntaxErrors = true;
      result.syntaxErrors.push('Your equation should contain exactly one ~');
      return result;
    }
    
    const lhs = parts[0].trim();
    const rhs = parts[1].trim();
    
    // Parse LHS (dependent variable) - handle spaces in variable names
    const lhsResult = parseSimpleTerm(lhs);
    if (!lhsResult.isValid) {
      result.hasErrors = true;
      result.hasUnknownVars = result.hasUnknownVars || lhsResult.unknownVars.length > 0;
      result.hasInvalidElements = result.hasInvalidElements || lhsResult.invalidElements.length > 0;
      result.unknownVars = result.unknownVars.concat(lhsResult.unknownVars);
      result.invalidElements = result.invalidElements.concat(lhsResult.invalidElements);
    }
    
    // Parse RHS (predictors) using new logic
    const rhsResult = parseRHS(rhs);
    
    if (rhsResult.hasErrors) {
      result.hasErrors = true;
      result.hasSyntaxErrors = result.hasSyntaxErrors || rhsResult.hasSyntaxErrors;
      result.hasUnknownVars = result.hasUnknownVars || rhsResult.hasUnknownVars;
      result.hasInvalidElements = result.hasInvalidElements || rhsResult.hasInvalidElements;
      result.syntaxErrors = result.syntaxErrors.concat(rhsResult.syntaxErrors);
      result.unknownVars = result.unknownVars.concat(rhsResult.unknownVars);
      result.invalidElements = result.invalidElements.concat(rhsResult.invalidElements);
      result.fixedEquation = `${lhs} ~ ${rhsResult.fixedEquation}`;
    }
    
    return result;
  };
  
  // Parse RHS (predictors) using the new structure-based logic
  function parseRHS(rhs) {
    const result = {
      hasErrors: false,
      hasSyntaxErrors: false,
      hasUnknownVars: false,
      hasInvalidElements: false,
      syntaxErrors: [],
      unknownVars: [],
      invalidElements: [],
      fixedEquation: rhs
    };
    
    // Split by + to get main terms
    const mainTerms = rhs.split('+').map(term => term.trim()).filter(term => term);
    
    const validTerms = [];
    const errors = [];
    const unknownVars = [];
    const invalidElements = [];
    
    for (let i = 0; i < mainTerms.length; i++) {
      const term = mainTerms[i];
      
      // Check if term contains * (interaction)
      if (term.includes('*')) {
        const interactionResult = parseInteractionTerm(term);
        
        if (interactionResult.isValid) {
          validTerms.push(interactionResult.term);
        } else {
          errors.push(...interactionResult.errors);
          unknownVars.push(...interactionResult.unknownVars);
          invalidElements.push(...interactionResult.invalidElements);
          
          // If we want to keep the term despite errors, we can add it here
          // For now, we'll skip invalid terms
        }
      } else {
        // Simple term (no interaction)
        const simpleResult = parseSimpleTerm(term);
        
        if (simpleResult.isValid) {
          validTerms.push(simpleResult.term);
        } else {
          errors.push(...simpleResult.errors);
          unknownVars.push(...simpleResult.unknownVars);
          invalidElements.push(...simpleResult.invalidElements);
          
          // If we want to keep the term despite errors, we can add it here
          // For now, we'll skip invalid terms
        }
      }
    }
    
    if (errors.length > 0 || unknownVars.length > 0 || invalidElements.length > 0) {
      result.hasErrors = true;
      result.hasSyntaxErrors = errors.length > 0;
      result.hasUnknownVars = unknownVars.length > 0;
      result.hasInvalidElements = invalidElements.length > 0;
      result.syntaxErrors = errors;
      result.unknownVars = [...new Set(unknownVars)];
      result.invalidElements = invalidElements;
      result.fixedEquation = validTerms.join(' + ');
    }
    
    return result;
  }
  
  // Parse interaction term (contains *)
  function parseInteractionTerm(term) {
    const result = {
      isValid: true,
      term: term,
      errors: [],
      unknownVars: [],
      invalidElements: []
    };
    
    // Split by * to get interaction components
    const components = term.split('*').map(comp => comp.trim()).filter(comp => comp);
    
    
    
    const validComponents = [];
    
    for (const component of components) {
      const compResult = parseSimpleTerm(component);
      
      if (compResult.isValid) {
        validComponents.push(compResult.term);
      } else {
        result.isValid = false;
        result.errors.push(...compResult.errors);
        result.unknownVars.push(...compResult.unknownVars);
        result.invalidElements.push(...compResult.invalidElements);
      }
    }
    
    if (result.isValid) {
      result.term = validComponents.join('*');
    }
    
    return result;
  }
  
  // Parse simple term (no interaction)
  function parseSimpleTerm(term) {
    const result = {
      isValid: true,
      term: term,
      errors: [],
      unknownVars: [],
      invalidElements: []
    };
    
    // Check for invalid characters - allow spaces, dots, hyphens, and other common special chars
    const invalidChars = term.match(/[^a-zA-Z0-9_\s.\-()[\]+*:~^$|\\/?]/g);
    if (invalidChars) {
      result.isValid = false;
      result.errors.push(`Invalid characters in term: ${term}`);
      result.invalidElements.push(`Invalid characters: ${[...new Set(invalidChars)].join(', ')}`);
    }
    
    // Check for numbers
    const numbers = term.match(/\b\d+(\.\d+)?\b/g);
    if (numbers) {
      result.isValid = false;
      result.errors.push(`Numbers not allowed in terms: ${term}`);
      result.invalidElements.push(`Numbers: ${numbers.join(', ')}`);
    }
    
    // Check if it's a valid variable
    if (window.equationValidator && window.equationValidator.variables) {
      if (!window.equationValidator.variables.includes(term)) {
        result.isValid = false;
        result.unknownVars.push(term);
      }
    }
    
    return result;
  }
  
  // Show error fix modal
  window.showErrorFixModal = function(analysis) {
    currentErrorAnalysis = analysis;
    const modal = document.getElementById('errorFixModal');
    const title = document.getElementById('errorModalTitle');
    const message = document.getElementById('errorModalMessage');
    const originalEq = document.getElementById('originalEquation');
    const fixedEq = document.getElementById('fixedEquation');
    const fixedSection = document.getElementById('fixedEquationSection');
    const unknownVarsList = document.getElementById('unknownVarsList');
    const unknownVarsSection = document.getElementById('unknownVarsSection');
    const acceptBtn = document.getElementById('acceptFixBtn');
    const dropBtn = document.getElementById('dropUnknownBtn');
    const returnBtn = document.getElementById('returnToEditBtn');
    
    // Set title and message
    const hasMultipleErrors = (analysis.hasSyntaxErrors ? 1 : 0) + (analysis.hasInvalidElements ? 1 : 0) + (analysis.hasUnknownVars ? 1 : 0) > 1;
    
    if (hasMultipleErrors) {
      title.textContent = 'Fix Equation Issues';
      message.textContent = 'Your equation has multiple issues. We can fix syntax and invalid elements, but you need to replace unknown variables.';
      message.className = 'error-modal-message mixed-error';
    } else if (analysis.hasSyntaxErrors) {
      title.textContent = 'Fix Syntax Errors';
      message.textContent = 'Your equation has syntax errors. We can automatically fix them for you.';
      message.className = 'error-modal-message syntax-error';
    } else if (analysis.hasInvalidElements) {
      title.textContent = 'Fix Invalid Elements';
      message.textContent = 'Your equation contains numbers or invalid characters. We can automatically remove them for you.';
      message.className = 'error-modal-message syntax-error';
    } else if (analysis.hasUnknownVars) {
      title.textContent = 'Unknown Variables';
      message.textContent = 'Your equation contains variables that don\'t exist in the dataset. You can either remove them or replace them with valid variables.';
      message.className = 'error-modal-message unknown-vars';
    }
    
    // Show original equation
    originalEq.textContent = analysis.originalEquation;
    
    // Show fixed equation if syntax errors or invalid elements exist
    if (analysis.hasSyntaxErrors || analysis.hasInvalidElements) {
      fixedEq.textContent = analysis.fixedEquation;
      fixedSection.style.display = 'block';
    } else {
      fixedSection.style.display = 'none';
    }
    
    // Show unknown variables if they exist
    if (analysis.hasUnknownVars) {
      unknownVarsList.innerHTML = '';
      analysis.unknownVars.forEach(variable => {
        const tag = document.createElement('span');
        tag.className = 'unknown-var-tag';
        tag.textContent = variable;
        unknownVarsList.appendChild(tag);
      });
      unknownVarsSection.style.display = 'block';
    } else {
      unknownVarsSection.style.display = 'none';
    }
    
    // Show appropriate buttons
    const canAutoFix = analysis.hasSyntaxErrors || analysis.hasInvalidElements;
    const hasUnknownVars = analysis.hasUnknownVars;
    
    if (canAutoFix && hasUnknownVars) {
      // Both auto-fixable and unknown vars: show accept fix and return to edit
      acceptBtn.style.display = 'inline-block';
      acceptBtn.textContent = 'Accept Auto-Fix';
      dropBtn.style.display = 'none';
      returnBtn.style.display = 'inline-block';
    } else if (canAutoFix) {
      // Only auto-fixable errors: show accept fix and return to edit
      acceptBtn.style.display = 'inline-block';
      acceptBtn.textContent = 'Accept Fix';
      dropBtn.style.display = 'none';
      returnBtn.style.display = 'inline-block';
    } else if (hasUnknownVars) {
      // Only unknown vars: show drop unknown and return to edit
      acceptBtn.style.display = 'none';
      dropBtn.style.display = 'inline-block';
      returnBtn.style.display = 'inline-block';
    }
    
    modal.style.display = 'flex';
  };
  
  // Close error modal
  window.closeErrorModal = function() {
    const modal = document.getElementById('errorFixModal');
    modal.style.display = 'none';
    currentErrorAnalysis = null;
  };
  
  // Accept fix
  window.acceptFix = function() {
    if (!currentErrorAnalysis) return;
    
    const equationBox = document.getElementById('equationBox');
    equationBox.value = currentErrorAnalysis.fixedEquation;
    
    // Trigger validation
    if (window.equationValidator) {
      window.equationValidator.validate();
    }
    if (window.validateRun) {
      window.validateRun();
    }
    
    closeErrorModal();
  };
  
  // Drop unknown variables using new parsing logic
  window.dropUnknownVars = function() {
    if (!currentErrorAnalysis || !currentErrorAnalysis.hasUnknownVars) return;
    
    const equation = currentErrorAnalysis.originalEquation;
    
    // Parse the equation to get clean structure
    const parseResult = parseEquation(equation);
    
    // The parseResult.fixedEquation already contains only valid terms
    // This automatically removes unknown variables and their interactions
    const equationBox = document.getElementById('equationBox');
    equationBox.value = parseResult.fixedEquation;
    
    // Trigger validation
    if (window.equationValidator) {
      window.equationValidator.validate();
    }
    if (window.validateRun) {
      window.validateRun();
    }
    
    closeErrorModal();
  };
  
  
  // Return to edit
  window.returnToEdit = function() {
    closeErrorModal();
    const equationBox = document.getElementById('equationBox');
    equationBox.focus();
  };
  
  // Dataset Merge Functionality
  let selectedDatasets = [];
  let datasetColumns = {};
  
  // Add click event listeners to checkboxes for debugging
  document.addEventListener('DOMContentLoaded', function() {
    const checkboxes = document.querySelectorAll('.dataset-checkbox');
    console.log('Found checkboxes:', checkboxes.length);
    
    checkboxes.forEach((checkbox, index) => {
      checkbox.addEventListener('click', function(e) {
        console.log('Checkbox clicked:', index, 'checked:', this.checked);
        e.stopPropagation();
        // Call updateMergeButton after a short delay to ensure the checkbox state is updated
        setTimeout(() => {
          updateMergeButton();
        }, 10);
      });
    });
  });
  
  // Update merge button state
  window.updateMergeButton = function() {
    const checkboxes = document.querySelectorAll('.dataset-checkbox:checked');
    const mergeBtn = document.getElementById('mergeBtn');
    
    console.log('updateMergeButton called, checked checkboxes:', checkboxes.length);
    
    if (checkboxes.length >= 2) {
      mergeBtn.disabled = false;
      mergeBtn.style.opacity = '1';
      mergeBtn.style.cursor = 'pointer';
    } else {
      mergeBtn.disabled = true;
      mergeBtn.style.opacity = '0.5';
      mergeBtn.style.cursor = 'not-allowed';
    }
  };
  
  // Open merge modal
  window.openMergeModal = function() {
    const checkboxes = document.querySelectorAll('.dataset-checkbox:checked');
    if (checkboxes.length < 2) return;
    
    selectedDatasets = Array.from(checkboxes).map(cb => ({
      id: parseInt(cb.getAttribute('data-dataset-id')),
      name: cb.getAttribute('data-dataset-name')
    }));
    
    console.log('Selected datasets:', selectedDatasets);
    
    // Load columns for each dataset
    loadDatasetColumns();
    
    // Show modal
    document.getElementById('mergeModal').style.display = 'flex';
  };
  
  // Close merge modal
  window.closeMergeModal = function() {
    document.getElementById('mergeModal').style.display = 'none';
    selectedDatasets = [];
    datasetColumns = {};
  };
  
  // Load columns for selected datasets
  async function loadDatasetColumns() {
    const datasetsList = document.getElementById('mergeDatasetsList');
    datasetsList.innerHTML = '';
    
    console.log('Loading columns for datasets:', selectedDatasets);
    
    for (const dataset of selectedDatasets) {
      try {
        console.log('Fetching columns for dataset:', dataset.id);
        const response = await fetch(`/api/dataset/${dataset.id}/variables/`);
        const data = await response.json();
        
        console.log('Response for dataset', dataset.id, ':', data);
        
        if (data.success) {
          datasetColumns[dataset.id] = data.variables;
          createDatasetColumnSelector(dataset, data.variables);
        } else {
          console.error('Failed to load columns for dataset:', dataset.name, data);
        }
      } catch (error) {
        console.error('Error loading columns:', error);
      }
    }
  }
  
  // Create column selector for a dataset
  function createDatasetColumnSelector(dataset, columns) {
    const datasetsList = document.getElementById('mergeDatasetsList');
    
    const datasetCard = document.createElement('div');
    datasetCard.className = 'dataset-card';
    
    // Determine file type icon
    let fileIcon = '📄';
    if (dataset.name.toLowerCase().endsWith('.csv')) {
      fileIcon = '📊';
    } else if (dataset.name.toLowerCase().endsWith('.xlsx') || dataset.name.toLowerCase().endsWith('.xls')) {
      fileIcon = '📈';
    }
    
    datasetCard.innerHTML = `
      <div class="dataset-card-header">
        <div class="dataset-icon">${fileIcon}</div>
        <div class="dataset-name">${dataset.name}</div>
      </div>
      <div class="column-selector">
        <select class="merge-column-select" data-dataset-id="${dataset.id}" onchange="updateMergePreview()">
          <option value="">Select a column to merge on...</option>
          ${columns.map(col => `<option value="${col}">${col}</option>`).join('')}
        </select>
      </div>
    `;
    
    datasetsList.appendChild(datasetCard);
  }
  
  // Update merge preview
  window.updateMergePreview = function() {
    const selects = document.querySelectorAll('.merge-column-select');
    const previewContent = document.getElementById('mergePreviewContent');
    const executeBtn = document.getElementById('executeMergeBtn');
    
    const selectedColumns = Array.from(selects).map(select => ({
      datasetId: parseInt(select.getAttribute('data-dataset-id')),
      column: select.value
    }));
    
    const allSelected = selectedColumns.every(sc => sc.column);
    
    if (allSelected) {
      // Show preview
      const previewText = selectedColumns.map((sc, index) => {
        const dataset = selectedDatasets.find(d => d.id === sc.datasetId);
        return `${dataset.name}.${sc.column}`;
      }).join(' + ');
      
      previewContent.innerHTML = `
        <div style="color: #059669; font-weight: 500;">
          ✓ Ready to merge on: ${previewText}
        </div>
        <div style="margin-top: 8px; color: #6b7280; font-size: 13px;">
          This will create a new dataset combining all columns from both datasets where the selected columns have matching values.
        </div>
      `;
      
      executeBtn.disabled = false;
      executeBtn.style.opacity = '1';
    } else {
      previewContent.innerHTML = 'Select columns to see merge preview';
      executeBtn.disabled = true;
      executeBtn.style.opacity = '0.5';
    }
  };
  
  // Execute merge
  window.executeMerge = async function() {
    const selects = document.querySelectorAll('.merge-column-select');
    const selectedColumns = Array.from(selects).map(select => ({
      datasetId: parseInt(select.getAttribute('data-dataset-id')),
      column: select.value
    }));
    
    if (selectedColumns.length < 2 || !selectedColumns.every(sc => sc.column)) {
      alert('Please select columns for all datasets');
      return;
    }
    
    try {
      const response = await fetch('/api/datasets/merge/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        },
        body: JSON.stringify({
          datasets: selectedDatasets.map(d => d.id),
          merge_columns: selectedColumns
        })
      });
      
      const data = await response.json();
      
      if (data.success) {
        showModernSuccessPopup(data.dataset_name);
        closeMergeModal();
        // Reload page to show new dataset
        setTimeout(() => {
          window.location.reload();
        }, 2000);
      } else {
        showModernErrorPopup(data.error);
      }
    } catch (error) {
      console.error('Error merging datasets:', error);
      showModernErrorPopup('Error merging datasets. Please try again.');
    }
  };
  
  // Modern Success Popup
  function showModernSuccessPopup(datasetName) {
    const popup = document.createElement('div');
    popup.className = 'modern-success-popup';
    popup.innerHTML = `
      <div class="success-backdrop"></div>
      <div class="success-content">
        <div class="success-icon">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="currentColor">
            <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
          </svg>
        </div>
        <div class="success-text">
          <h3>Merge Successful!</h3>
          <p>Your datasets have been successfully merged into: <strong>${datasetName}</strong></p>
        </div>
        <div class="success-actions">
          <button onclick="this.closest('.modern-success-popup').remove()" class="btn-primary">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" style="margin-right: 8px;">
              <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
            </svg>
            Close
          </button>
        </div>
      </div>
    `;
    
    document.body.appendChild(popup);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
      if (popup.parentNode) {
        popup.remove();
      }
    }, 5000);
  }
  
  // Modern Error Popup
  function showModernErrorPopup(errorMessage) {
    const popup = document.createElement('div');
    popup.className = 'modern-error-popup';
    popup.innerHTML = `
      <div class="error-backdrop"></div>
      <div class="error-content">
        <div class="error-icon">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
          </svg>
        </div>
        <div class="error-text">
          <h3>Merge Failed</h3>
          <p>${errorMessage}</p>
        </div>
        <div class="error-actions">
          <button onclick="this.closest('.modern-error-popup').remove()" class="btn-secondary">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" style="margin-right: 8px;">
              <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
            </svg>
            Close
          </button>
        </div>
      </div>
    `;
    
    document.body.appendChild(popup);
  }
})();
