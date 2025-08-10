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
    
    # Secure the filename to prevent directory traversal
    filename = secure_filename(file.filename)
    
    # Ensure the file doesn't already exist, add number if it does
    base_name = Path(filename).stem
    extension = Path(filename).suffix
    counter = 1
    final_filename = filename
    
    while os.path.exists(os.path.join(SOUNDS_DIR, final_filename)):
        final_filename = f"{base_name}_{counter}{extension}"
        counter += 1
    
    try:
        file.save(os.path.join(SOUNDS_DIR, final_filename))
        return jsonify({'status': 'File uploaded successfully', 'filename': final_filename})
    except Exception as e:
        return jsonify({'error': f'Failed to save file: {str(e)}'}), 500

@app.route('/sounds')
def list_sounds():
    sounds = []
    for root, dirs, files in os.walk(SOUNDS_DIR):
        for file in files:
            if is_audio_file(file):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, SOUNDS_DIR)
                sounds.append(rel_path)
    sounds.sort()
    return jsonify(sounds)


INDEX_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Soundboard</title>
    <style>
        body { font-family: sans-serif; background: #222; color: #eee; margin: 40px;}
        button, .sound-btn { margin: 5px; padding: 10px 18px; background: #444; border: 1px solid #666; color: #eee; border-radius: 7px; font-size: 1em;}
        .sound-btn:hover, button:hover { background: #770099; cursor:pointer }
        .upload-section { margin: 20px 0; padding: 20px; background: #333; border-radius: 10px; }
        .upload-section input[type="file"] { margin: 10px 0; }
        .upload-section button { background: #0066cc; }
        .upload-section button:hover { background: #0052a3; }
        .message { margin: 10px 0; padding: 10px; border-radius: 5px; }
        .success { background: #2d5a2d; color: #90ee90; }
        .error { background: #5a2d2d; color: #ffb6c1; }
    </style>
</head>
<body>
    <h1>Soundboard</h1>
    
    <div class="upload-section">
        <h3>📁 Upload Audio File</h3>
        <input type="file" id="audioFile" accept=".wav,.mp3,.ogg,.flac,.aac,.m4a" />
        <button onclick="uploadFile()">📤 Upload</button>
        <div id="uploadMessage"></div>
    </div>
    
    <div>
        <button onclick="stopAll()">⏹️ Stop All</button>
        <button onclick="stop()">🛑 Stop Current</button>
        <button onclick="fetchSounds()">🔄 Refresh List</button>
    </div>
    <ul id="sound-list"></ul>
<script>
async function fetchSounds() {
    const res = await fetch('/sounds');
    const sounds = await res.json();
    const list = document.getElementById('sound-list');
    list.innerHTML = '';
    for (const file of sounds) {
        const li = document.createElement('li');
        const btn = document.createElement('button');
        btn.textContent = '▶️ ' + file;
        btn.className = "sound-btn";
        btn.onclick = () => play(file);
        li.appendChild(btn);
        list.appendChild(li);
    }
}

async function play(filename) {
    await fetch('/play', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({filename})
    });
}
async function stop() {
    await fetch('/stop', { method: 'POST' });
}
async function stopAll() {
    await fetch('/stopall', { method: 'POST' });
}

async function uploadFile() {
    const fileInput = document.getElementById('audioFile');
    const messageDiv = document.getElementById('uploadMessage');
    
    if (!fileInput.files[0]) {
        showMessage('Please select a file to upload.', 'error');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    
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

window.onload = fetchSounds;
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
