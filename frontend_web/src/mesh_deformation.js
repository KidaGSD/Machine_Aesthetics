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
import { useLoader } from '@react-three/fiber';
//port * as THREE from 'three';

const ColorCloud = forwardRef(({ csvPath, onEmotionChange }, ref) => {
  const meshRef = useRef();
  const innerRef = useRef(); // ✅ inner shell
  const groupRef = useRef(); // ✅ group for export 
  const [dataRows, setDataRows] = useState([]);
  const [originalData, setOriginalData] = useState(null);
  const [revealProgress, setRevealProgress] = useState(0);
  // Add texture management state
  const [currentEmotion, setCurrentEmotion] = useState("neutral");
  const [activeTextures, setActiveTextures] = useState({});
  const [textureLoading, setTextureLoading] = useState(false);

  const radiusTop = 10;
  const radiusBottom = 10;
  const height = 25;
  const radialSegments = 256;
  const heightSegments = 256;
  const wallThickness = 0.5; // ✅ thickness

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
    getMesh: () => meshRef.current,
    exportSTL: () => {
      if (!groupRef.current) return;
      const exporter = new STLExporter();
      const stlString = exporter.parse(groupRef.current);
      const blob = new Blob([stlString], { type: "text/plain" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "lamp_mesh_with_thickness.stl";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    },
    startReveal: () => setRevealProgress(0),
  }));

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
    let start = performance.now();
    let duration = 4000;
    const animate = (time) => {
      const elapsed = time - start;
      const progress = Math.min(elapsed / duration, 1);
      setRevealProgress(progress);
      if (progress < 1) requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
  }, []);

  const displ = (a, v, u) => {
    const vNorm = (v + 1.0) * 0.5;
    const k = 5 + (1 - vNorm) * 1;
    const base = Math.sin(u * 2 * Math.PI);
    const spike = Math.max(0, Math.sin(k * u * Math.PI));
    return base * (1 + a * 20 * spike) * (1 - vNorm);
  };

  useFrame(() => {
    if (!originalData || dataRows.length === 0) return;

    const geo = meshRef.current.geometry;
    const innerGeo = innerRef.current.geometry;
    const pos = geo.attributes.position.array;
    const innerPos = innerGeo.attributes.position.array;
    const count = geo.attributes.position.count;
    const vThreshold = revealProgress;

    for (let i = 0; i < count; i++) {
      const p0x = originalData.positions[i * 3];
      const p0y = originalData.positions[i * 3 + 1];
      const p0z = originalData.positions[i * 3 + 2];
      const nx = originalData.normals[i * 3];
      const ny = originalData.normals[i * 3 + 1];
      const nz = originalData.normals[i * 3 + 2];
      const u = originalData.uvs[i * 2];
      const v = originalData.uvs[i * 2 + 1];

      if (v > vThreshold) continue;

      const index = Math.floor(v * dataRows.length);
      const row = dataRows[Math.min(index, dataRows.length - 1)];
      const val = row.Valence ?? 0;
      const aro = row.Arousal ?? 0;
      const dom = row.Dominance ?? 0;

      const d = displ(aro, val, u);
      const domNorm = (dom + 1.0) * 1;
      const twistAmount = (domNorm - 0.5) * 1.5;
      const twistFreq = 60.0;

      const dx = p0x + d * nx;
      const dy = p0y + d * ny;
      const dz = p0z + d * nz;
      const angle = 2 * Math.PI * twistFreq * v * twistAmount;
      const twistRadius = 1;

      const tx = dx + twistRadius * Math.sin(angle);
      const tz = dz + twistRadius * Math.cos(angle);

      // Outer surface
      pos[i * 3] = tx;
      pos[i * 3 + 1] = dy;
      pos[i * 3 + 2] = tz;

      // Inner surface offset inward
      innerPos[i * 3] = tx - wallThickness * nx;
      innerPos[i * 3 + 1] = dy - wallThickness * ny;
      innerPos[i * 3 + 2] = tz - wallThickness * nz;
    }

    geo.attributes.position.needsUpdate = true;
    geo.attributes.normal.needsUpdate = true;
    geo.computeVertexNormals();

    innerGeo.attributes.position.needsUpdate = true;
    innerGeo.attributes.normal.needsUpdate = true;
    innerGeo.computeVertexNormals();
  });

  // Get the current textures based on emotion
  const textures = getCurrentTextures();
  
  return (
    <>
      <pointLight position={[0, 0, 0]} intensity={1000} distance={10000} color="orange" />
      <group ref={groupRef}>
        {/* Main lamp mesh */}
        <mesh ref={meshRef}>
          <cylinderGeometry
            args={[radiusTop, radiusBottom, height, radialSegments, heightSegments, true]}
          />
          <meshStandardMaterial
            displacementMap={textures.normal}
            displacementScale={0.5}
            displacementSmoothing={0.04}
            displacementBias={0.05}
            normalMap={textures.normalColor}
            map={textures.color}
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

const Scene = forwardRef(({ csvPath, onEmotionChange }, ref) => {
  return (
    <Canvas
      camera={{ position: [30, 10, 20], fov: 75 }}
      style={{ background: "#F1F1F1", width: "100vw", height: "100vh" }}
    >
      <ambientLight intensity={0.2} />
      <directionalLight position={[10, 10, 10]} intensity={0.8} />
      <ColorCloud ref={ref} csvPath={csvPath} onEmotionChange={onEmotionChange} />
      <OrbitControls />
    </Canvas>
  );
});

export default Scene;