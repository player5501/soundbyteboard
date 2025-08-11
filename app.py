import threading
import os
import argparse
from pathlib import Path
import pygame
from flask import Flask, render_template, request, jsonify, render_template_string, send_file
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
    return render_template('index.html')

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

@app.route('/audio/<path:filename>')
def serve_audio(filename):
    # Prevent directory traversal
    safe_path = os.path.normpath(os.path.join(SOUNDS_DIR, filename))
    if not safe_path.startswith(os.path.abspath(SOUNDS_DIR)):
        return jsonify({'error': 'Invalid path'}), 400
    
    if not os.path.exists(safe_path):
        return jsonify({'error': 'File not found'}), 404
    
    return send_file(safe_path)

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

@app.route('/manifest.json')
def manifest():
    return app.send_static_file('json/manifest.json')

@app.route('/sw.js')
def service_worker():
    return app.send_static_file('js/sw.js')

@app.route('/icon-192.png')
def icon_192():
    # Return a simple 192x192 icon (you can replace this with a real icon)
    return app.response_class(
        '<svg width="192" height="192" xmlns="http://www.w3.org/2000/svg"><rect width="192" height="192" fill="#0f0f23"/><text x="96" y="96" text-anchor="middle" dy=".3em" fill="#00ff88" font-family="monospace" font-size="24">🎵</text></svg>',
        mimetype='image/svg+xml'
    )

@app.route('/icon-512.png')
def icon_512():
    # Return a simple 512x512 icon (you can replace this with a real icon)
    return app.response_class(
        '<svg width="512" height="512" xmlns="http://www.w3.org/2000/svg"><rect width="512" height="512" fill="#0f0f23"/><text x="256" y="256" text-anchor="middle" dy=".3em" fill="#00ff88" font-family="monospace" font-size="64">🎵</text></svg>',
        mimetype='image/svg+xml'
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Soundboard Flask App")
    parser.add_argument('--sounds-dir', "-d", "--dir", type=str, required=True,
                        help='Path to the directory containing sound files')
    parser.add_argument('-p', '--port', type=int, default=5000,
                        help='Port to run the web app on (default: 5000)')
    args = parser.parse_args()
    SOUNDS_DIR = os.path.abspath(args.sounds_dir)

    app.run(host='0.0.0.0', port=args.port)
