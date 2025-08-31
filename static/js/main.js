// MedPeer Main JavaScript
document.addEventListener('DOMContentLoaded', function() {
    'use strict';

    // Theme Management
    const themeToggle = document.getElementById('theme-toggle');
    const themeIcon = document.getElementById('theme-icon');
    const htmlElement = document.documentElement;

    // Initialize theme from localStorage or system preference
    function initializeTheme() {
        const savedTheme = localStorage.getItem('theme');
        const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        const initialTheme = savedTheme || (systemPrefersDark ? 'dark' : 'light');
        
        setTheme(initialTheme);
    }

    function setTheme(theme) {
        htmlElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
        
        if (themeIcon) {
            if (theme === 'dark') {
                themeIcon.className = 'fas fa-sun';
                themeToggle.title = 'Switch to light mode';
            } else {
                themeIcon.className = 'fas fa-moon';
                themeToggle.title = 'Switch to dark mode';
            }
        }
    }

    if (themeToggle) {
        themeToggle.addEventListener('click', function() {
            const currentTheme = htmlElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            setTheme(newTheme);
        });
    }

    // Initialize theme
    initializeTheme();

    // CSRF Token Management
    function getCSRFToken() {
        const token = document.querySelector('meta[name=csrf-token]');
        return token ? token.getAttribute('content') : null;
    }

    // Auto-refresh notification count
    function updateNotificationCount() {
        fetch('/api/notifications/count', {
            method: 'GET',
            headers: {
                'X-CSRFToken': getCSRFToken()
            }
        })
        .then(response => response.json())
        .then(data => {
            const badge = document.getElementById('notification-count');
            if (badge) {
                if (data.count > 0) {
                    badge.textContent = data.count > 99 ? '99+' : data.count;
                    badge.style.display = 'inline';
                } else {
                    badge.style.display = 'none';
                }
            }
        })
        .catch(error => console.error('Error updating notification count:', error));
    }

    // Update unread message count
    function updateMessageCount() {
        fetch('/messages/unread-count', {
            method: 'GET',
            headers: {
                'X-CSRFToken': getCSRFToken()
            }
        })
        .then(response => response.json())
        .then(data => {
            const badge = document.getElementById('unread-messages');
            if (badge) {
                if (data.count > 0) {
                    badge.textContent = data.count > 99 ? '99+' : data.count;
                    badge.style.display = 'inline';
                } else {
                    badge.style.display = 'none';
                }
            }
        })
        .catch(error => console.error('Error updating message count:', error));
    }

    // Initialize Feather Icons
    if (typeof feather !== 'undefined') {
        feather.replace();
    }

    // File Upload Handler
    function initializeFileUpload() {
        const fileInputs = document.querySelectorAll('input[type="file"]');
        
        fileInputs.forEach(input => {
            const maxSize = 50 * 1024 * 1024; // 50MB
            const allowedTypes = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/vnd.ms-powerpoint', 'application/vnd.openxmlformats-officedocument.presentationml.presentation', 'image/png', 'image/jpeg', 'image/jpg', 'video/mp4'];
            
            input.addEventListener('change', function() {
                const files = Array.from(this.files);
                let valid = true;
                let errorMessage = '';
                
                files.forEach(file => {
                    if (file.size > maxSize) {
                        valid = false;
                        errorMessage += `File "${file.name}" is too large (max 50MB).\n`;
                    }
                    
                    if (!allowedTypes.includes(file.type)) {
                        valid = false;
                        errorMessage += `File "${file.name}" has an invalid type.\n`;
                    }
                });
                
                if (!valid) {
                    alert(errorMessage);
                    this.value = '';
                    return;
                }
                
                // Display file preview
                displayFilePreview(files, this);
            });
        });
    }

    function displayFilePreview(files, input) {
        const previewContainer = input.parentElement.querySelector('.file-preview') || 
                               createFilePreviewContainer(input);
        
        previewContainer.innerHTML = '';
        
        files.forEach(file => {
            const fileItem = document.createElement('div');
            fileItem.className = 'file-item d-flex align-items-center justify-content-between mb-2 p-2 bg-light rounded';
            
            const fileInfo = document.createElement('div');
            fileInfo.innerHTML = `
                <i class="fas fa-file me-2"></i>
                <span class="fw-bold">${file.name}</span>
                <small class="text-muted ms-2">(${formatFileSize(file.size)})</small>
            `;
            
            const removeBtn = document.createElement('button');
            removeBtn.type = 'button';
            removeBtn.className = 'btn btn-sm btn-outline-danger';
            removeBtn.innerHTML = '<i class="fas fa-times"></i>';
            removeBtn.onclick = () => {
                fileItem.remove();
                removeFileFromInput(input, file);
            };
            
            fileItem.appendChild(fileInfo);
            fileItem.appendChild(removeBtn);
            previewContainer.appendChild(fileItem);
        });
    }

    function createFilePreviewContainer(input) {
        const container = document.createElement('div');
        container.className = 'file-preview mt-2';
        input.parentElement.appendChild(container);
        return container;
    }

    function removeFileFromInput(input, fileToRemove) {
        const dt = new DataTransfer();
        const files = Array.from(input.files);
        
        files.forEach(file => {
            if (file !== fileToRemove) {
                dt.items.add(file);
            }
        });
        
        input.files = dt.files;
    }

    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // Form Validation Enhancement
    function enhanceFormValidation() {
        const forms = document.querySelectorAll('form[data-validate="true"]');
        
        forms.forEach(form => {
            form.addEventListener('submit', function(e) {
                let isValid = true;
                const requiredFields = form.querySelectorAll('[required]');
                
                requiredFields.forEach(field => {
                    if (!field.value.trim()) {
                        isValid = false;
                        field.classList.add('is-invalid');
                        showFieldError(field, 'This field is required');
                    } else {
                        field.classList.remove('is-invalid');
                        hideFieldError(field);
                    }
                });
                
                if (!isValid) {
                    e.preventDefault();
                    const firstInvalidField = form.querySelector('.is-invalid');
                    if (firstInvalidField) {
                        firstInvalidField.focus();
                    }
                }
            });
        });
    }

    function showFieldError(field, message) {
        let feedback = field.parentElement.querySelector('.invalid-feedback');
        if (!feedback) {
            feedback = document.createElement('div');
            feedback.className = 'invalid-feedback';
            field.parentElement.appendChild(feedback);
        }
        feedback.textContent = message;
    }

    function hideFieldError(field) {
        const feedback = field.parentElement.querySelector('.invalid-feedback');
        if (feedback) {
            feedback.remove();
        }
    }

    // Auto-resize textareas
    function initializeAutoResizeTextareas() {
        const textareas = document.querySelectorAll('textarea[data-auto-resize="true"]');
        
        textareas.forEach(textarea => {
            textarea.addEventListener('input', function() {
                this.style.height = 'auto';
                this.style.height = this.scrollHeight + 'px';
            });
            
            // Initial resize
            textarea.style.height = textarea.scrollHeight + 'px';
        });
    }

    // Search functionality
    function initializeSearch() {
        const searchInputs = document.querySelectorAll('.search-input');
        
        searchInputs.forEach(input => {
            let searchTimeout;
            
            input.addEventListener('input', function() {
                const query = this.value.trim();
                clearTimeout(searchTimeout);
                
                if (query.length < 2) {
                    hideSearchResults(this);
                    return;
                }
                
                searchTimeout = setTimeout(() => {
                    performSearch(query, this);
                }, 300);
            });
        });
    }

    function performSearch(query, input) {
        const resultsContainer = input.parentElement.querySelector('.search-results') ||
                               createSearchResultsContainer(input);
        
        resultsContainer.innerHTML = '<div class="p-2 text-muted">Searching...</div>';
        resultsContainer.style.display = 'block';
        
        fetch(`/api/search?q=${encodeURIComponent(query)}&type=all`)
            .then(response => response.json())
            .then(data => {
                displaySearchResults(data, resultsContainer);
            })
            .catch(error => {
                resultsContainer.innerHTML = '<div class="p-2 text-danger">Search failed</div>';
                console.error('Search error:', error);
            });
    }

    function createSearchResultsContainer(input) {
        const container = document.createElement('div');
        container.className = 'search-results dropdown-menu show';
        container.style.position = 'absolute';
        container.style.top = '100%';
        container.style.left = '0';
        container.style.right = '0';
        container.style.zIndex = '1000';
        
        input.parentElement.style.position = 'relative';
        input.parentElement.appendChild(container);
        
        return container;
    }

    function displaySearchResults(data, container) {
        container.innerHTML = '';
        
        if (!data.posts?.length && !data.users?.length && !data.files?.length) {
            container.innerHTML = '<div class="p-2 text-muted">No results found</div>';
            return;
        }
        
        // Display posts
        if (data.posts?.length) {
            data.posts.slice(0, 3).forEach(post => {
                const item = document.createElement('a');
                item.className = 'dropdown-item';
                item.href = `/posts/${post.id}`;
                item.innerHTML = `
                    <div class="fw-bold">${post.title}</div>
                    <small class="text-muted">${post.author}</small>
                `;
                container.appendChild(item);
            });
        }
        
        // Display users
        if (data.users?.length) {
            data.users.slice(0, 3).forEach(user => {
                const item = document.createElement('a');
                item.className = 'dropdown-item';
                item.href = `/profile/${user.username}`;
                item.innerHTML = `
                    <div class="fw-bold">${user.full_name}</div>
                    <small class="text-muted">@${user.username}</small>
                `;
                container.appendChild(item);
            });
        }
        
        // Add "View all results" link
        const viewAllItem = document.createElement('a');
        viewAllItem.className = 'dropdown-item text-primary fw-bold border-top mt-2 pt-2';
        viewAllItem.href = `/search?q=${encodeURIComponent(data.query || '')}`;
        viewAllItem.textContent = 'View all results';
        container.appendChild(viewAllItem);
    }

    function hideSearchResults(input) {
        const resultsContainer = input.parentElement.querySelector('.search-results');
        if (resultsContainer) {
            resultsContainer.style.display = 'none';
        }
    }

    // Infinite Scroll Implementation
    function initializeInfiniteScroll() {
        const infiniteContainers = document.querySelectorAll('[data-infinite-scroll="true"]');
        
        infiniteContainers.forEach(container => {
            let isLoading = false;
            let page = 1;
            const endpoint = container.dataset.endpoint;
            
            const observer = new IntersectionObserver((entries) => {
                const lastEntry = entries[0];
                
                if (lastEntry.isIntersecting && !isLoading) {
                    loadMoreContent(container, endpoint, ++page);
                }
            });
            
            // Observe the last item in the container
            const lastItem = container.children[container.children.length - 1];
            if (lastItem) {
                observer.observe(lastItem);
            }
        });
    }

    function loadMoreContent(container, endpoint, page) {
        const isLoading = true;
        
        fetch(`${endpoint}?page=${page}`)
            .then(response => response.json())
            .then(data => {
                if (data.items && data.items.length > 0) {
                    appendContent(container, data.items);
                    
                    // Update observer to watch new last item
                    const newLastItem = container.children[container.children.length - 1];
                    observer.observe(newLastItem);
                }
                isLoading = false;
            })
            .catch(error => {
                console.error('Error loading more content:', error);
                isLoading = false;
            });
    }

    function appendContent(container, items) {
        items.forEach(item => {
            const element = createContentElement(item);
            container.appendChild(element);
        });
    }

    // Toast Notifications
    function showToast(message, type = 'info') {
        const toastContainer = document.getElementById('toast-container') || createToastContainer();
        
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        toastContainer.appendChild(toast);
        
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    }

    function createToastContainer() {
        const container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        container.style.zIndex = '1055';
        document.body.appendChild(container);
        return container;
    }

    // Keyboard Shortcuts
    function initializeKeyboardShortcuts() {
        document.addEventListener('keydown', function(e) {
            // Ctrl/Cmd + K for search
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                const searchInput = document.querySelector('input[name="q"]');
                if (searchInput) {
                    searchInput.focus();
                }
            }
            
            // Escape to close modals/dropdowns
            if (e.key === 'Escape') {
                const openModal = document.querySelector('.modal.show');
                if (openModal) {
                    bootstrap.Modal.getInstance(openModal).hide();
                }
                
                hideAllSearchResults();
            }
        });
    }

    function hideAllSearchResults() {
        const searchResults = document.querySelectorAll('.search-results');
        searchResults.forEach(results => {
            results.style.display = 'none';
        });
    }

    // Real-time Updates
    function initializeRealTimeUpdates() {
        // Check for updates every 30 seconds
        setInterval(() => {
            if (document.hasFocus()) {
                updateNotificationCount();
                updateMessageCount();
            }
        }, 30000);
        
        // Update when window gains focus
        window.addEventListener('focus', () => {
            updateNotificationCount();
            updateMessageCount();
        });
    }

    // Lazy Image Loading
    function initializeLazyImageLoading() {
        if ('IntersectionObserver' in window) {
            const imageObserver = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        img.src = img.dataset.src;
                        img.classList.remove('lazy');
                        imageObserver.unobserve(img);
                    }
                });
            });
            
            const lazyImages = document.querySelectorAll('img[data-src]');
            lazyImages.forEach(img => {
                imageObserver.observe(img);
            });
        }
    }

    // Global Error Handler
    window.addEventListener('error', function(e) {
        console.error('Global error:', e.error);
        showToast('An unexpected error occurred', 'danger');
    });

    // Initialize all functionality
    function initialize() {
        initializeFileUpload();
        enhanceFormValidation();
        initializeAutoResizeTextareas();
        initializeSearch();
        initializeInfiniteScroll();
        initializeKeyboardShortcuts();
        initializeRealTimeUpdates();
        initializeLazyImageLoading();
        
        // Update counts on page load
        if (document.querySelector('#notification-count, #unread-messages')) {
            updateNotificationCount();
            updateMessageCount();
        }
    }

    // Initialize everything
    initialize();

    // Expose utilities globally
    window.MedPeer = {
        showToast,
        updateNotificationCount,
        updateMessageCount,
        setTheme
    };
});

// Service Worker Registration (for PWA features)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js')
            .then(registration => {
                console.log('SW registered: ', registration);
            })
            .catch(registrationError => {
                console.log('SW registration failed: ', registrationError);
            });
    });
}
