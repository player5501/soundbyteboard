import threading
import os
import argparse
from pathlib import Path
import pygame
from flask import Flask, request, jsonify, render_template_string

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

@app.route('/sounds')
def list_sounds():
    sounds = []
    for root, files in os.walk(SOUNDS_DIR):
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
    </style>
</head>
<body>
    <h1>Soundboard</h1>
    <div>
        <button onclick="stopAll()">⏹️ Stop All</button>
        <button onclick="stop()">🛑 Stop Current</button>
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
