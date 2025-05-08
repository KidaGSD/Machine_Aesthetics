import React, { useRef, useEffect, useState } from 'react';
import { OrbitControls } from '@react-three/drei';
import { Canvas, useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import Papa from 'papaparse';

// Simple WebGL detector function
const hasWebGL = () => {
  try {
    const canvas = document.createElement('canvas');
    return !!(window.WebGLRenderingContext && 
      (canvas.getContext('webgl') || canvas.getContext('experimental-webgl')));
  } catch (e) {
    return false;
  }
};

const EmotionCurveMorphContent = ({ emotionCurves, emotionA, emotionB }) => {
  const groupRef = useRef();
  const [lines, setLines] = useState([]);
  const [animationStage, setAnimationStage] = useState(0);
  const [linesRevealed, setLinesRevealed] = useState(0);
  const totalLinesRef = useRef(0);
  // Add refs to track animation timers
  const animationTimerRef = useRef(null);
  const animationFrameRef = useRef(null);
  // Track if component is mounted to prevent updates after unmount
  const isMountedRef = useRef(true);

  // Cleanup function to cancel all animations and timers
  const cleanupAnimations = () => {
    if (animationTimerRef.current) {
      clearTimeout(animationTimerRef.current);
      animationTimerRef.current = null;
    }
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }
  };

  // Component lifecycle management
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      cleanupAnimations();
    };
  }, []);

  // Reset animation when emotions or curves change, but only if mounted
  useEffect(() => {
    if (isMountedRef.current) {
      // Clean up existing animations first
      cleanupAnimations();
      
      // Reset animation state
      setAnimationStage(0);
      setLinesRevealed(0);
    }
  }, [emotionA, emotionB, emotionCurves]);

  // Modified animation system with better timing and cleanup
  useEffect(() => {
    // Skip if component is unmounting
    if (!isMountedRef.current) return;
    
    // Clean up any existing timers
    cleanupAnimations();
    
    if (animationStage === 0) {
      // First stage: Show top shape only - delay before next stage
      animationTimerRef.current = setTimeout(() => {
        if (isMountedRef.current) setAnimationStage(1);
      }, 800);
    } else if (animationStage === 1) {
      // Second stage: Show top and bottom shapes - delay before revealing lines
      animationTimerRef.current = setTimeout(() => {
        if (isMountedRef.current) setAnimationStage(2);
      }, 800);
    } else if (animationStage === 2 && linesRevealed < totalLinesRef.current) {
      // Third stage: Reveal connecting lines gradually
      animationTimerRef.current = setTimeout(() => {
        if (isMountedRef.current) {
          setLinesRevealed(prev => Math.min(prev + 1, totalLinesRef.current));
        }
      }, 30);
    } else if (animationStage === 2 && linesRevealed === totalLinesRef.current) {
      // When all lines are revealed, pause before restarting
      animationTimerRef.current = setTimeout(() => {
        // Set a much longer delay before restarting animation to reduce flashing
        animationTimerRef.current = setTimeout(() => {
          if (isMountedRef.current) {
            setAnimationStage(0);
            setLinesRevealed(0);
          }
        }, 8000); // 8-second pause at completed state
      }, 1500);
    }
    
    // Cleanup function to prevent memory leaks and timing issues
    return cleanupAnimations;
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

  // Add slow rotation animation with requestAnimationFrame instead of useFrame
  useFrame(() => {
    if (groupRef.current && isMountedRef.current) {
      // Use a smaller increment for smoother rotation
      groupRef.current.rotation.y += 0.001;
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

// 2D Canvas fallback visualization
const Canvas2DFallback = ({ emotionCurves, emotionA, emotionB }) => {
  const canvasRef = useRef(null);
  const [angle, setAngle] = useState(0);
  const animationRef = useRef(null);
  
  // Main drawing function
  const drawCanvas = (ctx, width, height, rotationAngle) => {
    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = "#000000";
    ctx.fillRect(0, 0, width, height);
    
    const centerX = width / 2;
    const centerY = height / 2;
    const scale = Math.min(width, height) / 60;
    
    // Draw only if we have valid curves
    if (emotionCurves && emotionCurves[emotionA] && emotionCurves[emotionB]) {
      // Apply rotation transformation
      ctx.save();
      ctx.translate(centerX, centerY);
      ctx.rotate(rotationAngle);
      ctx.translate(-centerX, -centerY);
      
      // Top curve (first emotion)
      const topCurve = emotionCurves[emotionA];
      ctx.beginPath();
      ctx.strokeStyle = "#88ccff";
      ctx.lineWidth = 2;
      
      // Calculate center point of all points for centering
      let sumX = 0, sumY = 0;
      topCurve.forEach(point => {
        sumX += point[0];
        sumY += point[1];
      });
      const offsetX = sumX / topCurve.length;
      const offsetY = sumY / topCurve.length;
      
      topCurve.forEach((point, i) => {
        const x = centerX + (point[0] - offsetX) * scale;
        const y = centerY - 30 + (point[1] - offsetY) * scale;
        
        if (i === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      });
      // Close the path
      if (topCurve.length > 0) {
        const firstPoint = topCurve[0];
        const x = centerX + (firstPoint[0] - offsetX) * scale;
        const y = centerY - 30 + (firstPoint[1] - offsetY) * scale;
        ctx.lineTo(x, y);
      }
      ctx.stroke();
      
      // Bottom curve (second emotion)
      const bottomCurve = emotionCurves[emotionB];
      ctx.beginPath();
      ctx.strokeStyle = "#ffccaa";
      ctx.lineWidth = 2;
      
      // Calculate center for bottom curve
      sumX = 0;
      sumY = 0;
      bottomCurve.forEach(point => {
        sumX += point[0];
        sumY += point[1];
      });
      const offsetBX = sumX / bottomCurve.length;
      const offsetBY = sumY / bottomCurve.length;
      
      bottomCurve.forEach((point, i) => {
        const x = centerX + (point[0] - offsetBX) * scale;
        const y = centerY + 30 + (point[1] - offsetBY) * scale;
        
        if (i === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      });
      // Close the path
      if (bottomCurve.length > 0) {
        const firstPoint = bottomCurve[0];
        const x = centerX + (firstPoint[0] - offsetBX) * scale;
        const y = centerY + 30 + (firstPoint[1] - offsetBY) * scale;
        ctx.lineTo(x, y);
      }
      ctx.stroke();
      
      // Draw connecting lines between the shapes
      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 1;
      ctx.globalAlpha = 0.5;
      
      const numLines = Math.min(topCurve.length, bottomCurve.length);
      for (let i = 0; i < numLines; i += 3) { // Draw every third line for cleaner look
        const topPoint = topCurve[i];
        const bottomPoint = bottomCurve[i];
        
        const x1 = centerX + (topPoint[0] - offsetX) * scale;
        const y1 = centerY - 30 + (topPoint[1] - offsetY) * scale;
        const x2 = centerX + (bottomPoint[0] - offsetBX) * scale;
        const y2 = centerY + 30 + (bottomPoint[1] - offsetBY) * scale;
        
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
      }
      
      ctx.globalAlpha = 1.0;
      ctx.restore();
    } else {
      // Draw placeholder shapes if no curves
      ctx.beginPath();
      ctx.strokeStyle = "#88ccff";
      ctx.lineWidth = 2;
      ctx.arc(centerX, centerY - 30, 30, 0, Math.PI * 2);
      ctx.stroke();
      
      ctx.beginPath();
      ctx.strokeStyle = "#ffccaa";
      ctx.lineWidth = 2;
      ctx.arc(centerX, centerY + 30, 30, 0, Math.PI * 2);
      ctx.stroke();
      
      // Draw text indicating missing data
      ctx.fillStyle = "#ffffff";
      ctx.font = "12px Arial";
      ctx.textAlign = "center";
      ctx.fillText("Shape Data Missing", centerX, centerY);
    }
  };
  
  // Animation loop function
  const animateCanvas = () => {
    if (canvasRef.current) {
      const canvas = canvasRef.current;
      const ctx = canvas.getContext('2d');
      
      // Update rotation angle - use a smaller increment for smoother rotation
      setAngle(prev => (prev + 0.002) % (Math.PI * 2));
      
      // Draw with current angle
      drawCanvas(ctx, canvas.width, canvas.height, angle);
      
      // Continue animation - use requestAnimationFrame for smoother animation
      animationRef.current = requestAnimationFrame(animateCanvas);
    }
  };
  
  // Setup canvas and start animation
  useEffect(() => {
    const canvas = canvasRef.current;
    if (canvas) {
      const ctx = canvas.getContext('2d');
      
      // Set canvas dimensions based on actual display size for sharper rendering
      const setCanvasDimensions = () => {
        const rect = canvas.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;
        canvas.width = rect.width * dpr;
        canvas.height = rect.height * dpr;
        ctx.scale(dpr, dpr);
      };
      
      // Set dimensions initially
      setCanvasDimensions();
      
      // Handle resize events to adjust canvas
      const handleResize = () => {
        setCanvasDimensions();
        drawCanvas(ctx, canvas.width, canvas.height, angle);
      };
      
      window.addEventListener('resize', handleResize);
      
      // Start animation
      animationRef.current = requestAnimationFrame(animateCanvas);
      
      // Cleanup animation on unmount
      return () => {
        window.removeEventListener('resize', handleResize);
        if (animationRef.current) {
          cancelAnimationFrame(animationRef.current);
        }
      };
    }
  }, []);
  
  // Redraw when the emotion curves data changes
  useEffect(() => {
    // Only trigger a redraw, don't restart the animation
    if (canvasRef.current) {
      const ctx = canvasRef.current.getContext('2d');
      drawCanvas(ctx, canvasRef.current.width, canvasRef.current.height, angle);
    }
  }, [emotionCurves, emotionA, emotionB]);
  
  return (
    <canvas 
      ref={canvasRef}
      style={{
        width: '100%',
        height: '100%',
        borderRadius: '8px',
        background: 'black'
      }}
    />
  );
};

const EmotionCurveMorph = ({ emotionCurvesPath, top2CsvPath }) => {
  // Use refs to store current path values to prevent effect re-runs
  const pathsRef = useRef({ emotionCurvesPath, top2CsvPath });
  const [emotionCurves, setEmotionCurves] = useState(null);
<<<<<<< Updated upstream
  const [emotionLabels, setEmotionLabels] = useState(["j", "s"]);

  useEffect(() => {
    const loadAll = async () => {
      try {
        const [csvText, json] = await Promise.all([
          fetch(`${top2CsvPath}?t=${Date.now()}`).then(res => res.text()),
          fetch(`${emotionCurvesPath}?t=${Date.now()}`).then(res => res.json())
        ]);

=======
  const [emotionLabels, setEmotionLabels] = useState(["c", "j"]); // Default to calm/joy
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  // Check WebGL support once
  const [webGLSupported] = useState(() => hasWebGL());
  
  // Update path refs when props change
  useEffect(() => {
    pathsRef.current = { emotionCurvesPath, top2CsvPath };
  }, [emotionCurvesPath, top2CsvPath]);
  
  // Load data only once at component mount or when paths actually change
  useEffect(() => {
    let isMounted = true;
    const loadData = async () => {
      try {
        setIsLoading(true);
        if (!pathsRef.current.emotionCurvesPath || !pathsRef.current.top2CsvPath) {
          throw new Error("Missing required file paths");
        }
        
        // Avoid excessive logging
        if (process.env.NODE_ENV === 'development') {
          console.log("Loading data from:", {
            emotionCurvesPath: pathsRef.current.emotionCurvesPath,
            top2CsvPath: pathsRef.current.top2CsvPath
          });
        }
        
        const [csvResponse, jsonResponse] = await Promise.all([
          fetch(pathsRef.current.top2CsvPath),
          fetch(pathsRef.current.emotionCurvesPath)
        ]);
        
        if (!csvResponse.ok || !jsonResponse.ok) {
          throw new Error("Failed to load required data files");
        }
        
        const csvText = await csvResponse.text();
        const json = await jsonResponse.json();
        
        // Skip state updates if component unmounted
        if (!isMounted) return;
        
        // Process the CSV data
>>>>>>> Stashed changes
        const parsed = Papa.parse(csvText, { header: true });
        const rows = parsed.data.filter(r => r.emotion && r.emotion.length > 0);
        
        const emotionMap = {
<<<<<<< Updated upstream
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
=======
          joy: "j", sad: "s", angry: "a", fear: "f",
          surprise: "su", neutral: "c", disgust: "d",
          peaceful: "c", serene: "se", calm: "c",
          happy: "j", sadness: "s", anger: "a", fearful: "f",
          surprised: "su", disgusted: "d"
        };
        
        // Get the emotions from the data or use defaults
        const emotionA = rows[0]?.emotion?.trim().toLowerCase() || "neutral";
        const emotionB = rows[1]?.emotion?.trim().toLowerCase() || "joy";
        
        const labelA = emotionMap[emotionA] || "c";
        const labelB = emotionMap[emotionB] || "j";
        
        if (!json[labelA] || !json[labelB]) {
          // Create default curves
          const defaultCurves = {
            "j": Array.from({length: 36}, (_, i) => [Math.cos(i/36*Math.PI*2)*20, Math.sin(i/36*Math.PI*2)*20]),
            "s": Array.from({length: 36}, (_, i) => [Math.cos(i/36*Math.PI*2)*15, Math.sin(i/36*Math.PI*2)*15]),
            "c": Array.from({length: 36}, (_, i) => [Math.cos(i/36*Math.PI*2)*18, Math.sin(i/36*Math.PI*2)*18])
          };
          
          setEmotionCurves(defaultCurves);
          setEmotionLabels(["c", "j"]);
        } else {
          setEmotionCurves(json);
          setEmotionLabels([labelA, labelB]);
        }
      } catch (err) {
        if (isMounted) {
          console.error("Error loading data:", err);
          setError(`Failed to load visualization data: ${err.message}`);
          
          // Set default curves on error
          const defaultCurves = {
            "j": Array.from({length: 36}, (_, i) => [Math.cos(i/36*Math.PI*2)*20, Math.sin(i/36*Math.PI*2)*20]),
            "s": Array.from({length: 36}, (_, i) => [Math.cos(i/36*Math.PI*2)*15, Math.sin(i/36*Math.PI*2)*15]),
            "c": Array.from({length: 36}, (_, i) => [Math.cos(i/36*Math.PI*2)*18, Math.sin(i/36*Math.PI*2)*18])
          };
          
          setEmotionCurves(defaultCurves);
          setEmotionLabels(["c", "j"]);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };
    
    loadData();
    
    return () => {
      isMounted = false;
    };
  }, [emotionCurvesPath, top2CsvPath]);
  
  // Display error message if any
  if (error) {
    return (
      <div style={{ 
        color: 'red', 
        padding: '10px', 
        textAlign: 'center', 
        background: '#222'
      }}>
        {error}
      </div>
    );
  }
  
  // Show loading state if data is not ready
  if (!emotionCurves) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100%', 
        color: '#888',
        background: '#111'
      }}>
        Loading shapes...
      </div>
    );
  }
  
  // Render either 3D or 2D version based on WebGL support
  if (webGLSupported) {
    try {
      return (
        <div style={{ width: '100%', height: '100%' }}>
          <Canvas
            camera={{ position: [0, 0, 70], fov: 50 }}
            style={{ background: '#000000' }}
          >
            <EmotionCurveMorphContent
              emotionCurves={emotionCurves}
              emotionA={emotionLabels[0]}
              emotionB={emotionLabels[1]}
            />
            <OrbitControls enableZoom={false} enablePan={false} />
          </Canvas>
        </div>
      );
    } catch (e) {
      console.error("Error rendering WebGL version:", e);
      // Fall back to 2D if 3D rendering fails
      return (
        <div style={{ width: '100%', height: '100%' }}>
          <div style={{
            padding: '4px',
            background: 'rgba(255,150,0,0.2)',
            color: '#ccc',
            fontSize: '10px',
            textAlign: 'center'
          }}>
            Using 2D fallback visualization (WebGL error)
          </div>
          <Canvas2DFallback
            emotionCurves={emotionCurves}
            emotionA={emotionLabels[0]}
            emotionB={emotionLabels[1]}
          />
        </div>
      );
    }
  } else {
    // Use 2D Canvas for browsers without WebGL
    return (
      <div style={{ width: '100%', height: '100%' }}>
        <div style={{
          padding: '4px',
          background: 'rgba(255,150,0,0.2)',
          color: '#ccc',
          fontSize: '10px',
          textAlign: 'center'
        }}>
          Using 2D fallback visualization (WebGL not supported)
        </div>
        <Canvas2DFallback
          emotionCurves={emotionCurves}
          emotionA={emotionLabels[0]}
          emotionB={emotionLabels[1]}
        />
      </div>
    );
  }
>>>>>>> Stashed changes
};

export default EmotionCurveMorph;
