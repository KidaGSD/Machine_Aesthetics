import React, { useRef, useEffect, useState } from 'react';
import { OrbitControls } from '@react-three/drei';
import { Canvas, useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import Papa from 'papaparse';

const EmotionCurveMorphContent = ({ emotionCurves, emotionA, emotionB }) => {
  const groupRef = useRef();
  const [lines, setLines] = useState([]);

  useEffect(() => {
    const rawA = emotionCurves[emotionA];
    const rawB = emotionCurves[emotionB];
    if (!rawA || !rawB) return;

    let ptsA = rawA.map(([x, y]) => new THREE.Vector2(x, y));
    let ptsB = rawB.map(([x, y]) => new THREE.Vector2(x, y));

    const center = pts => {
      const avg = pts.reduce((acc, p) => acc.add(p), new THREE.Vector2(0, 0)).divideScalar(pts.length);
      return pts.map(p => p.clone().sub(avg));
    };
    ptsA = center(ptsA);
    ptsB = center(ptsB);

    const polygonArea = pts => pts.reduce((a, p, i) => {
      const next = pts[(i + 1) % pts.length];
      return a + (p.x * next.y - next.x * p.y);
    }, 0) / 2;
    if (polygonArea(ptsA) * polygonArea(ptsB) < 0) ptsB.reverse();

    const rotateToMatch = (ref, target) => {
      let best = target;
      let minDist = Infinity;
      for (let s = 0; s < target.length; s++) {
        const rotated = [...target.slice(s), ...target.slice(0, s)];
        const dist = ref.reduce((sum, p, i) => sum + p.distanceTo(rotated[i]), 0);
        if (dist < minDist) {
          minDist = dist;
          best = rotated;
        }
      }
      return best;
    };
    ptsB = rotateToMatch(ptsA, ptsB);

    const top = ptsA.map(p => new THREE.Vector3(p.x, 10, p.y));
    const bot = ptsB.map(p => new THREE.Vector3(p.x, -10, p.y));

    const segments = [];
    for (let i = 0; i < top.length; i++) {
      const geom = new THREE.BufferGeometry().setFromPoints([top[i], bot[i]]);
      segments.push(
        <line key={`seg-${i}`} geometry={geom}>
          <lineBasicMaterial color="#ffffff" />
        </line>
      );
    }

    segments.push(
      <line key="top-outline" geometry={new THREE.BufferGeometry().setFromPoints([...top, top[0]])}>
        <lineBasicMaterial color="#88ccff" />
      </line>
    );
    segments.push(
      <line key="bot-outline" geometry={new THREE.BufferGeometry().setFromPoints([...bot, bot[0]])}>
        <lineBasicMaterial color="#ffccaa" />
      </line>
    );

    setLines(segments);
  }, [emotionA, emotionB, emotionCurves]);

  // 🔄 Add slow rotation animation
  useFrame(() => {
    if (groupRef.current) {
      groupRef.current.rotation.y += 0.002;
    }
  });

  return (
    <group ref={groupRef}>
      <ambientLight />
      <pointLight position={[0, 20, 20]} intensity={1} />
      {lines}
    </group>
  );
};

const EmotionCurveMorph = ({ emotionCurvesPath, top2CsvPath }) => {
  const [emotionCurves, setEmotionCurves] = useState(null);
  const [emotionLabels, setEmotionLabels] = useState(["c", "j"]); // Default to calm/joy
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadAll = async () => {
      setError(null); // Clear previous errors
      try {
        console.log("Fetching morph data:", top2CsvPath, emotionCurvesPath);
        const [csvResponse, jsonResponse] = await Promise.all([
          fetch(top2CsvPath),
          fetch(emotionCurvesPath)
        ]);

        // Check responses before processing
        if (!csvResponse.ok) {
          throw new Error(`Failed to load top2 CSV: ${csvResponse.status}`);
        }
        if (!jsonResponse.ok) {
          throw new Error(`Failed to load emotion curves JSON: ${jsonResponse.status}`);
        }

        const csvText = await csvResponse.text();
        const json = await jsonResponse.json(); // This might fail if response is not JSON

        const parsed = Papa.parse(csvText, { header: true });
        const rows = parsed.data.filter(r => r.emotion && r.emotion.length > 0);

        const emotionMap = {
          joy: "j", sadness: "s", anger: "a", fear: "f",
          surprise: "su", neutral: "c", disgust: "d",
          peaceful: "c", serene: "c", calm: "c" // Map variants to base
        };

        // Safely get emotions, defaulting if needed
        const emotionA = rows[0]?.emotion?.trim().toLowerCase() || "neutral";
        const emotionB = rows[1]?.emotion?.trim().toLowerCase() || "joy";

        const labelA = emotionMap[emotionA] || "c";
        const labelB = emotionMap[emotionB] || "j";
        
        // Verify that the required curves exist in the loaded JSON
        if (!json || typeof json !== 'object' || !json[labelA] || !json[labelB]) {
          console.warn(`Required emotion curves (${labelA}, ${labelB}) not found in JSON. Using defaults.`);
          // Use default curves if required ones are missing
          const defaultCurves = {
            "j": Array.from({length: 36}, (_, i) => [Math.cos(i/36*Math.PI*2)*20, Math.sin(i/36*Math.PI*2)*20]),
            "s": Array.from({length: 36}, (_, i) => [Math.cos(i/36*Math.PI*2)*15, Math.sin(i/36*Math.PI*2)*15]),
            "c": Array.from({length: 36}, (_, i) => [Math.cos(i/36*Math.PI*2)*18, Math.sin(i/36*Math.PI*2)*18])
          };
          setEmotionCurves(defaultCurves);
          setEmotionLabels(["c", "j"]); // Reset labels to match default curves
        } else {
          setEmotionCurves(json);
          setEmotionLabels([labelA, labelB]);
        }
        
      } catch (err) {
        console.error("Failed to load emotion morph data:", err);
        setError(`Error loading visualization data: ${err.message}`);
        // Set default curves on error
        const defaultCurves = {
            "j": Array.from({length: 36}, (_, i) => [Math.cos(i/36*Math.PI*2)*20, Math.sin(i/36*Math.PI*2)*20]),
            "s": Array.from({length: 36}, (_, i) => [Math.cos(i/36*Math.PI*2)*15, Math.sin(i/36*Math.PI*2)*15]),
            "c": Array.from({length: 36}, (_, i) => [Math.cos(i/36*Math.PI*2)*18, Math.sin(i/36*Math.PI*2)*18])
        };
        setEmotionCurves(defaultCurves);
        setEmotionLabels(["c", "j"]);
      }
    };

    // Only load if paths are provided
    if (emotionCurvesPath && top2CsvPath) {
        loadAll();
    } else {
        console.warn("EmotionCurveMorph: Missing required paths.");
        // Optionally set default curves immediately if paths are missing
        const defaultCurves = {
            "j": Array.from({length: 36}, (_, i) => [Math.cos(i/36*Math.PI*2)*20, Math.sin(i/36*Math.PI*2)*20]),
            "s": Array.from({length: 36}, (_, i) => [Math.cos(i/36*Math.PI*2)*15, Math.sin(i/36*Math.PI*2)*15]),
            "c": Array.from({length: 36}, (_, i) => [Math.cos(i/36*Math.PI*2)*18, Math.sin(i/36*Math.PI*2)*18])
        };
        setEmotionCurves(defaultCurves);
        setEmotionLabels(["c", "j"]);
    }
  }, [emotionCurvesPath, top2CsvPath]);

  // Display error message or loading state
  if (error) {
    return <div style={{ color: 'red', padding: '10px', background: '#222' }}>{error}</div>;
  }

  if (!emotionCurves) {
    // Show a simple loading indicator or placeholder
    return <div style={{ padding: '10px', background: '#111', color: 'grey' }}>Loading curves...</div>;
  }

  return (
    <Canvas camera={{ position: [0, 0, 80], fov: 50 }} 
    style={{ background: '#000000' }}>
      <EmotionCurveMorphContent
        emotionCurves={emotionCurves}
        emotionA={emotionLabels[0]}
        emotionB={emotionLabels[1]}
      />
      <OrbitControls />
    </Canvas>
  );
};

export default EmotionCurveMorph;
