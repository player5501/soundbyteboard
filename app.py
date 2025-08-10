import threading
import os
import argparse
from pathlib import Path
import pygame
from flask import Flask, request, jsonify, render_template_string
from werkzeug.utils import secure_filename

app = Flask(__name__)
pygame.mixer.init()
CURRENT_CHANNEL = None

def play_audio(filename):
    global CURRENT_CHANNEL
    # Prevent directory traversal
    safe_path = os.path.normpath(os.path.join(SOUNDS_DIR, filename))
    if not safe_path.startswith(os.path.abspath(SOUNDS_DIR)):
        print(f"Unsafe path: {safe_path}")
        return
    if os.path.exists(safe_path):
        sound = pygame.mixer.Sound(safe_path)
        CURRENT_CHANNEL = sound.play()
    else:
        print(f"File not found: {safe_path}")

@app.route('/play', methods=['POST'])
def play_sound():
    data = request.get_json()
    filename = data.get('filename')
    if not filename:
        return jsonify({'error': 'No filename provided'}), 400
    threading.Thread(target=play_audio, args=(filename,)).start()
    return jsonify({'status': f'Playing {filename}'})

@app.route('/stop', methods=['POST'])
def stop_sound():
    global CURRENT_CHANNEL
    if CURRENT_CHANNEL:
        CURRENT_CHANNEL.stop()
        return jsonify({'status': 'Playback stopped'})
    return jsonify({'status': 'No sound is playing'})


@app.route('/stopall', methods=['POST'])
def stopall_sound():
    pygame.mixer.stop()
    return jsonify({'status': 'All playback stopped'})

@app.route('/')
def index():
    # serves the HTML UI page (see template below)
    return render_template_string(INDEX_HTML)

def is_audio_file(filename):
    audio_extensions = {'.wav', '.mp3', '.ogg', '.flac', '.aac', '.m4a'}
    return Path(filename).suffix.lower() in audio_extensions

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not is_audio_file(file.filename):
        return jsonify({'error': 'Invalid file type. Only audio files are allowed.'}), 400
    
    # Get target folder from form data
    target_folder = request.form.get('folder', 'Main')
    
    # Secure the filename to prevent directory traversal
    filename = secure_filename(file.filename)
    
    # Ensure the file doesn't already exist, add number if it does
    base_name = Path(filename).stem
    extension = Path(filename).suffix
    counter = 1
    final_filename = filename
    
    # Determine target path
    if target_folder == 'Main':
        target_path = SOUNDS_DIR
    else:
        target_path = os.path.join(SOUNDS_DIR, target_folder)
        # Create folder if it doesn't exist
        os.makedirs(target_path, exist_ok=True)
    
    while os.path.exists(os.path.join(target_path, final_filename)):
        final_filename = f"{base_name}_{counter}{extension}"
        counter += 1
    
    try:
        file.save(os.path.join(target_path, final_filename))
        return jsonify({'status': 'File uploaded successfully', 'filename': final_filename})
    except Exception as e:
        return jsonify({'error': f'Failed to save file: {str(e)}'}), 500

@app.route('/sounds')
def list_sounds():
    sounds_by_folder = {}
    
    for root, dirs, files in os.walk(SOUNDS_DIR):
        for file in files:
            if is_audio_file(file):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, SOUNDS_DIR)
                display_name = os.path.splitext(file)[0]  # Remove file extension
                # Remove dashes and underscores, replace with spaces
                display_name = display_name.replace('-', ' ').replace('_', ' ')
                
                # Determine folder name (use "Main" for files in root directory)
                if root == SOUNDS_DIR:
                    folder_name = "Main"
                else:
                    folder_name = os.path.basename(root)
                
                if folder_name not in sounds_by_folder:
                    sounds_by_folder[folder_name] = []
                
                sounds_by_folder[folder_name].append({
                    'display_name': display_name,
                    'full_path': rel_path
                })
    
    # Sort files within each folder and sort folders
    for folder in sounds_by_folder:
        sounds_by_folder[folder].sort(key=lambda x: x['display_name'])
    
    return jsonify(sounds_by_folder)

