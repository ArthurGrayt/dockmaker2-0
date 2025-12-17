from flask import Flask, render_template, request, jsonify, send_file, current_app
import os
import uuid
from werkzeug.utils import secure_filename
from docx_processor import DocxProcessor

app = Flask(__name__)

# config
import tempfile
from storage import get_storage

# storage setup
storage = get_storage()
# For local processing steps we still need tmp info
# but storage handles persistence.

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
            # Save to storage (models folder)
            try:
                storage.save(file, 'models', filename)
                return jsonify({'message': 'Model uploaded', 'filename': filename})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        return jsonify({'error': 'Invalid file type'}), 400
    
    else:
        # GET
        try:
            models = storage.list_files('models')
            # Filter just in case
            models = [f for f in models if f.endswith('.docx')]
            return jsonify(models)
        except Exception as e:
             return jsonify({'error': str(e)}), 500

@app.route('/api/upload_content', methods=['POST'])
def upload_content():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and file.filename.endswith('.docx'):
        unique_name = f"{uuid.uuid4()}_{secure_filename(file.filename)}"
        try:
            storage.save(file, 'uploads', unique_name)
            return jsonify({'filename': unique_name, 'original_name': file.filename})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/api/process', methods=['POST'])
def process():
    data = request.json
    model_filename = data.get('model_filename')
    content_filename = data.get('content_filename')
    
    if not model_filename or not content_filename:
        return jsonify({'error': 'Missing filename'}), 400
        
    # We need to process locally, so we download files to a temp dir
    with tempfile.TemporaryDirectory() as tmp_dir:
        model_path = os.path.join(tmp_dir, model_filename)
        content_path = os.path.join(tmp_dir, content_filename)
        output_filename = f"processed_{content_filename}"
        output_path = os.path.join(tmp_dir, output_filename)
        
        try:
            # Download
            storage.download_to_path(model_filename, 'models', model_path)
            storage.download_to_path(content_filename, 'uploads', content_path)
            
            # Process
            # We create a new processor instance just for this op to avoid global state issues with paths
            # actually DocxProcessor just needs paths
            processor.output_folder = tmp_dir # Hackily update? No, pass paths.
            # DocxProcessor process_document returns output_path
            # But DocxProcessor was init with global folders.
            # Let's instantiate a localized one or ignore the instance folders if methods allow.
            # Looking at docx_processor.py:
            # process_document uses self.output_folder to construct output path if we pass filename?
            # actually it takes (content_path, model_path, output_filename).
            # And calculates output_path = join(self.output_folder, output_filename).
            # So we need to ensure the processor uses our tmp_dir.
            local_processor = DocxProcessor(tmp_dir, tmp_dir) 
            generated_path = local_processor.process_document(content_path, model_path, output_filename)
            
            # Upload result
            # We assume generated_path is what we want to upload
            # We upload to 'output' folder
            result_url_or_name = storage.upload_from_path(generated_path, 'output', output_filename)
            
            # If storage is Blob, result_url_or_name is a public URL.
            # If Local, it is the filename.
            # We need to standardize response.
            if result_url_or_name.startswith('http'):
                return jsonify({'download_url': result_url_or_name})
            else:
                return jsonify({'download_url': f"/api/download/{output_filename}"})

        except Exception as e:
            return jsonify({'error': str(e)}), 500

@app.route('/api/download/<filename>')
def download(filename):
    # This route is mainly for Local storage or if we want to proxy.
    # For Local: serve from output folder.
    # We need to know where 'output' is.
    # storage.download_to_path? No, send_file needs a path.
    # If we are in Local mode, we know the path.
    # If in Blob mode, we shouldn't be hitting this unless we proxy.
    # But 'process' returns a direct URL if Blob. So this is fallback.
    
    # We can rely on storage implementation details for Local:
    if hasattr(storage, 'base_path'): # LocalStorage
        path = os.path.join(storage.base_path, 'output', filename)
        if os.path.exists(path):
            return send_file(path, as_attachment=True)
    
    return jsonify({'error': 'File not found or handled via direct link'}), 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)
