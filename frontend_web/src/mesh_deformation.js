// mesh_deformation.js — Fragment Shader Integration Version
import React, {
  useRef,
  useEffect,
  useState,
  useImperativeHandle,
  forwardRef,
} from "react";
import { Canvas, useFrame, useLoader } from "@react-three/fiber";
import { OrbitControls, Environment } from "@react-three/drei";
import * as THREE from "three";
import Papa from "papaparse";
import { STLExporter } from "three/examples/jsm/exporters/STLExporter";
import emotionGradientData from "./emotionGradientData";
import emotionColors, { getEmotionColor } from "./emotionColors";
import { emotionGradientShader } from "./shaders/emotionGradientShader";
import { useTextureLoader } from "./TextureLoader";
import { RGBELoader } from 'three/examples/jsm/loaders/RGBELoader';

// Get backend URL
const backendUrl = "http://localhost:5001";

const ColorCloud = forwardRef(({ top2CsvPath, amplitudeCsvPath, vadCsvPath, textureClassificationCsvPath, emotionCurvesPath, onTextureUpdate, textureEnabled: propTextureEnabled = true }, ref) => {
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
  // Use the prop for initial state if provided
  const [textureEnabled, setTextureEnabled] = useState(propTextureEnabled);
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

  const envMap = useLoader(RGBELoader, '/hdri/hdri.hdr');
  envMap.mapping = THREE.EquirectangularReflectionMapping;

  // Update textureEnabled state when the prop changes
  useEffect(() => {
    if (propTextureEnabled !== textureEnabled) {
      console.log(`[mesh_deformation] Updating texture state from prop: ${propTextureEnabled}`);
      setTextureEnabled(propTextureEnabled);
      
      // Also update material if it exists
      if (materialRef.current) {
        materialRef.current.uniforms.useTexture.value = propTextureEnabled ? 1.0 : 0.0;
      }
    }
  }, [propTextureEnabled]);

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
      // Enhance texture info with the URL and more details
      const enhancedTextureInfo = {
        ...textureMaps.texture1.textureInfo,
        source: textureMaps.texture1.textureInfo.source || 'unknown',
        // Extract the full texture URL directly from the texture object
        fullPath: textureMaps.texture1.displacementMap?.image?.src || null,
        // If texture is already loaded, use its name
        name: textureMaps.texture1.displacementMap?.name || textureMaps.texture1.textureInfo.filename,
        // Include loading state 
        loadingState: loadingState
      };
      
      // Send enhanced texture info to parent
      onTextureUpdate(enhancedTextureInfo);
    }
  }, [textureMaps?.texture1?.textureInfo, onTextureUpdate, loadingState]);

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
      console.log(`[mesh_deformation] Toggling textures from ${textureEnabled ? 'ON' : 'OFF'} to ${!textureEnabled ? 'ON' : 'OFF'}`);
      
      // Toggle texture state using functional update to ensure latest state
      setTextureEnabled(prev => {
        const newState = !prev;
        
        // Apply immediately to material if it exists
        if (materialRef.current) {
          materialRef.current.uniforms.useTexture.value = newState ? 1.0 : 0.0;
          console.log(`[mesh_deformation] Set material useTexture uniform to ${newState ? 1.0 : 0.0}`);
        } else {
          console.warn("[mesh_deformation] Material reference not available for texture toggle");
        }
        
        return newState;
      });
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
        // Update the useTexture uniform with the current state to ensure consistency
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

  // Add a more robust fetch function that handles CORS issues
  const fetchWithNoCache = async (url) => {
    const timestamp = Date.now();
    const cacheBustedUrl = `${url}${url.includes('?') ? '&' : '?'}t=${timestamp}`;
    
    console.log("[mesh_deformation] Fetching with cache-busting:", cacheBustedUrl);
    
    try {
      // If it's a relative path starting with "/emotions/"
      if (url.startsWith('/emotions/')) {
        console.log("[mesh_deformation] Using local path for emotions file");
        const response = await fetch(url, { 
          method: 'GET',
          mode: 'same-origin',
          cache: 'no-store',
          headers: {
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
          }
        });
        
        if (!response.ok) {
          throw new Error(`HTTP error: ${response.status}`);
        }
        
        const text = await response.text();
        console.log("[mesh_deformation] Successfully loaded local emotions file");
        return text;
      }

      // For other URLs (like backend URLs)
      const response = await fetch(cacheBustedUrl, {
        method: 'GET',
        mode: 'cors',
        credentials: 'omit',
        headers: {
          'Cache-Control': 'no-cache',
          'Pragma': 'no-cache',
        }
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error: ${response.status}`);
      }
      
      const text = await response.text();
      console.log("[mesh_deformation] Fetch successful");
      return text;
    } catch (error) {
      console.error("[mesh_deformation] Fetch error:", error);
      
      // Try a direct fallback for emotion_curves.json
      if (url.includes('emotion_curves.json')) {
        try {
          console.log("[mesh_deformation] Trying direct fetch for emotion_curves.json");
          const response = await fetch("/emotions/emotion_curves.json", { 
            mode: 'same-origin',
            cache: 'no-store' 
          });
          
          if (!response.ok) {
            throw new Error(`HTTP error: ${response.status}`);
          }
          
          const text = await response.text();
          console.log("[mesh_deformation] Direct fetch successful");
          return text;
        } catch (altError) {
          console.error("[mesh_deformation] Direct fetch failed:", altError);
        }
      }
      
      throw error;
    }
  };

  // Load the top 2 emotions data
  useEffect(() => {
    if (!top2CsvPath) {
      console.log("[mesh_deformation] No top2CsvPath provided, component may not show data");
      return;
    }
    
    const loadData = async () => {
      try {
        console.log("[mesh_deformation] Loading top 2 emotions data from:", top2CsvPath);
        const text = await fetchWithNoCache(top2CsvPath);
        if (!text) {
          console.error("[mesh_deformation] Failed to fetch data from:", top2CsvPath);
          return;
        }
        const cleanText = text.replace(/^﻿/, '');
        const parsed = Papa.parse(cleanText, { header: true, dynamicTyping: true, skipEmptyLines: true });
        const cleaned = parsed.data.filter(row => row.emotion);
        console.log("Loaded emotion data:", cleaned);
        if (cleaned.length === 0) {
          console.error("[mesh_deformation] ⚠️ No emotion data found after parsing CSV!");
          console.log("Original CSV content:", text);
          console.log("Parsed result:", parsed);
        }
        setDataRows(cleaned);
      } catch (error) {
        console.error("[mesh_deformation] Error loading top 2 emotions:", error);
      }
    };
    
    loadData();
  }, [top2CsvPath]);

  // Load amplitude data
  useEffect(() => {
    if (!amplitudeCsvPath) {
      console.log("[mesh_deformation] No amplitudeCsvPath provided, using default values");
      // Create default amplitude data if none provided
      const defaultAmplitudes = Array(100).fill(0).map((_, i) => Math.sin(i / 10) * 0.5 + 0.5);
      setAmplitudes(defaultAmplitudes);
      return;
    }
    
    const loadData = async () => {
      try {
        console.log("[mesh_deformation] Loading amplitude data from:", amplitudeCsvPath);
        const text = await fetchWithNoCache(amplitudeCsvPath);
        if (!text) {
          console.error("[mesh_deformation] Failed to fetch amplitude data");
          return;
        }
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
    if (!emotionCurvesPath) {
      console.error("[mesh_deformation] No emotionCurvesPath provided!");
      return;
    }
    
    const loadData = async () => {
      try {
        console.log("[mesh_deformation] Loading emotion curves from:", emotionCurvesPath);
        const text = await fetchWithNoCache(emotionCurvesPath);
        if (!text) {
          console.error("[mesh_deformation] Failed to fetch emotion curves data");
          return;
        }
        const data = JSON.parse(text);
        console.log("Loaded emotion curves:", Object.keys(data));
        if (!data || Object.keys(data).length === 0) {
          console.error("[mesh_deformation] ⚠️ Loaded emotion curves is empty or invalid");
        }
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
      
      // Add more detailed debugging
      if (!dataRows.length) {
        console.warn("[mesh_deformation] No data rows loaded. Check if top2CsvPath is correct:", top2CsvPath);
      }
      if (!emotionCurves) {
        console.warn("[mesh_deformation] No emotion curves loaded. Check if emotionCurvesPath is correct:", emotionCurvesPath);
      }
      return;
    }

    console.log("[mesh_deformation] Dependencies met. Starting geometry generation using previous approach...");
    console.log("[mesh_deformation] Emotion curves available:", Object.keys(emotionCurves));
    console.log("[mesh_deformation] First two emotion rows:", dataRows.slice(0, 2));
    
    try {
      // --- Revert to previous Shape Logic --- 
      const emotionMap = {
        joy: "j", happy: "j",
        sadness: "s", sad: "s",
        anger: "a", angry: "a",
        fear: "f", fearful: "f",
        surprise: "su", surprised: "su",
        neutral: "c", calm: "c", peaceful: "c", serene: "se",
        disgust: "d", disgusted: "d"
      };

      const getEmotionSafely = (emotion) => {
        if (!emotion) return "c";
        const lowercaseEmotion = emotion.toLowerCase().trim();
        const mapped = emotionMap[lowercaseEmotion];
        console.log(`[mesh_deformation] Mapping emotion "${lowercaseEmotion}" → "${mapped || 'not_found'}"`);
        return mapped || "c";
      };

      const topEmotion = dataRows[0]?.emotion?.trim().toLowerCase() || "neutral";
      const bottomEmotion = dataRows[1]?.emotion?.trim().toLowerCase() || "neutral";
      
      console.log("[mesh_deformation] Raw emotion data from CSV:", { 
        rawTop: dataRows[0]?.emotion, 
        rawBottom: dataRows[1]?.emotion
      });
      console.log("Top emotion:", topEmotion, "Bottom emotion:", bottomEmotion);
      setCurrentEmotion(topEmotion); // Keep this for potential use elsewhere

      const labelA = getEmotionSafely(topEmotion);
      const labelB = getEmotionSafely(bottomEmotion);
      
      console.log("[mesh_deformation] Will look for curves with keys:", labelA, labelB);
      console.log("[mesh_deformation] Available curve keys:", emotionCurves ? Object.keys(emotionCurves) : "No curves loaded");

      // Get arousal values for scaling
      const arousalA = Math.max(0, Math.min(1, parseFloat(dataRows[0]?.arousal ?? 0.5)));
      const arousalB = Math.max(0, Math.min(1, parseFloat(dataRows[1]?.arousal ?? 0.5)));
      const minScale = 0.7;
      const maxScale = 1.3;
      const scaleA = minScale + (maxScale - minScale) * arousalA;
      const scaleB = minScale + (maxScale - minScale) * arousalB;
      console.log("Arousal values and scaling:", { arousalA, arousalB, scaleA, scaleB });

      // Wave amplitude based on arousal
      const minWave = 0.5;
      const maxWave = 4.0;
      const waveAmpA = minWave + (maxWave - minWave) * arousalA;
      const waveAmpB = minWave + (maxWave - minWave) * arousalB;

      // Get the raw curve points and apply scaling
      const rawA = emotionCurves[labelA];
      const rawB = emotionCurves[labelB];
      
      // Debug emotion curve mapping
      console.log("[mesh_deformation] Using emotion curve mapping:", { 
        topEmotion, 
        bottomEmotion, 
        labelA, 
        labelB, 
        rawA: rawA ? `Found ${rawA.length} points` : "Not found", 
        rawB: rawB ? `Found ${rawB.length} points` : "Not found"
      });
      
      // If raw curves aren't found, use fallback curves
      if (!rawA || !rawB) {
        console.error("[mesh_deformation] Missing emotion curves for", labelA, "or", labelB);
        console.error("[mesh_deformation] Available curves:", Object.keys(emotionCurves));
        
        // Create default star shapes as fallback
        const createDefaultStar = (size) => {
          const points = [];
          for (let i = 0; i < 10; i++) {
            const radius = i % 2 === 0 ? size : size * 0.5;
            const angle = (i / 10) * Math.PI * 2;
            points.push([Math.cos(angle) * radius, Math.sin(angle) * radius]);
          }
          return points;
        };
        
        if (!rawA) emotionCurves.j = createDefaultStar(10);
        if (!rawB) emotionCurves.s = createDefaultStar(8);
        
        console.log("[mesh_deformation] Created fallback star shapes:", {
          topLabel: !rawA ? "j (fallback)" : labelA,
          bottomLabel: !rawB ? "s (fallback)" : labelB
        });
        
        createDefaultGeometry(); // Still use default geometry for safety
        return;
      }
      
      let ptsA = rawA.map(([x, y]) => new THREE.Vector2(x * scaleA, y * scaleA));
      let ptsB = rawB.map(([x, y]) => new THREE.Vector2(x * scaleB, y * scaleB));

      if (!ptsA || !ptsB) {
        console.error("[mesh_deformation] Missing emotion curves for", labelA, "or", labelB);
        createDefaultGeometry(); // Fallback if curves are missing
        return;
      }
      
      // Center points (using Vector2)
      const center2D = pts => {
        const avg = pts.reduce((acc, p) => acc.add(p), new THREE.Vector2(0, 0)).divideScalar(pts.length);
        return pts.map(p => p.clone().sub(avg));
      };
      ptsA = center2D(ptsA);
      ptsB = center2D(ptsB);

      // Check winding order (using Vector2)
      const polygonArea2D = pts => pts.reduce((a, p, i) => {
        const next = pts[(i + 1) % pts.length];
        return a + (p.x * next.y - next.x * p.y);
      }, 0) / 2;
      if (polygonArea2D(ptsA) * polygonArea2D(ptsB) < 0) {
        console.log("[mesh_deformation] Reversing bottom shape orientation (2D)");
        ptsB.reverse();
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
      ptsB = rotateToMatch2D(ptsA, ptsB);

      // Convert back to Vector3 for 3D geometry
      const ptsA_3D = ptsA.map(p => new THREE.Vector3(p.x, 0, p.y)); // Set Y to 0 initially
      const alignedB = ptsB.map(p => new THREE.Vector3(p.x, 0, p.y));

      // --- Geometry construction similar to prev_meshdeformation.js --- 
      const segments = ptsA_3D.length;
      const vertices = [];
      const uvs = [];
      const valences = [];
      const arousals = [];
      const indices = [];
      const segmentCount = emotionGradientData.length; 

      // Add thickness
      const thickness = 2.0;
      // Helper to offset a point radially in XZ plane
      function offsetRadial(vec, amount) {
        const radial = new THREE.Vector2(vec.x, vec.z).normalize();
        return new THREE.Vector3(vec.x - radial.x * amount, vec.y, vec.z - radial.y * amount);
      }
      // Store all points for outer and inner shells
      const outerTop = [];
      const outerBot = [];
      const innerTop = [];
      const innerBot = [];
      for (let i = 0; i < segments; i++) {
        outerTop.push(ptsA_3D[i].clone().add(new THREE.Vector3(0, heightPerLayer / 2, 0)));
        outerBot.push(alignedB[i].clone().add(new THREE.Vector3(0, -heightPerLayer / 2, 0)));
        innerTop.push(offsetRadial(outerTop[i], thickness));
        innerBot.push(offsetRadial(outerBot[i], thickness));
      }

      // Create vertical strips (outer shell)
      for (let i = 0; i < segments; i++) {
        for (let j = 0; j < waveDivs; j++) {
          const t = j / (waveDivs - 1); // Vertical progress (0 to 1)
          const top = outerTop[i];
          const bottom = outerBot[i];
          const base = new THREE.Vector3().lerpVectors(top, bottom, t);
          const waved = base.clone(); // No wave effect, just linear interpolation
          vertices.push(waved.x, waved.y, waved.z);
          uvs.push(i / (segments - 1), t);
          const segmentIndex = Math.floor(t * segmentCount);
          const { valence, arousal } = emotionGradientData[Math.min(segmentIndex, segmentCount - 1)];
          valences.push(valence);
          arousals.push(arousal);
        }
      }
      // Create vertical strips (inner shell)
      for (let i = 0; i < segments; i++) {
        for (let j = 0; j < waveDivs; j++) {
          const t = j / (waveDivs - 1);
          const top = innerTop[i];
          const bottom = innerBot[i];
          const base = new THREE.Vector3().lerpVectors(top, bottom, t);
          vertices.push(base.x, base.y, base.z);
          uvs.push(i / (segments - 1), t);
          const segmentIndex = Math.floor(t * segmentCount);
          const { valence, arousal } = emotionGradientData[Math.min(segmentIndex, segmentCount - 1)];
          valences.push(valence);
          arousals.push(arousal);
        }
      }

      // Create faces (outer shell)
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
      // Create faces (inner shell, reversed winding)
      const innerOffset = segments * waveDivs;
      for (let i = 0; i < segments; i++) {
        for (let j = 0; j < waveDivs - 1; j++) {
          const currentSegment = i % segments;
          const nextSegment = (i + 1) % segments;
          const a = innerOffset + currentSegment * waveDivs + j;
          const b = innerOffset + nextSegment * waveDivs + j;
          const c = innerOffset + nextSegment * waveDivs + (j + 1);
          const d = innerOffset + currentSegment * waveDivs + (j + 1);
          indices.push(a, d, b); // Reverse winding
          indices.push(b, d, c);
        }
      }
      // Create side faces (connect outer and inner shells)
      for (let i = 0; i < segments; i++) {
        const nextSegment = (i + 1) % segments;
        for (let j = 0; j < waveDivs - 1; j++) {
          // Top ring
          let a = i * waveDivs + j;
          let b = nextSegment * waveDivs + j;
          let a2 = innerOffset + i * waveDivs + j;
          let b2 = innerOffset + nextSegment * waveDivs + j;
          // Connect outer top to inner top
          indices.push(a, b, a2);
          indices.push(b, b2, a2);
          // Bottom ring
          a = i * waveDivs + (j + 1);
          b = nextSegment * waveDivs + (j + 1);
          a2 = innerOffset + i * waveDivs + (j + 1);
          b2 = innerOffset + nextSegment * waveDivs + (j + 1);
          // Connect outer bottom to inner bottom
          indices.push(a2, b2, a);
          indices.push(b2, b, a);
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
      
      // console.log("[mesh_deformation] Created simplified geometry with", vertices.length/3, "vertices");
      
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
      <ambientLight intensity={100} />
      <pointLight position={[0, 0, 0]} color="#fff8e1" intensity={2000} distance={2000} decay={2} />
      <group ref={groupRef}>
        {generatedGeometry && (
          <mesh 
            ref={meshRef} 
            geometry={generatedGeometry}
            material={materialRef.current}
          />
        )}
        {/* Add a long, thin cylinder in the center as a lamp post */}
        <mesh position={[0, 20, 0]}>
          <cylinderGeometry args={[0.7, 0.7, 60, 24]} />
          <meshPhysicalMaterial
            color="#cccccc"
            metalness={1}
            roughness={0}
            ior={2.0}
            reflectivity={1.0}
            envMap={envMap}
          />
        </mesh>
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

const Scene = forwardRef(({ top2CsvPath, amplitudeCsvPath, vadCsvPath, textureClassificationCsvPath, emotionCurvesPath, onTextureUpdate, textureEnabled }, ref) => {
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
        textureEnabled={textureEnabled}
      />
    </Canvas>
  );
});

export default Scene;