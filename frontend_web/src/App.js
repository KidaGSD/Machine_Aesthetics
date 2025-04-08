import React from "react";
import "./App.css";
import MeshViewer from "./MeshViewer";

function App() {
  return (
    <div className="App">
      <header className="header">
        <h1>Shape Viewer</h1>
        <button className="cta-button">Refresh Mesh</button>
      </header>
      <div className="viewer-container">
        <MeshViewer />
      </div>
    </div>
  );
}

export default App;
