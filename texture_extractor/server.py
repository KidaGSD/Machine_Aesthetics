import os
import sys
import json
import tempfile
import uuid
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import subprocess
import shutil

# Ensure the src directory is in the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, "src")
if src_dir not in sys.path:
    sys.path.append(src_dir)

# Path to web resources
frontend_data_dir = os.path.abspath(os.path.join(script_dir, "..", "frontend_web", "public", "data"))
os.makedirs(frontend_data_dir, exist_ok=True)

# Temporary directory for uploads and processing
temp_dir = os.path.join(script_dir, "temp")
os.makedirs(temp_dir, exist_ok=True)

# Results directory for shared data
results_dir = os.path.join(frontend_data_dir, "results")
os.makedirs(results_dir, exist_ok=True)

# Initialize Flask app
app = Flask(__name__, static_folder=frontend_data_dir)
CORS(app)  # Enable CORS for all routes

@app.route('/api/process-audio', methods=['POST'])
def process_audio():
    """Process uploaded audio file and generate VAD timeline and texture mapping"""
    if 'audioFile' not in request.files:
        return jsonify({'success': False, 'error': 'No audio file provided'}), 400
    
    audio_file = request.files['audioFile']
    if audio_file.filename == '':
        return jsonify({'success': False, 'error': 'Empty filename'}), 400
    
    # Generate unique ID for this processing run
    process_id = str(uuid.uuid4())
    process_dir = os.path.join(temp_dir, process_id)
    os.makedirs(process_dir, exist_ok=True)
    
    # Save uploaded audio file
    audio_path = os.path.join(process_dir, audio_file.filename)
    audio_file.save(audio_path)
    
    # Set output paths
    vad_csv_path = os.path.join(process_dir, "vad_timeline.csv")
    web_csv_path = os.path.join(results_dir, f"{process_id}_vad_timeline.csv")
    
    try:
        # Step 1: Run valence-analysis.py to generate VAD timeline
        valence_analysis_script = os.path.abspath(os.path.join(
            script_dir, "..", "audio_analysis", "machine_ase", "luminote", "valence-analysis.py"
        ))
        
        # Check if the script exists
        if not os.path.exists(valence_analysis_script):
            return jsonify({
                'success': False, 
                'error': f'Valence analysis script not found at {valence_analysis_script}'
            }), 500
        
        # Run the script
        subprocess.run([
            sys.executable,
            valence_analysis_script,
            "--input", audio_path,
            "--output", vad_csv_path
        ], check=True)
        
        # Check if VAD CSV was generated
        if not os.path.exists(vad_csv_path):
            return jsonify({'success': False, 'error': 'Failed to generate VAD timeline'}), 500
        
        # Step 2: Run main.py for texture mapping and generation
        main_script = os.path.join(script_dir, "main.py")
        config_path = os.path.join(script_dir, "config", "pipeline_config.yaml")
        
        # Ensure the config directory exists
        os.makedirs(os.path.join(script_dir, "config"), exist_ok=True)
        
        # Run the main processing pipeline
        subprocess.run([
            sys.executable,
            main_script,
            "--config", config_path,
            "--vad_csv", vad_csv_path,
            "--classifier", "vad",
            "--output_dir", os.path.join(process_dir, "results")
        ], check=True)
        
        # Step 3: Copy the VAD CSV to the web-accessible directory
        shutil.copy2(vad_csv_path, web_csv_path)
        
        # Step 4: Read the overall emotion from the VAD CSV
        import pandas as pd
        try:
            df = pd.read_csv(vad_csv_path)
            overall_emotion = df["OverallDiscreteEmotion"].iloc[0] if "OverallDiscreteEmotion" in df.columns else "neutral"
        except Exception as e:
            print(f"Error reading overall emotion from CSV: {e}")
            overall_emotion = "neutral"
        
        # Return the paths and overall emotion to the frontend
        return jsonify({
            'success': True,
            'csvPath': f"/data/results/{process_id}_vad_timeline.csv",
            'overallEmotion': overall_emotion,
            'processId': process_id
        })
    
    except Exception as e:
        import traceback
        print(f"Error processing audio: {e}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/textures/<emotion>', methods=['GET'])
def get_texture_info(emotion):
    """Get texture information for a specific emotion"""
    try:
        # Path to texture dataset
        texture_dataset = os.path.join(script_dir, "data", "binary_va_classification")
        
        # Map emotion to VA quadrant
        emotion_to_quadrant = {
            "joy": "high_high",
            "peaceful": "high_low",
            "serene": "high_low",
            "surprised": "high_high",
            "angry": "low_high",
            "fearful": "low_high", 
            "disgusted": "low_high",
            "sad": "low_low",
            "neutral": "neu_neu"  # Default
        }
        
        quadrant = emotion_to_quadrant.get(emotion.lower(), "neu_neu")
        
        # Find textures for this quadrant
        import glob
        texture_info = {
            "emotion": emotion,
            "quadrant": quadrant,
            "textures": []
        }
        
        # Find top 5 textures for this quadrant
        texture_files = glob.glob(os.path.join(texture_dataset, quadrant, "*.jpg")) + \
                       glob.glob(os.path.join(texture_dataset, quadrant, "*.png"))
        
        if not texture_files and quadrant != "neu_neu":
            # Fall back to neutral if no textures found
            texture_files = glob.glob(os.path.join(texture_dataset, "neu_neu", "*.jpg")) + \
                           glob.glob(os.path.join(texture_dataset, "neu_neu", "*.png"))
        
        # Take the top 5 textures
        for texture_path in texture_files[:5]:
            texture_name = os.path.basename(texture_path)
            # Copy to web-accessible directory if not already there
            web_texture_path = os.path.join(frontend_data_dir, "textures", emotion.lower(), texture_name)
            os.makedirs(os.path.dirname(web_texture_path), exist_ok=True)
            
            if not os.path.exists(web_texture_path):
                shutil.copy2(texture_path, web_texture_path)
            
            texture_info["textures"].append({
                "name": texture_name,
                "path": f"/data/textures/{emotion.lower()}/{texture_name}"
            })
        
        return jsonify(texture_info)
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/texture-keys', methods=['GET'])
def get_texture_keys():
    """Get all texture parameters for emotion mapping"""
    try:
        # Create a mapping of emotions to texture pattern descriptions
        texture_keys = {
            "joy": {"texturePattern": "Bright, vibrant patterns with high energy"},
            "peaceful": {"texturePattern": "Smooth, flowing patterns with calm energy"},
            "serene": {"texturePattern": "Gentle, balanced patterns with tranquil energy"},
            "surprised": {"texturePattern": "Bold, unexpected patterns with sudden energy"},
            "angry": {"texturePattern": "Rough, jagged patterns with intense energy"},
            "fearful": {"texturePattern": "Sharp, unsettling patterns with nervous energy"},
            "disgusted": {"texturePattern": "Irregular, distorted patterns with rejecting energy"},
            "sad": {"texturePattern": "Muted, heavy patterns with low energy"},
            "neutral": {"texturePattern": "Balanced, moderate patterns with even energy"}
        }
        
        # Save this to a static file for the frontend to use
        with open(os.path.join(frontend_data_dir, "texture_keys.json"), 'w') as f:
            json.dump(texture_keys, f, indent=2)
        
        return jsonify(texture_keys)
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/', methods=['GET'])
def index():
    """Serve a simple HTML interface for testing without the React frontend"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Machine Aesthetics - Simple Interface</title>
        <style>
            body { font-family: Arial; max-width: 800px; margin: 0 auto; padding: 20px; }
            .drop-area { border: 2px dashed #ccc; padding: 20px; text-align: center; margin: 20px 0; }
            .button { background: #3B82F6; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; }
            #result { margin-top: 20px; }
            .emotion-tag { display: inline-block; padding: 4px 8px; border-radius: 12px; font-size: 14px; font-weight: 500; margin-right: 8px; color: white; }
            .emotion-joy { background-color: #FFCC00; }
            .emotion-peaceful { background-color: #9EE5A1; color: #333; }
            .emotion-serene { background-color: #7AE7FF; color: #333; }
            .emotion-neutral { background-color: #DDDDDD; color: #333; }
            .emotion-sad { background-color: #3373CC; }
            .emotion-fearful { background-color: #8075CC; }
            .emotion-angry { background-color: #FF3333; }
            .emotion-surprised { background-color: #FF66CC; }
            .emotion-disgusted { background-color: #669933; }
            .processing { background-color: #f0f0f0; padding: 20px; border-radius: 4px; text-align: center; }
        </style>
    </head>
    <body>
        <h1>Machine Aesthetics - Audio to Texture</h1>
        <p>This is a simplified interface for testing the backend. For the full experience with 3D visualization, use the React frontend.</p>
        
        <div class="drop-area" id="dropArea">
            <p>Drop audio file here or</p>
            <input type="file" id="audioFile" accept="audio/*" style="display:none">
            <button class="button" onclick="document.getElementById('audioFile').click()">Select File</button>
        </div>
        <div id="result"></div>
        
        <script>
            const audioInput = document.getElementById('audioFile');
            const dropArea = document.getElementById('dropArea');
            const resultDiv = document.getElementById('result');
            
            audioInput.addEventListener('change', handleFile);
            
            dropArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                dropArea.style.background = '#f0f0f0';
            });
            
            dropArea.addEventListener('dragleave', () => {
                dropArea.style.background = 'transparent';
            });
            
            dropArea.addEventListener('drop', (e) => {
                e.preventDefault();
                dropArea.style.background = 'transparent';
                if (e.dataTransfer.files.length) {
                    audioInput.files = e.dataTransfer.files;
                    handleFile();
                }
            });
            
            function handleFile() {
                if (!audioInput.files.length) return;
                
                const file = audioInput.files[0];
                resultDiv.innerHTML = `<div class="processing"><p>Processing ${file.name}...</p><p>This may take a minute or two...</p></div>`;
                
                const formData = new FormData();
                formData.append('audioFile', file);
                
                fetch('/api/process-audio', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        resultDiv.innerHTML = `
                            <h3>Processing Complete</h3>
                            <p>
                                <span class="emotion-tag emotion-${data.overallEmotion.toLowerCase()}">
                                    ${data.overallEmotion.charAt(0).toUpperCase() + data.overallEmotion.slice(1)}
                                </span>
                                Overall emotion detected
                            </p>
                            <p>CSV Path: <a href="${data.csvPath}" target="_blank">${data.csvPath}</a></p>
                            <p>Processed ID: ${data.processId}</p>
                            <p>
                                <a href="javascript:fetchTextureInfo('${data.overallEmotion}')">
                                    View available textures for this emotion
                                </a>
                            </p>
                        `;
                    } else {
                        resultDiv.innerHTML = `<p>Error: ${data.error}</p>`;
                    }
                })
                .catch(error => {
                    resultDiv.innerHTML = `<p>Error: ${error.message}</p>`;
                });
            }
            
            function fetchTextureInfo(emotion) {
                fetch(`/api/textures/${emotion}`)
                    .then(response => response.json())
                    .then(data => {
                        let textureHtml = `
                            <h4>Textures for ${emotion}</h4>
                            <p>Quadrant: ${data.quadrant}</p>
                            <div style="display: flex; flex-wrap: wrap; gap: 10px;">
                        `;
                        
                        if (data.textures && data.textures.length > 0) {
                            data.textures.forEach(texture => {
                                textureHtml += `
                                    <div style="flex: 0 0 150px;">
                                        <img src="${texture.path}" style="width: 100%; height: auto; display: block; border: 1px solid #ccc;">
                                        <p style="font-size: 12px; overflow: hidden; text-overflow: ellipsis;">${texture.name}</p>
                                    </div>
                                `;
                            });
                        } else {
                            textureHtml += `<p>No textures found for this emotion</p>`;
                        }
                        
                        textureHtml += `</div>`;
                        document.getElementById('textureResults').innerHTML = textureHtml;
                    })
                    .catch(error => {
                        console.error('Error fetching texture info:', error);
                    });
            }
        </script>
        
        <div id="textureResults" style="margin-top: 30px;"></div>
    </body>
    </html>
    """
    return html

if __name__ == "__main__":
    # Generate texture keys on startup
    with app.test_request_context():
        get_texture_keys()
    
    # Run the server
    port = int(os.environ.get("PORT", 3001))
    app.run(host='0.0.0.0', port=port, debug=True) 