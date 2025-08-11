async function fetchSounds() {
    const list = document.getElementById('sound-list');
    list.innerHTML = '<div class="loading">Loading sounds...</div>';
    
    try {
        const res = await fetch('/sounds');
        const soundsByFolder = await res.json();
        
        if (Object.keys(soundsByFolder).length === 0) {
            list.innerHTML = `
                <div class="empty-state">
                    <h3>No sounds yet</h3>
                    <p>Upload your first audio file to get started!</p>
                </div>
            `;
            return;
        }
        
        list.innerHTML = '';
        
        // Sort folder names (Main first, then alphabetically)
        const folderNames = Object.keys(soundsByFolder).sort((a, b) => {
            if (a === "Main") return -1;
            if (b === "Main") return 1;
            return a.localeCompare(b);
        });
        
        for (const folderName of folderNames) {
            const sounds = soundsByFolder[folderName];
            
            // Create folder section
            const folderSection = document.createElement('div');
            folderSection.className = 'folder-section';
            
            const folderHeader = document.createElement('h3');
            folderHeader.className = 'folder-header';
            folderHeader.textContent = folderName;
            folderSection.appendChild(folderHeader);
            
            const soundsGrid = document.createElement('div');
            soundsGrid.className = 'sounds-grid';
            
            for (const sound of sounds) {
                const btn = document.createElement('button');
                btn.textContent = sound.display_name;
                btn.className = "sound-btn";
                btn.onclick = () => {
                    if (document.getElementById('sound-list').classList.contains('organize-mode')) {
                        openMoveModal(sound.display_name, sound.full_path);
                    } else {
                        play(sound.full_path);
                    }
                };
                
                soundsGrid.appendChild(btn);
            }
            
            folderSection.appendChild(soundsGrid);
            list.appendChild(folderSection);
        }
    } catch (error) {
        list.innerHTML = `
            <div class="empty-state">
                <h3>Error loading sounds</h3>
                <p>Failed to load sound files. Please try refreshing.</p>
            </div>
        `;
    }
}

async function play(filename) {
    try {
        // Find the button for this sound and add visual feedback
        const buttons = document.querySelectorAll('.sound-btn');
        const targetButton = Array.from(buttons).find(btn => btn.textContent === filename.split('/').pop());
        
        if (targetButton) {
            targetButton.style.background = 'linear-gradient(135deg, #00ff88 0%, #00cc6a 100%)';
            targetButton.style.color = '#1a1a2e';
            targetButton.style.borderColor = '#00ff88';
            
            // Reset after 2 seconds
            setTimeout(() => {
                targetButton.style.background = 'linear-gradient(135deg, #2d2d44 0%, #1e1e2e 100%)';
                targetButton.style.color = '#e6e6e6';
                targetButton.style.borderColor = '#444';
            }, 2000);
        }
        
        const remotePlay = document.getElementById('remotePlay').checked;
        const localPlay = document.getElementById('localPlay').checked;
        
        if (remotePlay) {
            // Play on server
            await fetch('/play', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({filename})
            });
        }
        
        if (localPlay) {
            // Play in browser
            playLocalAudio(filename);
        }
    } catch (error) {
        console.error('Error playing sound:', error);
    }
}

function playLocalAudio(filename) {
    try {
        // Create audio element
        const audio = new Audio(`/audio/${filename}`);
        audio.volume = 1.0;
        
        // Play the audio
        audio.play().catch(error => {
            console.error('Error playing local audio:', error);
        });
        
        // Clean up after playback
        audio.addEventListener('ended', () => {
            audio.remove();
        });
        
        audio.addEventListener('error', (error) => {
            console.error('Audio playback error:', error);
            audio.remove();
        });
    } catch (error) {
        console.error('Error creating audio element:', error);
    }
}

async function stop() {
    await fetch('/stop', { method: 'POST' });
}

async function stopAll() {
    await fetch('/stopall', { method: 'POST' });
}

