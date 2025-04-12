document.addEventListener('DOMContentLoaded', () => {
  const selectFoldersBtn = document.getElementById('selectFoldersBtn');
  const searchInput = document.getElementById('searchInput');
  const searchBtn = document.getElementById('searchBtn');
  const resultsArea = document.getElementById('resultsArea');
  const previewArea = document.getElementById('previewArea');
  const relatedArea = document.getElementById('relatedArea');
  const indexingStatus = document.getElementById('indexingStatus');
  const statusArea = document.getElementById('statusArea');
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('overlay');
  const openSidebar = document.getElementById('openSidebar');
  const closeSidebar = document.getElementById('closeSidebar');

  // Sidebar toggle
  openSidebar.addEventListener('click', () => {
    sidebar.classList.add('show');
    overlay.classList.add('active');
  });

  closeSidebar.addEventListener('click', () => {
    sidebar.classList.remove('show');
    overlay.classList.remove('active');
  });

  overlay.addEventListener('click', () => {
    sidebar.classList.remove('show');
    overlay.classList.remove('active');
  });

  let indexedFolders = [];

  const updateIndexedFolders = (folders) => {
    indexedFolders = folders;
    indexingStatus.innerText = folders.length > 0
      ? `${folders.length} folder${folders.length === 1 ? '' : 's'} indexed`
      : 'No folders indexed';
  };

  window.electronAPI.onUpdateIndexedFolders(updateIndexedFolders);

  selectFoldersBtn.addEventListener('click', async () => {
    try {
      // Update UI to show indexing is in progress
      indexingStatus.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Indexing in progress...';
      selectFoldersBtn.disabled = true;
      
      const folders = await window.electronAPI.selectFolders();
      if (folders.length > 0) {
        const result = await window.electronAPI.indexFolders(folders);
        updateIndexedFolders(result.indexed_folders);
        
        // Show success message with animation
        indexingStatus.innerHTML = '<i class="fas fa-check-circle"></i> Indexing complete';
        // Show toast notification
        showToast('Indexing completed successfully!', 'success');
        setTimeout(() => {
          updateIndexedFolders(result.indexed_folders);
        }, 2000);
      } else {
        indexingStatus.innerHTML = 'No folders selected';
      }
    } catch (err) {
      indexingStatus.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Failed to index folders';
      showToast('Failed to index folders', 'error');
      console.error(err);
    } finally {
      selectFoldersBtn.disabled = false;
    }
  });

  // Enable search on Enter key
  searchInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
      searchBtn.click();
    }
  });

  searchBtn.addEventListener('click', async () => {
    const query = searchInput.value.trim();
    if (!query) return;

    try {
      // Update UI to show search is in progress
      statusArea.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Searching...';
      resultsArea.innerHTML = '<div class="loading-indicator"><i class="fas fa-spinner fa-spin"></i> Searching documents...</div>';
      previewArea.innerHTML = '';
      relatedArea.innerHTML = '';
      
      const results = await window.electronAPI.searchDocuments(query);
      displayResults(results);
      statusArea.innerHTML = 'Ready';
      
      // Show success toast
      if (results.length > 0) {
        showToast(`Found ${results.length} result${results.length === 1 ? '' : 's'}`, 'success');
      } else {
        showToast('No results found', 'info');
      }
    } catch (error) {
      console.error('Search error:', error);
      statusArea.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Search failed';
      resultsArea.innerHTML = '<div class="error-message"><i class="fas fa-exclamation-circle"></i> An error occurred during search</div>';
      showToast('Search failed', 'error');
    }
  });

  // Function to attach event listeners to all .open-file buttons
  const attachOpenFileListeners = () => {
    document.querySelectorAll('.open-file').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        // Get the file path directly from the button's dataset
        const filePath = e.currentTarget.dataset.filepath;
        await window.electronAPI.openFile(filePath);
      });
    });
  };

  const displayResults = (results) => {
    resultsArea.innerHTML = '';
    previewArea.innerHTML = '';
    relatedArea.innerHTML = '';

    if (results.length === 0) {
      resultsArea.innerHTML = `
        <div class="empty-state">
          <i class="fas fa-search"></i>
          <p>No results found for your query.</p>
          <p class="suggestion">Try using different keywords or indexing more folders.</p>
        </div>`;
      return;
    }

    // Create a header for the results area
    const resultsHeader = document.createElement('div');
    resultsHeader.classList.add('results-header');
    resultsHeader.innerHTML = `<h3>Found ${results.length} result${results.length === 1 ? '' : 's'}</h3>`;
    resultsArea.appendChild(resultsHeader);

    results.forEach((result, index) => {
      const div = document.createElement('div');
      div.classList.add('result-item');
      div.style.animationDelay = `${index * 0.05}s`;
      
      const fileName = result.file_path.split('/').pop().split('\\').pop();
      const fileExtension = fileName.split('.').pop().toLowerCase();
      let iconClass = 'fas fa-file-alt';
      
      if (['pdf'].includes(fileExtension)) iconClass = 'fas fa-file-pdf';
      else if (['doc', 'docx'].includes(fileExtension)) iconClass = 'fas fa-file-word';
      else if (['xls', 'xlsx'].includes(fileExtension)) iconClass = 'fas fa-file-excel';
      else if (['ppt', 'pptx'].includes(fileExtension)) iconClass = 'fas fa-file-powerpoint';
      else if (['jpg', 'jpeg', 'png', 'gif'].includes(fileExtension)) iconClass = 'fas fa-file-image';
      else if (['mp3', 'wav'].includes(fileExtension)) iconClass = 'fas fa-file-audio';
      else if (['mp4', 'avi', 'mov'].includes(fileExtension)) iconClass = 'fas fa-file-video';
      else if (['zip', 'rar', '7z'].includes(fileExtension)) iconClass = 'fas fa-file-archive';
      else if (['html', 'htm', 'xml'].includes(fileExtension)) iconClass = 'fas fa-file-code';
      else if (['txt', 'md'].includes(fileExtension)) iconClass = 'fas fa-file-alt';

      div.innerHTML = `
        <div class="result-icon"><i class="${iconClass}"></i></div>
        <div class="result-content">
          <h3>${result.title || fileName || 'Untitled Document'}</h3>
          <p class="result-path">${result.file_path}</p>
          <p class="result-snippet">${result.snippet}</p>
          <div class="result-actions">
            <button class="btn-primary view-summary" data-filepath="${result.file_path}">
              <i class="fas fa-eye"></i> View Summary
            </button>
            <button class="btn-secondary open-file" data-filepath="${result.file_path}">
              <i class="fas fa-external-link-alt"></i> Open File
            </button>
          </div>
        </div>
      `;
      resultsArea.appendChild(div);
    });

    // Add animation to results after they're added to DOM
    animateResults();
    
    // Add event listeners for buttons
    document.querySelectorAll('.view-summary').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const filePath = e.currentTarget.dataset.filepath;
        try {
          // Show loading state
          previewArea.innerHTML = '<div class="loading-indicator"><i class="fas fa-spinner fa-spin"></i> Generating summary...</div>';
          relatedArea.innerHTML = '<div class="loading-indicator"><i class="fas fa-spinner fa-spin"></i> Finding related documents...</div>';
          
          const summary = await window.electronAPI.getSummary(filePath);
          const related = await window.electronAPI.getRelated(filePath);
          showPreview(summary, related);
        } catch (err) {
          console.error('Summary error:', err);
          previewArea.innerHTML = `
            <div class="error-message">
              <i class="fas fa-exclamation-circle"></i>
              <h3>Error Loading Summary</h3>
              <p>Could not generate summary for this document.</p>
              <button class="btn-primary open-file" data-filepath="${filePath}">
                <i class="fas fa-external-link-alt"></i> Open File Instead
              </button>
            </div>`;
          
          showToast('Failed to generate summary', 'error');
            
          // Immediately attach event listener to the error button
          setTimeout(() => {
            attachOpenFileListeners();
          }, 0);
        }
      });
    });

    // Attach open file listeners to all results
    attachOpenFileListeners();
    
    // Add ripple effect to buttons
    addRippleEffect();
  };

  const showPreview = (summary, related) => {
    const fileName = summary.file_path.split('/').pop().split('\\').pop();
    
    previewArea.innerHTML = `
      <h3><i class="fas fa-file-alt"></i> ${summary.title || fileName || 'Document Summary'}</h3>
      <div class="summary-content">
        <p>${summary.content || 'No summary available.'}</p>
      </div>
      <div class="preview-actions">
        <button class="btn-secondary open-file" data-filepath="${summary.file_path}">
          <i class="fas fa-external-link-alt"></i> Open Original File
        </button>
      </div>
    `;

    relatedArea.innerHTML = '<h4><i class="fas fa-link"></i> Related Documents</h4>';
    
    if (!related || related.length === 0) {
      relatedArea.innerHTML += `
        <div class="empty-state small">
          <i class="fas fa-search"></i>
          <p>No related documents found</p>
        </div>`;
      return;
    }

    related.forEach(doc => {
      const fileName = doc.file_path.split('/').pop().split('\\').pop();
      const fileExtension = fileName.split('.').pop().toLowerCase();
      let iconClass = 'fas fa-file-alt';
      
      if (['pdf'].includes(fileExtension)) iconClass = 'fas fa-file-pdf';
      else if (['doc', 'docx'].includes(fileExtension)) iconClass = 'fas fa-file-word';
      else if (['xls', 'xlsx'].includes(fileExtension)) iconClass = 'fas fa-file-excel';
      else if (['ppt', 'pptx'].includes(fileExtension)) iconClass = 'fas fa-file-powerpoint';
      else if (['jpg', 'jpeg', 'png', 'gif'].includes(fileExtension)) iconClass = 'fas fa-file-image';

      const div = document.createElement('div');
      div.classList.add('related-item');
      div.innerHTML = `
        <div class="related-item-header">
          <div class="related-icon"><i class="${iconClass}"></i></div>
          <h4>${doc.title || fileName || 'Related Document'}</h4>
        </div>
        <div class="related-actions">
          <button class="btn-secondary view-related" data-filepath="${doc.file_path}">
            <i class="fas fa-eye"></i> View
          </button>
          <button class="btn-secondary open-file" data-filepath="${doc.file_path}">
            <i class="fas fa-external-link-alt"></i> Open
          </button>
        </div>
      `;
      relatedArea.appendChild(div);
    });
    
    // Add animation to related items
    addRelatedItemsAnimation();

    // Attach listeners to the newly created buttons
    attachOpenFileListeners();
    
    // Add ripple effect to new buttons
    addRippleEffect();

    document.querySelectorAll('.view-related').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const filePath = e.currentTarget.dataset.filepath;
        try {
          const summary = await window.electronAPI.getSummary(filePath);
          const related = await window.electronAPI.getRelated(filePath);
          showPreview(summary, related);
        } catch (err) {
          console.error('Error viewing related document:', err);
          showToast('Failed to load related document', 'error');
        }
      });
    });
  };

  // Initial state
  if (indexedFolders.length === 0) {
    resultsArea.innerHTML = `
      <div class="empty-state">
        <i class="fas fa-folder-open"></i>
        <h3>Welcome to Ashborn AI</h3>
        <p>Select folders to index before searching documents.</p>
        <button id="emptyStateIndexBtn" class="btn-primary">
          <i class="fas fa-folder-plus"></i> Index Your Folders
        </button>
      </div>`;
    
    document.getElementById('emptyStateIndexBtn')?.addEventListener('click', () => {
      openSidebar.click();
    });
  }
  
  // Apply UI enhancements
  enhancePlaceholders();
  addSmoothScroll();
  addRippleEffect();
});

