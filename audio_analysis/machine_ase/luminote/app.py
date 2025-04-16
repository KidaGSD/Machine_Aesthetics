import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from valence_analysis import process_audio

# Always use absolute path relative to this file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
CORS(app)

# Ensure it exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/")
def home():
    return "✅ Flask backend is running!"

@app.route("/process-audio", methods=["POST"])
def handle_audio():
    if "file" not in request.files:
        return "No file uploaded", 400

    file = request.files["file"]
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(file_path)

    try:
        output_csv = process_audio(file_path, output_dir=app.config["UPLOAD_FOLDER"])
        return jsonify({
            "status": "success",
            "csv_path": f"/uploads/{os.path.basename(output_csv)}"
        })
    except Exception as e:
        print("Processing error:", e)
        return jsonify({"error": str(e)}), 500

@app.route("/uploads/<filename>")
def serve_csv(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

if __name__ == "__main__":
    app.run(port=5000, debug=True)