function toggleUpload() {
    const uploadSection = document.querySelector('.upload-section');
    const uploadBtn = document.querySelector('.control-btn[onclick="toggleUpload()"]');
    
    if (uploadSection.style.display === 'none' || uploadSection.style.display === '') {
        uploadSection.style.display = 'block';
        uploadBtn.textContent = 'Close Upload';
        uploadBtn.style.background = 'linear-gradient(135deg, #ff4757 0%, #ff3742 100%)';
        uploadBtn.style.borderColor = '#ff4757';
    } else {
        uploadSection.style.display = 'none';
        uploadBtn.textContent = 'Upload';
        uploadBtn.style.background = 'linear-gradient(135deg, #2d2d44 0%, #1e1e2e 100%)';
        uploadBtn.style.borderColor = '#444';
    }
}

function toggleOptions() {
    const optionsSection = document.querySelector('.options-section');
    const optionsBtn = document.querySelector('.control-btn[onclick="toggleOptions()"]');
    
    if (optionsSection.style.display === 'none' || optionsSection.style.display === '') {
        optionsSection.style.display = 'block';
        optionsBtn.textContent = 'Close Options';
        optionsBtn.style.background = 'linear-gradient(135deg, #ff4757 0%, #ff3742 100%)';
        optionsBtn.style.borderColor = '#ff4757';
    } else {
        optionsSection.style.display = 'none';
        optionsBtn.textContent = 'Options';
        optionsBtn.style.background = 'linear-gradient(135deg, #2d2d44 0%, #1e1e2e 100%)';
        optionsBtn.style.borderColor = '#444';
    }
}

function toggleOrganize() {
    const soundList = document.getElementById('sound-list');
    const organizeBtn = document.getElementById('organizeBtn');
    
    if (soundList.classList.contains('organize-mode')) {
        soundList.classList.remove('organize-mode');
        organizeBtn.classList.remove('active');
        organizeBtn.querySelector('.option-text').textContent = 'Organize Files';
        organizeBtn.style.background = 'linear-gradient(135deg, #2d2d44 0%, #1e1e2e 100%)';
        organizeBtn.style.borderColor = '#444';
        organizeBtn.style.color = '#e6e6e6';
    } else {
        soundList.classList.add('organize-mode');
        organizeBtn.classList.add('active');
        organizeBtn.querySelector('.option-text').textContent = 'Exit Organize';
        organizeBtn.style.background = 'linear-gradient(135deg, #ff4757 0%, #ff3742 100%)';
        organizeBtn.style.borderColor = '#ff4757';
        organizeBtn.style.color = 'white';
    }
}

async function uploadFile() {
    const fileInput = document.getElementById('audioFile');
    const messageDiv = document.getElementById('uploadMessage');
    const uploadBtn = document.querySelector('.upload-btn');
    
    if (!fileInput.files[0]) {
        showMessage('Please select a file to upload.', 'error');
        return;
    }
    
    // Show loading state
    uploadBtn.innerHTML = 'Uploading...';
    uploadBtn.disabled = true;
    
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('folder', document.getElementById('uploadFolder').value);
    
    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showMessage(`File uploaded successfully: ${result.filename}`, 'success');
            fileInput.value = ''; // Clear the file input
            fetchSounds(); // Refresh the sound list
        } else {
            showMessage(`Upload failed: ${result.error}`, 'error');
        }
    } catch (error) {
        showMessage(`Upload failed: ${error.message}`, 'error');
    } finally {
        // Reset button state
        uploadBtn.innerHTML = 'Upload File';
        uploadBtn.disabled = false;
    }
}

function showMessage(message, type) {
    const messageDiv = document.getElementById('uploadMessage');
    messageDiv.textContent = message;
    messageDiv.className = `message ${type}`;
    
    // Clear message after 5 seconds
    setTimeout(() => {
        messageDiv.textContent = '';
        messageDiv.className = 'message';
    }, 5000);
}

// Global variables for move functionality
let currentMoveFile = null;
let currentMovePath = null;

