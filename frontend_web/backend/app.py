# backend/app.py
from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
import os
import shutil
import traceback
import json
from overall_shape_emotion_analysis import run_analysis  # refactor your script into a callable

app = Flask(__name__)
# Enable CORS for all routes and allow credentials
CORS(app, supports_credentials=True, resources={r"/*": {"origins": "*"}})

UPLOAD_FOLDER = "audio"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.after_request
def add_header(response):
    """Add headers to prevent caching of responses."""
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/analyze', methods=['POST'])
def analyze_audio():
    """Handle audio upload and run analysis."""
    try:
        # Check if file was provided
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file name provided"}), 400
        
        # Ensure filename is safe
        filename = os.path.basename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        # Delete old files with the same name
        if os.path.exists(filepath):
            os.remove(filepath)
        
        # Save the file
        file.save(filepath)
        
        print(f"Saved file to {filepath}")
            
        # Run analysis
        try:
            result_paths = run_analysis(filepath)
            print(f"Analysis complete: {result_paths}")
            return jsonify(result_paths)
        except Exception as e:
            traceback.print_exc()
            return jsonify({"error": f"Analysis failed: {str(e)}"}), 500
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Server error: {str(e)}"}), 500

# Serve CSV and other files from output and statics folders
@app.route('/output/<path:path>')
def serve_output_file(path):
    """Serve files from the output directory."""
    return send_from_directory('output', path)

@app.route('/static/<path:path>')
def serve_static_file(path):
    """Serve files from the static directory."""
    return send_from_directory('static', path)

# Add routes to serve texture files
@app.route('/texture_extractor/data/<path:path>')
def serve_texture_file(path):
    """Serve texture files from the texture_extractor directory."""
    # The texture_extractor directory is two levels up from the backend
    base_path = os.path.join(app.root_path, '..', '..', 'texture_extractor', 'data')
    full_path = os.path.abspath(os.path.join(base_path, path))
    
    # Security check: Ensure the path stays within the intended base directory
    if not full_path.startswith(os.path.abspath(base_path)):
        print(f"Forbidden path requested: {full_path} (derived from {path})")
        return jsonify({"error": "Forbidden path"}), 403
    
    print(f"Attempting to serve texture: {full_path} (requested path: {path})") # Add logging
    
    # Check if the file exists
    if os.path.isfile(full_path):
        print(f"Found file: {full_path}") # Add logging
        return send_file(full_path)
    
    # If it's a directory, we'll return a listing (optional, maybe remove for production)
    if os.path.isdir(full_path):
        print(f"Path is a directory: {full_path}") # Add logging
        # Consider removing directory listing for security/simplicity
        # items = os.listdir(full_path)
        # return jsonify({
        #     "type": "directory",
        #     "path": path,
        #     "items": items
        # })
        return jsonify({"error": "Path is a directory, not a file"}), 404 # More specific error
    
    # File or directory not found
    print(f"File not found: {full_path}") # Add logging
    return jsonify({"error": "File not found"}), 404

# API endpoint to get texture classification data
@app.route('/api/textures/va_classification')
def get_va_classification():
    """Get valence-arousal classification data for textures."""
    try:
        csv_path = os.path.join('..', '..', 'texture_extractor', 'data', 
                           'binary_va_classification9', 'va_classification_all.csv')
        
        if not os.path.exists(csv_path):
            return jsonify({"error": "Classification data not found"}), 404
            
        return send_file(csv_path)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# API endpoint to get textures by quadrant
@app.route('/api/textures/by_quadrant/<quadrant>')
def get_textures_by_quadrant(quadrant):
    """Get textures for a specific valence-arousal quadrant."""
    try:
        # Validate quadrant parameter
        valid_quadrants = ['high_high', 'high_low', 'low_high', 'low_low']
        if quadrant not in valid_quadrants:
            return jsonify({"error": f"Invalid quadrant. Must be one of: {', '.join(valid_quadrants)}"}), 400
        
        # Define paths to search
        search_paths = [
            os.path.join('..', '..', 'texture_extractor', 'data', 'binary_va_classification9', 
                      f'va_results_normal_grey/{quadrant}'),
            os.path.join('..', '..', 'texture_extractor', 'data', 'binary_va_classification9', 
                      f'va_results_gray_textures/{quadrant}')
        ]
        
        # Find texture files
        texture_files = []
        for path in search_paths:
            if os.path.exists(path):
                files = os.listdir(path)
                # Filter image files
                image_files = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
                texture_files.extend([os.path.join(os.path.basename(path), f) for f in image_files])
        
        if not texture_files:
            # If no files found in requested quadrant, use a fallback
            return jsonify({
                "quadrant": quadrant,
                "count": 0,
                "textures": [],
                "error": "No textures found for this quadrant"
            }), 200
        
        return jsonify({
            "quadrant": quadrant,
            "count": len(texture_files),
            "textures": texture_files
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
