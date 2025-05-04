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
import { useLoader } from '@react-three/fiber';
//port * as THREE from 'three';

const ColorCloud = forwardRef(({ csvPath, amplitudeCsvPath, emotionCurvesPath, onEmotionChange }, ref) => {
  const groupRef = useRef();
  const meshRef = useRef();
  const innerRef = useRef(); // ✅ inner shell
  const groupRef = useRef(); // ✅ group for export
  const [dataRows, setDataRows] = useState([]);
  const [amplitudes, setAmplitudes] = useState([]);
  const [emotionCurves, setEmotionCurves] = useState(null);
  const [generatedGeometry, setGeneratedGeometry] = useState(null);
  const [revealProgress, setRevealProgress] = useState(0);
  // Add texture management state
  const [currentEmotion, setCurrentEmotion] = useState("neutral");
  const [activeTextures, setActiveTextures] = useState({});
  const [textureLoading, setTextureLoading] = useState(false);

  const waveDivs = 40;
  const waveCount = 5;
  const heightPerLayer = 40;
  const amplitudeFactor = 10;

  // Base texture (used as fallback)
  const fallbackTexture = useLoader(THREE.TextureLoader, '/data/textures/normal_grey/texture_0011_normal.png');
  const fallbackColormap = useLoader(THREE.TextureLoader, '/data/textures/normal_grey/texture_0011_color.png');
  const fallbackNormalMap = useLoader(THREE.TextureLoader, '/data/textures/normal_grey/texture_0011_normal_color.png');

  // Configure texture wrapping and repeating for all textures
  const configureTexture = (texture) => {
    if (!texture) return null;
    texture.wrapS = THREE.RepeatWrapping;
    texture.wrapT = THREE.RepeatWrapping;
    texture.repeat.set(2, 4);
    return texture;
  };

  // Initialize fallback textures
  useEffect(() => {
    configureTexture(fallbackTexture);
    configureTexture(fallbackColormap);
    configureTexture(fallbackNormalMap);
  }, [fallbackTexture, fallbackColormap, fallbackNormalMap]);

  // Function to load emotion-specific textures
  const loadTextureForEmotion = (emotion) => {
    if (activeTextures[emotion]) return; // Already loaded
    
    setTextureLoading(true);
    
    // Path to texture directory based on emotion
    const basePath = `/data/textures/${emotion.toLowerCase()}`;
    
    // Load textures asynchronously
    const textureLoader = new THREE.TextureLoader();
    Promise.all([
      new Promise(resolve => textureLoader.load(`${basePath}/texture_normal.png`, texture => resolve(configureTexture(texture)))),
      new Promise(resolve => textureLoader.load(`${basePath}/texture_color.png`, texture => resolve(configureTexture(texture)))),
      new Promise(resolve => textureLoader.load(`${basePath}/texture_normal_color.png`, texture => resolve(configureTexture(texture))))
    ])
    .then(([normalTexture, colorTexture, normalColorTexture]) => {
      setActiveTextures(prev => ({
        ...prev,
        [emotion]: {
          normal: normalTexture,
          color: colorTexture,
          normalColor: normalColorTexture
        }
      }));
      setTextureLoading(false);
    })
    .catch(error => {
      console.error(`Error loading textures for emotion ${emotion}:`, error);
      // Use fallback textures
      setActiveTextures(prev => ({
        ...prev,
        [emotion]: {
          normal: fallbackTexture,
          color: fallbackColormap,
          normalColor: fallbackNormalMap
        }
      }));
      setTextureLoading(false);
    });
  };

  // Get current textures based on emotion
  const getCurrentTextures = () => {
    if (activeTextures[currentEmotion]) {
      return activeTextures[currentEmotion];
    }
    
    // Return fallback textures if not loaded yet
    return {
      normal: fallbackTexture,
      color: fallbackColormap,
      normalColor: fallbackNormalMap
    };
  };

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
    if (!csvPath || !meshRef.current) return;

    const geo = meshRef.current.geometry;
    const originalPositions = geo.attributes.position.array.slice();
    const originalNormals = geo.attributes.normal.array.slice();
    const originalUVs = geo.attributes.uv.array.slice();
    setOriginalData({
      positions: originalPositions,
      normals: originalNormals,
      uvs: originalUVs,
    });

    setTextureLoading(true);
    fetch(csvPath)
      .then((res) => res.text())
      .then((text) => {
        const parsed = Papa.parse(text, { header: true, dynamicTyping: true });
        
        // Handle both older and newer CSV formats
        let cleanedData = [];
        if (parsed.data[0] && 'ChunkValence' in parsed.data[0]) {
          // New format
          cleanedData = parsed.data.filter(
            (row) =>
              typeof row.ChunkValence === "number" &&
              typeof row.ChunkArousal === "number" &&
              typeof row.ChunkDominance === "number"
          );
          
          // Set the current emotion from the overall emotion if available
          if (cleanedData.length > 0 && cleanedData[0].OverallDiscreteEmotion) {
            const overallEmotion = cleanedData[0].OverallDiscreteEmotion;
            setCurrentEmotion(overallEmotion);
            if (onEmotionChange) onEmotionChange(overallEmotion);
            loadTextureForEmotion(overallEmotion);
          }
        } else {
          // Old format
          cleanedData = parsed.data.filter(
            (row) =>
              typeof row.Valence === "number" &&
              typeof row.Arousal === "number" &&
              typeof row.Dominance === "number"
          );
          
          // For old format, determine emotion from valence/arousal
          if (cleanedData.length > 0) {
            const v = cleanedData[0].Valence;
            const a = cleanedData[0].Arousal;
            // Simple mapping logic
            let emotion = "neutral";
            if (v > 0.6 && a > 0.6) emotion = "joy";
            else if (v > 0.6 && a < 0.4) emotion = "peaceful";
            else if (v < 0.4 && a > 0.6) emotion = "angry";
            else if (v < 0.4 && a < 0.4) emotion = "sad";
            setCurrentEmotion(emotion);
            if (onEmotionChange) onEmotionChange(emotion);
            loadTextureForEmotion(emotion);
          }
        }
        
        // Normalize data for processing
        const normalizedData = cleanedData.map(row => {
          return {
            Valence: row.ChunkValence || row.Valence || 0,
            Arousal: row.ChunkArousal || row.Arousal || 0,
            Dominance: row.ChunkDominance || row.Dominance || 0
          };
        });
        
        setDataRows(normalizedData);
      })
      .catch(error => {
        console.error("Error loading CSV:", error);
        setTextureLoading(false);
      });
  }, [csvPath, onEmotionChange]);

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
        {/* Outer mesh */}
        <mesh ref={meshRef}>
          <cylinderGeometry
            args={[radiusTop, radiusBottom, height, radialSegments, heightSegments, true]}
          />
          <meshPhysicalMaterial
            color="white"
            roughness={0.7}
            transmission={0.6}
            thickness={2.0}
            transparent={true}
            opacity={0.9}
            side={THREE.DoubleSide}
          />
        </mesh>

        {/* Inner mesh with backface orientation */}
        <mesh ref={innerRef}>
          <cylinderGeometry
            args={[
              radiusTop - wallThickness,
              radiusBottom - wallThickness,
              height,
              radialSegments,
              heightSegments,
              true,
            ]}
          />
          <meshPhysicalMaterial
            color="white"
            roughness={0.7}
            transparent={true}
            opacity={0.1}
            side={THREE.BackSide}
          />
        </mesh>
      </group>
    </>
  );
});

const Scene = forwardRef(({ csvPath, amplitudeCsvPath, emotionCurvesPath }, ref) => {
  return (
    <Canvas
      camera={{ position: [30, 10, 20], fov: 75 }}
      style={{ background: "#F1F1F1", width: "100vw", height: "100vh" }}
    >
      <ambientLight intensity={0.2} />
      <directionalLight position={[10, 10, 10]} intensity={0.8} />
      <ColorCloud ref={ref} csvPath={csvPath} />
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