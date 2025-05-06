import React, { useState, useRef, useEffect } from "react";
import "./LampCreation.css";
import Scene from "./mesh_deformation";
import EmotionCurveMorph from "./EmotionCurveMorph";
import Papa from "papaparse";
import VectorSpaceVisualization from "./components/VectorSpaceVisualization";
// Import the configuration
import { BACKEND_URL, TEXTURE_PATHS, getFullBackendPath } from "./config";

const LampCreation = () => {
  const [audioFile, setAudioFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [sceneKey, setSceneKey] = useState(0);
  const sceneRef = useRef();
  const [topEmotions, setTopEmotions] = useState([]);
  const [errorMessage, setErrorMessage] = useState('');
  const [resultPaths, setResultPaths] = useState({}); // Store paths from backend
  const [textureEnabled, setTextureEnabled] = useState(true); // Add texture toggle state
  const [currentTextureInfo, setCurrentTextureInfo] = useState(null); // Store full texture info
  const audioRef = useRef(null);
  const [showScrollIndicator, setShowScrollIndicator] = useState(true);
  
  // Use configuration for backend URL instead of hardcoding
  // const backendUrl = "http://localhost:5001";

  // Add scroll event listener to hide indicator after user scrolls
  useEffect(() => {
    const handleScroll = () => {
      if (window.scrollY > 100) {
        setShowScrollIndicator(false);
      } else {
        setShowScrollIndicator(true);
      }
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const handleAudioChange = async (event) => {
    const file = event.target.files[0];
    if (file) {
      setAudioFile(file);
      setLoading(true);
      setErrorMessage('');
      setResultPaths({}); // Clear previous results

      const formData = new FormData();
      formData.append("file", file);

      try {
        // Updated to use config BACKEND_URL
        const response = await fetch(`${BACKEND_URL}/analyze`, {
          method: "POST",
          body: formData,
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Analysis request failed: ${response.status} - ${errorText}`);
        }

        const result = await response.json();
        
        if (result.error) {
          setErrorMessage(result.error || "Analysis failed. Check backend logs.");
          console.error("Analysis error details:", result);
        } else {
          console.log("Analysis successful, paths received:", result);
          setResultPaths(result); // Store the received paths
          // Increment sceneKey to force re-render
          setSceneKey((prev) => prev + 1);
          // Explicitly start the reveal animation
          setTimeout(() => {
            if (sceneRef.current) {
              console.log("Starting reveal animation");
              sceneRef.current.startRevealAnimation();
            }
          }, 100);
          // Load top emotions using the new paths and getFullBackendPath helper
          if (result.top2SummaryPath) {
              loadTopEmotions(getFullBackendPath(result.top2SummaryPath));
          }
        }
      } catch (error) {
        console.error("Upload/Analysis error:", error);
        setErrorMessage(`Server/Analysis error: ${error.message}`);
      } finally {
        setLoading(false);
      }
    }
  };

  const handleDeleteAudio = () => {
      setAudioFile(null);
      setResultPaths({}); // Clear results when audio is deleted
      setSceneKey(prev => prev + 1); // Force scene re-render to default state
  };
  
  const handleExportMesh = () => sceneRef.current?.exportSTL();

  // Add texture toggle handler
  const handleToggleTexture = () => {
    setTextureEnabled(!textureEnabled);
    // Call the toggle method on the 3D scene
    if (sceneRef.current?.toggleTextures) {
      sceneRef.current.toggleTextures();
    }
  };

  const loadTopEmotions = async (url) => {
    if (!url) {
      console.warn("loadTopEmotions called without a valid URL");
      setTopEmotions([]);
      setCurrentTextureInfo(null);
      return;
    }
    try {
      const response = await fetch(url);
      if (!response.ok) {
         throw new Error(`Failed to load top emotions: ${response.status}`);
      }
      const text = await response.text();
      console.log("Loaded top emotions data:", text.slice(0, 100));
      const parsed = Papa.parse(text, { header: true });
      const filtered = parsed.data.filter(row => row.emotion);
      const top2 = filtered.slice(0, 2).map(row => row.emotion);
      setTopEmotions(top2);
      
      // Set current texture info based on quadrant
      if (filtered.length > 0) {
        const valence = parseFloat(filtered[0].valence || 0); // Use valence, not valence_normalized
        const arousal = parseFloat(filtered[0].arousal || 0); // Use arousal, not arousal_normalized
        const quadrant = valence >= 0 
          ? (arousal >= 0 ? "high_high" : "high_low")
          : (arousal >= 0 ? "low_high" : "low_low");
        setCurrentTextureInfo({ filename: quadrant });
      }
    } catch (err) {
      console.error("Failed to load emotion summary:", err);
      setErrorMessage(`Failed to load visualization data: ${err.message}`);
      setTopEmotions([]); // Clear emotions on error
      setCurrentTextureInfo(null);
    }
  };

  // Handle texture update from the mesh component
  const handleTextureUpdate = (textureInfo) => {
    if (textureInfo && textureInfo !== currentTextureInfo) {
      console.log("Texture update:", textureInfo);
      setCurrentTextureInfo(textureInfo);
    }
  };

  // Use the getFullBackendPath utility from config
  const top2Path = getFullBackendPath(resultPaths.top2SummaryPath);
  const amplitudePath = getFullBackendPath(resultPaths.arousalTrackPath); // Use arousal for amplitude
  const curvesPath = getFullBackendPath(resultPaths.emotionCurvesPath);
  // Use the texture path from config
  const classificationPath = TEXTURE_PATHS.fullClassificationPath;

  return (
    <div className="lamp-container">
      {loading && (
        <div className="loading-overlay">
          <div className="loading-spinner" />
          <p>Analyzing your audio...</p>
        </div>
      )}

      {/* Scroll Indicator */}
      {showScrollIndicator && (
        <div className="scroll-indicator" onClick={() => {
          window.scrollTo({
            top: window.innerHeight,
            behavior: 'smooth'
          });
          setShowScrollIndicator(false);
        }}></div>
      )}

      {errorMessage && (
        <div className="error-message" style={{
          position: 'fixed', 
          top: '20px', 
          right: '20px',
          background: 'rgba(255, 0, 0, 0.8)',
          color: 'white',
          padding: '10px',
          borderRadius: '5px',
          zIndex: 1000,
          maxWidth: '300px'
        }}>
          <p>{errorMessage}</p>
          <button 
            style={{background: 'transparent', border: 'none', color: 'white', cursor: 'pointer'}}
            onClick={() => setErrorMessage('')}
          >
            ✕
          </button>
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

            {audioFile && (
              <div className="audio-player" style={{ marginTop: "15px", width: "100%" }}>
                <audio 
                  ref={audioRef}
                  controls 
                  src={URL.createObjectURL(audioFile)}
                  style={{ width: "100%" }}
                />
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
            <button className="export-button" onClick={handleExportMesh} disabled={!resultPaths.top2SummaryPath}>
              Download My Design
            </button>
          </div>
        </div>

        {/* Center */}
        <div className="lamp-center">
          <Scene
            ref={sceneRef}
            key={sceneKey}
            // Pass specific paths needed by components
            top2CsvPath={top2Path} 
            amplitudeCsvPath={amplitudePath} // For waves/amplitude visual effect if needed
            textureClassificationCsvPath={classificationPath} // For texture database
            emotionCurvesPath={curvesPath} // For shape morph
            onTextureUpdate={handleTextureUpdate}
          />
        </div>

        {/* Right */}
        <div className="lamp-right">
          <div className="content-container01">
            <div className="step-wrapper">
            <div className="step-box first"></div>
              <span>Base Shape Visualization</span>
            </div>
            <div className="step-wrapper">
            <div className="step-box"></div>

              {topEmotions.length === 2 ? (
              <p>
                  Audio transitions: <strong>{topEmotions[0]}</strong> to <strong>{topEmotions[1]}</strong>
              </p>
              ) : (
                <p>Analyzing emotions...</p> 
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
              {curvesPath && top2Path ? (
              <EmotionCurveMorph
                key={sceneKey}
                  emotionCurvesPath={curvesPath}
                  top2CsvPath={top2Path}
              />
              ) : (
                 <div style={{display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', color: 'grey'}}>
                     {errorMessage ? <span style={{color: 'red'}}>Error</span> : <span>Waiting for analysis...</span>}
                 </div>
              )}
            </div>
          </div>

          <div className="content-container01">
            <div className="step-wrapper">
            <div className="step-box first"></div>
              <span>Texture Visualization</span>
            </div>
            
            {/* Texture Controls */}
            <div className="texture-controls" style={{ marginTop: "10px", display: "flex", flexDirection: "column", gap: "10px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span>Surface Texture</span>
                <button
                  onClick={handleToggleTexture}
                  style={{
                    background: textureEnabled ? "#4CAF50" : "#555",
                    color: "white",
                    border: "none",
                    borderRadius: "20px",
                    padding: "5px 15px",
                    cursor: "pointer",
                    transition: "background-color 0.3s"
                  }}
                  disabled={!resultPaths.top2SummaryPath}
                >
                  {textureEnabled ? "ON" : "OFF"}
                </button>
              </div>
              
              {/* Current Texture Display */}
              <div style={{ 
                background: "#1a1a1a", 
                padding: "10px", 
                borderRadius: "8px",
                marginTop: "5px" 
              }}>
                <p style={{ margin: "0 0 5px 0", fontSize: "14px" }}>Current Texture:</p>
                <div style={{ 
                  display: "flex",
                  alignItems: "center",
                  gap: "10px" 
                }}>
                  <div style={{ 
                    width: "50px",
                    height: "50px",
                    background: "#333",
                    borderRadius: "4px",
                    backgroundSize: "cover"
                  }}></div>
                  <span style={{ fontSize: "12px", wordBreak: 'break-all' }}>
                      {currentTextureInfo?.filename || "Loading..."}
                  </span>
                </div>
              </div>
              
              <p style={{ fontSize: "13px", color: "#888", marginTop: "5px" }}>
                Textures are automatically selected based on emotional analysis of the audio.
              </p>
            </div>
          </div>
        </div>
      </div>
      
      {/* New Section for Vector Space Visualization */}
      <div className="vector-space-section">
        <h2 className="vector-space-title">Texture Emotion Space</h2>
        <div style={{ 
          fontSize: "14px", 
          color: "#aaa", 
          maxWidth: "800px", 
          margin: "0 auto 20px auto", 
          textAlign: "center" 
        }}>
          Explore how different textures map to emotional states based on valence (positive/negative) and arousal (energetic/calm)
        </div>
        <div className="vector-space-wrapper">
          <VectorSpaceVisualization />
        </div>
      </div>
    </div>
  );
};

export default LampCreation;
