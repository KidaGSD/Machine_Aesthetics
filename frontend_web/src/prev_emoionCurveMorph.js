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
  const [emotionLabels, setEmotionLabels] = useState(["j", "s"]);

  useEffect(() => {
    const loadAll = async () => {
      try {
        const [csvText, json] = await Promise.all([
          fetch(`${top2CsvPath}?t=${Date.now()}`).then(res => res.text()),
          fetch(`${emotionCurvesPath}?t=${Date.now()}`).then(res => res.json())
        ]);

        const parsed = Papa.parse(csvText, { header: true });
        const rows = parsed.data.filter(r => r.emotion && r.emotion.length > 0);

        const emotionMap = {
          joy: "j", sadness: "s", anger: "a", fear: "f",
          surprise: "su", neutral: "c", disgust: "d"
        };

        const a = emotionMap[rows[0]?.emotion.trim().toLowerCase()] || "j";
        const b = emotionMap[rows[1]?.emotion.trim().toLowerCase()] || "s";

        setEmotionCurves(json);
        setEmotionLabels([a, b]);
      } catch (err) {
        console.error("Failed to load emotion morph data", err);
      }
    };

    loadAll();
  }, [emotionCurvesPath, top2CsvPath]);

  if (!emotionCurves) return null;

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