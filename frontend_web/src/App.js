import React, { useRef, useState } from "react";
import "./App.css";
import ColorCloud from "./mesh_deformation";

function App() {
  const fileInputRef = useRef();
  const [selectedFile, setSelectedFile] = useState(null);
  const [csvPath, setCsvPath] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleFileChange = (event) => {
    const file = event.target.files[0];
    if (!file) return;

    const allowedTypes = ["audio/mpeg", "audio/mp3", "video/mp4", "audio/wav"
    ];
    if (!allowedTypes.includes(file.type)) {
      alert("Please upload a .mp3 or .mp4 file.");
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      alert("File must be under 10MB.");
      return;
    }

    setSelectedFile(file);
  };

  const handleGenerate = async () => {
    if (!selectedFile) {
      alert("Please upload a file first.");
      return;
    }

    setLoading(true);
    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const res = await fetch("http://127.0.0.1:5000/process-audio", {
        method: "POST",
        body: formData,
      });

      if (res.ok) {
        const data = await res.json();
        const fullPath = `http://127.0.0.1:5000${data.csv_path}`;
        console.log("✅ Audio processed. CSV Path:", fullPath);
        setCsvPath(fullPath);
      } else {
        alert("❌ Failed to process audio.");
      }
    } catch (err) {
      console.error("Error:", err);
      alert("❌ Backend not reachable.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App">
      <div className="background-scene">
        <ColorCloud csvPath={csvPath} />
      </div>

      <div className="foreground-ui">
        <div
          className="mesh-upload-frame"
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "32px",
            alignItems: "flex-start",
            padding: "24px",
            maxWidth: "480px",
          }}
        >
          <div className="upload-bar" style={{ display: "flex", gap: "16px", alignItems: "center" }}>
            <input
              ref={fileInputRef}
              id="file-upload"
              type="file"
              accept=".mp3, .mp4, audio/*, video/*"
              onChange={handleFileChange}
              style={{ display: "none" }}
            />
            <label
              className="upload-label"
              htmlFor="file-upload"
              style={{
                padding: "10px 20px",
                borderRadius: "24px",
                border: "1px solid white",
                color: "white",
                background: "transparent",
                fontSize: "14px",
                cursor: "pointer",
              }}
            >
              {selectedFile ? `📎 ${selectedFile.name}` : "Upload Audio/Video"}
            </label>

            <button
              className="generate-btn"
              onClick={handleGenerate}
              style={{
                padding: "10px 20px",
                borderRadius: "24px",
                background: loading ? "#ccc" : "white",
                color: "black",
                border: "none",
                fontSize: "14px",
                fontWeight: "500",
                cursor: loading ? "not-allowed" : "pointer",
              }}
              disabled={loading}
            >
              {loading ? "Generating..." : "Generate"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
