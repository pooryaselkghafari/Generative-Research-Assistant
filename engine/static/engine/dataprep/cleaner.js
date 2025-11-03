// engine/static/engine/dataprep/cleaner.js
(function () {
  function wire() {
    document.querySelectorAll('select.type-select').forEach(function (sel) {
      function toggleOrder() {
        const th = sel.closest('th');
        const box = th.querySelector('.order-input');
        if (sel.value === 'ordinal') {
          box.style.display = 'block';
        } else {
          box.style.display = 'none';
          const input = box.querySelector('input[name="order[]"]');
          if (input) input.value = '';
        }
      }
      sel.addEventListener('change', toggleOrder);
      toggleOrder();

      // When selecting ordinal, open ranking modal to build order list
      sel.addEventListener('change', function(){
        if (sel.value !== 'ordinal') return;
        const th = sel.closest('th');
        const colName = th.querySelector('input[name="orig[]"]').value;
        const dataEl = document.getElementById('uniques-data');
        let uniques = {};
        if (dataEl) {
          try { uniques = JSON.parse(dataEl.textContent || '{}'); } catch(e) { uniques = {}; }
        }
        const values = (uniques && uniques[colName]) ? uniques[colName].slice() : [];
        openRankModal(colName, values, function(ordered){
          const input = th.querySelector('input[name="order[]"]');
          if (input) input.value = ordered.join(', ');
        });
      });
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', wire);
  } else {
    wire();
  }
})();

// Simple ranking modal helpers (drag to reorder)
let __rankApplyCb = null;
function openRankModal(col, values, onApply){
  const modal = document.getElementById('rankModal');
  const list  = document.getElementById('rankList');
  const title = document.getElementById('rankTitle');
  if (!modal || !list) return;
  title.textContent = 'Rank values — ' + col;
  list.innerHTML = '';
  values.forEach(v => {
    const li = document.createElement('li');
    li.textContent = v;
    li.draggable = true;
    li.style.padding = '8px 10px';
    li.style.border = '1px solid #1f2937';
    li.style.borderRadius = '8px';
    li.style.margin = '6px 0';
    li.style.background = '#0b0f17';
    li.addEventListener('dragstart', (e) => {
      e.dataTransfer.setData('text/plain', v);
      li.classList.add('dragging');
    });
    li.addEventListener('dragend', () => li.classList.remove('dragging'));
    list.appendChild(li);
  });
  list.addEventListener('dragover', (e) => {
    e.preventDefault();
    const dragging = list.querySelector('.dragging');
    const after = getDragAfterElement(list, e.clientY);
    if (!dragging) return;
    if (after == null) list.appendChild(dragging);
    else list.insertBefore(dragging, after);
  });
  function getDragAfterElement(container, y){
    const els = [...container.querySelectorAll('li:not(.dragging)')];
    return els.reduce((closest, child) => {
      const box = child.getBoundingClientRect();
      const offset = y - box.top - box.height / 2;
      if (offset < 0 && offset > closest.offset) return { offset, element: child };
      else return closest;
    }, { offset: Number.NEGATIVE_INFINITY }).element;
  }
  __rankApplyCb = function(){
    const ordered = Array.from(list.querySelectorAll('li')).map(li => li.textContent);
    if (onApply) onApply(ordered);
  };
  modal.style.display = 'block';
}
function closeRankModal(){
  const modal = document.getElementById('rankModal');
  if (modal) modal.style.display = 'none';
}
function applyRank(){
  if (__rankApplyCb) __rankApplyCb();
  closeRankModal();
}

// Save actions (overwrite / save-as)
(function(){
  function collectFormData(){
    const form = document.getElementById('cleaner-form');
    const fd = new FormData(form);
    return fd;
  }
  async function postData(fd){
    fd.append('ajax', '1');
    const resp = await fetch(form.action, { method: 'POST', body: fd });
    if (!resp.ok) throw new Error(await resp.text());
    return resp.text();
  }
  const form = document.getElementById('cleaner-form');
  document.addEventListener('DOMContentLoaded', function(){
    const btnOverwrite = document.getElementById('btnSaveOverwrite');
    const btnSaveAs    = document.getElementById('btnSaveAs');
    if (btnOverwrite) btnOverwrite.addEventListener('click', async () => {
      const fd = collectFormData();
      fd.append('save_mode', 'overwrite');
      try { 
        await postData(fd); 
        // Update analysis sessions with renamed variables
        await updateAnalysisSessions(fd);
        // Ensure any open equation boxes reflect the latest variable names
        setTimeout(() => {
          try {
            if (window.opener && !window.opener.closed) {
              window.opener.location.reload();
            } else if (window.parent && window.parent !== window) {
              window.parent.location.reload();
            } else {
              window.location.reload();
            }
          } catch (e) { /* no-op */ }
        }, 300);
        if (window.parent && window.parent.sbCloseModal) window.parent.sbCloseModal(); 
      } catch(e){ alert('Save failed: ' + e.message); }
    });
    if (btnSaveAs) btnSaveAs.addEventListener('click', () => openSaveAs());
  });
})();

// Save As modal helpers
function openSaveAs(){
  const m = document.getElementById('saveAsModal');
  if (m) m.style.display = 'block';
}
function closeSaveAs(){
  const m = document.getElementById('saveAsModal');
  if (m) m.style.display = 'none';
}
async function confirmSaveAs(mode){
  const name = document.getElementById('saveAsName').value.trim();
  const fmt  = document.getElementById('saveAsFormat').value;
  const form = document.getElementById('cleaner-form');
  const fd = new FormData(form);
  if (mode === 'download'){
    // For downloads, we need a full form POST to get a file response
    const tmp = document.createElement('form');
    tmp.method = 'POST';
    tmp.action = form.action;
    tmp.style.display = 'none';
    // CSRF token
    const csrf = form.querySelector('input[name="csrfmiddlewaretoken"]').value;
    const add = (k,v) => { const i=document.createElement('input'); i.type='hidden'; i.name=k; i.value=v; tmp.appendChild(i); };
    add('csrfmiddlewaretoken', csrf);
    // include arrays
    fd.getAll('orig[]').forEach(v => add('orig[]', v));
    fd.getAll('name[]').forEach(v => add('name[]', v));
    fd.getAll('type[]').forEach(v => add('type[]', v));
    fd.getAll('order[]').forEach(v => add('order[]', v));
    add('save_mode', 'download');
    add('save_format', fmt);
    if (name) add('save_name', name);
    document.body.appendChild(tmp);
    tmp.submit();
    document.body.removeChild(tmp);
    closeSaveAs();
    return;
  }
  // Save to server via AJAX
  fd.append('ajax', '1');
  fd.append('save_mode', 'new');
  fd.append('save_format', fmt);
  if (name) fd.append('save_name', name);
  try {
    const resp = await fetch(form.action, { method: 'POST', body: fd });
    if (!resp.ok) throw new Error(await resp.text());
    
    // Update analysis sessions with renamed variables
    await updateAnalysisSessions(fd);
    
    // Ensure any open equation boxes reflect the latest variable names
    setTimeout(() => {
      try {
        if (window.opener && !window.opener.closed) {
          window.opener.location.reload();
        } else if (window.parent && window.parent !== window) {
          window.parent.location.reload();
        } else {
          window.location.reload();
        }
      } catch (e) { /* no-op */ }
    }, 300);

    closeSaveAs();
    if (window.parent && window.parent.sbCloseModal) window.parent.sbCloseModal();
  } catch(e){
    alert('Save failed: ' + e.message);
  }
}

// Function to update analysis sessions when variables are renamed
async function updateAnalysisSessions(formData) {
  try {
    // Extract the dataset ID from the current URL
    const urlParts = window.location.pathname.split('/');
    const datasetId = urlParts[urlParts.length - 2]; // Assuming URL is /dataprep/{id}/
    
    if (!datasetId || isNaN(datasetId)) {
      console.warn('Could not determine dataset ID for session updates');
      return;
    }
    
    // Build rename mapping from form data
    const origNames = formData.getAll('orig[]');
    const newNames = formData.getAll('name[]');
    
    if (origNames.length !== newNames.length) {
      console.warn('Mismatch between original and new names');
      return;
    }
    
    // Create rename mapping (only for names that actually changed)
    const renameMap = {};
    for (let i = 0; i < origNames.length; i++) {
      const origName = origNames[i].trim();
      const newName = newNames[i].trim();
      if (origName !== newName && newName) {
        renameMap[origName] = newName;
      }
    }
    
    // Only proceed if there are actual changes
    if (Object.keys(renameMap).length === 0) {
      console.log('No variable name changes detected');
      return;
    }
    
    // Call the API to update sessions
    const updateData = new FormData();
    updateData.append('rename_map', JSON.stringify(renameMap));
    
    const response = await fetch(`/api/dataset/${datasetId}/update-sessions/`, {
      method: 'POST',
      body: updateData,
      headers: {
        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
      }
    });
    
    if (response.ok) {
      const result = await response.json();
      if (result.success) {
        console.log(`Updated ${result.updated_sessions} analysis sessions with renamed variables`);
        // Broadcast a rename event so open equation boxes can update live
        try {
          window.dispatchEvent(new CustomEvent('dataset-variables-renamed', {
            detail: { renameMap }
          }));
        } catch (e) {
          console.warn('Could not dispatch rename event', e);
        }
        // Show a subtle notification to the user
        if (result.updated_sessions > 0) {
          // Create a temporary notification
          const notification = document.createElement('div');
          notification.style.cssText = `
            position: fixed; top: 20px; right: 20px; z-index: 10000;
            background: #10b981; color: white; padding: 12px 16px;
            border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            font-size: 14px; font-weight: 500;
          `;
          notification.textContent = `Updated ${result.updated_sessions} analysis session${result.updated_sessions > 1 ? 's' : ''} with renamed variables`;
          document.body.appendChild(notification);
          
          // Remove notification after 3 seconds
          setTimeout(() => {
            if (notification.parentNode) {
              notification.parentNode.removeChild(notification);
            }
          }, 3000);
        }
      } else {
        console.error('Failed to update sessions:', result.error);
      }
    } else {
      console.error('Failed to update sessions: HTTP', response.status);
    }
  } catch (error) {
    console.error('Error updating analysis sessions:', error);
  }
}
