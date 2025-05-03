// mesh_deformation.js — Fragment Shader Integration Version
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
import emotionGradientData from "./emotionGradientData";
import emotionColors from "./emotionColors";
import { emotionGradientShader } from "./shaders/emotionGradientShader"; // 🔄 NEW

const ColorCloud = forwardRef(({ csvPath, amplitudeCsvPath, emotionCurvesPath }, ref) => {
  const groupRef = useRef();
  const meshRef = useRef();
  const [dataRows, setDataRows] = useState([]);
  const [amplitudes, setAmplitudes] = useState([]);
  const [emotionCurves, setEmotionCurves] = useState(null);
  const [generatedGeometry, setGeneratedGeometry] = useState(null);
  const [revealProgress, setRevealProgress] = useState(0);

  const waveDivs = 200;
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
    if (meshRef.current) {
      meshRef.current.rotation.y += 0.002;
    }
    if (revealProgress < 1.0) {
      setRevealProgress((prev) => Math.min(prev + 0.003, 1.0));
    }
  });

  const fetchWithNoCache = (url) => `${url}?t=${Date.now()}`;

  useEffect(() => {
    if (!csvPath) return;
    fetch(fetchWithNoCache(csvPath))
      .then(res => res.text())
      .then(text => {
        const cleanText = text.replace(/^﻿/, '');
        const parsed = Papa.parse(cleanText, { header: true, dynamicTyping: true, skipEmptyLines: true });
        const cleaned = parsed.data.filter(row => row.emotion);
        setDataRows(cleaned);
      });
  }, [csvPath]);

  useEffect(() => {
    if (!amplitudeCsvPath) return;
    fetch(fetchWithNoCache(amplitudeCsvPath))
      .then(res => res.text())
      .then(text => {
        const parsed = Papa.parse(text, { header: true, dynamicTyping: true, skipEmptyLines: true });
        const amps = parsed.data.map(row => parseFloat(row.arousal ?? 0));
        setAmplitudes(amps);
      });
  }, [amplitudeCsvPath]);

  useEffect(() => {
    if (!emotionCurvesPath) return;
    fetch(fetchWithNoCache(emotionCurvesPath))
      .then(res => res.json())
      .then(data => setEmotionCurves(data));
  }, [emotionCurvesPath]);

  useEffect(() => {
    if (!dataRows.length || !amplitudes.length || !emotionCurves) return;

    const emotionMap = {
      joy: "j", sadness: "s", anger: "a", fear: "f",
      surprise: "su", neutral: "c", disgust: "d"
    };

    const bottomEmotion = dataRows[1].emotion?.trim().toLowerCase();
    const labelA = emotionMap[dataRows[0].emotion?.trim().toLowerCase()];
    const labelB = emotionMap[bottomEmotion];
    const rawA = emotionCurves[labelA]?.map(([x, y]) => new THREE.Vector3(x, 0, y));
    const rawB = emotionCurves[labelB]?.map(([x, y]) => new THREE.Vector3(x, 0, y));
    if (!rawA || !rawB) return;

    const centroid = pts => pts.reduce((sum, p) => sum.add(p), new THREE.Vector3()).divideScalar(pts.length);
    const centerA = centroid(rawA);
    const centerB = centroid(rawB);

    const valence = parseFloat(dataRows[0]?.valence ?? 0);
    const valenceScale = 1 + valence * 0.5;

    const ptsA = rawA.map(p => {
      const centered = p.clone().sub(centerA);
      return new THREE.Vector3(centered.x * valenceScale, centered.y, centered.z * valenceScale);
    });

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
      for (let j = 0; j < waveDivs; j++) {
        const t = j / (waveDivs - 1);
        const revealT = Math.min(1, revealProgress * 1.2);
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

    const segmentCount = emotionGradientData.length;
    const baseColor = emotionColors[bottomEmotion] || new THREE.Color('gray');
    const baseHSL = {};
    baseColor.getHSL(baseHSL);

    const vertices = [];
    const uvs = [];
    const valences = [];
    const arousals = [];
    const indices = [];

    for (let i = 0; i < segments; i++) {
      for (let j = 0; j < waveDivs; j++) {
        const p = waveCurves[i][j];
        vertices.push(p.x, p.y, p.z);
        uvs.push(i / (segments - 1), j / (waveDivs - 1));

        const t = j / (waveDivs - 1);
        const segmentIndex = Math.floor(t * segmentCount);
        const { valence, arousal } = emotionGradientData[Math.min(segmentIndex, segmentCount - 1)];
        valences.push(valence);
        arousals.push(arousal);
      }
    }

    for (let i = 0; i < segments - 1; i++) {
      for (let j = 0; j < waveDivs - 1; j++) {
        const a = i * waveDivs + j;
        const b = (i + 1) * waveDivs + j;
        const c = (i + 1) * waveDivs + (j + 1);
        const d = i * waveDivs + (j + 1);
        indices.push(a, b, d, b, c, d);
      }
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
    geometry.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
    geometry.setAttribute('valence', new THREE.Float32BufferAttribute(valences, 1));
    geometry.setAttribute('arousal', new THREE.Float32BufferAttribute(arousals, 1));
    geometry.setIndex(indices);
    geometry.computeVertexNormals();
    emotionGradientShader.uniforms.baseHue.value = baseHSL.h;
    setGeneratedGeometry(geometry);
  }, [dataRows, amplitudes, emotionCurves, revealProgress]);

  return (
    <>
      <ambientLight intensity={0.6} />
      <pointLight position={[0, 0, 0]} intensity={100} color={new THREE.Color(1.0, 0.85, 0.3)} distance={100} decay={2} />
      <group ref={groupRef}>
        {generatedGeometry && (
          <mesh ref={meshRef} geometry={generatedGeometry} material={emotionGradientShader} />
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