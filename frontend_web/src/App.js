
// need to install: npm install react-router-dom
import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { Canvas } from "@react-three/fiber";
import LampCreation from "./LampCreation";
import './App.css';
// Import the new visualization component
import VectorSpaceVisualization from './components/VectorSpaceVisualization';
// Comment out or remove the old visualization component
// import InteractiveVAVisualization from './components/InteractiveVAVisualization';
import EmotionCurveMorph from "./EmotionCurveMorph";

function App() {
  return (
    <Router>
      <Routes>
        {/* Main Lamp Creation Route */}
        <Route path="/" element={<LampCreation />} />

        {/* Optional: 404 Fallback Route */}
        <Route path="*" element={<h2>404 – Page Not Found</h2>} />
      </Routes>
    </Router>
  );
}

export default App;


// function App() {
//   return (
//     <div style={{ width: "100vw", height: "100vh", background: "#000" }}>
//       <Canvas>
//         <EmotionCurveMorph emotionCurvesPath="emotions/emotion_curves.json" />
//       </Canvas>
//     </div>
//   );
// }

// export default App;
