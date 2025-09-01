// File upload handling with drag and drop functionality
document.addEventListener('DOMContentLoaded', function() {
    const projectSpecInput = document.getElementById('project_spec');
    const vendorSubmittalInput = document.getElementById('vendor_submittal');
    const projectSpecArea = document.getElementById('projectSpecArea');
    const vendorSubmittalArea = document.getElementById('vendorSubmittalArea');
    const projectSpecInfo = document.getElementById('projectSpecInfo');
    const vendorSubmittalInfo = document.getElementById('vendorSubmittalInfo');
    const submitBtn = document.getElementById('submitBtn');
    
    // Only run upload functionality if elements exist (on upload page)
    if (!projectSpecInput || !vendorSubmittalInput || !projectSpecArea || 
        !vendorSubmittalArea || !projectSpecInfo || !vendorSubmittalInfo || !submitBtn) {
        return; // Exit if not on upload page
    }
    
    // File validation
    function validateFile(file) {
        const maxSize = 50 * 1024 * 1024; // 50MB
        const allowedTypes = ['application/pdf'];
        
        if (file.size > maxSize) {
            return { valid: false, message: 'File size exceeds 50MB limit' };
        }
        
        if (!allowedTypes.includes(file.type)) {
            return { valid: false, message: 'Only PDF files are allowed' };
        }
        
        return { valid: true };
    }
    
    // Format file size
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    // Update file info display
    function updateFileInfo(file, infoElement, uploadArea) {
        const validation = validateFile(file);
        
        if (!validation.valid) {
            infoElement.innerHTML = `
                <div class="text-danger">
                    <i class="fas fa-exclamation-circle me-2"></i>
                    <strong>Error:</strong> ${validation.message}
                </div>
            `;
            infoElement.classList.add('show');
            uploadArea.classList.remove('file-selected');
            return false;
        }
        
        infoElement.innerHTML = `
            <div class="text-success">
                <i class="fas fa-check-circle me-2"></i>
                <strong>${file.name}</strong>
                <br>
                <small class="text-muted">Size: ${formatFileSize(file.size)} | Type: PDF</small>
            </div>
        `;
        infoElement.classList.add('show');
        uploadArea.classList.add('file-selected');
        return true;
    }
    
    // Check if both files are selected and valid
    function checkSubmitButton() {
        const projectValid = projectSpecInput.files.length > 0 && 
                           validateFile(projectSpecInput.files[0]).valid;
        const vendorValid = vendorSubmittalInput.files.length > 0 && 
                          validateFile(vendorSubmittalInput.files[0]).valid;
        
        submitBtn.disabled = !(projectValid && vendorValid);
    }
    
    // Handle file input changes
    projectSpecInput.addEventListener('change', function(e) {
        if (e.target.files.length > 0) {
            updateFileInfo(e.target.files[0], projectSpecInfo, projectSpecArea);
        } else {
            projectSpecInfo.classList.remove('show');
            projectSpecArea.classList.remove('file-selected');
        }
        checkSubmitButton();
    });
    
    vendorSubmittalInput.addEventListener('change', function(e) {
        if (e.target.files.length > 0) {
            updateFileInfo(e.target.files[0], vendorSubmittalInfo, vendorSubmittalArea);
        } else {
            vendorSubmittalInfo.classList.remove('show');
            vendorSubmittalArea.classList.remove('file-selected');
        }
        checkSubmitButton();
    });
    
    // Drag and drop functionality
    function setupDragAndDrop(uploadArea, fileInput, infoElement) {
        uploadArea.addEventListener('dragover', function(e) {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        
        uploadArea.addEventListener('dragleave', function(e) {
            e.preventDefault();
            if (!uploadArea.contains(e.relatedTarget)) {
                uploadArea.classList.remove('dragover');
            }
        });
        
        uploadArea.addEventListener('drop', function(e) {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                fileInput.files = files;
                
                // Create and dispatch change event
                const changeEvent = new Event('change', { bubbles: true });
                fileInput.dispatchEvent(changeEvent);
            }
        });
        
        // Click to upload
        uploadArea.addEventListener('click', function(e) {
            if (e.target === fileInput) return;
            fileInput.click();
        });
    }
    
    // Setup drag and drop for both upload areas
    setupDragAndDrop(projectSpecArea, projectSpecInput, projectSpecInfo);
    setupDragAndDrop(vendorSubmittalArea, vendorSubmittalInput, vendorSubmittalInfo);
    
    // Form submission validation
    const uploadForm = document.getElementById('uploadForm');
    if (uploadForm) {
        uploadForm.addEventListener('submit', function(e) {
        const projectFile = projectSpecInput.files[0];
        const vendorFile = vendorSubmittalInput.files[0];
        
        if (!projectFile || !vendorFile) {
            e.preventDefault();
            alert('Please select both files before submitting.');
            return false;
        }
        
        const projectValidation = validateFile(projectFile);
        const vendorValidation = validateFile(vendorFile);
        
        if (!projectValidation.valid || !vendorValidation.valid) {
            e.preventDefault();
            alert('Please fix file validation errors before submitting.');
            return false;
        }
        
        // Show loading state
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processing...';
        
        return true;
        });
    }
    
    // Initialize button state
    checkSubmitButton();
});
