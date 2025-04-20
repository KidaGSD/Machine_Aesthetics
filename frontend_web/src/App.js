
// need to install: npm install react-router-dom
import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import LandingPage from "./landingpage";
import LampCreation from "./LampCreation";

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/lampcreation" element={<LampCreation />} />
      </Routes>
    </Router>
  );
}

export default App;


// // need to install: npm install file-saver
// import React, { useRef, useState } from "react";
// import "./App.css";
// import ColorCloud from "./mesh_deformation";
// import LandingPage from "./landingpage";
// import { STLExporter } from "three/examples/jsm/exporters/STLExporter";
// import { saveAs } from "file-saver";

// function App() {
//   const fileInputRef = useRef();
//   const cloudRef = useRef();
//   const [selectedFile, setSelectedFile] = useState(null);
//   const csvPath = 'data/valence_arousal_timeline-angry.csv'; 
//   const [loading, setLoading] = useState(false);
//   const [showLanding, setShowLanding] = useState(false);

//   const handleFileChange = (event) => {
//     const file = event.target.files[0];
//     if (!file) return;

//     const allowedTypes = [
//       "audio/mpeg",
//       "audio/mp3",
//       "video/mp4",
//       "audio/wav"
//     ];
//     if (!allowedTypes.includes(file.type)) {
//       alert("Please upload a .mp3 or .mp4 file.");
//       return;
//     }

//     if (file.size > 10 * 1024 * 1024) {
//       alert("File must be under 10MB.");
//       return;
//     }

//     setSelectedFile(file);
//   };

//   const handleGenerate = async () => {
//     if (!selectedFile) {
//       alert("Please upload a file first.");
//       return;
//     }

//     setLoading(true);
//     const formData = new FormData();
//     formData.append("file", selectedFile);

//     try {
//       const res = await fetch("http://127.0.0.1:5000/process-audio", {
//         method: "POST",
//         body: formData,
//       });

//       if (res.ok) {
//         const data = await res.json();
//         const fullPath = `http://127.0.0.1:5000${data.csv_path}`;
//         console.log("✅ Audio processed. CSV Path:", fullPath);
//       } else {
//         alert("❌ Failed to process audio.");
//       }
//     } catch (err) {
//       console.error("Error:", err);
//       alert("❌ Backend not reachable.");
//     } finally {
//       setLoading(false);
//     }
//   };

//   const handleExport = () => {
//     if (!cloudRef.current || !cloudRef.current.getMesh) {
//       alert("Mesh not ready for export.");
//       return;
//     }

//     const mesh = cloudRef.current.getMesh();
//     const exporter = new STLExporter();
//     const stlString = exporter.parse(mesh);

//     const blob = new Blob([stlString], { type: 'text/plain' });
//     saveAs(blob, 'deformed_mesh.stl');
//   };

//   if (showLanding) {
//     return <LandingPage />;
//   }

//   return (
//     <div className="App">
//       <div className="background-scene">
//         <ColorCloud ref={cloudRef} csvPath={csvPath} />
//       </div>

//       <div className="foreground-ui">
//         <div
//           className="mesh-upload-frame"
//           style={{
//             display: "flex",
//             flexDirection: "column",
//             gap: "32px",
//             alignItems: "flex-start",
//             padding: "24px",
//             maxWidth: "480px",
//           }}
//         >
//           <div className="upload-bar" style={{ display: "flex", gap: "16px", alignItems: "center" }}>
//             <input
//               ref={fileInputRef}
//               id="file-upload"
//               type="file"
//               accept=".mp3, .mp4, audio/*, video/*"
//               onChange={handleFileChange}
//               style={{ display: "none" }}
//             />
//             <label
//               className="upload-label"
//               htmlFor="file-upload"
//               style={{
//                 padding: "10px 20px",
//                 borderRadius: "24px",
//                 border: "1px solid white",
//                 color: "white",
//                 background: "transparent",
//                 fontSize: "14px",
//                 cursor: "pointer",
//               }}
//             >
//               {selectedFile ? `📎 ${selectedFile.name}` : "Upload Audio/Video"}
//             </label>

//             <button
//               className="generate-btn"
//               onClick={handleGenerate}
//               style={{
//                 padding: "10px 20px",
//                 borderRadius: "24px",
//                 background: loading ? "#ccc" : "white",
//                 color: "black",
//                 border: "none",
//                 fontSize: "14px",
//                 fontWeight: "500",
//                 cursor: loading ? "not-allowed" : "pointer",
//               }}
//               disabled={loading}
//             >
//               {loading ? "Generating..." : "Generate"}
//             </button>
//           </div>

//           <button
//             onClick={handleExport}
//             style={{
//               padding: "10px 20px",
//               background: "#3B82F6",
//               color: "white",
//               borderRadius: "24px",
//               fontSize: "14px",
//               fontWeight: "500",
//               cursor: "pointer",
//             }}
//           >
//             Export Mesh as STL
//           </button>

//           <button
//             onClick={() => setShowLanding(true)}
//             style={{
//               marginTop: "24px",
//               padding: "10px 20px",
//               background: "#10B981",
//               color: "white",
//               borderRadius: "24px",
//               fontSize: "14px",
//               fontWeight: "500",
//               cursor: "pointer",
//             }}
//           >
//             View Landing Page
//           </button>
//         </div>
//       </div>
//     </div>
//   );
// }

// export default App;