async function loadFolders() {
    try {
        const response = await fetch('/folders');
        const folders = await response.json();
        
        // Update upload folder dropdown
        const uploadFolder = document.getElementById('uploadFolder');
        uploadFolder.innerHTML = '';
        folders.forEach(folder => {
            const option = document.createElement('option');
            option.value = folder;
            option.textContent = folder;
            uploadFolder.appendChild(option);
        });
        
        // Update move folder dropdown
        const moveFolder = document.getElementById('moveFolder');
        moveFolder.innerHTML = '';
        folders.forEach(folder => {
            const option = document.createElement('option');
            option.value = folder;
            option.textContent = folder;
            moveFolder.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading folders:', error);
    }
}

function openMoveModal(displayName, fullPath) {
    currentMoveFile = displayName;
    currentMovePath = fullPath;
    
    const modal = document.getElementById('moveModal');
    const modalText = document.getElementById('moveModalText');
    modalText.textContent = `Move "${displayName}" to a different folder:`;
    
    modal.style.display = 'block';
}

function closeMoveModal() {
    const modal = document.getElementById('moveModal');
    modal.style.display = 'none';
    currentMoveFile = null;
    currentMovePath = null;
    
    // Exit organize mode when closing the modal
    const soundList = document.getElementById('sound-list');
    const organizeBtn = document.getElementById('organizeBtn');
    
    if (soundList.classList.contains('organize-mode')) {
        soundList.classList.remove('organize-mode');
        organizeBtn.classList.remove('active');
        organizeBtn.querySelector('.option-text').textContent = 'Organize Files';
        organizeBtn.style.background = 'linear-gradient(135deg, #2d2d44 0%, #1e1e2e 100%)';
        organizeBtn.style.borderColor = '#444';
        organizeBtn.style.color = '#e6e6e6';
    }
}

async function confirmMove() {
    if (!currentMovePath) return;
    
    const targetFolder = document.getElementById('moveFolder').value;
    
    try {
        const response = await fetch('/move', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                source_path: currentMovePath,
                target_folder: targetFolder
            })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showMessage(`File moved successfully to ${targetFolder}`, 'success');
            closeMoveModal();
            fetchSounds(); // Refresh the sound list
        } else {
            showMessage(`Move failed: ${result.error}`, 'error');
        }
    } catch (error) {
        showMessage(`Move failed: ${error.message}`, 'error');
    }
}

// Close modal when clicking outside
document.addEventListener('click', function(event) {
    const moveModal = document.getElementById('moveModal');
    const createCategoryModal = document.getElementById('createCategoryModal');
    const removeEmptyCategoriesModal = document.getElementById('removeEmptyCategoriesModal');
    
    if (event.target === moveModal) {
        closeMoveModal();
    }
    
    if (event.target === createCategoryModal) {
        closeCreateCategoryModal();
    }
    
    if (event.target === removeEmptyCategoriesModal) {
        closeRemoveEmptyCategoriesModal();
    }
});

function openCreateCategoryModal() {
    const modal = document.getElementById('createCategoryModal');
    const categoryInput = document.getElementById('categoryName');
    
    // Clear any previous input
    categoryInput.value = '';
    
    // Show modal and focus on input
    modal.style.display = 'block';
    categoryInput.focus();
    
    // Add enter key listener
    categoryInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            confirmCreateCategory();
        }
    });
}

function closeCreateCategoryModal() {
    const modal = document.getElementById('createCategoryModal');
    const categoryInput = document.getElementById('categoryName');
    
    modal.style.display = 'none';
    categoryInput.value = '';
}

async function confirmCreateCategory() {
    const categoryName = document.getElementById('categoryName').value.trim();
    
    if (!categoryName) {
        showMessage('Please enter a category name', 'error');
        return;
    }
    
    try {
        const response = await fetch('/create-category', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({category_name: categoryName})
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showMessage(result.status, 'success');
            closeCreateCategoryModal();
            loadFolders(); // Refresh folder lists
        } else {
            showMessage(`Failed to create category: ${result.error}`, 'error');
        }
    } catch (error) {
        showMessage(`Failed to create category: ${error.message}`, 'error');
    }
}

function openRemoveEmptyCategoriesModal() {
    const modal = document.getElementById('removeEmptyCategoriesModal');
    const categoriesList = document.getElementById('emptyCategoriesList');
    const removeBtn = document.getElementById('removeCategoriesBtn');
    
    // Show modal
    modal.style.display = 'block';
    
    // Reset button state
    removeBtn.disabled = true;
    
    // Load empty categories
    loadEmptyCategories();
}

