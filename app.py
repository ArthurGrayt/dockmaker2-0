from flask import Flask, render_template, request, jsonify, send_file, current_app
import os
import uuid
from werkzeug.utils import secure_filename
from docx_processor import DocxProcessor

app = Flask(__name__)

# config
import tempfile

# config
if os.environ.get('VERCEL'):
    # Vercel filesystem is read-only except for /tmp
    BASE_DIR = tempfile.gettempdir()
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    MODELS_FOLDER = os.path.join(BASE_DIR, 'models')
    OUTPUT_FOLDER = os.path.join(BASE_DIR, 'output')
else:
    # Local development
    UPLOAD_FOLDER = os.path.abspath('uploads')
    MODELS_FOLDER = os.path.abspath('models')
    OUTPUT_FOLDER = os.path.abspath('output')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(MODELS_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MODELS_FOLDER'] = MODELS_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

processor = DocxProcessor(UPLOAD_FOLDER, OUTPUT_FOLDER)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/models', methods=['GET', 'POST'])
def handle_models():
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        if file and file.filename.endswith('.docx'):
            filename = secure_filename(file.filename)
            # Use UUID to prevent overwrites or collisions? Or keep names?
            # Keeping names is friendlier.
            save_path = os.path.join(app.config['MODELS_FOLDER'], filename)
            file.save(save_path)
            return jsonify({'message': 'Model uploaded', 'filename': filename})
        return jsonify({'error': 'Invalid file type'}), 400
    
    else:
        # GET
        files = os.listdir(app.config['MODELS_FOLDER'])
        models = [f for f in files if f.endswith('.docx')]
        return jsonify(models)

@app.route('/api/upload_content', methods=['POST'])
def upload_content():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and file.filename.endswith('.docx'):
        # Save temp file
        unique_name = f"{uuid.uuid4()}_{secure_filename(file.filename)}"
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
        file.save(save_path)
        return jsonify({'filename': unique_name, 'original_name': file.filename})
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/api/process', methods=['POST'])
def process():
    data = request.json
    model_filename = data.get('model_filename')
    content_filename = data.get('content_filename')
    
    if not model_filename or not content_filename:
        return jsonify({'error': 'Missing filename'}), 400
        
    model_path = os.path.join(app.config['MODELS_FOLDER'], model_filename)
    content_path = os.path.join(app.config['UPLOAD_FOLDER'], content_filename)
    
    if not os.path.exists(model_path) or not os.path.exists(content_path):
        return jsonify({'error': 'File not found'}), 404
        
    try:
        output_filename = f"processed_{content_filename}"
        output_path = processor.process_document(content_path, model_path, output_filename)
        return jsonify({'download_url': f"/api/download/{output_filename}"})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/<filename>')
def download(filename):
    return send_file(os.path.join(app.config['OUTPUT_FOLDER'], filename), as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
