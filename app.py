import os
import uuid
import subprocess
from flask import Flask, request, jsonify, send_file, render_template
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max upload

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
    if 'video' not in request.files:
        return jsonify({'error': 'No video file'}), 400

    file = request.files['video']
    if not file or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400

    mode = request.form.get('mode', 'stretch')
    size = request.form.get('size', '1080')
    pad_color = request.form.get('padColor', '#000000')

    try:
        size = int(size)
        if size not in [720, 1080, 1440, 2048, 3840]:
            size = 1080
    except:
        size = 1080

    # Save uploaded file
    job_id = str(uuid.uuid4())
    ext = file.filename.rsplit('.', 1)[1].lower()
    input_path = os.path.join(UPLOAD_FOLDER, f'{job_id}.{ext}')
    output_path = os.path.join(OUTPUT_FOLDER, f'{job_id}_output.mp4')
    file.save(input_path)

    # Build FFmpeg filter
    if mode == 'stretch':
        vf = f'scale={size}:{size}'
    elif mode == 'crop':
        vf = f'scale={size}:{size}:force_original_aspect_ratio=increase,crop={size}:{size}'
    else:  # pad
        hex_color = pad_color.lstrip('#')
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        vf = f'scale={size}:{size}:force_original_aspect_ratio=decrease,pad={size}:{size}:(ow-iw)/2:(oh-ih)/2:color={r}/{g}/{b}'

    cmd = [
        'ffmpeg', '-y',
        '-i', input_path,
        '-vf', vf,
        '-c:v', 'libx264',
        '-crf', '16',
        '-preset', 'fast',
        '-c:a', 'aac',
        '-b:a', '192k',
        '-movflags', '+faststart',
        output_path
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            print("FFmpeg error:", result.stderr)
            return jsonify({'error': 'FFmpeg failed', 'details': result.stderr}), 500
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Processing timed out'}), 500
    finally:
        # Clean up input file
        if os.path.exists(input_path):
            os.remove(input_path)

    if not os.path.exists(output_path):
        return jsonify({'error': 'Output file not created'}), 500

    return send_file(
        output_path,
        mimetype='video/mp4',
        as_attachment=True,
        download_name=f'square_{size}x{size}.mp4'
    )

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
