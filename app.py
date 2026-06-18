import os
import uuid
import subprocess
from flask import Flask, request, jsonify, send_file, render_template

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024

UPLOAD_FOLDER = '/tmp/uploads'
OUTPUT_FOLDER = '/tmp/outputs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'mp4', 'mov', 'webm', 'avi', 'mkv', 'm4v'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_video():
    print('REQUEST RECEIVED', flush=True)

    if 'video' not in request.files:
        return jsonify({'error': 'No video file'}), 400

    file = request.files['video']
    if not file or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400

    mode = request.form.get('mode', 'stretch')
    pad_color = request.form.get('padColor', '#000000')

    try:
        ratio_w = int(request.form.get('ratioW', 1))
        ratio_h = int(request.form.get('ratioH', 1))
    except:
        ratio_w, ratio_h = 1, 1

    try:
        res = int(request.form.get('res', 1080))
    except:
        res = 1080

    try:
        quality = int(request.form.get('quality', 23))
    except:
        quality = 23

    if ratio_w >= ratio_h:
        out_w = res
        out_h = int(res * ratio_h / ratio_w)
    else:
        out_h = r
