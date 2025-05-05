# backend/app.py
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import shutil
import traceback
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

@app.route("/upload-audio", methods=["POST"])
def upload_audio():
    try:
        if "file" not in request.files:
            return jsonify({"status": "error", "message": "No file part in the request"}), 400
            
        file = request.files["file"]
        if file.filename == '':
            return jsonify({"status": "error", "message": "No file selected"}), 400
            
        if file:
            save_path = os.path.join(UPLOAD_FOLDER, "uploaded_audio.wav")
            file.save(save_path)
            
            # Make sure the public/data directory exists
            data_dir = os.path.join("../public/data")
            os.makedirs(data_dir, exist_ok=True)
            
            # Run the analysis with better error handling
            run_analysis(audio_path=save_path)
            
            # Add a timestamp to force cache invalidation
            timestamp = str(int(os.path.getmtime(os.path.join("../public/data/top2_emotion_summary.csv"))))
            return jsonify({
                "status": "success",
                "timestamp": timestamp
            })
    except Exception as e:
        # Log the full stack trace for debugging
        error_message = traceback.format_exc()
        print(f"Error processing audio: {error_message}")
        return jsonify({
            "status": "error", 
            "message": str(e),
            "details": error_message
        }), 500

    return jsonify({"status": "error", "message": "Unknown error"}), 400

# Add a route to serve the data files directly (for debugging)
@app.route("/data/<path:filename>")
def serve_data(filename):
    data_dir = os.path.join("../public/data")
    absolute_path = os.path.abspath(data_dir)
    print(f"Serving {filename} from {absolute_path}")
    
    # Add cache-busting headers
    response = send_from_directory(absolute_path, filename)
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

if __name__ == "__main__":
    app.run(port=5001, debug=True)
