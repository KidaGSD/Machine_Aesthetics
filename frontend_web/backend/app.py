# backend/app.py
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import os
import shutil
import traceback
from overall_shape_emotion_analysis import run_analysis  # refactor your script into a callable

app = Flask(__name__)
# Enhanced CORS configuration
CORS(app, 
     resources={r"/*": {"origins": "*"}},
     supports_credentials=True, 
     allow_headers=["Content-Type", "Authorization", "Access-Control-Allow-Origin"],
     expose_headers=["Content-Disposition", "Content-Length"],
     methods=["GET", "POST", "OPTIONS"]
)

UPLOAD_FOLDER = "audio"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.after_request
def add_header(response):
    """Add headers to prevent caching of responses and add CORS headers."""
    # Caching prevention
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    # CORS headers
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    
    return response

@app.route('/analyze', methods=['POST'])
def analyze_audio():
    """Handle audio file upload and analysis"""
    if 'file' in request.files:
        file = request.files['file']
        save_path = os.path.join(UPLOAD_FOLDER, "uploaded_audio.wav")
        file.save(save_path)
        
        result = run_analysis(audio_path=save_path)  # ← you need to refactor your current script into a function
        return jsonify(result or {"status": "success"})
    return jsonify({"status": "error", "error": "No file provided"}), 400

# Serve CSV and other files from output and statics folders
@app.route('/output/<path:path>')
def serve_output_file(path):
    """Serve files from the output directory with fallback to public/data/output."""
    # First try the legacy output directory
    legacy_path = os.path.join('output', path)
    if os.path.isfile(legacy_path):
        print(f"Serving legacy file from {legacy_path}")
        return send_from_directory('output', path)
    
    # Then try the new public location
    public_path = os.path.join('..', 'public', 'data', 'output', path)
    if os.path.isfile(public_path):
        print(f"Serving file from public path: {public_path}")
        return send_from_directory('../public/data/output', path)
    
    # Log that we couldn't find the file in either location
    print(f"File {path} not found in either legacy output or public/data/output")
    return jsonify({"error": f"File not found: {path}"}), 404

@app.route('/static/<path:path>')
def serve_static_file(path):
    """Serve files from the static directory."""
    return send_from_directory('static', path)

@app.route('/emotions/<path:path>')
def serve_public_emotions_file(path):
    """Serve files from the public/emotions directory."""
    full_path = os.path.join(app.root_path, '..', 'public', 'emotions', path)
    print(f"Request for /emotions/{path}")
    print(f"Attempting to serve from: {full_path}")
    
    if os.path.isfile(full_path):
        print(f"Found emotions file at {full_path}")
        response = send_file(full_path)
        # Explicitly add CORS headers to this response
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    else:
        print(f"Emotions file not found at {full_path}")
        return jsonify({"error": f"Emotions file not found: {path}"}), 404

# New routes to serve files from public folder structure
@app.route('/data/output/<path:path>')
def serve_public_data_file(path):
    """Serve files from the public/data/output directory."""
    full_path = os.path.join(app.root_path, '..', 'public', 'data', 'output', path)
    print(f"Request for /data/output/{path}")
    print(f"Attempting to serve from: {full_path}")
    
    if os.path.isfile(full_path):
        print(f"Found file at {full_path}")
        response = send_file(full_path)
        # Explicitly add CORS headers to this response
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    else:
        print(f"File not found at {full_path}")
        # Try to list the directory contents
        try:
            dir_path = os.path.dirname(full_path)
            if os.path.isdir(dir_path):
                print(f"Directory contents of {dir_path}:")
                print(os.listdir(dir_path))
            else:
                print(f"No directory at {dir_path}")
        except Exception as e:
            print(f"Error listing directory: {e}")
        
        return jsonify({"error": f"File not found: {path}"}), 404

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

@app.route('/debug/paths')
def debug_paths():
    """Debug endpoint to check all paths in the application."""
    base_path = app.root_path
    public_path = os.path.join(base_path, '..', 'public')
    output_path = os.path.join(base_path, 'output')
    
    try:
        paths = {
            "app_root_path": base_path,
            "public_path": public_path,
            "public_path_exists": os.path.exists(public_path),
            "output_path": output_path,
            "output_path_exists": os.path.exists(output_path),
            
            "public_data_output_path": os.path.join(public_path, 'data', 'output'),
            "public_data_output_exists": os.path.exists(os.path.join(public_path, 'data', 'output')),
            "public_emotions_path": os.path.join(public_path, 'emotions'),
            "public_emotions_exists": os.path.exists(os.path.join(public_path, 'emotions')),
            
            # Check for specific files
            "files_in_output": os.listdir(output_path) if os.path.exists(output_path) else [],
            "files_in_public_data_output": os.listdir(os.path.join(public_path, 'data', 'output')) 
                if os.path.exists(os.path.join(public_path, 'data', 'output')) else [],
            "files_in_public_emotions": os.listdir(os.path.join(public_path, 'emotions')) 
                if os.path.exists(os.path.join(public_path, 'emotions')) else []
        }
        
        # Try to check file content
        top2_csv_path = os.path.join(public_path, 'data', 'output', 'top2_emotion_summary.csv')
        if os.path.exists(top2_csv_path):
            with open(top2_csv_path, 'r') as f:
                paths["top2_csv_content"] = f.read()
                
        return jsonify(paths)
    except Exception as e:
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        })

# Add a route to handle OPTIONS requests for CORS preflight
@app.route('/', defaults={'path': ''}, methods=['OPTIONS'])
@app.route('/<path:path>', methods=['OPTIONS'])
def handle_options(path):
    """Handles OPTIONS requests for CORS preflight."""
    return '', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
