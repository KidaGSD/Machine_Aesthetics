import React, {
  useRef,
  useEffect,
  useState,
  useImperativeHandle,
  forwardRef,
} from "react";
import { Canvas, useFrame, useLoader } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import * as THREE from "three";
import Papa from "papaparse";
import { STLExporter } from "three/examples/jsm/exporters/STLExporter";

// Define emotion color mapping with warmer/colder colors for better blending
const emotionColors = {
  joy: new THREE.Color(0xffaa00),      // Warm yellow/orange
  serene: new THREE.Color(0x7ae7ff),   // Light blue
  peaceful: new THREE.Color(0x9ee5a1), // Light green
  neutral: new THREE.Color(0xdddddd),  // Light gray
  sad: new THREE.Color(0x3373cc),      // Darker blue
  fearful: new THREE.Color(0x8075cc),  // Purple
  angry: new THREE.Color(0xff3333),    // Red
  surprised: new THREE.Color(0xff66cc),// Pink
  disgusted: new THREE.Color(0x669933) // Olive green
};

// Emotion intensity modifiers
const intensityModifiers = {
  low: 0.4,
  mod: 0.7,
  high: 1.0
};

// Helper function to parse emotion and intensity from format like "pos_high", "neg_mod", etc.
const parseEmotionCode = (code) => {
  if (!code || typeof code !== 'string') return { emotion: 'neutral', intensity: 'mod' };
  
  // Parse valence_arousal codes like "pos_high", "neg_low", etc.
  const parts = code.split('_');
  let emotion = 'neutral';
  let intensity = 'mod';
  
  // Map valence + arousal to an emotion
  if (parts.length >= 2) {
    const valence = parts[0];
    const arousal = parts[1];
    
    if (valence === 'pos' && (arousal === 'high' || arousal === 'mod')) {
      emotion = 'joy';
    } else if (valence === 'pos' && arousal === 'low') {
      emotion = 'peaceful';
    } else if (valence === 'neg' && (arousal === 'high' || arousal === 'mod')) {
      emotion = 'angry';
    } else if (valence === 'neg' && arousal === 'low') {
      emotion = 'sad';
    }
    
    intensity = arousal; // Use arousal level as intensity
  }
  
  return { emotion, intensity };
};