// UI enhancement functions from paste.txt

// Add smooth animations to search results
function animateResults() {
const resultItems = document.querySelectorAll('.result-item');
resultItems.forEach((item, index) => {
  item.style.opacity = '0';
  item.style.transform = 'translateY(20px)';
  
  setTimeout(() => {
    item.style.transition = 'opacity 0.5s cubic-bezier(0.34, 1.56, 0.64, 1), transform 0.5s cubic-bezier(0.34, 1.56, 0.64, 1)';
    item.style.opacity = '1';
    item.style.transform = 'translateY(0)';
  }, index * 100);
});
}

// Add click ripple effect to buttons
function addRippleEffect() {
const buttons = document.querySelectorAll('.btn-primary, .btn-secondary');

buttons.forEach(button => {
  button.addEventListener('click', function(e) {
    const rect = button.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    const ripple = document.createElement('span');
    ripple.style.position = 'absolute';
    ripple.style.backgroundColor = 'rgba(255, 255, 255, 0.7)';
    ripple.style.borderRadius = '50%';
    ripple.style.width = '100px';
    ripple.style.height = '100px';
    ripple.style.left = x - 50 + 'px';
    ripple.style.top = y - 50 + 'px';
    ripple.style.transform = 'scale(0)';
    ripple.style.opacity = '1';
    ripple.style.transition = 'transform 0.6s, opacity 0.6s';
    
    button.style.position = 'relative';
    button.style.overflow = 'hidden';
    button.appendChild(ripple);
    
    setTimeout(() => {
      ripple.style.transform = 'scale(4)';
      ripple.style.opacity = '0';
    }, 10);
    
    setTimeout(() => {
      ripple.remove();
    }, 600);
  });
});
}

