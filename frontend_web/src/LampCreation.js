import React, { useRef, useEffect, useState } from "react";
import Scene from "./mesh_deformation";

const LampCreation = () => {
  const cloudRef = useRef();
  const [csvPath, setCsvPath] = useState("data/valence_arousal_timeline-angry.csv");

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
    `;
    document.head.appendChild(styleSheet);
    return () => {
      document.head.removeChild(styleSheet);
    };
  }, []);

  const handleUploadAudio = (e) => {
    const file = e.target.files[0];
    if (file) {
      console.log("🎵 Uploaded audio file:", file.name);
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
        <Scene ref={cloudRef} csvPath={csvPath} />
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