function closeRemoveEmptyCategoriesModal() {
    const modal = document.getElementById('removeEmptyCategoriesModal');
    modal.style.display = 'none';
}

async function loadEmptyCategories() {
    const categoriesList = document.getElementById('emptyCategoriesList');
    
    try {
        const response = await fetch('/empty-categories');
        const emptyCategories = await response.json();
        
        if (emptyCategories.length === 0) {
            categoriesList.innerHTML = '<div class="no-empty-categories">No empty categories found</div>';
            return;
        }
        
        categoriesList.innerHTML = '';
        
        emptyCategories.forEach(category => {
            const item = document.createElement('div');
            item.className = 'category-item';
            
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.id = `category-${category}`;
            checkbox.value = category;
            checkbox.addEventListener('change', updateRemoveButton);
            
            const label = document.createElement('label');
            label.htmlFor = `category-${category}`;
            label.textContent = category;
            
            item.appendChild(checkbox);
            item.appendChild(label);
            categoriesList.appendChild(item);
        });
        
    } catch (error) {
        categoriesList.innerHTML = '<div class="no-empty-categories">Error loading empty categories</div>';
        console.error('Error loading empty categories:', error);
    }
}

function updateRemoveButton() {
    const checkboxes = document.querySelectorAll('#emptyCategoriesList input[type="checkbox"]');
    const removeBtn = document.getElementById('removeCategoriesBtn');
    
    const checkedCount = Array.from(checkboxes).filter(cb => cb.checked).length;
    removeBtn.disabled = checkedCount === 0;
    
    if (checkedCount > 0) {
        removeBtn.textContent = `Remove Selected (${checkedCount})`;
    } else {
        removeBtn.textContent = 'Remove Selected';
    }
}

async function confirmRemoveEmptyCategories() {
    const checkboxes = document.querySelectorAll('#emptyCategoriesList input[type="checkbox"]:checked');
    const categoriesToRemove = Array.from(checkboxes).map(cb => cb.value);
    
    if (categoriesToRemove.length === 0) {
        showMessage('Please select at least one category to remove', 'error');
        return;
    }
    
    try {
        const response = await fetch('/remove-categories', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({categories: categoriesToRemove})
        });
        
        const result = await response.json();
        
        if (response.ok || response.status === 207) { // 207 is Multi-Status
            let message = '';
            
            if (result.removed && result.removed.length > 0) {
                message += `Successfully removed: ${result.removed.join(', ')}`;
            }
            
            if (result.failed && result.failed.length > 0) {
                if (message) message += '\n';
                message += `Failed to remove: ${result.failed.join(', ')}`;
            }
            
            if (result.removed && result.removed.length > 0) {
                showMessage(message, 'success');
                closeRemoveEmptyCategoriesModal();
                loadFolders(); // Refresh folder lists
            } else {
                showMessage(message, 'error');
            }
        } else {
            showMessage(`Failed to remove categories: ${result.error}`, 'error');
        }
    } catch (error) {
        showMessage(`Failed to remove categories: ${error.message}`, 'error');
    }
}

// Register service worker for PWA functionality
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        navigator.serviceWorker.register('/sw.js')
            .then(function(registration) {
                console.log('ServiceWorker registration successful');
            })
            .catch(function(err) {
                console.log('ServiceWorker registration failed');
            });
    });
}

window.onload = function() {
    fetchSounds();
    loadFolders();
    setupPlayModeCheckboxes();
};

function setupPlayModeCheckboxes() {
    const remotePlay = document.getElementById('remotePlay');
    const localPlay = document.getElementById('localPlay');
    
    // Ensure at least one play mode is selected
    remotePlay.addEventListener('change', function() {
        if (!remotePlay.checked && !localPlay.checked) {
            // If both are unchecked, force remote play to be checked
            remotePlay.checked = true;
        }
    });
    
    localPlay.addEventListener('change', function() {
        if (!remotePlay.checked && !localPlay.checked) {
            // If both are unchecked, force local play to be checked
            localPlay.checked = true;
        }
    });
}
