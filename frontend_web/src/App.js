// need to install: npm install react-router-dom
// App.js
import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import LampCreation from "./LampCreation";
import './App.css';
// Import the new visualization component
import VectorSpaceVisualization from './components/VectorSpaceVisualization';
// Comment out or remove the old visualization component
// import InteractiveVAVisualization from './components/InteractiveVAVisualization';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<LampCreation />} />
        <Route path="*" element={<h2>404 – Page Not Found</h2>} />
      </Routes>
    </Router>
  );
}

export default App;
