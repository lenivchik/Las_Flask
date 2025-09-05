// Enhanced LAS File Validator with same-file upload fix
class LASValidator {
  constructor() {
    this.fileInput = document.getElementById('las-file');
    this.fileInfo = document.getElementById('file-info');
    this.fileNameElem = document.getElementById('file-name');
    this.fileSizeElem = document.getElementById('file-size');
    this.validateBtn = document.getElementById('validate-btn');
    this.progressContainer = document.getElementById('progress-container');
    this.progressBar = document.getElementById('progress-bar');
    this.resultsContainer = document.getElementById('results-container');
    this.validationSummary = document.getElementById('validation-summary');
    this.validationDetails = document.getElementById('validation-details');
    this.filePreview = document.getElementById('file-preview');
    
    this.currentFile = null;
    this.validationResults = null;
    
    this.init();
  }
  
  init() {
    // File input change handler
    this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
    
    // IMPORTANT FIX: Clear file input value when clicking to allow same file selection
    this.fileInput.addEventListener('click', (e) => {
      // Clear the input value before file dialog opens
      e.target.value = '';
    });
    
    // Validate button handler
    this.validateBtn.addEventListener('click', () => this.validateFile());
    
    // Add clear/reset button handler
    const clearBtn = document.getElementById('clear-file-btn');
    if (clearBtn) {
      clearBtn.addEventListener('click', () => this.clearFile());
    }
    
    // Export handlers
    const exportJson = document.getElementById('export-json');
    const exportTxt = document.getElementById('export-txt');
    
    if (exportJson) {
      exportJson.addEventListener('click', () => this.exportResults('json'));
    }
    
    if (exportTxt) {
      exportTxt.addEventListener('click', () => this.exportResults('txt'));
    }
    
    // Drag and drop enhancement
    this.setupDragAndDrop();
    
    // Add button click handler for file selection
    // Look for the button by ID first, then by other selectors
    const selectFileBtn = document.getElementById('select-file-btn') || 
                          document.querySelector('button[onclick*="las-file"]') ||
                          document.querySelector('#upload-zone button.btn-primary');
    
    if (selectFileBtn) {
      // Remove any inline onclick if it exists
      selectFileBtn.removeAttribute('onclick');
      
      // Add click event listener
      selectFileBtn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        // Clear value before triggering click to ensure change event fires
        this.fileInput.value = '';
        this.fileInput.click();
      });
    }
    
    // Also make the entire upload zone clickable
    const uploadZone = document.getElementById('upload-zone');
    if (uploadZone) {
      uploadZone.addEventListener('click', (e) => {
        // Only trigger if clicking on the zone itself, not the button
        if (!e.target.closest('button') && !e.target.closest('input')) {
          this.fileInput.value = '';
          this.fileInput.click();
        }
      });
    }
    
    // Add "New check" button handler
    const newCheckBtn = document.getElementById('new-check-btn');
    if (newCheckBtn) {
      newCheckBtn.addEventListener('click', () => {
        this.resetUI();
        // Scroll back to upload zone
        document.getElementById('validator').scrollIntoView({ behavior: 'smooth' });
      });
    }
  }
  
  handleFileSelect(event) {
    const file = event.target.files[0];
    
    if (!file) {
      // Don't reset UI if no file selected (user cancelled dialog)
      return;
    }
    
    // Validate file size
    const maxSize = 10 * 1024 * 1024; // 10MB
    if (file.size > maxSize) {
      this.showError('Файл слишком большой. Максимальный размер: 10 МБ');
      this.fileInput.value = '';
      return;
    }
    
    // Validate file extension
    if (!file.name.toLowerCase().endsWith('.las')) {
      this.showError('Допускаются только файлы с расширением .las');
      this.fileInput.value = '';
      return;
    }
    
    // Check if it's actually a different file even with same name
    if (this.currentFile && 
        this.currentFile.name === file.name && 
        this.currentFile.size === file.size && 
        this.currentFile.lastModified === file.lastModified) {
      // Same exact file, but process it anyway since user explicitly selected it
      console.log('Same file selected again, processing anyway...');
    }
    
    this.currentFile = file;
    
    // Reset previous results when new file is selected
    this.resultsContainer.style.display = 'none';
    this.validationResults = null;
    
    // Update file info display
    this.fileNameElem.textContent = file.name;
    this.fileSizeElem.textContent = this.formatFileSize(file.size);
    this.fileInfo.style.display = 'block';
    
    // Add modification time info
    const fileDate = new Date(file.lastModified);
    const dateInfo = document.getElementById('file-date');
    if (dateInfo) {
      dateInfo.textContent = `Изменен: ${fileDate.toLocaleString('ru-RU')}`;
    }
    
    // Preview file content
    this.previewFile(file);
    
    // Show success message
    this.showSuccess(`Файл "${file.name}" загружен и готов к проверке`);
  }
  
  clearFile() {
    // Reset file input
    this.fileInput.value = '';
    
    // Reset UI
    this.resetUI();
    
    // Show notification
    this.showSuccess('Файл очищен');
  }
  
  previewFile(file) {
    const reader = new FileReader();
    
    reader.onload = (e) => {
      const text = e.target.result;
      const lines = text.split('\n');
      const preview = lines.slice(0, 50).join('\n');
      
      // Add line numbers
      const numberedPreview = preview.split('\n')
        .map((line, i) => `${String(i + 1).padStart(4, ' ')} | ${line}`)
        .join('\n');
      
      this.filePreview.textContent = numberedPreview;
      
      // Add syntax highlighting (basic)
      this.highlightSyntax();
    };
    
    reader.onerror = () => {
      this.filePreview.textContent = 'Ошибка при чтении файла';
    };
    
    // Try different encodings
    reader.readAsText(file, 'CP1251');
  }
  
  highlightSyntax() {
    // Basic syntax highlighting for LAS files
    let content = this.filePreview.innerHTML;
    
    // Highlight section headers (lines starting with ~)
    content = content.replace(/^(\s*\d+\s*\|\s*)(~.*)$/gm, '$1<span class="text-primary fw-bold">$2</span>');
    
    // This would need more implementation for proper syntax highlighting
  }
  
  async validateFile() {
    if (!this.currentFile) {
      this.showError('Пожалуйста, выберите файл для проверки');
      return;
    }
    
    // Disable validate button during processing
    this.validateBtn.disabled = true;
    this.validateBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Проверка...';
    
    const formData = new FormData();
    formData.append('file', this.currentFile);
    
    // Show progress
    this.showProgress();
    
    try {
      const response = await fetch('/validate', {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Ошибка сервера');
      }
      
      const data = await response.json();
      this.validationResults = data;
      
      // Update progress
      this.updateProgress(100);
      
      // Show results after animation
      setTimeout(() => {
        this.hideProgress();
        this.displayResults(data);
        
        // Re-enable validate button
        this.validateBtn.disabled = false;
        this.validateBtn.innerHTML = '<i class="bi bi-play-fill me-2"></i>Проверить';
      }, 500);
      
    } catch (error) {
      this.hideProgress();
      this.showError(`Ошибка при проверке: ${error.message}`);
      console.error('Validation error:', error);
      
      // Re-enable validate button
      this.validateBtn.disabled = false;
      this.validateBtn.innerHTML = '<i class="bi bi-play-fill me-2"></i>Проверить';
    }
  }
  
  displayResults(data) {
    this.resultsContainer.style.display = 'block';
    
    // Scroll to results
    this.resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
    
    // Display summary
    if (data.valid) {
      this.validationSummary.innerHTML = `
        <div class="alert alert-success d-flex align-items-center">
          <i class="bi bi-check-circle-fill me-3 fs-3"></i>
          <div>
            <h5 class="mb-1">Файл прошёл проверку успешно!</h5>
            <p class="mb-0">${data.summary || 'Все проверки пройдены без ошибок'}</p>
          </div>
        </div>`;
      this.validationDetails.innerHTML = '';
      
    } else {
      const errorCount = data.errors ? data.errors.length : 0;
      const warningCount = data.warnings ? data.warnings.length : 0;
      
      this.validationSummary.innerHTML = `
        <div class="alert alert-danger d-flex align-items-center">
          <i class="bi bi-exclamation-triangle-fill me-3 fs-3"></i>
          <div>
            <h5 class="mb-1">Обнаружены проблемы</h5>
            <p class="mb-0">
              Ошибок: <span class="badge bg-danger">${errorCount}</span>
              ${warningCount > 0 ? `Предупреждений: <span class="badge bg-warning">${warningCount}</span>` : ''}
            </p>
          </div>
        </div>`;
      
      // Display detailed errors
      this.displayDetailedErrors(data);
    }
    
    // Display additional info if available
    if (data.info && data.info.length > 0) {
      this.displayAdditionalInfo(data.info);
    }
    
    // Display statistics if available
    if (data.statistics) {
      this.displayStatistics(data.statistics);
    }
  }
  
  displayDetailedErrors(data) {
    let detailsHTML = '<div class="error-list">';
    
    // Group errors by category if available
    const errors = data.errors || [];
    const warnings = data.warnings || [];
    
    if (errors.length > 0) {
      detailsHTML += `
        <div class="mb-4">
          <h6 class="text-danger mb-3">
            <i class="bi bi-x-circle me-2"></i>Ошибки (${errors.length})
          </h6>
          <div class="list-group">`;
      
      errors.forEach((error, index) => {
        const errorText = typeof error === 'string' ? error : error.message;
        detailsHTML += `
          <div class="list-group-item list-group-item-danger">
            <div class="d-flex w-100 justify-content-between">
              <div>
                <i class="bi bi-exclamation-circle me-2"></i>
                <span>${this.escapeHtml(errorText)}</span>
              </div>
              <small>#${index + 1}</small>
            </div>
          </div>`;
      });
      
      detailsHTML += '</div></div>';
    }
    
    if (warnings.length > 0) {
      detailsHTML += `
        <div class="mb-4">
          <h6 class="text-warning mb-3">
            <i class="bi bi-exclamation-triangle me-2"></i>Предупреждения (${warnings.length})
          </h6>
          <div class="list-group">`;
      
      warnings.forEach((warning, index) => {
        const warningText = typeof warning === 'string' ? warning : warning.message;
        detailsHTML += `
          <div class="list-group-item list-group-item-warning">
            <div class="d-flex w-100 justify-content-between">
              <div>
                <i class="bi bi-info-circle me-2"></i>
                <span>${this.escapeHtml(warningText)}</span>
              </div>
              <small>#${index + 1}</small>
            </div>
          </div>`;
      });
      
      detailsHTML += '</div></div>';
    }
    
    detailsHTML += '</div>';
    this.validationDetails.innerHTML = detailsHTML;
  }
  
  displayAdditionalInfo(info) {
    const infoContainer = document.createElement('div');
    infoContainer.className = 'mt-4';
    infoContainer.innerHTML = `
      <h6 class="mb-3">
        <i class="bi bi-info-circle me-2"></i>Информация о файле
      </h6>
      <ul class="list-unstyled">
        ${info.map(item => `<li><i class="bi bi-chevron-right me-2"></i>${this.escapeHtml(item)}</li>`).join('')}
      </ul>`;
    
    this.validationDetails.appendChild(infoContainer);
  }
  
  displayStatistics(stats) {
    const statsContainer = document.createElement('div');
    statsContainer.className = 'mt-4';
    
    let statsHTML = `
      <h6 class="mb-3">
        <i class="bi bi-graph-up me-2"></i>Статистика
      </h6>
      <div class="row g-3">`;
    
    if (stats.curve_count !== undefined) {
      statsHTML += `
        <div class="col-md-4">
          <div class="card bg-light">
            <div class="card-body text-center">
              <h4 class="mb-0">${stats.curve_count}</h4>
              <small class="text-muted">Кривых</small>
            </div>
          </div>
        </div>`;
    }
    
    if (stats.file_size_mb !== undefined) {
      statsHTML += `
        <div class="col-md-4">
          <div class="card bg-light">
            <div class="card-body text-center">
              <h4 class="mb-0">${stats.file_size_mb} MB</h4>
              <small class="text-muted">Размер файла</small>
            </div>
          </div>
        </div>`;
    }
    
    statsHTML += '</div>';
    statsContainer.innerHTML = statsHTML;
    
    this.validationDetails.appendChild(statsContainer);
  }
  
  showProgress() {
    this.progressContainer.style.display = 'block';
    this.progressBar.style.width = '0%';
    
    // Animate progress
    let progress = 0;
    const interval = setInterval(() => {
      progress += 10;
      this.updateProgress(Math.min(progress, 90));
      
      if (progress >= 90) {
        clearInterval(interval);
      }
    }, 100);
  }
  
  updateProgress(percent) {
    this.progressBar.style.width = `${percent}%`;
    this.progressBar.setAttribute('aria-valuenow', percent);
  }
  
  hideProgress() {
    this.progressContainer.style.display = 'none';
  }
  
  showError(message) {
    // Create toast notification
    const toast = this.createToast('error', message);
    document.querySelector('.toast-container').appendChild(toast);
    
    // Initialize and show Bootstrap toast
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    // Remove after hidden
    toast.addEventListener('hidden.bs.toast', () => {
      toast.remove();
    });
  }
  
  showSuccess(message) {
    const toast = this.createToast('success', message);
    document.querySelector('.toast-container').appendChild(toast);
    
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    toast.addEventListener('hidden.bs.toast', () => {
      toast.remove();
    });
  }
  
  createToast(type, message) {
    const iconClass = type === 'error' ? 'bi-x-circle-fill' : 'bi-check-circle-fill';
    const bgClass = type === 'error' ? 'bg-danger' : 'bg-success';
    
    const toast = document.createElement('div');
    toast.className = 'toast align-items-center text-white ' + bgClass;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
      <div class="d-flex">
        <div class="toast-body">
          <i class="bi ${iconClass} me-2"></i>
          ${this.escapeHtml(message)}
        </div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
      </div>`;
    
    return toast;
  }
  
  exportResults(format) {
    if (!this.validationResults) {
      this.showError('Нет результатов для экспорта');
      return;
    }
    
    let content, filename, mimeType;
    
    if (format === 'json') {
      content = JSON.stringify(this.validationResults, null, 2);
      filename = `validation_${this.currentFile.name}_${Date.now()}.json`;
      mimeType = 'application/json';
      
    } else if (format === 'txt') {
      content = this.formatResultsAsText(this.validationResults);
      filename = `validation_${this.currentFile.name}_${Date.now()}.txt`;
      mimeType = 'text/plain';
    }
    
    // Create and download file
    const blob = new Blob([content], { type: mimeType });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
    
    this.showSuccess(`Результаты экспортированы в ${format.toUpperCase()}`);
  }
  
  formatResultsAsText(data) {
    let text = '=== РЕЗУЛЬТАТЫ ПРОВЕРКИ LAS ФАЙЛА ===\n\n';
    text += `Файл: ${this.currentFile.name}\n`;
    text += `Дата проверки: ${new Date().toLocaleString('ru-RU')}\n`;
    text += `Статус: ${data.valid ? 'УСПЕШНО' : 'ОШИБКИ'}\n\n`;
    
    if (data.summary) {
      text += `Резюме: ${data.summary}\n\n`;
    }
    
    if (data.errors && data.errors.length > 0) {
      text += `=== ОШИБКИ (${data.errors.length}) ===\n`;
      data.errors.forEach((error, i) => {
        const errorText = typeof error === 'string' ? error : error.message;
        text += `${i + 1}. ${errorText}\n`;
      });
      text += '\n';
    }
    
    if (data.warnings && data.warnings.length > 0) {
      text += `=== ПРЕДУПРЕЖДЕНИЯ (${data.warnings.length}) ===\n`;
      data.warnings.forEach((warning, i) => {
        const warningText = typeof warning === 'string' ? warning : warning.message;
        text += `${i + 1}. ${warningText}\n`;
      });
      text += '\n';
    }
    
    if (data.info && data.info.length > 0) {
      text += '=== ИНФОРМАЦИЯ ===\n';
      data.info.forEach(item => {
        text += `- ${item}\n`;
      });
    }
    
    return text;
  }
  
  setupDragAndDrop() {
    const uploadZone = document.getElementById('upload-zone');
    
    if (!uploadZone) return;
    
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
      uploadZone.addEventListener(eventName, this.preventDefaults, false);
    });
    
    ['dragenter', 'dragover'].forEach(eventName => {
      uploadZone.addEventListener(eventName, () => {
        uploadZone.classList.add('border-primary', 'bg-primary', 'bg-opacity-10');
      }, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
      uploadZone.addEventListener(eventName, () => {
        uploadZone.classList.remove('border-primary', 'bg-primary', 'bg-opacity-10');
      }, false);
    });
    
    uploadZone.addEventListener('drop', (e) => {
      const files = e.dataTransfer.files;
      if (files.length > 0) {
        // IMPORTANT: Clear the input value first to ensure change event fires
        this.fileInput.value = '';
        this.fileInput.files = files;
        const event = new Event('change', { bubbles: true });
        this.fileInput.dispatchEvent(event);
      }
    }, false);
  }
  
  preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
  }
  
  formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }
  
  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
  
  resetUI() {
    this.fileInfo.style.display = 'none';
    this.resultsContainer.style.display = 'none';
    this.filePreview.textContent = '';
    this.currentFile = null;
    this.validationResults = null;
    
    // Reset validate button state
    this.validateBtn.disabled = false;
    this.validateBtn.innerHTML = '<i class="bi bi-play-fill me-2"></i>Проверить';
  }
}

// Initialize validator when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  const validator = new LASValidator();
  
  // Store instance globally for debugging
  window.lasValidator = validator;
});