# backend/app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import shutil
from overall_shape_emotion_analysis import run_analysis  # refactor your script into a callable

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "audio"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/upload-audio", methods=["POST"])
def upload_audio():
    file = request.files["file"]
    if file:
        save_path = os.path.join(UPLOAD_FOLDER, "uploaded_audio.wav")
        file.save(save_path)

        run_analysis(audio_path=save_path)  # ← you need to refactor your current script into a function
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 400

if __name__ == "__main__":
    app.run(port=5001)
