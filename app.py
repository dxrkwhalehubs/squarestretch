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
        res = int(request.form.get('res', 1440))
    except:
        res = 1440

    try:
        quality = int(request.form.get('quality', 20))
    except:
        quality = 20

    # Calculate output dimensions
    if ratio_w >= ratio_h:
        out_w = res
        out_h = int(res * ratio_h / ratio_w)
    else:
        out_h = res
        out_w = int(res * ratio_w / ratio_h)

    # H264 requires even dimensions
    out_w = out_w + (out_w % 2)
    out_h = out_h + (out_h % 2)

    job_id = str(uuid.uuid4())
    ext = file.filename.rsplit('.', 1)[1].lower()
    input_path = os.path.join(UPLOAD_FOLDER, f'{job_id}.{ext}')
    output_path = os.path.join(OUTPUT_FOLDER, f'{job_id}.mp4')
    file.save(input_path)

    if mode == 'stretch':
        vf = f'scale={out_w}:{out_h}'
    elif mode == 'crop':
        vf = f'scale={out_w}:{out_h}:force_original_aspect_ratio=increase,crop={out_w}:{out_h}'
    else:
        hex_color = pad_color.lstrip('#')
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        vf = f'scale={out_w}:{out_h}:force_original_aspect_ratio=decrease,pad={out_w}:{out_h}:(ow-iw)/2:(oh-ih)/2:color={r}/{g}/{b}'

    cmd = [
        'ffmpeg', '-y',
        '-i', input_path,
        '-vf', vf,
        '-c:v', 'libx264',
        '-crf', str(quality),
        '-preset', 'fast',
        '-c:a', 'aac',
        '-b:a', '192k',
        '-movflags', '+faststart',
        output_path
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            return jsonify({'error': result.stderr[-300:]}), 500
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Timed out'}), 500
    finally:
        if os.path.exists(input_path):
            os.remove(input_path)

    if not os.path.exists(output_path):
        return jsonify({'error': 'Output not created'}), 500

    return send_file(
        output_path,
        mimetype='video/mp4',
        as_attachment=True,
        download_name=f'stretched_{ratio_w}x{ratio_h}.mp4'
    )

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
