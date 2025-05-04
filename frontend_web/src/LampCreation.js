import React, { useState } from "react";
import "./LampCreation.css";
import Scene from "./mesh_deformation";
import EmotionCurveMorph from "./EmotionCurveMorph";
import { Canvas } from "@react-three/fiber";

const LampCreation = () => {
  const [audioFile, setAudioFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [sceneKey, setSceneKey] = useState(0); // Refresh Scene
  const [currentEmotion, setCurrentEmotion] = useState("neutral");
  const [testMode, setTestMode] = useState(false); // Add test mode state

  const handleAudioChange = async (event) => {
    const file = event.target.files[0];
    if (file) {
      setAudioFile(file);
      setLoading(true);

      const formData = new FormData();
      formData.append("audioFile", file);

      try {
        const response = await fetch("http://localhost:3001/api/process-audio", {
          method: "POST",
          body: formData,
        });

        const result = await response.json();
        if (result.success) {
          setSceneKey((prev) => prev + 1);
          if (result.overallEmotion) {
            setCurrentEmotion(result.overallEmotion);
          }
        } else {
          console.error("Processing failed:", result.error);
          alert("Failed to process audio: " + (result.error || "Unknown error"));
        }
      } catch (error) {
        console.error("Upload error:", error);
        alert("Server error: Please ensure the backend server is running on port 3001");
      } finally {
        setLoading(false);
      }
    }
  };

  const handleDeleteAudio = () => {
    setAudioFile(null);
  };
  
  const handleEmotionChange = (emotion) => {
    setCurrentEmotion(emotion);
  };
  
  // Toggle test mode function
  const toggleTestMode = () => {
    setTestMode(!testMode);
    // Reset key to force re-render
    setSceneKey(prev => prev + 1);
  };

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
            <input type="checkbox" />
            <span>LAMP GENERATION FROM SOUND</span>
          </div>
          <div className="meta-item">
            <input 
              type="checkbox" 
              checked={testMode}
              onChange={toggleTestMode}
            />
            <span>TEST MODE (CYLINDER WITH DEFAULT TEXTURES)</span>
          </div>
        </div>
      </header>

      <div className="lamp-body">
        {/* Left Panel */}
        <div className="lamp-left">
          <div className="content-container01">
            <h2 className="reveal-heading">Transform Sound into Lamp Design</h2>
            <p>
              Luminote is a lamp generation platform that analyzes audio and
              converts it into expressive lamp forms.
            </p>
          </div>

          <div className="content-container">
            <div className="step-wrapper">
              <div className="step-box-group">
                <div className="step-box first"></div>
                <div className="step-box faded"></div>
                <div className="step-box faded"></div>
              </div>
              <span className="step-caption">STEP 1</span>
            </div>

            <p>
              Upload a piece of your favorite audio (we recommend ≤ 10 minutes)
            </p>

            <label className="upload-box">
              <input
                type="file"
                accept="audio/*"
                onChange={handleAudioChange}
                style={{ display: "none" }}
              />
              <svg
                className="upload-icon"
                xmlns="http://www.w3.org/2000/svg"
                height="1rem"
                viewBox="0 0 24 24"
                width="1rem"
                fill="white"
              >
                <path d="M0 0h24v24H0z" fill="none" />
                <path d="M5 20h14v-2H5v2zm7-18l-7 7h4v6h6v-6h4l-7-7z" />
              </svg>
              <span>Upload an Audio Clip</span>
            </label>

            {audioFile && (
              <div className="uploaded-file">
                <span>{audioFile.name}</span>
                <button className="delete-button" onClick={handleDeleteAudio}>
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    height="1rem"
                    viewBox="0 0 24 24"
                    width="1rem"
                    fill="white"
                  >
                    <path d="M0 0h24v24H0z" fill="none" />
                    <path d="M16 9v10H8V9h8m-1.5-6h-5l-1 1H5v2h14V4h-4.5l-1-1z" />
                  </svg>
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Center Mesh Viewer */}
        <div className="lamp-center">
          <Scene
            key={sceneKey}
            csvPath="data/top2_emotion_summary.csv"
            amplitudeCsvPath="data/summary_per_segment.csv"
            emotionCurvesPath="emotions/emotion_curves.json"
            onEmotionChange={handleEmotionChange}
            testMode={testMode}
          />
        </div>

        {/* Right Panel */}
        <div className="lamp-right">
          <div className="content-container01">
            <span>☐ Emotion Data</span>
            <div>Base Shape Design</div>
            <div>Detected Emotion: {currentEmotion}</div>
            <div>{testMode ? "TEST MODE ACTIVE" : "Normal Mode"}</div>
            <div
              style={{
                width: "100%",
                height: "200px",
                overflow: "hidden",
              }}
            >
              <Canvas camera={{ position: [0, 0, 30], fov: 40 }}>
                <EmotionCurveMorph emotionCurvesPath="emotions/emotion_curves.json" />
              </Canvas>
            </div>
          </div>

          <div className="section-block">
            <span>☐ Emotion Textures</span>
            <div>Final Shape</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LampCreation;
