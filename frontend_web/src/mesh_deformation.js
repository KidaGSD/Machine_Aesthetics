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
  // Add texture management state
  const [currentEmotion, setCurrentEmotion] = useState("neutral");
  const [activeTextures, setActiveTextures] = useState({});
  const [textureLoading, setTextureLoading] = useState(false);
  // Add a ref to track component mounting state
  const isMountedRef = useRef(true);
  // Add lastPaths to track changes to paths
  const lastPathsRef = useRef({ csvPath, amplitudeCsvPath, emotionCurvesPath });

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
      console.log("Starting reveal animation");
      setRevealProgress(0);
    }
  }));

  useFrame(() => {
    if (meshRef.current) {
      meshRef.current.rotation.y += 0.002;
    }
    // Only update reveal progress if the component is still mounted
    if (revealProgress < 1.0 && isMountedRef.current) {
      setRevealProgress((prev) => Math.min(prev + 0.003, 1.0));
    }
  });

  // Track component unmounting to prevent state updates
  useEffect(() => {
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  // Reset state when paths change
  useEffect(() => {
    const currentPaths = { csvPath, amplitudeCsvPath, emotionCurvesPath };
    const lastPaths = lastPathsRef.current;
    
    // Check if any paths changed
    if (currentPaths.csvPath !== lastPaths.csvPath || 
        currentPaths.amplitudeCsvPath !== lastPaths.amplitudeCsvPath ||
        currentPaths.emotionCurvesPath !== lastPaths.emotionCurvesPath) {
      
      console.log("Path changed, resetting state");
      // Reset states
      setDataRows([]);
      setAmplitudes([]);
      setEmotionCurves(null);
      setGeneratedGeometry(null);
      setRevealProgress(0);
      
      // Update lastPaths
      lastPathsRef.current = currentPaths;
    }
  }, [csvPath, amplitudeCsvPath, emotionCurvesPath]);

  const fetchWithNoCache = (url) => `${url}?t=${Date.now()}`;

  useEffect(() => {
    if (!csvPath) return;
    console.log("Fetching data from:", csvPath);
    fetch(csvPath)
      .then(res => {
        if (!res.ok) {
          throw new Error(`Failed to load ${csvPath}: ${res.status} ${res.statusText}`);
        }
        return res.text();
      })
      .then(text => {
        const cleanText = text.replace(/^﻿/, '');
        const parsed = Papa.parse(cleanText, { header: true, dynamicTyping: true, skipEmptyLines: true });
        const cleaned = parsed.data.filter(row => row.emotion);
        if (cleaned.length === 0) {
          console.warn("No emotion data found in CSV");
        }
        console.log("Loaded emotion data:", cleaned);
        setDataRows(cleaned);
      })
      .catch(error => {
        console.error("Error loading emotion data:", error);
      });
  }, [csvPath]);

  useEffect(() => {
    if (!amplitudeCsvPath) return;
    console.log("Fetching amplitude data from:", amplitudeCsvPath);
    fetch(amplitudeCsvPath)
      .then(res => {
        if (!res.ok) {
          throw new Error(`Failed to load ${amplitudeCsvPath}: ${res.status} ${res.statusText}`);
        }
        return res.text();
      })
      .then(text => {
        const parsed = Papa.parse(text, { header: true, dynamicTyping: true, skipEmptyLines: true });
        const amps = parsed.data.map(row => parseFloat(row.arousal ?? 0));
        console.log("Loaded amplitude data:", amps.length);
        setAmplitudes(amps);
      })
      .catch(error => {
        console.error("Error loading amplitude data:", error);
      });
  }, [amplitudeCsvPath]);

  useEffect(() => {
    if (!emotionCurvesPath) return;
    console.log("Fetching emotion curves from:", emotionCurvesPath);
    fetch(emotionCurvesPath)
      .then(res => {
        if (!res.ok) {
          throw new Error(`Failed to load ${emotionCurvesPath}: ${res.status} ${res.statusText}`);
        }
        return res.json();
      })
      .then(data => {
        console.log("Loaded emotion curves:", Object.keys(data));
        setEmotionCurves(data);
      })
      .catch(error => {
        console.error("Error loading emotion curves:", error);
        // 创建一个默认的圆形曲线结构作为应急方案
        const defaultCurves = {
          "j": Array.from({length: 36}, (_, i) => {
            const angle = (i / 36) * Math.PI * 2;
            return [Math.cos(angle) * 20, Math.sin(angle) * 20];
          }),
          "s": Array.from({length: 36}, (_, i) => {
            const angle = (i / 36) * Math.PI * 2;
            return [Math.cos(angle) * 15, Math.sin(angle) * 15];
          }),
          "c": Array.from({length: 36}, (_, i) => {
            const angle = (i / 36) * Math.PI * 2;
            return [Math.cos(angle) * 18, Math.sin(angle) * 18];
          }),
        };
        setEmotionCurves(defaultCurves);
      });
  }, [emotionCurvesPath]);

  useEffect(() => {
    if (!dataRows.length || !amplitudes.length || !emotionCurves) return;
    console.log("Processing data with", dataRows.length, "rows,", amplitudes.length, "amplitudes, and emotion curves");

    // 增强的情感映射，支持更多变体
    const emotionMap = {
      joy: "j", 
      sadness: "s", sad: "s",
      anger: "a", angry: "a", 
      fear: "f", fearful: "f",
      surprise: "su", surprised: "su",
      neutral: "c", calm: "c", peaceful: "c",
      disgust: "d", disgusted: "d",
      serene: "c", // 映射到calm
      // 默认为neutral/calm
      undefined: "c", null: "c"
    };

    // 更健壮的情感获取
    const getEmotionSafely = (emotion) => {
      // 转换为小写并去除空格
      const processedEmotion = (emotion || "").trim().toLowerCase();
      // 获取映射，如果没有则使用neutral
      return emotionMap[processedEmotion] || "c";
    };

    try {
      console.log("Processing emotions:", dataRows.map(row => row.emotion));
      
      // 确保我们有两个情感
      if (dataRows.length < 2) {
        console.warn("Less than 2 emotions found, using defaults");
        dataRows.push({...dataRows[0], emotion: "joy"});
      }

      const topEmotion = dataRows[0].emotion?.trim().toLowerCase() || "neutral";
      const bottomEmotion = dataRows[1].emotion?.trim().toLowerCase() || "joy";
      
      console.log(`Top emotion: ${topEmotion}, Bottom emotion: ${bottomEmotion}`);
      
      const labelA = getEmotionSafely(topEmotion);
      const labelB = getEmotionSafely(bottomEmotion);
      
      console.log(`Using curve labels: ${labelA} and ${labelB}`);
      
      // 安全地获取曲线，并确保当映射不存在时有备选方案
      let rawA = emotionCurves[labelA]?.map(([x, y]) => new THREE.Vector3(x, 0, y));
      let rawB = emotionCurves[labelB]?.map(([x, y]) => new THREE.Vector3(x, 0, y));
      
      // 如果曲线不存在，使用默认值
      if (!rawA || !rawB) {
        console.warn("Using fallback curves");
        
        // 尝试找到任何可用的曲线
        const availableCurves = Object.keys(emotionCurves || {});
        const defaultKey = availableCurves.length > 0 ? availableCurves[0] : null;
        
        if (!rawA && defaultKey) {
          rawA = emotionCurves[defaultKey].map(([x, y]) => new THREE.Vector3(x, 0, y));
        } else if (!rawA) {
          // 创建一个圆形作为备选
          rawA = Array.from({length: 36}, (_, i) => {
            const angle = (i / 36) * Math.PI * 2;
            return new THREE.Vector3(Math.cos(angle) * 30, 0, Math.sin(angle) * 30);
          });
        }
        
        if (!rawB && defaultKey) {
          rawB = emotionCurves[defaultKey].map(([x, y]) => new THREE.Vector3(x, 0, y));
        } else if (!rawB) {
          // 创建一个形状不同的圆形
          rawB = Array.from({length: 36}, (_, i) => {
            const angle = (i / 36) * Math.PI * 2;
            return new THREE.Vector3(Math.cos(angle) * 25, 0, Math.sin(angle) * 25);
          });
        }
      }

      const centroid = pts => pts.reduce((sum, p) => sum.add(p), new THREE.Vector3()).divideScalar(pts.length);
      const centerA = centroid(rawA);
      const centerB = centroid(rawB);

      // 使用安全的值获取
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
      
      // 为底部情感获取颜色，增加健壮性处理
      const getColorForEmotion = (emotion) => {
        const processedEmotion = (emotion || "").trim().toLowerCase();
        // 检查是否直接存在于emotionColors中
        if (emotionColors[processedEmotion]) {
          return emotionColors[processedEmotion];
        }
        
        // 尝试查找相似情感
        const similarEmotions = {
          surprised: "surprise", 
          angry: "anger", 
          sad: "sadness",
          fearful: "fear",
          disgusted: "disgust",
          peaceful: "neutral",
          serene: "neutral",
          calm: "neutral"
        };
        
        // 查找相似情感
        if (similarEmotions[processedEmotion] && emotionColors[similarEmotions[processedEmotion]]) {
          return emotionColors[similarEmotions[processedEmotion]];
        }
        
        // 使用默认颜色
        console.warn(`No color for emotion: ${processedEmotion}, using default`);
        return new THREE.Color('#00CED1'); // 默认蓝色
      };
      
      const baseColor = getColorForEmotion(bottomEmotion);
      const baseHSL = {};
      baseColor.getHSL(baseHSL);
      
      // 添加颜色日志
      console.log(`Using base color HSL(${baseHSL.h.toFixed(2)}, ${baseHSL.s.toFixed(2)}, ${baseHSL.l.toFixed(2)}) for emotion: ${bottomEmotion}`);

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
      console.log("Generated new geometry");
      setGeneratedGeometry(geometry);
    } catch (error) {
      console.error("Error processing emotions:", error);
    }
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

const Scene = forwardRef(({ csvPath, amplitudeCsvPath, emotionCurvesPath, onError }, ref) => {
  // Add error handling to expose errors
  useEffect(() => {
    const handleError = (event) => {
      console.error("Three.js error:", event.message);
      if (onError) {
        onError(new Error(event.message));
      }
    };
    
    window.addEventListener('error', handleError);
    return () => window.removeEventListener('error', handleError);
  }, [onError]);

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