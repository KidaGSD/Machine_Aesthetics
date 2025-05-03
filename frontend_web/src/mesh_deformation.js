import React, {
  useRef,
  useEffect,
  useState,
  useImperativeHandle,
  forwardRef,
} from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import * as THREE from "three";
import Papa from "papaparse";
import { STLExporter } from "three/examples/jsm/exporters/STLExporter";
import { frostedGlassShader } from "./shaders/frostedGlassShader";

const ColorCloud = forwardRef(({ csvPath, amplitudeCsvPath, emotionCurvesPath }, ref) => {
  const groupRef = useRef();
  const meshRef = useRef();
  const [dataRows, setDataRows] = useState([]);
  const [amplitudes, setAmplitudes] = useState([]);
  const [emotionCurves, setEmotionCurves] = useState(null);
  const [generatedGeometry, setGeneratedGeometry] = useState(null);
  const [revealProgress, setRevealProgress] = useState(0);

  const waveDivs = 40;
  const waveCount = 5;
  const heightPerLayer = 40;
  const amplitudeFactor = 10;

  useImperativeHandle(ref, () => ({
    exportSTL: () => {
      if (!groupRef.current) return;
      const exporter = new STLExporter();
      const stlString = exporter.parse(groupRef.current);
      const blob = new Blob([stlString], { type: "text/plain" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "mesh_debug.stl";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    },
    startRevealAnimation: () => {
      setRevealProgress(0);
    }
  }));

  useFrame(() => {
    // Slow rotation
    if (meshRef.current) {
      meshRef.current.rotation.y += 0.002; // Rotate around Y-axis
    }
  
    // Reveal animation logic
    if (revealProgress < 1.0) {
      setRevealProgress((prev) => Math.min(prev + 0.003, 1.0));
    }
  });
  

  const fetchWithNoCache = (url) => `${url}?t=${Date.now()}`;

  useEffect(() => {
    if (!csvPath) return;
    fetch(fetchWithNoCache(csvPath))
      .then((res) => res.text())
      .then((text) => {
        const cleanText = text.replace(/^﻿/, '');
        const parsed = Papa.parse(cleanText, {
          header: true,
          dynamicTyping: true,
          skipEmptyLines: true,
        });
        const cleaned = parsed.data.filter(row => row.emotion);
        setDataRows(cleaned);
      });
  }, [csvPath]);

  useEffect(() => {
    if (!amplitudeCsvPath) return;
    fetch(fetchWithNoCache(amplitudeCsvPath))
      .then((res) => res.text())
      .then((text) => {
        const parsed = Papa.parse(text, {
          header: true,
          dynamicTyping: true,
          skipEmptyLines: true,
        });
        const amps = parsed.data.map(row => parseFloat(row.arousal ?? 0));
        setAmplitudes(amps);
      });
  }, [amplitudeCsvPath]);

  useEffect(() => {
    if (!emotionCurvesPath) return;
    fetch(fetchWithNoCache(emotionCurvesPath))
      .then((res) => res.json())
      .then((data) => setEmotionCurves(data));
  }, [emotionCurvesPath]);

  useEffect(() => {
    if (!dataRows.length || !amplitudes.length || !emotionCurves) return;

    const emotionMap = {
      joy: "j", sadness: "s", anger: "a", fear: "f",
      surprise: "su", neutral: "c", disgust: "d"
    };

    const labelA = emotionMap[dataRows[0].emotion?.trim().toLowerCase()];
    const labelB = emotionMap[dataRows[1].emotion?.trim().toLowerCase()];
    const rawA = emotionCurves[labelA]?.map(([x, y]) => new THREE.Vector3(x, 0, y));
    const rawB = emotionCurves[labelB]?.map(([x, y]) => new THREE.Vector3(x, 0, y));
    if (!rawA || !rawB) return;

    const centroid = pts => pts.reduce((sum, p) => sum.add(p), new THREE.Vector3()).divideScalar(pts.length);
    const centerA = centroid(rawA);
    const centerB = centroid(rawB);
    const ptsA = rawA.map(p => p.clone().sub(centerA));
    const ptsB = rawB.map(p => p.clone().sub(centerB));

    const alignedB = (() => {
      let best = ptsB, min = Infinity;
      for (let i = 0; i < ptsB.length; i++) {
        const rotated = [...ptsB.slice(i), ...ptsB.slice(0, i)];
        const dist = ptsA.reduce((sum, pt, idx) => sum + pt.distanceTo(rotated[idx]), 0);
        if (dist < min) {
          min = dist;
          best = rotated;
        }
      }
      return best;
    })();

    const segments = ptsA.length;
    const waveCurves = [];

    for (let i = 0; i < segments; i++) {
      const curvePoints = [];
      const amp = amplitudes[i % amplitudes.length] * amplitudeFactor;
      for (let j = 0; j < waveDivs; j++) {
        const t = j / (waveDivs - 1);
        const revealT = Math.min(1, revealProgress * 1.2); // reveal stretch

        const waveOffset = Math.sin(t * Math.PI * waveCount + i * 0.3) * 3;

        const top = ptsA[i].clone().add(new THREE.Vector3(0, heightPerLayer / 2, 0));
        const bottom = alignedB[i].clone().add(new THREE.Vector3(0, -heightPerLayer / 2, 0));
        const base = new THREE.Vector3().lerpVectors(top, bottom, t);
        const anchor = new THREE.Vector3().lerpVectors(top, bottom, t);

        let radial = base.clone().sub(anchor).setY(0);
        if (radial.length() < 0.001) radial = new THREE.Vector3(1, 0, 0);
        else radial.normalize();

        const waved = base.clone();
        if (t < revealT && t > 0.05) {
          waved.add(radial.multiplyScalar(waveOffset));
        }
        curvePoints.push(waved);
      }
      waveCurves.push(curvePoints);
    }

    const vertices = [];
    const indices = [];
    for (let i = 0; i < segments; i++) {
      const next = (i + 1) % segments;
      for (let j = 0; j < waveDivs - 1; j++) {
        const a = waveCurves[i][j];
        const b = waveCurves[next][j];
        const c = waveCurves[next][j + 1];
        const d = waveCurves[i][j + 1];
        const baseIdx = vertices.length / 3;
        vertices.push(a.x, a.y, a.z, b.x, b.y, b.z, c.x, c.y, c.z, d.x, d.y, d.z);
        indices.push(baseIdx, baseIdx + 1, baseIdx + 2, baseIdx, baseIdx + 2, baseIdx + 3);
      }
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
    geometry.setIndex(indices);
    geometry.computeVertexNormals();
    setGeneratedGeometry(geometry);
  }, [dataRows, amplitudes, emotionCurves, revealProgress]);

  return (
    <>
      <ambientLight intensity={0.6} />
      <pointLight position={[0, 0, 0]} intensity={100} color={new THREE.Color(1.0, 0.85, 0.3)} distance={100} decay={2} />
      <group ref={groupRef}>
        {generatedGeometry && (
          <mesh ref={meshRef} geometry={generatedGeometry} material={frostedGlassShader} />
        )}
      </group>
    </>
  );
});

const Scene = forwardRef(({ csvPath, amplitudeCsvPath, emotionCurvesPath }, ref) => {
  return (
    <Canvas camera={{ position: [0, 50, 100], fov: 45 }} style={{ background: "#000000", width: "100vw", height: "100vh" }}>
      <OrbitControls />
      <ColorCloud
        ref={ref}
        csvPath={csvPath}
        amplitudeCsvPath={amplitudeCsvPath}
        emotionCurvesPath={emotionCurvesPath}
      />
    </Canvas>
  );
});

export default Scene;
