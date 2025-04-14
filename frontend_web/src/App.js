import React from "react";
import "./App.css";
import Scene from "./mesh_deformation"; // 👈 make sure path is correct

function App() {
  return (
    <div className="App">
      <header className="header">
        <h1>Mesh Deformation Test</h1>
      </header>
      <div className="viewer-container">
        <Scene />
      </div>
    </div>
  );
}

export default App;