const ColorCloud = forwardRef(({ csvPath, onEmotionChange }, ref) => {
  const meshRef = useRef();
  const innerRef = useRef(); // ✅ inner shell
  const groupRef = useRef(); // ✅ group for export
  const [dataRows, setDataRows] = useState([]);
  const [originalData, setOriginalData] = useState(null);
  const [revealProgress, setRevealProgress] = useState(0);
  const [textureParams, setTextureParams] = useState(null);
  const [currentEmotion, setCurrentEmotion] = useState(null);
  const [displacementMaps, setDisplacementMaps] = useState([]);
  const [timeToEmotionMap, setTimeToEmotionMap] = useState({}); // Maps time points to emotions

  const radiusTop = 10;
  const radiusBottom = 10;
  const height = 25;
  const radialSegments = 128;
  const heightSegments = 128;                                      
  const wallThickness = 0.5; // ✅ thickness

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
      link.download = "lamp_mesh_with_texture.stl";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    },
    startReveal: () => setRevealProgress(0),
  }));

  // Load texture parameters and displacement maps
  useEffect(() => {
    // Load texture parameters
    fetch("/texture_keys.json")
      .then(res => res.json())
      .catch(error => {
        console.log("Using default texture parameters due to error:", error);
        // Fallback to hardcoded key parameters in case the file doesn't exist
        return {
          "joy": { "displacementScale": 1.2, "noiseFrequency": 0.5 },
          "serene": { "displacementScale": 0.8, "noiseFrequency": 0.3 },
          "peaceful": { "displacementScale": 0.6, "noiseFrequency": 0.2 },
          "neutral": { "displacementScale": 0.5, "noiseFrequency": 0.4 },
          "sad": { "displacementScale": 0.7, "noiseFrequency": 0.6 },
          "fearful": { "displacementScale": 1.0, "noiseFrequency": 0.8 },
          "angry": { "displacementScale": 1.5, "noiseFrequency": 0.9 },
          "surprised": { "displacementScale": 1.1, "noiseFrequency": 0.7 },
          "disgusted": { "displacementScale": 0.9, "noiseFrequency": 0.5 }
        };
      })
      .then(params => {
        setTextureParams(params);
      });
    
    // Load selected displacement maps from parametric JSONs
    const selectedTimepoints = [0, 100]; // Only use t000 and t100 which have the correct format
    
    console.log("Loading displacement maps for timepoints:", selectedTimepoints);
    
    Promise.all(
      selectedTimepoints.map(time => {
        // Format the filename according to the pattern observed
        const formattedTime = time.toString().padStart(3, '0');
        const url = `/displacement_maps/lamp_params_t${formattedTime}.json`;
        
        console.log(`Loading displacement map from: ${url}`);
        return fetch(url)
          .then(res => {
            if (!res.ok) {
              throw new Error(`Failed to load: ${res.status} ${res.statusText}`);
            }
            return res.json();
          })
          .then(data => {
            console.log(`Successfully loaded displacement map for time ${time}:`, data);
            
            // Validate the structure is as expected
            if (!data.parameters || !data.parameters.displacement_values) {
              console.error(`Missing displacement_values in map for time ${time}`);
            } else {
              console.log(`Displacement map for time ${time} has ${data.parameters.displacement_values.length} layers`);
              if (data.parameters.displacement_values.length > 0) {
                console.log(`First layer has ${data.parameters.displacement_values[0]?.length || 0} subdivisions`);
              }
            }
            
            return data;
          })
          .catch(error => {
            console.warn(`Failed to load displacement map for time ${time}:`, error);
            return null;
          });
      })
    )
    .then(maps => {
      const validMaps = maps.filter(map => map !== null);
      
      if (validMaps.length === 0) {
        console.warn("No displacement maps loaded, using procedural fallback");
      } else {
        console.log(`Loaded ${validMaps.length} displacement maps`);
        
        // Create a time-to-emotion mapping
        const emotionMap = {};
        validMaps.forEach(map => {
          if (map && map.metadata && map.metadata.time !== undefined && map.metadata.emotions) {
            const time = map.metadata.time;
            const emotionCode = map.metadata.emotions;
            const { emotion, intensity } = parseEmotionCode(emotionCode);
            
            // Make sure displacement values exist
            if (!map.parameters || !map.parameters.displacement_values || 
                !Array.isArray(map.parameters.displacement_values)) {
              console.error(`Map for time ${time} has invalid displacement_values structure`);
              return;
            }
            
            emotionMap[time] = { 
              emotion, 
              intensity, 
              displacementValues: map.parameters.displacement_values 
            };
            
            console.log(`Added emotion map for time ${time}: ${emotion} (${intensity})`);
          } else {
            console.error("Invalid map structure:", map);
          }
        });
        
        console.log("Final timeToEmotionMap:", emotionMap);
        setTimeToEmotionMap(emotionMap);
        setDisplacementMaps(validMaps);
      }
    });
  }, []);

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

    // Use a full URL for fetch to ensure it works in both development and production
    console.log("Attempting to fetch CSV from:", csvPath);
    fetch(csvPath + `?t=${Date.now()}`)
      .then((res) => {
        if (!res.ok) {
          throw new Error(`Failed to fetch CSV: ${res.status} ${res.statusText}`);
        }
        return res.text();
      })
      .then((text) => {
        console.log("CSV data received, length:", text.length);
        console.log("CSV data first 100 chars:", text.substring(0, 100));
        
        // Parse the CSV to ensure headers are recognized correctly
        const parsed = Papa.parse(text, { 
          header: true, 
          dynamicTyping: true,
          skipEmptyLines: true
        });
        
        console.log("CSV headers:", parsed.meta.fields);
        console.log("CSV rows count:", parsed.data.length);
        console.log("First row sample:", parsed.data.length > 0 ? JSON.stringify(parsed.data[0]) : "No data");
        
        // Filter and map the rows to ensure we have all the necessary fields
        const cleanedData = parsed.data
          .filter(row => {
            // Keep rows that have valid numeric data for VAD values
            const valid = (
              typeof row.Valence === "number" &&
              typeof row.Arousal === "number" &&
              typeof row.Dominance === "number" &&
              row["Start Time (s)"] !== undefined
            );
            return valid;
          })
          .map(row => {
            // For each row, derive emotion from VAD values if not present
            // Determine the emotion based on the Valence/Arousal values
            let emotion = "neutral";
            if (row.Valence > 0.3 && row.Arousal > 0.3) emotion = "joy";
            else if (row.Valence > 0.3 && row.Arousal < -0.1) emotion = "peaceful";
            else if (row.Valence < -0.3 && row.Arousal > 0.3) emotion = "angry";
            else if (row.Valence < -0.3 && row.Arousal < -0.1) emotion = "sad";
            
            // Use "Start Time (s)" as the timepoint
            return {
              ...row,
              ChunkDiscreteEmotion: emotion
            };
          });
        
        console.log("Parsed data rows:", cleanedData.length);
        
        // If we have valid data, set it
        if (cleanedData.length > 0) {
          console.log("First cleaned row:", JSON.stringify(cleanedData[0]));
          setDataRows(cleanedData);
        } else {
          console.error("No valid data rows found in CSV");
        }
      })
      .catch(error => {
        console.error("Error fetching or parsing CSV:", error);
      });
  }, [csvPath]);

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

  // Finds the appropriate displacement value from the loaded maps
  const getDisplacementValueFromMaps = (v, u, timePoint) => {
    if (displacementMaps.length === 0 || !timeToEmotionMap) return null;
    
    // Find the two nearest time points
    const times = Object.keys(timeToEmotionMap).map(Number).sort((a, b) => a - b);
    if (times.length === 0) return null;
    
    // If only one time point is available, use it
    if (times.length === 1) {
      const time = times[0];
      const data = timeToEmotionMap[time];
      if (!data || !data.displacementValues) return null;
      
      // Check if the arrays are properly defined and have length
      if (!Array.isArray(data.displacementValues) || data.displacementValues.length === 0) return null;
      
      // Map v (0-1) to layers (0-32)
      const layerIdx = Math.min(Math.floor(v * data.displacementValues.length), data.displacementValues.length - 1);
      
      // Check if the layer exists and has values
      if (!data.displacementValues[layerIdx] || !Array.isArray(data.displacementValues[layerIdx]) || data.displacementValues[layerIdx].length === 0) return null;
      
      // Map u (0-1) to subdivisions (0-32)
      const subdivIdx = Math.min(Math.floor(u * data.displacementValues[layerIdx].length), data.displacementValues[layerIdx].length - 1);
      
      // One more null check before accessing the final value
      if (data.displacementValues[layerIdx][subdivIdx] === undefined) return null;
      
      return data.displacementValues[layerIdx][subdivIdx] / 25.0; // Normalize by the displacement scale
    }
    
    // Find the two closest time points for blending
    let lowerIdx = 0;
    while (lowerIdx < times.length - 1 && times[lowerIdx + 1] <= timePoint) {
      lowerIdx++;
    }
    
    const lowerTime = times[lowerIdx];
    const upperTime = lowerIdx < times.length - 1 ? times[lowerIdx + 1] : lowerTime;
    
    // If exact time point match, no blending needed
    if (lowerTime === upperTime || lowerTime === timePoint) {
      const data = timeToEmotionMap[lowerTime];
      if (!data || !data.displacementValues) return null;
      
      // Additional safety checks
      if (!Array.isArray(data.displacementValues) || data.displacementValues.length === 0) return null;
      
      const layerIdx = Math.min(Math.floor(v * data.displacementValues.length), data.displacementValues.length - 1);
      
      if (!data.displacementValues[layerIdx] || !Array.isArray(data.displacementValues[layerIdx]) || data.displacementValues[layerIdx].length === 0) return null;
      
      const subdivIdx = Math.min(Math.floor(u * data.displacementValues[layerIdx].length), data.displacementValues[layerIdx].length - 1);
      
      if (data.displacementValues[layerIdx][subdivIdx] === undefined) return null;
      
      return data.displacementValues[layerIdx][subdivIdx] / 25.0;
    }
    
    // Need to blend between two time points
    const lowerData = timeToEmotionMap[lowerTime];
    const upperData = timeToEmotionMap[upperTime];
    
    if (!lowerData || !upperData || !lowerData.displacementValues || !upperData.displacementValues) return null;
    
    // Additional array checks
    if (!Array.isArray(lowerData.displacementValues) || lowerData.displacementValues.length === 0) return null;
    if (!Array.isArray(upperData.displacementValues) || upperData.displacementValues.length === 0) return null;
    
    // Calculate blend factor (0-1)
    const blendFactor = (timePoint - lowerTime) / (upperTime - lowerTime);
    
    const layerIdxLower = Math.min(Math.floor(v * lowerData.displacementValues.length), lowerData.displacementValues.length - 1);
    const layerIdxUpper = Math.min(Math.floor(v * upperData.displacementValues.length), upperData.displacementValues.length - 1);
    
    // Check arrays exist before accessing length
    if (!lowerData.displacementValues[layerIdxLower] || !Array.isArray(lowerData.displacementValues[layerIdxLower]) || 
        lowerData.displacementValues[layerIdxLower].length === 0) return null;
    if (!upperData.displacementValues[layerIdxUpper] || !Array.isArray(upperData.displacementValues[layerIdxUpper]) || 
        upperData.displacementValues[layerIdxUpper].length === 0) return null;
        
    const subdivIdxLower = Math.min(Math.floor(u * lowerData.displacementValues[layerIdxLower].length), lowerData.displacementValues[layerIdxLower].length - 1);
    const subdivIdxUpper = Math.min(Math.floor(u * upperData.displacementValues[layerIdxUpper].length), upperData.displacementValues[layerIdxUpper].length - 1);
    
    // Final null checks
    if (lowerData.displacementValues[layerIdxLower][subdivIdxLower] === undefined || 
        upperData.displacementValues[layerIdxUpper][subdivIdxUpper] === undefined) return null;
    
    const lowerValue = lowerData.displacementValues[layerIdxLower][subdivIdxLower] / 25.0;
    const upperValue = upperData.displacementValues[layerIdxUpper][subdivIdxUpper] / 25.0;
    
    // Linear interpolation between the two values
    return lowerValue * (1 - blendFactor) + upperValue * blendFactor;
  };

  // Procedural displacement function as a fallback
  const displ = (a, v, u, emotion, dominance, timePoint) => {
    // First check if we have real displacement data
    let realDisplacement = null;
    try {
      realDisplacement = getDisplacementValueFromMaps(v, u, timePoint);
      // Amplify the real displacement but keep it smoother
      if (realDisplacement !== null) {
        realDisplacement *= 3.5; // Reduced from 5.0 for smoother appearance
      }
    } catch (error) {
      console.warn("Error getting displacement from maps, using fallback:", error);
      realDisplacement = null;
    }
    
    if (realDisplacement !== null) {
      return realDisplacement;
    }
    
    // Fallback to procedural generation with more refined patterns
    const vNorm = (v + 1.0) * 0.5;
    
    // Create texture patterns based on emotion but smoother
    let patternFrequency = 4; // Default value - reduced for smoother appearance
    let patternDepth = 2.0;   // Default value - reduced for smoother appearance
    
    if (emotion === 'joy') {
      patternFrequency = 6;
      patternDepth = 2.5;
    } else if (emotion === 'angry') {
      patternFrequency = 8;
      patternDepth = 3.0;
    } else if (emotion === 'sad') {
      patternFrequency = 4;
      patternDepth = 2.0;
    } else if (emotion === 'peaceful') {
      patternFrequency = 3;
      patternDepth = 1.8;
    }
    
    // Create patterns with smoother sine waves
    const k = patternFrequency + (1 - vNorm) * 2;
    const base = Math.sin(u * Math.PI * 2) * 0.5;
    
    // Smoother wave pattern 
    const wave1 = Math.sin(k * u * Math.PI);
    const wave2 = Math.sin((k * 0.5) * u * Math.PI + 0.2); // Lower frequency wave for smoother effect
    const spike = (wave1 * 0.7 + wave2 * 0.3); // Blend waves for smoother variation
    
    // Add smoother variations in height
    const smoothFeature = Math.sin(u * patternFrequency * Math.PI) * 0.6;
    
    // Adjust displacement based on emotion with moderate multipliers
    let emotionMultiplier = 3.0; // Default multiplier - reduced for smoother effect
    if (textureParams && emotion && textureParams[emotion]) {
      emotionMultiplier = textureParams[emotion].displacementScale * 3.0;
    }
    
    // Add texture-based noise with multiple frequencies for detail without sharpness
    let noiseFrequency = 0.4;
    if (textureParams && emotion && textureParams[emotion]) {
      noiseFrequency = textureParams[emotion].noiseFrequency * 1.2;
    }
    
    // Create smoother noise with multiple harmonics
    const noiseValue = 
      Math.sin(u * 30 * noiseFrequency) * Math.cos(v * 20 * noiseFrequency) * 1.0 + // Primary noise
      Math.sin(u * 45 * noiseFrequency) * Math.cos(v * 30 * noiseFrequency) * 0.5 + // Medium-frequency detail
      Math.sin(u * 15 * noiseFrequency) * Math.cos(v * 10 * noiseFrequency) * 0.8;  // Low-frequency variation
    
    // Combine all effects for a detailed but smoother texture
    return (base * (1 + a * patternDepth * spike) + smoothFeature * patternDepth * 0.7) * 
           (1 - vNorm) * emotionMultiplier + noiseValue;
  };

  // Function to get color based on emotion and intensity
  const getEmotionColor = (emotion, intensity = 1.0) => {
    if (!emotion || !emotionColors[emotion]) {
      return new THREE.Color(0xdddddd); // Default light gray
    }
    
    const baseColor = emotionColors[emotion].clone();
    
    // Apply intensity
    if (intensity < 1.0) {
      // Mix with white for lower intensity
      return baseColor.lerp(new THREE.Color(0xffffff), 1.0 - intensity);
    }
    
    return baseColor;
  };

  // Function to blend between two emotion colors
  const blendEmotionColors = (emotion1, emotion2, blendFactor) => {
    const color1 = getEmotionColor(emotion1);
    const color2 = getEmotionColor(emotion2);
    
    return color1.clone().lerp(color2, blendFactor);
  };

  // Update when currentEmotion changes to notify parent
  useEffect(() => {
    if (currentEmotion && onEmotionChange) {
      onEmotionChange(currentEmotion);
    }
  }, [currentEmotion, onEmotionChange]);

  useFrame(() => {
    if (!originalData || dataRows.length === 0 || !meshRef.current) return;

    const geo = meshRef.current.geometry;
    const innerGeo = innerRef.current.geometry;
    const pos = geo.attributes.position.array;
    const innerPos = innerGeo.attributes.position.array;
    const count = geo.attributes.position.count;
    const vThreshold = revealProgress;
    
    // Store vertex colors for blending
    if (!geo.attributes.color) {
      geo.setAttribute('color', new THREE.BufferAttribute(new Float32Array(count * 3), 3));
    }
    const colors = geo.attributes.color.array;
    
    // Current material
    const material = meshRef.current.material;
    material.vertexColors = true; // Enable vertex colors
    
    // Precompute the emotional segments for blending
    const emotionalSegments = [];
    let lastEmotion = null;
    let segmentStart = 0;
    
    for (let i = 0; i < dataRows.length; i++) {
      const row = dataRows[i];
      const emotion = row.ChunkDiscreteEmotion || "neutral";
      
      if (emotion !== lastEmotion) {
        if (lastEmotion !== null) {
          emotionalSegments.push({
            startIdx: segmentStart,
            endIdx: i - 1,
            emotion: lastEmotion,
            startTime: dataRows[segmentStart]["Start Time (s)"] || 0,
            endTime: row["Start Time (s)"] || 0
          });
        }
        
        lastEmotion = emotion;
        segmentStart = i;
      }
    }
    
    // Add the last segment
    if (lastEmotion !== null) {
      emotionalSegments.push({
        startIdx: segmentStart,
        endIdx: dataRows.length - 1,
        emotion: lastEmotion,
        startTime: dataRows[segmentStart]["Start Time (s)"] || 0,
        endTime: dataRows[dataRows.length - 1]["Start Time (s)"] || 0
      });
    }

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

      // Map v coordinate (0-1) to CSV data index
      const index = Math.floor(v * dataRows.length);
      const row = dataRows[Math.min(index, dataRows.length - 1)];
      const val = row.Valence ?? 0;
      const aro = row.Arousal ?? 0;
      const dom = row.Dominance ?? 0;
      const emotion = row.ChunkDiscreteEmotion || "neutral";
      const timePoint = row["Start Time (s)"] || 0;

      // Update current emotion for UI/display if this is the first vertex
      if (i === 0) {
        if (currentEmotion !== emotion) {
          setCurrentEmotion(emotion);
        }
      }
      
      // Find which emotional segment this vertex belongs to for color blending
      let vertexColor = getEmotionColor(emotion);
      
      // Find if we're in a transition area between two emotions
      for (let s = 0; s < emotionalSegments.length - 1; s++) {
        const currentSegment = emotionalSegments[s];
        const nextSegment = emotionalSegments[s + 1];
        
        const transitionStart = currentSegment.endIdx / dataRows.length;
        const transitionEnd = nextSegment.startIdx / dataRows.length;
        
        // If v is in transition area, blend colors
        if (v >= transitionStart && v <= transitionEnd) {
          const blendFactor = (v - transitionStart) / (transitionEnd - transitionStart);
          vertexColor = blendEmotionColors(
            currentSegment.emotion, 
            nextSegment.emotion, 
            blendFactor
          );
          break;
        }
      }
      
      // Store color in vertex color attribute
      colors[i * 3] = vertexColor.r;
      colors[i * 3 + 1] = vertexColor.g;
      colors[i * 3 + 2] = vertexColor.b;

      const d = displ(aro, val, u, emotion, dom, timePoint);
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
    geo.attributes.color.needsUpdate = true;
    
    // Ensure proper smooth normals
    geo.computeVertexNormals();
    innerGeo.attributes.position.needsUpdate = true;
    innerGeo.attributes.normal.needsUpdate = true;
    innerGeo.computeVertexNormals();
  });

  return (
    <>
      <pointLight position={[0, 0, 0]} intensity={800} distance={10000} color="#ffbb66" />
      {/* Add directional lights from multiple angles to highlight textures */}
      <directionalLight position={[10, 10, 10]} intensity={0.8} />
      <directionalLight position={[-10, -10, -10]} intensity={0.6} />
      <directionalLight position={[10, -10, 10]} intensity={0.5} />
      <spotLight 
        position={[20, 20, 20]} 
        angle={0.3} 
        penumbra={0.2} 
        intensity={1.0} 
        castShadow
      />
      <group ref={groupRef}>
        {/* Outer mesh */}
        <mesh ref={meshRef} castShadow receiveShadow>
          <cylinderGeometry
            args={[radiusTop, radiusBottom, height, radialSegments, heightSegments, true]}
          />
          <meshPhysicalMaterial
            color="white"
            roughness={0.4}
            metalness={0.2}
            transparent={true}
            opacity={0.9}
            side={THREE.DoubleSide}
            vertexColors={true}
            flatShading={false}
            clearcoat={0.4}
            clearcoatRoughness={0.2}
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
            roughness={0.5}
            transparent={true}
            opacity={0.3}
            side={THREE.BackSide}
            metalness={0.2}
          />
        </mesh>
      </group>
    </>
  );
});

const Scene = forwardRef(({ csvPath, onEmotionChange }, ref) => {
  return (
    <Canvas
      camera={{ position: [25, 5, 25], fov: 60 }}
      style={{ background: "#1a1a1a", width: "100vw", height: "100vh" }}
      shadows
    >
      <fog attach="fog" args={['#1a1a1a', 30, 90]} />
      <ambientLight intensity={0.2} />
      <directionalLight 
        position={[10, 10, 10]} 
        intensity={1.0} 
        castShadow
        shadow-mapSize-width={2048}
        shadow-mapSize-height={2048}
      />
      <hemisphereLight 
        skyColor="#ffffff" 
        groundColor="#303030" 
        intensity={0.3} 
      />
      <ColorCloud ref={ref} csvPath={csvPath} onEmotionChange={onEmotionChange} />
      <OrbitControls 
        minDistance={15}
        maxDistance={50}
        autoRotate
        autoRotateSpeed={0.7}
        enableDamping
        dampingFactor={0.05}
      />
    </Canvas>
  );
});

export default Scene;
