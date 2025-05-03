import React, { useRef, useEffect, useState } from "react";
import Scene from "./mesh_deformation";

const LampCreation = () => {
  const cloudRef = useRef();
  const [csvPath, setCsvPath] = useState("/data/trumpbiden.csv");
  const [currentEmotion, setCurrentEmotion] = useState(null);
  const [currentPattern, setCurrentPattern] = useState(null);
  const [textureParams, setTextureParams] = useState(null);

  useEffect(() => {
    const styleSheet = document.createElement("style");
    styleSheet.innerText = `
      @keyframes fadeInUp {
        0% {
          opacity: 0;
          transform: translateY(10px);
          filter: blur(6px);
        }
        100% {
          opacity: 1;
          transform: translateY(0);
          filter: blur(0);
        }
      }

      .text-animate {
        animation: fadeInUp 1s ease-out forwards;
      }

      .button-outline {
        border: 1px solid #3B82F6;
        padding: 10px 20px;
        border-radius: 24px;
        background: transparent;
        color: #3B82F6;
        font-size: 16px;
        font-weight: 500;
        cursor: pointer;
        transition: background 0.2s ease;
      }

      .button-outline:hover {
        background: rgba(59, 130, 246, 0.1);
      }
      
      .emotion-tag {
        display: inline-block;
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 14px;
        font-weight: 500;
        margin-right: 8px;
        color: white;
      }
      
      .emotion-joy {
        background-color: #FFCC00;
      }
      
      .emotion-serene {
        background-color: #7AE7FF;
        color: #333;
      }
      
      .emotion-peaceful {
        background-color: #9EE5A1;
        color: #333;
      }
      
      .emotion-neutral {
        background-color: #DDDDDD;
        color: #333;
      }
      
      .emotion-sad {
        background-color: #3373CC;
      }
      
      .emotion-fearful {
        background-color: #8075CC;
      }
      
      .emotion-angry {
        background-color: #FF3333;
      }
      
      .emotion-surprised {
        background-color: #FF66CC;
      }
      
      .emotion-disgusted {
        background-color: #669933;
      }
    `;
    document.head.appendChild(styleSheet);
    
    // Load texture parameters
    fetch("/texture_keys.json")
      .then(res => res.json())
      .then(params => {
        setTextureParams(params);
      })
      .catch(error => {
        console.error("Error loading texture parameters:", error);
      });
      
    return () => {
      document.head.removeChild(styleSheet);
    };
  }, []);

  // Method to receive updates from the 3D mesh component
  const handleEmotionUpdate = (emotion) => {
    setCurrentEmotion(emotion);
    if (textureParams && textureParams[emotion]) {
      setCurrentPattern(textureParams[emotion].texturePattern);
    }
  };

  const handleUploadAudio = (e) => {
    const file = e.target.files[0];
    if (file) {
      console.log("🎵 Uploading audio file:", file.name);
      
      // Create a FormData object to send the file
      const formData = new FormData();
      formData.append('audioFile', file);
      
      // Show loading state
      setCurrentEmotion("processing");
      setCurrentPattern("Analyzing audio and generating textures...");
      
      // Send the audio file to the backend for processing
      fetch('/api/process-audio', {
        method: 'POST',
        body: formData,
      })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          console.log("✅ Audio processed successfully:", data);
          setCsvPath(data.csvPath + `?t=${Date.now()}`); // Add timestamp to prevent caching
          setCurrentEmotion(data.overallEmotion);
          if (textureParams && textureParams[data.overallEmotion]) {
            setCurrentPattern(textureParams[data.overallEmotion].texturePattern);
          }
        } else {
          console.error("❌ Error processing audio:", data.error);
          setCurrentEmotion("error");
          setCurrentPattern("Failed to process audio");
          // Fallback to a demo CSV
          setCsvPath("/data/valence_arousal_timeline-screams.csv");
        }
      })
      .catch(error => {
        console.error("❌ Error uploading audio:", error);
        setCurrentEmotion("error");
        setCurrentPattern("Failed to upload audio");
        // Fallback to a demo CSV
        setCsvPath("/data/valence_arousal_timeline-screams.csv");
      });
    }
  };

  const handlePrint = () => {
    if (cloudRef.current?.exportSTL) {
      cloudRef.current.exportSTL();
    } else {
      console.warn("⚠️ STL export not available.");
    }
  };

  return (
    <div className="relative w-screen h-screen overflow-hidden">
      {/* 3D Scene */}
      <div style={{ position: "absolute", inset: 0, zIndex: 0 }}>
        <Scene 
          ref={cloudRef} 
          csvPath={csvPath} 
          onEmotionChange={handleEmotionUpdate}
        />
      </div>

      {/* UI Overlay */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          zIndex: 10,
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "flex-start",
          paddingLeft: "60px",
          pointerEvents: "none",
        }}
      >
        <div className="text-animate" style={{ pointerEvents: "auto" }}>
          <h1
            style={{
              fontSize: "28px",
              fontWeight: "600",
              marginBottom: "16px",
              color: "#000",
            }}
          >
            Here Is Your Lamp Design
          </h1>
          
          {currentEmotion && (
            <div style={{ marginBottom: "16px" }}>
              <span className={`emotion-tag emotion-${currentEmotion.toLowerCase()}`}>
                {currentEmotion.charAt(0).toUpperCase() + currentEmotion.slice(1)}
              </span>
              {currentPattern && (
                <span style={{ fontSize: "14px", color: "#666" }}>
                  {currentPattern}
                </span>
              )}
            </div>
          )}

          <div
            style={{
              display: "flex",
              gap: "16px",
              alignItems: "center",
              marginTop: "16px",
            }}
          >
            <label className="button-outline" htmlFor="audio-upload" style={{ cursor: "pointer" }}>
              Upload Audio
            </label>
            <input
              id="audio-upload"
              type="file"
              accept="audio/*"
              style={{ display: "none" }}
              onChange={handleUploadAudio}
            />
            <button className="button-outline" onClick={handlePrint}>
              Print It Out
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LampCreation;
