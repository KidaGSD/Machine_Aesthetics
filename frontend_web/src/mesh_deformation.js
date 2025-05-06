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
import emotionColors, { getEmotionColor } from "./emotionColors";
import { emotionGradientShader } from "./shaders/emotionGradientShader";
import { useTextureLoader } from "./TextureLoader";

// Get backend URL
const backendUrl = "http://localhost:5001";

const ColorCloud = forwardRef(({ top2CsvPath, amplitudeCsvPath, vadCsvPath, textureClassificationCsvPath, emotionCurvesPath, onTextureUpdate }, ref) => {
  const groupRef = useRef();
  const meshRef = useRef();
  const materialRef = useRef();
  const [dataRows, setDataRows] = useState([]);
  const [amplitudes, setAmplitudes] = useState([]);
  const [emotionCurves, setEmotionCurves] = useState(null);
  const [generatedGeometry, setGeneratedGeometry] = useState(null);
  const [revealProgress, setRevealProgress] = useState(0);
  // Add texture management state
  const [currentEmotion, setCurrentEmotion] = useState("neutral");
  const [textureEnabled, setTextureEnabled] = useState(true);
  // Add a ref to track component mounting state
  const isMountedRef = useRef(true);
  // Add lastPaths to track changes to paths
  const lastPathsRef = useRef({ top2CsvPath, amplitudeCsvPath, vadCsvPath, textureClassificationCsvPath, emotionCurvesPath });
  // Track if material has been initialized
  const materialInitialized = useRef(false);

  // Initialize the texture loader hook - Pass VAD path and Classification path
  const { textureMaps, loadingState } = useTextureLoader(
    top2CsvPath,
    textureClassificationCsvPath
  );

  // Initialize the material once
  useEffect(() => {
    if (!materialInitialized.current) {
      console.log("[mesh_deformation] Initializing material");
      // Clone the shader material to create an instance for this component
      materialRef.current = emotionGradientShader.clone();
      materialInitialized.current = true;
    }
  }, []);

  // Update textures when they change
  useEffect(() => {
    if (materialRef.current && textureMaps) {
      console.log("[mesh_deformation] Updating texture uniforms");
      
      try {
        if (textureMaps.texture1?.displacementMap) {
          materialRef.current.uniforms.displacementMap.value = textureMaps.texture1.displacementMap;
        }
        if (textureMaps.texture1?.normalMap) {
          materialRef.current.uniforms.normalMap.value = textureMaps.texture1.normalMap;
        }
        if (textureMaps.texture2?.displacementMap) {
          materialRef.current.uniforms.displacementMap2.value = textureMaps.texture2.displacementMap;
        }
        if (textureMaps.texture2?.normalMap) {
          materialRef.current.uniforms.normalMap2.value = textureMaps.texture2.normalMap;
        }
        
        // Update texture detail based on emotion, more detail for high arousal emotions
        const topEmotion = dataRows?.[0]?.emotion?.trim().toLowerCase();
        if (topEmotion) {
          if (topEmotion === 'anger' || topEmotion === 'fear' || topEmotion === 'surprise') {
            materialRef.current.uniforms.textureDetail.value = 0.9; // More detail
          } else if (topEmotion === 'joy') {
            materialRef.current.uniforms.textureDetail.value = 0.7; // Medium detail
          } else {
            materialRef.current.uniforms.textureDetail.value = 0.5; // Less detail
          }
        }
      } catch (error) {
        console.error("[mesh_deformation] Error updating texture uniforms:", error);
      }
    }
  }, [textureMaps, dataRows]);
  
  // Propagate texture info updates upwards
  useEffect(() => {
    if (onTextureUpdate && textureMaps?.texture1?.textureInfo) {
        onTextureUpdate(textureMaps.texture1.textureInfo);
    }
  }, [textureMaps?.texture1?.textureInfo, onTextureUpdate]);

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
      link.download = "lamp_design.stl";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    },
    startRevealAnimation: () => {
      console.log("Starting reveal animation");
      setRevealProgress(0);
    },
    // Add method to toggle textures
    toggleTextures: () => {
      setTextureEnabled(prev => !prev);
    }
  }));

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  useFrame(() => {
    if (meshRef.current) {
      meshRef.current.rotation.y += 0.002;
      
      // Apply material properties in the animation frame for better sync
      if (materialRef.current) {
        materialRef.current.uniforms.useTexture.value = textureEnabled ? 1.0 : 0.0;
        materialRef.current.uniforms.revealProgress.value = revealProgress;
        
        // Update time uniform for subtle animation effects
        if (materialRef.current.uniforms.time) {
          materialRef.current.uniforms.time.value += 0.01; // Slow, subtle animation
        }
      }
    }
    
    // Only update reveal progress if the component is still mounted
    if (revealProgress < 1.0 && isMountedRef.current) {
      setRevealProgress((prev) => Math.min(prev + 0.003, 1.0));
    }
  });

  const fetchWithNoCache = (url) => `${url}?t=${Date.now()}`;

  // Load the top 2 emotions data
  useEffect(() => {
    if (!top2CsvPath) return;
    
    const loadData = async () => {
      try {
        console.log("[mesh_deformation] Loading top 2 emotions data");
        const response = await fetch(fetchWithNoCache(top2CsvPath));
        const text = await response.text();
        const cleanText = text.replace(/^﻿/, '');
        const parsed = Papa.parse(cleanText, { header: true, dynamicTyping: true, skipEmptyLines: true });
        const cleaned = parsed.data.filter(row => row.emotion);
        console.log("Loaded emotion data:", cleaned);
        setDataRows(cleaned);
      } catch (error) {
        console.error("[mesh_deformation] Error loading top 2 emotions:", error);
      }
    };
    
    loadData();
  }, [top2CsvPath]);

  // Load amplitude data
  useEffect(() => {
    if (!amplitudeCsvPath) return;
    
    const loadData = async () => {
      try {
        const response = await fetch(fetchWithNoCache(amplitudeCsvPath));
        const text = await response.text();
        const parsed = Papa.parse(text, { header: true, dynamicTyping: true, skipEmptyLines: true });
        const amps = parsed.data.map(row => parseFloat(row.arousal ?? 0));
        setAmplitudes(amps);
      } catch (error) {
        console.error("[mesh_deformation] Error loading amplitude data:", error);
      }
    };
    
    loadData();
  }, [amplitudeCsvPath]);

  // Load emotion curves
  useEffect(() => {
    if (!emotionCurvesPath) return;
    
    const loadData = async () => {
      try {
        const response = await fetch(fetchWithNoCache(emotionCurvesPath));
        const data = await response.json();
        console.log("Loaded emotion curves:", data);
        setEmotionCurves(data);
      } catch (error) {
        console.error("[mesh_deformation] Error loading emotion curves:", error);
      }
    };
    
    loadData();
  }, [emotionCurvesPath]);

  // Generate the geometry based on emotions
  useEffect(() => {
    if (!dataRows.length || !amplitudes.length || !emotionCurves) {
      console.log("[mesh_deformation] Dependencies not met. Waiting...");
      console.log("[mesh_deformation] Data rows:", dataRows.length, "Amplitudes:", amplitudes.length, "Emotion Curves:", emotionCurves ? "Loaded" : "Not loaded");
      return;
    }

    console.log("[mesh_deformation] Dependencies met. Starting geometry generation using previous approach...");

    try {
      // --- Revert to previous Shape Logic --- 
      const emotionMap = {
        joy: "j", sadness: "s", anger: "a", fear: "f",
        surprise: "su", neutral: "c", disgust: "d"
      };

      const getEmotionSafely = (emotion) => {
        if (!emotion) return "c";
        const lowercaseEmotion = emotion.toLowerCase().trim();
        return emotionMap[lowercaseEmotion] || "c";
      };

      const topEmotion = dataRows[0]?.emotion?.trim().toLowerCase() || "neutral";
      const bottomEmotion = dataRows[1]?.emotion?.trim().toLowerCase() || "neutral";
      
      console.log("Top emotion:", topEmotion, "Bottom emotion:", bottomEmotion);
      setCurrentEmotion(topEmotion); // Keep this for potential use elsewhere

      const labelA = getEmotionSafely(topEmotion);
      const labelB = getEmotionSafely(bottomEmotion);

      // Use Vector2 for 2D operations initially, consistent with prev_emoionCurveMorph.js
      let ptsA_2D = emotionCurves[labelA]?.map(([x, y]) => new THREE.Vector2(x, y));
      let ptsB_2D = emotionCurves[labelB]?.map(([x, y]) => new THREE.Vector2(x, y));

      if (!ptsA_2D || !ptsB_2D) {
        console.error("[mesh_deformation] Missing emotion curves for", labelA, "or", labelB);
        createDefaultGeometry(); // Fallback if curves are missing
        return;
      }
      
      // Center points (using Vector2)
      const center2D = pts => {
        const avg = pts.reduce((acc, p) => acc.add(p), new THREE.Vector2(0, 0)).divideScalar(pts.length);
        return pts.map(p => p.clone().sub(avg));
      };
      ptsA_2D = center2D(ptsA_2D);
      ptsB_2D = center2D(ptsB_2D);

      // Check winding order (using Vector2)
      const polygonArea2D = pts => pts.reduce((a, p, i) => {
        const next = pts[(i + 1) % pts.length];
        return a + (p.x * next.y - next.x * p.y);
      }, 0) / 2;
      if (polygonArea2D(ptsA_2D) * polygonArea2D(ptsB_2D) < 0) {
        console.log("[mesh_deformation] Reversing bottom shape orientation (2D)");
        ptsB_2D.reverse();
      }

      // Alignment based on closest points (using Vector2)
      const rotateToMatch2D = (ref, target) => {
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
      ptsB_2D = rotateToMatch2D(ptsA_2D, ptsB_2D);

      // Convert back to Vector3 for 3D geometry
      const ptsA = ptsA_2D.map(p => new THREE.Vector3(p.x, 0, p.y)); // Set Y to 0 initially
      const alignedB = ptsB_2D.map(p => new THREE.Vector3(p.x, 0, p.y));

      // --- Geometry construction similar to prev_meshdeformation.js --- 
      const segments = ptsA.length;
      const vertices = [];
      const uvs = [];
      const valences = [];
      const arousals = [];
      const indices = [];
      const segmentCount = emotionGradientData.length; 

      // Create vertical strips
      for (let i = 0; i < segments; i++) {
        for (let j = 0; j < waveDivs; j++) {
          const t = j / (waveDivs - 1); // Vertical progress (0 to 1)
          
          // Interpolate between top and bottom points
          const top = ptsA[i].clone().add(new THREE.Vector3(0, heightPerLayer / 2, 0));
          const bottom = alignedB[i].clone().add(new THREE.Vector3(0, -heightPerLayer / 2, 0));
          const base = new THREE.Vector3().lerpVectors(top, bottom, t);
          
          // Optional: Re-introduce wave effect if desired, ensure it doesn't break shape
          const revealT = Math.min(1, revealProgress * 1.2); // Use revealProgress
          const waved = base.clone();
          if (t < revealT && t > 0.02 && t < 0.98) { // Add edge guards for wave
            const waveOffset = Math.sin(t * Math.PI * waveCount + i * 0.3) * 2.5; // Slightly smaller wave
            let radial = base.clone().sub(new THREE.Vector3(0, base.y, 0)).normalize(); // Get radial direction
            if (radial.length() < 0.001) radial = new THREE.Vector3(1,0,0);
            waved.add(radial.multiplyScalar(waveOffset));
          }
          
          vertices.push(waved.x, waved.y, waved.z);
          uvs.push(i / (segments - 1), t); // Horizontal UV maps to segments, Vertical UV maps to t

          // Get VA from gradient data based on vertical position `t`
          const segmentIndex = Math.floor(t * segmentCount);
          const { valence, arousal } = emotionGradientData[Math.min(segmentIndex, segmentCount - 1)];
          valences.push(valence);
          arousals.push(arousal);
        }
      }

      // Create faces
      for (let i = 0; i < segments; i++) {
        for (let j = 0; j < waveDivs - 1; j++) {
          const currentSegment = i % segments;
          const nextSegment = (i + 1) % segments; // Wrap around for the last segment
          
          const a = currentSegment * waveDivs + j;
          const b = nextSegment * waveDivs + j;
          const c = nextSegment * waveDivs + (j + 1);
          const d = currentSegment * waveDivs + (j + 1);
          
          indices.push(a, b, d); // Triangle 1
          indices.push(b, c, d); // Triangle 2
        }
      }

      // Create BufferGeometry
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
      geometry.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
      geometry.setAttribute('valence', new THREE.Float32BufferAttribute(valences, 1));
      geometry.setAttribute('arousal', new THREE.Float32BufferAttribute(arousals, 1));
      geometry.setIndex(indices);
      geometry.computeVertexNormals(); // Calculate normals for lighting

      // --- Set Colors (Update Material Uniforms) --- 
      if (materialRef.current) {
        const topColor = getEmotionColor(topEmotion); // Use utility function
        const bottomColor = getEmotionColor(bottomEmotion);
        
        // Set the main color uniforms
        materialRef.current.uniforms.colorTop.value.copy(topColor);
        materialRef.current.uniforms.colorBottom.value.copy(bottomColor);
        
        // Keep texture parameter adjustments based on arousal
        const topArousal = Math.abs(parseFloat(dataRows[0]?.arousal ?? 0));
        const bottomArousal = Math.abs(parseFloat(dataRows[1]?.arousal ?? 0));
        
        const textureDetail = 0.4 + Math.max(topArousal, bottomArousal) * 0.4;
        materialRef.current.uniforms.textureDetail.value = textureDetail;
        
        if (topEmotion === 'surprise' || topEmotion === 'fear' || bottomEmotion === 'surprised' || bottomEmotion === 'fear') {
          materialRef.current.uniforms.textureTiling.value = 3.0;
        } else if (topEmotion === 'angry' || bottomEmotion === 'angry') {
          materialRef.current.uniforms.textureTiling.value = 2.5;
        } else {
          materialRef.current.uniforms.textureTiling.value = 2.0;
        }
        
        console.log(`[mesh_deformation] Set colors - Top: ${topEmotion}, Bottom: ${bottomEmotion}`);
      }
      
      console.log("[mesh_deformation] Regenerated geometry using previous method.");
      setGeneratedGeometry(geometry);

    } catch (error) {
      console.error("[mesh_deformation] Error regenerating geometry:", error);
      createDefaultGeometry();
    }
  }, [dataRows, amplitudes, emotionCurves, revealProgress]); // Keep revealProgress for wave animation

  // Create a default geometry when data is not available
  const createDefaultGeometry = () => {
    try {
      // Create a simple cylindrical shape
      const segments = 36;
      const radius = 20;
      const height = 40;
      
      const vertices = [];
      const uvs = [];
      const valences = [];
      const arousals = [];
      const indices = [];
      
      // Create circles for top and bottom
      for (let i = 0; i < segments; i++) {
        const angle = (i / segments) * Math.PI * 2;
        const x = Math.cos(angle) * radius;
        const z = Math.sin(angle) * radius;
        
        // Top vertices
        vertices.push(x, height/2, z);
        uvs.push(i / segments, 0);
        valences.push(0);
        arousals.push(0);
        
        // Bottom vertices
        vertices.push(x, -height/2, z);
        uvs.push(i / segments, 1);
        valences.push(0.5);
        arousals.push(0.5);
      }
      
      // Create face indices
      for (let i = 0; i < segments; i++) {
        const topIdx = i * 2;
        const bottomIdx = i * 2 + 1;
        const nextTopIdx = ((i + 1) % segments) * 2;
        const nextBottomIdx = ((i + 1) % segments) * 2 + 1;
        
        // Add triangles
        indices.push(topIdx, nextTopIdx, bottomIdx);
        indices.push(nextTopIdx, nextBottomIdx, bottomIdx);
      }
      
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
      geometry.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
      geometry.setAttribute('valence', new THREE.Float32BufferAttribute(valences, 1));
      geometry.setAttribute('arousal', new THREE.Float32BufferAttribute(arousals, 1));
      geometry.setIndex(indices);
      geometry.computeVertexNormals();
      
      setGeneratedGeometry(geometry);
    } catch (error) {
      console.error("[mesh_deformation] Error creating default geometry:", error);
    }
  };
  
  // Create a simplified geometry for performance
  const createSimplifiedGeometry = (topPoints, bottomPoints, baseHue) => {
    try {
      // Use fewer segments to reduce geometry complexity
      const simplifiedSegments = 24; // Down from original segments
      const simplifiedDivs = 48;    // Down from original waveDivs
      
      // Sample points evenly from the original paths
      const samplePoints = (points, count) => {
        const sampled = [];
        for (let i = 0; i < count; i++) {
          const idx = Math.floor((i / count) * points.length);
          sampled.push(points[idx % points.length]);
        }
        return sampled;
      };
      
      const sampledTopPoints = samplePoints(topPoints, simplifiedSegments);
      const sampledBottomPoints = samplePoints(bottomPoints, simplifiedSegments);
      
      const vertices = [];
      const uvs = [];
      const valences = [];
      const arousals = [];
      const indices = [];
      
      // Create vertices similar to the main geometry, but with fewer points
      for (let i = 0; i < simplifiedSegments; i++) {
        for (let j = 0; j < simplifiedDivs; j++) {
          const t = j / (simplifiedDivs - 1);
          const top = sampledTopPoints[i].clone().add(new THREE.Vector3(0, heightPerLayer / 2, 0));
          const bottom = sampledBottomPoints[i].clone().add(new THREE.Vector3(0, -heightPerLayer / 2, 0));
          const point = new THREE.Vector3().lerpVectors(top, bottom, t);
          
          // Optional wave effect (reduced)
          if (t > 0.05 && t < 0.95) {
            const waveOffset = Math.sin(t * Math.PI * 3 + i * 0.2) * 2;
            const radial = new THREE.Vector3(point.x, 0, point.z).normalize();
            point.add(radial.multiplyScalar(waveOffset));
          }
          
          vertices.push(point.x, point.y, point.z);
          uvs.push(i / (simplifiedSegments - 1), j / (simplifiedDivs - 1));
          valences.push(0.5 - t * 0.5);  // Simple gradient
          arousals.push(t * 0.5);        // Simple gradient
        }
      }
      
      // Create faces (similar to original)
      for (let i = 0; i < simplifiedSegments - 1; i++) {
        for (let j = 0; j < simplifiedDivs - 1; j++) {
          const a = i * simplifiedDivs + j;
          const b = (i + 1) * simplifiedDivs + j;
          const c = (i + 1) * simplifiedDivs + (j + 1);
          const d = i * simplifiedDivs + (j + 1);
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
      
      console.log("[mesh_deformation] Created simplified geometry with", vertices.length/3, "vertices");
      
      // Update material's base hue
      if (materialRef.current) {
        materialRef.current.uniforms.baseHue.value = baseHue;
      }
      
      return geometry;
    } catch (error) {
      console.error("[mesh_deformation] Error creating simplified geometry:", error);
      return createDefaultGeometry();
    }
  };

  return (
    <>
      <ambientLight intensity={0.6} />
      <pointLight position={[0, 0, 0]} intensity={100} color={new THREE.Color(1.0, 0.85, 0.3)} distance={100} decay={2} />
      <group ref={groupRef}>
        {generatedGeometry && (
          <mesh 
            ref={meshRef} 
            geometry={generatedGeometry}
            material={materialRef.current}
          />
        )}
      </group>
      {/* Loading indicator during development */}
      {process.env.NODE_ENV === 'development' && loadingState === 'loading' && (
        <mesh position={[0, -50, 0]}>
          <sphereGeometry args={[5, 16, 16]} />
          <meshBasicMaterial color="yellow" />
        </mesh>
      )}
    </>
  );
});

const Scene = forwardRef(({ top2CsvPath, amplitudeCsvPath, vadCsvPath, textureClassificationCsvPath, emotionCurvesPath, onTextureUpdate }, ref) => {
  return (
    <Canvas camera={{ position: [0, 50, 100], fov: 45 }} style={{ background: "#000000", width: "100vw", height: "100vh" }}>
      <OrbitControls />
      <ColorCloud
        ref={ref}
        top2CsvPath={top2CsvPath}
        amplitudeCsvPath={amplitudeCsvPath}
        vadCsvPath={vadCsvPath}
        textureClassificationCsvPath={textureClassificationCsvPath}
        emotionCurvesPath={emotionCurvesPath}
        onTextureUpdate={onTextureUpdate}
      />
    </Canvas>
  );
});

export default Scene;