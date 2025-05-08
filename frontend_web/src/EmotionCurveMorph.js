import React, { useRef, useEffect, useState } from 'react';
import { OrbitControls } from '@react-three/drei';
import { Canvas, useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import Papa from 'papaparse';

const EmotionCurveMorphContent = ({ emotionCurves, emotionA, emotionB }) => {
  const groupRef = useRef();
  const [lines, setLines] = useState([]);
  // Animation state
  const [animationStage, setAnimationStage] = useState(0); // 0: top only, 1: top+bottom, 2: reveal lines
  const [linesRevealed, setLinesRevealed] = useState(0);
  const totalLinesRef = useRef(0);

  useEffect(() => {
    // Reset animation when emotions or curves change
    setAnimationStage(0);
    setLinesRevealed(0);
  }, [emotionA, emotionB, emotionCurves]);

  useEffect(() => {
    if (animationStage === 0) {
      const t = setTimeout(() => setAnimationStage(1), 800);
      return () => clearTimeout(t);
    } else if (animationStage === 1) {
      const t = setTimeout(() => setAnimationStage(2), 800);
      return () => clearTimeout(t);
    } else if (animationStage === 2 && linesRevealed < totalLinesRef.current) {
      const interval = setInterval(() => {
        setLinesRevealed(n => {
          if (n < totalLinesRef.current) return n + 1;
          clearInterval(interval);
          return n;
        });
      }, 30);
      return () => clearInterval(interval);
    }
  }, [animationStage, linesRevealed]);

  useEffect(() => {
    if (animationStage === 2 && linesRevealed === totalLinesRef.current) {
      // Wait 1 second, then restart the animation
      const t = setTimeout(() => {
        setAnimationStage(0);
        setLinesRevealed(0);
      }, 1000);
      return () => clearTimeout(t);
    }
  }, [animationStage, linesRevealed]);

  useEffect(() => {
    const rawA = emotionCurves[emotionA];
    const rawB = emotionCurves[emotionB];
    if (!rawA || !rawB) {
      return;
    }

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
    if (polygonArea(ptsA) * polygonArea(ptsB) < 0) {
      ptsB.reverse();
    }

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
    totalLinesRef.current = segments.length;

    // Outlines
    const topOutline = (
      <line key="top-outline" geometry={new THREE.BufferGeometry().setFromPoints([...top, top[0]])}>
        <lineBasicMaterial color="#88ccff" />
      </line>
    );
    const botOutline = (
      <line key="bot-outline" geometry={new THREE.BufferGeometry().setFromPoints([...bot, bot[0]])}>
        <lineBasicMaterial color="#ffccaa" />
      </line>
    );

    // Animation logic for staged reveal
    let displayLines = [];
    if (animationStage === 0) {
      displayLines = [topOutline];
    } else if (animationStage === 1) {
      displayLines = [topOutline, botOutline];
    } else if (animationStage === 2) {
      displayLines = [topOutline, botOutline, ...segments.slice(0, linesRevealed)];
    }
    setLines(displayLines);
  }, [emotionA, emotionB, emotionCurves, animationStage, linesRevealed]);

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
        // Check if paths are valid before attempting to fetch
        if (!emotionCurvesPath) {
          throw new Error("No emotion curves path provided");
        }
        if (!top2CsvPath) {
          throw new Error("No top2 CSV path provided");
        }
        
        console.log("Loading emotion curves from:", emotionCurvesPath);
        console.log("Loading top2 emotions from:", top2CsvPath);
        
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
        const json = await jsonResponse.json();

        const parsed = Papa.parse(csvText, { header: true });
        const rows = parsed.data.filter(r => r.emotion && r.emotion.length > 0);

        const emotionMap = {
          joy: "j", sad: "s", angry: "a", fear: "f",
          surprise: "su", neutral: "c", disgust: "d",
          peaceful: "c", serene: "se", calm: "c",
          happy: "j", sadness: "s", anger: "a", fearful: "f",
          surprised: "su", disgusted: "d"
        };

        // Safely get emotions, defaulting if needed
        const emotionA = rows[0]?.emotion?.trim().toLowerCase() || "neutral";
        const emotionB = rows[1]?.emotion?.trim().toLowerCase() || "joy";

        const labelA = emotionMap[emotionA] || "c";
        const labelB = emotionMap[emotionB] || "j";

        // Verify that the required curves exist in the loaded JSON
        if (!json || typeof json !== 'object' || !json[labelA] || !json[labelB]) {
          console.warn(`Required emotion curves (${labelA}, ${labelB}) not found in JSON. Using defaults.`);
          console.log("Available curves in JSON:", Object.keys(json || {}));
          console.log("Requested curves:", {
            curveA: json?.[labelA],
            curveB: json?.[labelB]
          });
          // Use default curves if required ones are missing
          const defaultCurves = {
            "j": Array.from({length: 36}, (_, i) => [Math.cos(i/36*Math.PI*2)*20, Math.sin(i/36*Math.PI*2)*20]),
            "s": Array.from({length: 36}, (_, i) => [Math.cos(i/36*Math.PI*2)*15, Math.sin(i/36*Math.PI*2)*15]),
            "c": Array.from({length: 36}, (_, i) => [Math.cos(i/36*Math.PI*2)*18, Math.sin(i/36*Math.PI*2)*18])
          };
          console.log("Using default curves:", defaultCurves);
          setEmotionCurves(defaultCurves);
          setEmotionLabels(["c", "j"]); // Reset labels to match default curves
        } else {
          console.log("Using loaded curves from JSON");
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
        console.log("Using default curves due to error:", defaultCurves);
        setEmotionCurves(defaultCurves);
        setEmotionLabels(["c", "j"]);
      }
    };

    // Only load if paths are provided
    if (emotionCurvesPath && top2CsvPath) {
        loadAll();
    } else {
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
    <Canvas camera={{ position: [0, 0, 70], fov: 50 }} 
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
