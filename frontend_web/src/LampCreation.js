import React, { useState, useRef, useEffect } from "react";
import "./LampCreation.css";
import Scene from "./mesh_deformation";
import EmotionCurveMorph from "./EmotionCurveMorph";
import Papa from "papaparse";

const LampCreation = () => {
  const [audioFile, setAudioFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [sceneKey, setSceneKey] = useState(0);
  const sceneRef = useRef();
  const [topEmotions, setTopEmotions] = useState([]);

  const handleAudioChange = async (event) => {
    const file = event.target.files[0];
    if (file) {
      setAudioFile(file);
      setLoading(true);

      const formData = new FormData();
      formData.append("file", file);

      try {
        const response = await fetch("http://localhost:5001/upload-audio", {
          method: "POST",
          body: formData,
        });

        const result = await response.json();
        if (result.status === "success") {
          setSceneKey((prev) => prev + 1);
          loadTopEmotions(); // Refresh emotion summary
        } else {
          alert("Upload failed. Try again.");
        }
      } catch (error) {
        console.error("Upload error:", error);
        alert("Server error occurred.");
      } finally {
        setLoading(false);
      }
    }
  };

  const handleDeleteAudio = () => setAudioFile(null);
  const handleExportMesh = () => sceneRef.current?.exportSTL();

  const loadTopEmotions = async () => {
    try {
      const response = await fetch("data/top2_emotion_summary.csv");
      const text = await response.text();
      const parsed = Papa.parse(text, { header: true });
      const filtered = parsed.data.filter(row => row.emotion);
      const top2 = filtered.slice(0, 2).map(row => row.emotion);
      setTopEmotions(top2);
    } catch (err) {
      console.error("Failed to load emotion summary:", err);
    }
  };

  useEffect(() => {
    loadTopEmotions(); // Initial load
  }, []);

  return (
    <div className="lamp-container">
      {loading && (
        <div className="loading-overlay">
          <div className="loading-spinner" />
          <p>Analyzing your audio...</p>
        </div>
      )}

      <header className="lamp-header">
        <div className="lamp-logo">LUMINOTE</div>
        <div className="lamp-meta">
          <div className="meta-item">
            <span>LAMP GENERATION FROM SOUND</span>
          </div>
          <div className="meta-item">
            <span>DESIGNED BY KIDA HUANG AND SIJIA MA @HARVARD GSD</span>
          </div>
        </div>
      </header>

      <div className="lamp-body">
        {/* Left */}
        <div className="lamp-left">
          {/* Step 1 */}
          <div className="content-container01">
            <h2 className="reveal-heading">Transform Sound into Lamp Design</h2>
            <p>Luminote analyzes your voice or music to generate unique lamp forms</p>
          </div>

          <div className="content-container">
            <div className="step-wrapper">
              <div className="step-box-group">
                <div className="step-box first" />
                <div className="step-box faded" />
                <div className="step-box faded" />
              </div>
              <span className="step-caption">STEP 1</span>
            </div>

            <p>Upload your audio clip (≤ 10 minutes)</p>
            <label className="upload-box">
              <input
                type="file"
                accept="audio/*"
                onChange={handleAudioChange}
                style={{ display: "none" }}
              />
              <svg className="upload-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white" width="1rem" height="1rem">
                <path d="M0 0h24v24H0z" fill="none"/>
                <path d="M5 20h14v-2H5v2zm7-18l-7 7h4v6h6v-6h4l-7-7z"/>
              </svg>
              <span>Upload an Audio Clip</span>
            </label>

            {audioFile && (
              <div className="uploaded-file">
                <span>{audioFile.name}</span>
                <button className="delete-button" onClick={handleDeleteAudio}>
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white" width="1rem" height="1rem">
                    <path d="M0 0h24v24H0z" fill="none"/>
                    <path d="M16 9v10H8V9h8m-1.5-6h-5l-1 1H5v2h14V4h-4.5l-1-1z"/>
                  </svg>
                </button>
              </div>
            )}
          </div>

          {/* Step 2 */}
          <div className="content-container">
            <div className="step-wrapper">
              <div className="step-box-group">
                <div className="step-box first" />
                <div className="step-box first" />
                <div className="step-box faded" />
              </div>
              <span className="step-caption">STEP 2</span>
            </div>

            <p>Ready to save and export your design?</p>
            <button className="export-button" onClick={handleExportMesh}>
              Download My Design
            </button>
          </div>
        </div>

        {/* Center */}
        <div className="lamp-center">
          <Scene
            ref={sceneRef}
            key={sceneKey}
            csvPath="data/top2_emotion_summary.csv"
            amplitudeCsvPath="data/summary_per_segment.csv"
            emotionCurvesPath="emotions/emotion_curves.json"
          />
        </div>

        {/* Right */}
        <div className="lamp-right">
          <div className="content-container01">
            <div className="step-wrapper">
            <div className="step-box first"></div>
              <span> Base Shape Visualization</span>
            </div>
            <div className="step-wrapper">
            <div className="step-box"></div>

            {topEmotions.length === 2 && (
              <p>
                The audio transitions from <strong>{topEmotions[0]}</strong> to <strong>{topEmotions[1]}</strong>
              </p>
            )}
              </div>

            <div
              style={{
                width: "100%",
                height: "220px",
                marginTop: "12px",
                borderRadius: "12px",
                overflow: "hidden",
                background: "#1a1a1a"
              }}
            >
              <EmotionCurveMorph
                key={sceneKey}
                emotionCurvesPath="emotions/emotion_curves.json"
                top2CsvPath="data/top2_emotion_summary.csv"
              />
            </div>
          </div>

          <div className="content-container01">
            <div className="step-wrapper">
            <div className="step-box first"></div>
              <span> Texture Visualization</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LampCreation;