@app.route('/move', methods=['POST'])
def move_file():
    data = request.get_json()
    source_path = data.get('source_path')
    target_folder = data.get('target_folder')
    
    if not source_path or not target_folder:
        return jsonify({'error': 'Missing source_path or target_folder'}), 400
    
    # Validate paths to prevent directory traversal
    source_full_path = os.path.normpath(os.path.join(SOUNDS_DIR, source_path))
    if not source_full_path.startswith(os.path.abspath(SOUNDS_DIR)):
        return jsonify({'error': 'Invalid source path'}), 400
    
    if not os.path.exists(source_full_path):
        return jsonify({'error': 'Source file does not exist'}), 400
    
    # Determine target path
    if target_folder == 'Main':
        target_path = SOUNDS_DIR
    else:
        target_path = os.path.join(SOUNDS_DIR, target_folder)
        os.makedirs(target_path, exist_ok=True)
    
    filename = os.path.basename(source_path)
    target_full_path = os.path.join(target_path, filename)
    
    # Handle filename conflicts
    counter = 1
    base_name = Path(filename).stem
    extension = Path(filename).suffix
    
    while os.path.exists(target_full_path):
        new_filename = f"{base_name}_{counter}{extension}"
        target_full_path = os.path.join(target_path, new_filename)
        counter += 1
    
    try:
        # Move the file
        import shutil
        shutil.move(source_full_path, target_full_path)
        return jsonify({'status': 'File moved successfully'})
    except Exception as e:
        return jsonify({'error': f'Failed to move file: {str(e)}'}), 500

@app.route('/folders')
def get_folders():
    folders = ['Main']  # Always include Main
    try:
        for item in os.listdir(SOUNDS_DIR):
            item_path = os.path.join(SOUNDS_DIR, item)
            if os.path.isdir(item_path):
                folders.append(item)
    except OSError as e:
        print(f"Error reading sounds directory: {e}")
    
    folders.sort()
    return jsonify(folders)