// Enhance placeholders with iOS-style animation
function enhancePlaceholders() {
const searchInput = document.getElementById('searchInput');

searchInput.addEventListener('focus', function() {
  this.classList.add('active');
});

searchInput.addEventListener('blur', function() {
  if (this.value === '') {
    this.classList.remove('active');
  }
});
}

// Add smooth scroll behavior
function addSmoothScroll() {
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener('click', function(e) {
    e.preventDefault();
    const targetId = this.getAttribute('href');
    const targetElement = document.querySelector(targetId);
    
    if (targetElement) {
      targetElement.scrollIntoView({
        behavior: 'smooth',
        block: 'start'
      });
    }
  });
});
}

// Create a toast notification system
function showToast(message, type = 'info') {
// Remove existing toast if present
const existingToast = document.querySelector('.toast');
if (existingToast) {
  existingToast.remove();
}

const toast = document.createElement('div');
toast.className = `toast toast-${type}`;
toast.innerHTML = `
  <div class="toast-content">
    <i class="${type === 'success' ? 'fas fa-check-circle' : 
             type === 'error' ? 'fas fa-exclamation-circle' : 
             'fas fa-info-circle'}"></i>
    <span>${message}</span>
  </div>
`;

// Add toast styles if they don't exist in the CSS
if (!document.querySelector('#toast-styles')) {
  const style = document.createElement('style');
  style.id = 'toast-styles';
  style.textContent = `
    .toast {
      position: fixed;
      bottom: 20px;
      right: 20px;
      padding: 12px 16px;
      background: var(--card-bg);
      border-radius: var(--radius);
      box-shadow: var(--shadow-lg);
      z-index: 1000;
      min-width: 250px;
      transform: translateY(100px);
      opacity: 0;
      transition: transform 0.3s, opacity 0.3s;
    }
    .toast.show {
      transform: translateY(0);
      opacity: 1;
    }
    .toast-content {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .toast-success i {
      color: var(--success);
    }
    .toast-error i {
      color: var(--error);
    }
    .toast-info i {
      color: var(--primary);
    }
  `;
  document.head.appendChild(style);
}

document.body.appendChild(toast);

// Show toast with animation
setTimeout(() => {
  toast.classList.add('show');
}, 10);

// Hide toast after 3 seconds
setTimeout(() => {
  toast.classList.remove('show');
  setTimeout(() => {
    toast.remove();
  }, 300);
}, 3000);
}

// Add hover animation to related items
function addRelatedItemsAnimation() {
const relatedItems = document.querySelectorAll('.related-item');

relatedItems.forEach(item => {
  item.addEventListener('mouseenter', function() {
    this.style.transform = 'translateY(-5px)';
    this.style.boxShadow = 'var(--shadow-md)';
  });
  
  item.addEventListener('mouseleave', function() {
    this.style.transform = 'translateY(0)';
    this.style.boxShadow = 'inset 0 0 0 1px var(--border)';
  });
});
}