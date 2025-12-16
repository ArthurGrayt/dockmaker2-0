document.addEventListener('DOMContentLoaded', () => {
    // State
    let selectedModel = null;
    let uploadedContentFile = null;

    // Elements
    const tabs = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    // Model Upload
    const modelDropzone = document.getElementById('model-dropzone');
    const modelInput = document.getElementById('model-input');
    const modelsGrid = document.getElementById('models-grid');

    // Process Content
    const contentDropzone = document.getElementById('content-dropzone');
    const contentInput = document.getElementById('content-input');
    const contentInfo = document.getElementById('content-file-info');
    const contentFilenameDisplay = document.getElementById('content-filename');
    const modelSelect = document.getElementById('model-select');
    const previewBox = document.getElementById('selected-model-preview');
    const previewModelName = document.getElementById('preview-model-name');
    const btnProcess = document.getElementById('btn-process');
    const resultArea = document.getElementById('result-area');
    const downloadLink = document.getElementById('download-link');

    // --- Tab Switching ---
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            
            tab.classList.add('active');
            document.getElementById(tab.dataset.tab).classList.add('active');
            
            if(tab.dataset.tab === 'models') loadModels();
            if(tab.dataset.tab === 'process') loadModelsIntoSelect();
        });
    });

    // --- Models Logic ---
    function loadModels() {
        fetch('/api/models')
            .then(res => res.json())
            .then(files => {
                modelsGrid.innerHTML = '';
                if (files.length === 0) {
                    modelsGrid.innerHTML = '<div class="empty-state">Nenhum modelo cadastrado.</div>';
                    return;
                }
                files.forEach(file => {
                    const card = document.createElement('div');
                    card.className = 'model-card';
                    card.innerHTML = `
                        <div class="model-icon"><i class="fa-solid fa-file-contract"></i></div>
                        <div class="model-name">${file}</div>
                    `;
                    // Optional: click to select?
                    modelsGrid.appendChild(card);
                });
            });
    }

    // Initialize list
    loadModels();

    // Drag & Drop for Model
    setupDropzone(modelDropzone, modelInput, (file) => {
        const formData = new FormData();
        formData.append('file', file);
        fetch('/api/models', { method: 'POST', body: formData })
            .then(res => res.json())
            .then(data => {
                if(data.error) alert(data.error);
                else {
                    alert('Modelo cadastrado com sucesso!');
                    loadModels();
                }
            });
    });

    // --- Process Logic ---
    function loadModelsIntoSelect() {
        fetch('/api/models')
            .then(res => res.json())
            .then(files => {
                const currentVal = modelSelect.value;
                modelSelect.innerHTML = '<option value="" disabled selected>Escolha um modelo...</option>';
                files.forEach(f => {
                    const opt = document.createElement('option');
                    opt.value = f;
                    opt.textContent = f;
                    modelSelect.appendChild(opt);
                });
                if(files.includes(currentVal)) modelSelect.value = currentVal;
            });
    }

    setupDropzone(contentDropzone, contentInput, (file) => {
        const formData = new FormData();
        formData.append('file', file);
        fetch('/api/upload_content', { method: 'POST', body: formData })
            .then(res => res.json())
            .then(data => {
                if(data.error) alert(data.error);
                else {
                    uploadedContentFile = data.filename;
                    contentFilenameDisplay.textContent = data.original_name;
                    contentInfo.classList.remove('hidden');
                    checkProcessReady();
                }
            });
    });

    modelSelect.addEventListener('change', (e) => {
        selectedModel = e.target.value;
        if(selectedModel) {
            previewBox.classList.remove('hidden');
            previewModelName.textContent = selectedModel;
        } else {
            previewBox.classList.add('hidden');
        }
        checkProcessReady();
    });

    function checkProcessReady() {
        if(uploadedContentFile && selectedModel) {
            btnProcess.disabled = false;
        } else {
            btnProcess.disabled = true;
        }
    }

    btnProcess.addEventListener('click', () => {
        if(!uploadedContentFile || !selectedModel) return;
        
        btnProcess.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Processando...';
        btnProcess.disabled = true;

        fetch('/api/process', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                model_filename: selectedModel,
                content_filename: uploadedContentFile
            })
        })
        .then(res => res.json())
        .then(data => {
            btnProcess.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Processar Novamente';
            btnProcess.disabled = false;
            
            if(data.error) {
                alert('Erro: ' + data.error);
            } else {
                resultArea.classList.remove('hidden');
                downloadLink.href = data.download_url;
            }
        })
        .catch(err => {
            console.error(err);
            btnProcess.disabled = false;
            btnProcess.textContent = 'Processar Documento';
            alert('Erro de conexão.');
        });
    });

    // Helper
    function setupDropzone(zone, input, callback) {
        zone.addEventListener('click', () => input.click());
        input.addEventListener('change', (e) => {
            if(e.target.files.length) callback(e.target.files[0]);
        });
        
        zone.addEventListener('dragover', (e) => {
            e.preventDefault();
            zone.style.borderColor = 'var(--accent)';
        });
        zone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            zone.style.borderColor = 'rgba(255,255,255,0.2)';
        });
        zone.addEventListener('drop', (e) => {
            e.preventDefault();
            zone.style.borderColor = 'rgba(255,255,255,0.2)';
            if(e.dataTransfer.files.length) callback(e.dataTransfer.files[0]);
        });
    }
});