INDEX_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Soundboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', 'Monaco', monospace;
            background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%);
            color: #e6e6e6;
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: rgba(26, 26, 46, 0.95);
            border-radius: 12px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
            backdrop-filter: blur(10px);
            overflow: hidden;
            border: 1px solid #333;
        }

        .header {
            background: linear-gradient(135deg, #1e1e2e 0%, #2d2d44 100%);
            color: #00ff88;
            padding: 30px;
            text-align: center;
            border-bottom: 1px solid #333;
        }

        .header h1 {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 10px;
            text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
        }

        .header p {
            font-size: 1.1rem;
            opacity: 0.9;
        }



        .content {
            padding: 30px;
        }

        .upload-section {
            background: linear-gradient(135deg, #2d2d44 0%, #1e1e2e 100%);
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 30px;
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.3);
            border: 1px solid #444;
            display: none;
            animation: slideDown 0.3s ease;
        }

        @keyframes slideDown {
            from {
                opacity: 0;
                transform: translateY(-20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .upload-section h3 {
            color: #00ff88;
            font-size: 1.3rem;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .folder-select-wrapper {
            margin-bottom: 20px;
        }

        .folder-select-wrapper label {
            color: #e6e6e6;
            font-size: 1rem;
            margin-bottom: 8px;
            display: block;
        }

        .folder-select {
            width: 100%;
            padding: 12px;
            background: #2d2d44;
            border: 1px solid #444;
            border-radius: 8px;
            color: #e6e6e6;
            font-size: 1rem;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .folder-select:hover {
            border-color: #00ff88;
        }

        .folder-select:focus {
            outline: none;
            border-color: #00ff88;
            box-shadow: 0 0 0 2px rgba(0, 255, 136, 0.2);
        }

        .organize-mode .sound-btn {
            background: linear-gradient(135deg, #00ff88 0%, #00cc6a 100%);
            color: #1a1a2e;
            border-color: #00ff88;
        }

        .organize-mode .sound-btn:hover {
            background: linear-gradient(135deg, #00cc6a 0%, #00aa55 100%);
        }

        .organize-mode .sound-card {
            border-color: #00ff88;
            box-shadow: 0 5px 15px rgba(0, 255, 136, 0.2);
        }

        .move-modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            z-index: 1000;
            animation: fadeIn 0.3s ease;
        }

        .move-modal-content {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: #2d2d44;
            border: 1px solid #444;
            border-radius: 12px;
            padding: 30px;
            min-width: 400px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
        }

        .move-modal h3 {
            color: #00ff88;
            margin-bottom: 20px;
            font-size: 1.3rem;
        }

        .move-modal-buttons {
            display: flex;
            gap: 10px;
            margin-top: 20px;
        }

        .move-modal-buttons button {
            flex: 1;
            padding: 12px;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .move-modal-buttons .cancel-btn {
            background: linear-gradient(135deg, #ff4757 0%, #ff3742 100%);
            color: white;
            border: none;
        }

        .move-modal-buttons .move-confirm-btn {
            background: linear-gradient(135deg, #00ff88 0%, #00cc6a 100%);
            color: #1a1a2e;
            border: none;
        }

        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        .file-input-wrapper {
            position: relative;
            margin-bottom: 20px;
        }

        .file-input-wrapper input[type="file"] {
            width: 100%;
            padding: 15px;
            border: 2px dashed #00ff88;
            border-radius: 8px;
            background: rgba(0, 255, 136, 0.05);
            color: #e6e6e6;
            font-size: 1rem;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .file-input-wrapper input[type="file"]:hover {
            border-color: #00ff88;
            background: rgba(0, 255, 136, 0.1);
        }

        .file-input-wrapper input[type="file"]::file-selector-button {
            background: #00ff88;
            border: none;
            color: #1a1a2e;
            padding: 10px 20px;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s ease;
        }

        .file-input-wrapper input[type="file"]::file-selector-button:hover {
            background: #00cc6a;
        }

        .upload-btn {
            background: linear-gradient(135deg, #00ff88 0%, #00cc6a 100%);
            color: #1a1a2e;
            border: none;
            padding: 15px 30px;
            border-radius: 8px;
            font-size: 1.1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 5px 15px rgba(0, 255, 136, 0.3);
        }

        .upload-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0, 255, 136, 0.4);
        }

        .controls {
            display: flex;
            gap: 15px;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }

        .control-btn {
            background: linear-gradient(135deg, #2d2d44 0%, #1e1e2e 100%);
            color: #e6e6e6;
            border: 1px solid #444;
            padding: 12px 20px;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
            flex: 1;
            min-width: 120px;
        }

        .control-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
            border-color: #00ff88;
        }

        .control-btn.danger {
            background: linear-gradient(135deg, #ff4757 0%, #ff3742 100%);
            border-color: #ff4757;
        }

        .control-btn.success {
            background: linear-gradient(135deg, #00ff88 0%, #00cc6a 100%);
            border-color: #00ff88;
            color: #1a1a2e;
        }

        .folder-section {
            margin-bottom: 40px;
        }

        .folder-header {
            color: #00ff88;
            font-size: 1.5rem;
            font-weight: 700;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #444;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .sounds-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }

        .sound-card {
            background: #2d2d44;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
            transition: all 0.3s ease;
            border: 1px solid #444;
        }

        .sound-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.4);
            border-color: #00ff88;
        }

        .sound-btn {
            width: 100%;
            background: linear-gradient(135deg, #2d2d44 0%, #1e1e2e 100%);
            color: #e6e6e6;
            border: 1px solid #444;
            padding: 15px 20px;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }

        .sound-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
            border-color: #00ff88;
            background: linear-gradient(135deg, #3d3d54 0%, #2e2e3e 100%);
        }

        .sound-btn:active {
            transform: translateY(0);
        }

        .message {
            margin: 15px 0;
            padding: 15px;
            border-radius: 10px;
            font-weight: 600;
            text-align: center;
            animation: slideIn 0.3s ease;
        }

        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(-10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .success {
            background: linear-gradient(135deg, #00ff88 0%, #00cc6a 100%);
            color: #1a1a2e;
        }

        .error {
            background: linear-gradient(135deg, #ff4757 0%, #ff3742 100%);
            color: white;
        }

        .loading {
            text-align: center;
            padding: 40px;
            color: #888;
            font-size: 1.1rem;
        }

        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #888;
        }

        .empty-state h3 {
            font-size: 1.5rem;
            margin-bottom: 10px;
            color: #00ff88;
        }

        .empty-state p {
            font-size: 1.1rem;
            opacity: 0.8;
        }

        /* Mobile Responsive */
        @media (max-width: 768px) {
            body {
                padding: 10px;
            }

            .header h1 {
                font-size: 2rem;
            }

            .content {
                padding: 20px;
            }

            .controls {
                flex-direction: column;
            }

            .control-btn {
                min-width: auto;
            }

            .sounds-grid {
                grid-template-columns: 1fr;
            }

            .upload-section {
                padding: 20px;
            }
        }

        @media (max-width: 480px) {
            .header {
                padding: 20px;
            }

            .header h1 {
                font-size: 1.8rem;
            }

            .content {
                padding: 15px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>SoundByteBoard</h1>
        </div>
        
        <div class="content">
            <div class="controls">
                <button class="control-btn success" onclick="fetchSounds()">Refresh</button>
                <button class="control-btn danger" onclick="stopAll()">Stop All</button>
                <button class="control-btn" onclick="toggleUpload()">Upload</button>
                <button class="control-btn" onclick="toggleOrganize()" id="organizeBtn">Organize</button>
            </div>
    
    <div class="upload-section">
                <h3>Upload Audio File</h3>
                <div class="folder-select-wrapper">
                    <label for="uploadFolder">Upload to folder:</label>
                    <select id="uploadFolder" class="folder-select">
                        <option value="Main">Main</option>
                    </select>
                </div>
                <div class="file-input-wrapper">
        <input type="file" id="audioFile" accept=".wav,.mp3,.ogg,.flac,.aac,.m4a" />
                </div>
                <button class="upload-btn" onclick="uploadFile()">Upload File</button>
        <div id="uploadMessage"></div>
            </div>
            
            <div id="sound-list">
                <div class="loading">Loading sounds...</div>
            </div>
        </div>
    </div>
    
    <!-- Move Modal -->
    <div id="moveModal" class="move-modal">
        <div class="move-modal-content">
            <h3>Move Sound</h3>
            <p id="moveModalText">Move this sound to a different folder:</p>
            <div class="folder-select-wrapper">
                <label for="moveFolder">Target folder:</label>
                <select id="moveFolder" class="folder-select">
                    <option value="Main">Main</option>
                </select>
            </div>
            <div class="move-modal-buttons">
                <button class="cancel-btn" onclick="closeMoveModal()">Cancel</button>
                <button class="move-confirm-btn" onclick="confirmMove()">Move</button>
            </div>
        </div>
    </div>
<script>
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
                const card = document.createElement('div');
                card.className = 'sound-card';
                
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
                
                card.appendChild(btn);
                soundsGrid.appendChild(card);
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
        
    await fetch('/play', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({filename})
    });
    } catch (error) {
        console.error('Error playing sound:', error);
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

function toggleOrganize() {
    const soundList = document.getElementById('sound-list');
    const organizeBtn = document.getElementById('organizeBtn');
    
    if (soundList.classList.contains('organize-mode')) {
        soundList.classList.remove('organize-mode');
        organizeBtn.textContent = 'Organize';
        organizeBtn.style.background = 'linear-gradient(135deg, #2d2d44 0%, #1e1e2e 100%)';
        organizeBtn.style.borderColor = '#444';
        organizeBtn.style.color = '#e6e6e6';
    } else {
        soundList.classList.add('organize-mode');
        organizeBtn.textContent = 'Exit Organize';
        organizeBtn.style.background = 'linear-gradient(135deg, #00ff88 0%, #00cc6a 100%)';
        organizeBtn.style.borderColor = '#00ff88';
        organizeBtn.style.color = '#1a1a2e';
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
        organizeBtn.textContent = 'Organize';
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
    const modal = document.getElementById('moveModal');
    if (event.target === modal) {
        closeMoveModal();
    }
});

window.onload = function() {
    fetchSounds();
    loadFolders();
};
</script>
</body>
</html>
'''

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Soundboard Flask App")
    parser.add_argument('--sounds-dir', type=str, required=True,
                        help='Path to the directory containing sound files')
    parser.add_argument('-p', '--port', type=int, default=5000,
                        help='Port to run the web app on (default: 5000)')
    args = parser.parse_args()
    SOUNDS_DIR = args.sounds_dir

    app.run(host='0.0.0.0', port=args.port)
