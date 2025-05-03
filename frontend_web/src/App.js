// App.js
import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import LampCreation from "./LampCreation";

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
