from flask import Flask, jsonify
from flask_cors import CORS
import json
import os

app = Flask(__name__)
CORS(app)

# Automatically use the same folder this file is in
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SHAPE_PATH = os.path.join(BASE_DIR, "shape.json")

@app.route("/api/shape")
def get_shape():
    try:
        with open(SHAPE_PATH) as f:
            data = json.load(f)
        return jsonify(data)
    except FileNotFoundError:
        return jsonify({"error": "shape.json not found!"}), 404

@app.route("/")
def home():
    return "Flask API is running. Try /api/shape"

if __name__ == "__main__":
    app.run(debug=True)
