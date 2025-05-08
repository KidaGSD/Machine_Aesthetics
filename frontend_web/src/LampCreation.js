import React, { useState, useRef, useEffect, useMemo } from "react";
import "./LampCreation.css";
import Scene from "./mesh_deformation";
import EmotionCurveMorph from "./EmotionCurveMorph";
import Papa from "papaparse";
<<<<<<< Updated upstream
=======
import VectorSpaceVisualization from "./components/VectorSpaceVisualization";
// Import the configuration
import { BACKEND_URL, TEXTURE_PATHS, getFullBackendPath } from "./config";
import { getEmotionColor } from './emotionColors';
// Import the test functions
import { testBackendConnection, testFileAccess } from './testBackend';

// Default emotions to use when none are available
const DEFAULT_EMOTIONS = ["serene", "joy"];
>>>>>>> Stashed changes

const LampCreation = () => {
  const [audioFile, setAudioFile] = useState(null);
  const [audioObjectUrl, setAudioObjectUrl] = useState(null); // Add state for audio object URL
  const [loading, setLoading] = useState(false);
  const [sceneKey, setSceneKey] = useState(0);
  const sceneRef = useRef();
<<<<<<< Updated upstream
  const [topEmotions, setTopEmotions] = useState([]);
=======
  
  // Try to load saved emotions from localStorage or use defaults
  const initialEmotions = (() => {
    try {
      const saved = localStorage.getItem('topEmotions');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length === 2) {
          console.log("🔄 Using saved emotions from localStorage:", parsed);
          return parsed;
        }
      }
    } catch (e) {
      console.warn("Failed to load emotions from localStorage");
    }
    return DEFAULT_EMOTIONS;
  })();
  
  const [topEmotions, setTopEmotions] = useState(initialEmotions);
  const [errorMessage, setErrorMessage] = useState('');
  const [resultPaths, setResultPaths] = useState({}); // Store paths from backend
  const [textureEnabled, setTextureEnabled] = useState(true); // Add texture toggle state
  const [currentTextureInfo, setCurrentTextureInfo] = useState(null); // Store full texture info
  const [currentColors, setCurrentColors] = useState({
    topColor: null,
    bottomColor: null
  }); // Store current colors
  const audioRef = useRef(null);
  const [showScrollIndicator, setShowScrollIndicator] = useState(true);
  const [analysisComplete, setAnalysisComplete] = useState(false); // Track if analysis is complete
  
  // Version identifier to verify component mounting
  console.log("🔍 DEBUG: LampCreation component mounted (v2)");
  
  // Use configuration for backend URL instead of hardcoding
  // const backendUrl = "http://localhost:5001";

  // Create and manage audio object URL
  useEffect(() => {
    // Create object URL when audioFile changes
    if (audioFile) {
      const url = URL.createObjectURL(audioFile);
      setAudioObjectUrl(url);
      
      // Clean up function to revoke URL when component unmounts or audioFile changes
      return () => {
        URL.revokeObjectURL(url);
      };
    }
  }, [audioFile]);

  // Add scroll event listener to hide indicator after user scrolls
  useEffect(() => {
    const handleScroll = () => {
      if (window.scrollY > 100) {
        setShowScrollIndicator(false);
      } else {
        setShowScrollIndicator(true);
      }
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);
>>>>>>> Stashed changes

  // Add diagnostics on component mount
  useEffect(() => {
    console.log("🔍 Running diagnostic tests for backend connectivity...");
    
    // Test backend connection
    testBackendConnection().then(success => {
      if (success) {
        console.log("✅ Backend connection test passed");
      } else {
        console.error("❌ Backend connection test failed - check backend server is running on port 5001");
        setErrorMessage("Backend connection error. Please check if the server is running.");
      }
    });
    
    // Test important file access
    const filesToTest = [
      "/emotions/emotion_curves.json",
      "/data/output/top2_emotion_summary.csv"
    ];
    
    filesToTest.forEach(file => {
      testFileAccess(file).then(success => {
        if (success) {
          console.log(`✅ File access test passed for ${file}`);
        } else {
          console.error(`❌ File access test failed for ${file}`);
          setErrorMessage(prev => prev || `Failed to access required file: ${file}`);
        }
      });
    });
    
  }, []);

  // Create a more robust AudioPlayer component that handles remounting
  const AudioPlayer = React.memo(({ file, objectUrl }) => {
    // Keep a local copy of the file and URL
    const [localFile, setLocalFile] = useState(file);
    const [localObjectUrl, setLocalObjectUrl] = useState(objectUrl);
    const audioRef = useRef(null);
    
    // Track playback state to restore after remounting
    const [playbackTime, setPlaybackTime] = useState(0);
    const [isPlaying, setIsPlaying] = useState(false);
    
    // Update local state when props change
    useEffect(() => {
      if (file && objectUrl) {
        console.log("🔄 AudioPlayer received new file:", file.name);
        setLocalFile(file);
        setLocalObjectUrl(objectUrl);
        
        // Store filename in sessionStorage to persist across renders
        sessionStorage.setItem('audioFilename', file.name);
      }
    }, [file, objectUrl]);
    
    // Restore playback state from session storage on mount
    useEffect(() => {
      try {
        const savedState = sessionStorage.getItem('audioPlaybackState');
        if (savedState) {
          const { time, playing } = JSON.parse(savedState);
          setPlaybackTime(time || 0);
          setIsPlaying(playing || false);
        }
      } catch (e) {
        console.warn("Failed to restore audio playback state", e);
      }
    }, []);
    
    // Apply saved playback state after the audio element is created
    useEffect(() => {
      if (audioRef.current && localObjectUrl) {
        // Set the saved playback position
        if (playbackTime > 0) {
          audioRef.current.currentTime = playbackTime;
        }
        
        // Auto-resume if it was playing
        if (isPlaying) {
          audioRef.current.play().catch(e => {
            console.log("Auto-play prevented by browser policy:", e);
          });
        }
      }
    }, [audioRef.current, localObjectUrl, playbackTime, isPlaying]);
    
    // Save playback state to session storage when it changes
    useEffect(() => {
      if (audioRef.current) {
        // Set up event listeners to track playback state
        const handleTimeUpdate = () => {
          const time = audioRef.current.currentTime;
          setPlaybackTime(time);
          sessionStorage.setItem('audioPlaybackState', JSON.stringify({ 
            time, 
            playing: !audioRef.current.paused 
          }));
        };
        
        const handlePlay = () => {
          setIsPlaying(true);
          sessionStorage.setItem('audioPlaybackState', JSON.stringify({ 
            time: audioRef.current.currentTime, 
            playing: true 
          }));
        };
        
        const handlePause = () => {
          setIsPlaying(false);
          sessionStorage.setItem('audioPlaybackState', JSON.stringify({ 
            time: audioRef.current.currentTime, 
            playing: false 
          }));
        };
        
        // Add event listeners
        audioRef.current.addEventListener('timeupdate', handleTimeUpdate);
        audioRef.current.addEventListener('play', handlePlay);
        audioRef.current.addEventListener('pause', handlePause);
        
        // Clean up listeners on unmount
        return () => {
          if (audioRef.current) {
            audioRef.current.removeEventListener('timeupdate', handleTimeUpdate);
            audioRef.current.removeEventListener('play', handlePlay);
            audioRef.current.removeEventListener('pause', handlePause);
          }
        };
      }
    }, [audioRef.current]);
    
    // If we have no file or URL, try to show a message based on session storage
    if (!localFile || !localObjectUrl) {
      const savedFilename = sessionStorage.getItem('audioFilename');
      if (savedFilename) {
        return (
          <div className="audio-player-placeholder" style={{ marginTop: "15px", padding: "10px", background: "#333", borderRadius: "5px", color: "#aaa" }}>
            <p>Audio file "{savedFilename}" is being processed...</p>
          </div>
        );
      }
      return null;
    }
    
    return (
      <div className="audio-player" style={{ marginTop: "15px", width: "100%" }}>
        <audio 
          ref={audioRef}
          controls 
          src={localObjectUrl}
          style={{ width: "100%" }}
        />
      </div>
    );
  });

  const handleAudioChange = async (event) => {
    const file = event.target.files[0];
    if (file) {
      setAudioFile(file);
      setLoading(true);
<<<<<<< Updated upstream
=======
      setErrorMessage('');
      setResultPaths({}); // Clear previous results
      setAnalysisComplete(false); // Reset analysis state
      // Force Scene recreation
      setSceneKey(prevKey => prevKey + 1);
>>>>>>> Stashed changes

      const formData = new FormData();
      formData.append("file", file);

      try {
<<<<<<< Updated upstream
        const response = await fetch("http://localhost:5001/upload-audio", {
=======
        // More detailed logging for debugging
        console.log("Preparing to send audio file:", file.name, "Size:", file.size, "Type:", file.type);
        console.log("Sending request to:", `${BACKEND_URL}/analyze`);
        
        const response = await fetch(`${BACKEND_URL}/analyze`, {
>>>>>>> Stashed changes
          method: "POST",
          body: formData,
          // Don't set Content-Type header - browser will set it with boundary for FormData
          headers: {
            // Add headers to prevent caching
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
          },
          // No need to set credentials for same-origin requests
        });

<<<<<<< Updated upstream
        const result = await response.json();
        if (result.status === "success") {
          setSceneKey((prev) => prev + 1);
          loadTopEmotions(); // Refresh emotion summary
        } else {
          alert("Upload failed. Try again.");
        }
      } catch (error) {
        console.error("Upload error:", error);
        alert("Server error occurred.");
=======
        console.log("Response status:", response.status, response.statusText);
        
        if (!response.ok) {
            let errorText;
            try {
              errorText = await response.text();
            } catch (e) {
              errorText = "Could not read error response";
            }
            console.error("Analysis failed with status:", response.status, errorText);
            throw new Error(`Analysis request failed: ${response.status} - ${errorText}`);
        }

        let result;
        try {
          const text = await response.text();
          console.log("Raw response text:", text.substring(0, 200)); // Log first 200 chars
          result = JSON.parse(text);
        } catch (parseError) {
          console.error("Failed to parse JSON response:", parseError);
          throw new Error("Invalid response format from server");
        }
        
        if (result.error) {
          setErrorMessage(result.error || "Analysis failed. Check backend logs.");
          console.error("Analysis error details:", result);
        } else {
          console.log("Analysis successful, raw paths received:", result);
          
          // Store the received paths directly without modification
          setResultPaths(result);
          
          // Set analysis complete flag before updating scene
          setAnalysisComplete(true);
          
          // Force reset of scene key to ensure remounting
          setTimeout(() => {
            setSceneKey(prevKey => prevKey + 1);
          }, 100);
          
          // Explicitly start the reveal animation after a short delay to ensure scene is mounted
          setTimeout(() => {
            if (sceneRef.current) {
              console.log("Starting reveal animation");
              sceneRef.current.startRevealAnimation();
            }
          }, 500);
          
          // Load top emotions using direct backend URL
          if (result.top2SummaryPath) {
              const fullPath = `${BACKEND_URL}/${result.top2SummaryPath}`;
              console.log("Loading top emotions from:", fullPath);
              loadTopEmotions(fullPath);
          }
        }
      } catch (error) {
        console.error("Upload/Analysis error:", error);
        setErrorMessage(`Server/Analysis error: ${error.message}`);
        setAnalysisComplete(false); // Reset analysis state on error
>>>>>>> Stashed changes
      } finally {
        setLoading(false);
      }
    }
  };

<<<<<<< Updated upstream
  const handleDeleteAudio = () => setAudioFile(null);
  const handleExportMesh = () => sceneRef.current?.exportSTL();

  const loadTopEmotions = async () => {
    try {
      const response = await fetch("data/top2_emotion_summary.csv");
      const text = await response.text();
      const parsed = Papa.parse(text, { header: true });
      const filtered = parsed.data.filter(row => row.emotion);
      const top2 = filtered.slice(0, 2).map(row => row.emotion);
      setTopEmotions(top2);
    } catch (err) {
      console.error("Failed to load emotion summary:", err);
    }
  };

  useEffect(() => {
    loadTopEmotions(); // Initial load
  }, []);
=======
  const handleDeleteAudio = () => {
      setAudioFile(null);
      setAudioObjectUrl(null);
      setResultPaths({}); // Clear results when audio is deleted
      setAnalysisComplete(false); // Reset analysis state
      setTopEmotions(initialEmotions); // Reset emotion data
      // Force scene recreation
      setSceneKey(prevKey => prevKey + 1);
      
      // Clean up session storage
      sessionStorage.removeItem('audioFilename');
      sessionStorage.removeItem('audioPlaybackState');
  };
  
  const handleExportMesh = () => sceneRef.current?.exportSTL();

  // Add texture toggle handler
  const handleToggleTexture = () => {
    // Simply toggle the state - the prop will flow down to the components
    setTextureEnabled(prevState => !prevState);
    console.log("Toggling texture visibility");
  };

  const loadTopEmotions = async (url) => {
    if (!url) {
      console.warn("loadTopEmotions called without a valid URL");
      return; // Don't reset topEmotions if URL is missing
    }
    try {
      console.log("🔍 Fetching emotions from URL:", url);
      const response = await fetch(url, {
        headers: {
          'Cache-Control': 'no-cache',
          'Pragma': 'no-cache'
        }
      });
      if (!response.ok) {
         throw new Error(`Failed to load top emotions: ${response.status}`);
      }
      const text = await response.text();
      console.log("✅ Loaded top emotions data:", text.slice(0, 100));
      const parsed = Papa.parse(text, { header: true });
      const filtered = parsed.data.filter(row => row.emotion);
      
      if (filtered.length > 0) {
        console.log("✅ Found emotion data:", filtered.slice(0, 2));
        const top2 = filtered.slice(0, 2).map(row => row.emotion);
        
        // Store in localStorage as a backup in case state is lost on re-render
        localStorage.setItem('topEmotions', JSON.stringify(top2));
        
        // Set the state with the emotion data
        setTopEmotions(top2);
        
        // Set current texture info based on quadrant
        const valence = parseFloat(filtered[0].valence || 0); // Use valence, not valence_normalized
        const arousal = parseFloat(filtered[0].arousal || 0); // Use arousal, not arousal_normalized
        const quadrant = valence >= 0 
          ? (arousal >= 0 ? "high_high" : "high_low")
          : (arousal >= 0 ? "low_high" : "low_low");
        setCurrentTextureInfo({ filename: quadrant });
        
        console.log("🎨 Set emotion colors for:", top2.join(" → "));
      } else {
        console.warn("⚠️ No emotion data found in CSV");
      }
    } catch (err) {
      console.error("❌ Failed to load emotion summary:", err);
      setErrorMessage(`Failed to load visualization data: ${err.message}`);
      
      // Try to recover from localStorage if available
      const storedEmotions = localStorage.getItem('topEmotions');
      if (storedEmotions) {
        console.log("🔄 Recovering emotions from localStorage");
        setTopEmotions(JSON.parse(storedEmotions));
      }
    }
  };

  // Handle texture update from the mesh component
  const handleTextureUpdate = (textureInfo) => {
    if (textureInfo && textureInfo !== currentTextureInfo) {
      console.log("Texture update:", textureInfo);
      
      // Create a complete texture info object that includes the texture path
      const updatedTextureInfo = {
        ...textureInfo,
        imagePath: calculateTexturePath(textureInfo)
      };
      
      setCurrentTextureInfo(updatedTextureInfo);
    }
  };
  
  // Handle color update from the mesh component
  const handleColorUpdate = (colorInfo) => {
    if (colorInfo && (colorInfo.topColor !== currentColors.topColor || colorInfo.bottomColor !== currentColors.bottomColor)) {
      console.log("Color update:", colorInfo);
      setCurrentColors({
        topColor: colorInfo.topColor,
        bottomColor: colorInfo.bottomColor
      });
    }
  };
  
  // Helper function to calculate the texture path based on the texture info
  const calculateTexturePath = (textureInfo) => {
    if (!textureInfo || !textureInfo.filename) return null;
    
    // If we already have a full path, use it
    if (textureInfo.fullPath) return textureInfo.fullPath;
    
    // Extract source (category) and filename
    const filename = textureInfo.filename;
    const source = textureInfo.source || "";
    
    // Try to determine texture category
    let category = "";
    if (textureInfo.category) {
      category = textureInfo.category;
    } else if (filename.includes("_")) {
      // Try to extract from filename pattern like "lined_0123.jpg"
      const parts = filename.split("_");
      if (parts.length > 0) category = parts[0];
    }
    
    // Build complete path based on source
    if (source === "gray_textures" && category) {
      return `/data/textures/gray_textures/${category}/${filename}`;
    } else if (source === "normal_grey") {
      return `/data/textures/normal_grey/${filename}`;
    } else if (category) {
      // Default to gray_textures with category if we know the category
      return `/data/textures/gray_textures/${category}/${filename}`;
    } else {
      // Fallback to a placeholder
      return "/placeholder.png";
    }
  };

  // Build paths with the backend URL prefix - memoize to prevent recalculation on every render
  const paths = useMemo(() => {
    return {
      top2Path: resultPaths.top2SummaryPath 
        ? `${BACKEND_URL}/${resultPaths.top2SummaryPath}` 
        : "/data/output/top2_emotion_summary.csv",
      amplitudePath: resultPaths.arousalTrackPath 
        ? `${BACKEND_URL}/${resultPaths.arousalTrackPath}` 
        : "/data/output/arousal_100.csv",
      curvesPath: "/emotions/emotion_curves.json",
      classificationPath: TEXTURE_PATHS.fullClassificationPath
    };
  }, [resultPaths.top2SummaryPath, resultPaths.arousalTrackPath, BACKEND_URL, TEXTURE_PATHS.fullClassificationPath]);
  
  // Debug logs - move to a dedicated debug effect to prevent re-renders
  useEffect(() => {
    if (process.env.NODE_ENV === 'development') {
      console.log("=== Path Debug Info ===");
      console.log("top2Path:", paths.top2Path);
      console.log("amplitudePath:", paths.amplitudePath);
      console.log("curvesPath:", paths.curvesPath);
      console.log("topEmotions:", topEmotions);
      console.log("resultPaths:", resultPaths);
      console.log("BACKEND_URL:", BACKEND_URL);
    }
  }, [paths, topEmotions, resultPaths, BACKEND_URL]);
  
  // Help with debugging - validate paths are accessible - only on mount
  useEffect(() => {
    // Only run once when paths are available
    if (paths.curvesPath) {
      console.log("Validating paths...");
      
      // Check emotion curves JSON
      fetch(paths.curvesPath)
        .then(res => {
          console.log("Emotion curves fetch status:", res.status);
          return res.json();
        })
        .then(data => {
          console.log("Emotion curves available keys:", Object.keys(data));
        })
        .catch(err => console.error("Error fetching emotion curves:", err));
      
      // Check top2 emotions CSV
      fetch(paths.top2Path, {
        headers: {
          'Cache-Control': 'no-cache',
          'Pragma': 'no-cache'
        }
      })
        .then(res => {
          console.log("Top2 emotions fetch status:", res.status);
          return res.text();
        })
        .then(text => {
          console.log("Top2 emotions data:", text.substring(0, 100));
        })
        .catch(err => console.error("Error fetching top2 emotions:", err));
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only run on mount

  // Always render the Scene and EmotionCurveMorph with proper paths
  const shouldRenderScene = true; // Always render, with either uploaded or default paths

  // Create a dedicated component for the emotion color visualization to ensure it doesn't unmount
  const EmotionColorVisualization = React.memo(({ emotions }) => {
    // Keep a local copy of emotions to prevent flashing
    const [localEmotions, setLocalEmotions] = useState(emotions);
    
    // Update local state when props change and emotions are valid
    useEffect(() => {
      if (emotions && emotions.length === 2) {
        console.log("🔄 EmotionColorVisualization received new emotions:", emotions);
        setLocalEmotions(emotions);
      }
    }, [emotions]);
    
    // Get emotion colors for the circles - use currentColors when available
    const color1 = useMemo(() => {
      return currentColors.topColor || (localEmotions?.[0] ? getEmotionColor(localEmotions[0]).getStyle() : '#333');
    }, [localEmotions, currentColors.topColor]);
    
    const color2 = useMemo(() => {
      return currentColors.bottomColor || (localEmotions?.[1] ? getEmotionColor(localEmotions[1]).getStyle() : '#666');
    }, [localEmotions, currentColors.bottomColor]);
    
    const containerStyle = {
      width: '100%', 
      height: 220, 
      marginTop: 12, 
      borderRadius: 12, 
      overflow: 'hidden', 
      position: 'relative', 
      background: '#1a1a1a', 
      display: 'flex', 
      alignItems: 'center', 
      justifyContent: 'center'
    };
    
    // Circle animation container
    const circleContainerStyle = {
      position: 'absolute',
      width: '100%',
      height: '100%',
      left: 0,
      top: 0,
      overflow: 'hidden'
    };
    
    // Styles for the animated circles
    const circle1Style = {
      position: 'absolute',
      width: '180px',
      height: '180px',
      borderRadius: '50%',
      background: color1,
      filter: 'blur(40px)',
      opacity: 0.9,
      left: '30%',
      top: '50%',
      transform: 'translate(-50%, -50%)',
      animation: 'moveCircle1 20s ease-in-out infinite'
    };
    
    const circle2Style = {
      position: 'absolute',
      width: '200px',
      height: '200px',
      borderRadius: '50%',
      background: color2,
      filter: 'blur(40px)',
      opacity: 0.9,
      left: '70%',
      top: '50%',
      transform: 'translate(-50%, -50%)',
      animation: 'moveCircle2 25s ease-in-out infinite'
    };
    
    // Dynamic style element for animations
    const animationStyles = `
      @keyframes moveCircle1 {
        0%, 100% { transform: translate(-50%, -50%) translate(20px, 10px); }
        25% { transform: translate(-50%, -50%) translate(-20px, 30px); }
        50% { transform: translate(-50%, -50%) translate(-30px, -20px); }
        75% { transform: translate(-50%, -50%) translate(40px, -25px); }
      }
      
      @keyframes moveCircle2 {
        0%, 100% { transform: translate(-50%, -50%) translate(-40px, -15px); }
        25% { transform: translate(-50%, -50%) translate(30px, -30px); }
        50% { transform: translate(-50%, -50%) translate(35px, 40px); }
        75% { transform: translate(-50%, -50%) translate(-25px, 25px); }
      }
    `;
    
    return (
      <>
        <div className="step-wrapper">
          <div className="step-box"></div>
          {localEmotions && localEmotions.length === 2 ? (
            <p>
              Color transitions: <span style={{color: color1}}>{color1}</span> to <span style={{color: color2}}>{color2}</span>
            </p>
          ) : (
            <p>Analyzing emotions...</p>
          )}
        </div>
        
        <div style={containerStyle}>
          {/* Add style element for animations */}
          <style>{animationStyles}</style>
          
          {/* Circle animations */}
          <div style={circleContainerStyle}>
            <div style={circle1Style}></div>
            <div style={circle2Style}></div>
          </div>
          
          {/* Overlay effect for better blending */}
          <div style={{
            position: 'absolute',
            width: '100%',
            height: '100%',
            background: 'rgba(26, 26, 26, 0.1)',
            mixBlendMode: 'overlay'
          }}></div>
          
          {(!localEmotions || localEmotions.length !== 2) && (
            <div style={{ 
              color: '#888', 
              background: 'rgba(26, 26, 26, 0.7)',
              fontSize: 18, 
              textAlign: 'center', 
              width: '100%', 
              position: 'absolute', 
              left: 0, 
              top: 0, 
              height: '100%', 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center', 
              pointerEvents: 'none',
              zIndex: 2
            }}>
              Waiting for analysis...
            </div>
          )}
        </div>
      </>
    );
  });
>>>>>>> Stashed changes

  return (
    <div className="lamp-container">
      {loading && (
        <div className="custom-loading-overlay">
          <div className="loading-spinner" style={{ marginBottom: 32 }} />
          <p className="custom-loading-text">Analyzing your audio...</p>
        </div>
      )}

      <header className="lamp-header">
        <div className="lamp-logo">LUMINOTE</div>
        <div className="lamp-meta">
          <div className="meta-item">
            <span>LAMP GENERATION FROM SOUND</span>
          </div>
          <div className="meta-item">
            <span>DESIGNED BY KIDA HUANG AND SIJIA MA @HARVARD GSD</span>
          </div>
        </div>
      </header>

      <div className="lamp-body">
        {/* Left */}
        <div className="lamp-left">
          {/* Step 1 */}
          <div className="content-container01">
            <h2 className="reveal-heading">Transform Sound into Lamp Design</h2>
            <p>Luminote analyzes your voice or music to generate unique lamp forms</p>
          </div>

          <div className="content-container">
            <div className="step-wrapper">
              <div className="step-box-group">
                <div className="step-box first" />
                <div className="step-box faded" />
                <div className="step-box faded" />
              </div>
              <span className="step-caption">STEP 1</span>
            </div>

            <p>Upload your audio clip (≤ 10 minutes)</p>
            <label className="upload-box" onClick={() => console.log("CLICK TEST: Upload box clicked")}>
              <input
                type="file"
                accept="audio/*"
                onChange={(e) => {
                  console.log("INPUT TEST: File input changed", e.target.files?.[0]?.name);
                  handleAudioChange(e);
                }}
                style={{ display: "none" }}
              />
              <svg className="upload-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white" width="1rem" height="1rem">
                <path d="M0 0h24v24H0z" fill="none"/>
                <path d="M5 20h14v-2H5v2zm7-18l-7 7h4v6h6v-6h4l-7-7z"/>
              </svg>
              <span>Upload an Audio Clip</span>
            </label>

            {audioFile && (
              <div className="uploaded-file">
                <span>{audioFile.name}</span>
                <button className="delete-button" onClick={handleDeleteAudio}>
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white" width="1rem" height="1rem">
                    <path d="M0 0h24v24H0z" fill="none"/>
                    <path d="M16 9v10H8V9h8m-1.5-6h-5l-1 1H5v2h14V4h-4.5l-1-1z"/>
                  </svg>
                </button>
              </div>
            )}
<<<<<<< Updated upstream
=======

            {/* Always render the AudioPlayer component with available data */}
            <AudioPlayer file={audioFile} objectUrl={audioObjectUrl} />
>>>>>>> Stashed changes
          </div>

          {/* Step 2 */}
          <div className="content-container">
            <div className="step-wrapper">
              <div className="step-box-group">
                <div className="step-box first" />
                <div className="step-box first" />
                <div className="step-box faded" />
              </div>
              <span className="step-caption">STEP 2</span>
            </div>

            <p>Ready to save and export your design?</p>
            <button className="export-button" onClick={handleExportMesh}>
              Download My Design
            </button>
          </div>
        </div>

        {/* Center */}
        <div className="lamp-center">
<<<<<<< Updated upstream
          <Scene
            ref={sceneRef}
            key={sceneKey}
            csvPath="data/top2_emotion_summary.csv"
            amplitudeCsvPath="data/summary_per_segment.csv"
            emotionCurvesPath="emotions/emotion_curves.json"
          />
=======
          {shouldRenderScene ? (
            <Scene
              ref={sceneRef}
              key="main-scene"
              // Pass specific paths needed by components - use memoized values
              top2CsvPath={paths.top2Path} 
              amplitudeCsvPath={paths.amplitudePath}
              textureClassificationCsvPath={paths.classificationPath}
              emotionCurvesPath={paths.curvesPath}
              onTextureUpdate={handleTextureUpdate}
              onColorUpdate={handleColorUpdate}
              textureEnabled={textureEnabled} // Pass down the texture enabled state
            />
          ) : (
            <div style={{
              width: '100%',
              height: '100%',
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              color: '#888'
            }}>
              Waiting for data loading...
            </div>
          )}
>>>>>>> Stashed changes
        </div>

        {/* Right */}
        <div className="lamp-right">
          <div className="content-container01">
            <div className="step-wrapper">
<<<<<<< Updated upstream
            <div className="step-box first"></div>
              <span> Base Shape Visualization</span>
=======
              <div className="step-box-group">
                <div className="step-box first" />
                <div className="step-box faded" />
                <div className="step-box faded" />
              </div>
              <span className="step-caption"> Base Shape Visualization</span>
>>>>>>> Stashed changes
            </div>
            <div className="step-wrapper">
              <div className="step-box"></div>

            {topEmotions.length === 2 && (
              <p>
                The audio transitions from <strong>{topEmotions[0]}</strong> to <strong>{topEmotions[1]}</strong>
              </p>
            )}
              </div>

            <div
              style={{
                width: "100%",
                height: "220px",
                marginTop: "12px",
                borderRadius: "12px",
                overflow: "hidden",
                background: "#1a1a1a"
              }}
            >
<<<<<<< Updated upstream
              <EmotionCurveMorph
                key={sceneKey}
                emotionCurvesPath="emotions/emotion_curves.json"
                top2CsvPath="data/top2_emotion_summary.csv"
=======
              {shouldRenderScene ? (
              <EmotionCurveMorph
                key="emotion-curve-morph"
                // Use memoized paths
                emotionCurvesPath={paths.curvesPath}
                top2CsvPath={paths.top2Path}
>>>>>>> Stashed changes
              />
            </div>
          </div>

          {/* Additional Base Shape Visualization Section */}
          <div className="content-container">
            <div className="step-wrapper">
<<<<<<< Updated upstream
            <div className="step-box first"></div>
              <span> Texture Visualization</span>
=======
              <div className="step-box-group">
                <div className="step-box first" />
                <div className="step-box faded" />
                <div className="step-box faded" />
              </div>
              <span className="step-caption"> Emotion Color Selection </span>
            </div>
            
            {/* Use the dedicated component for emotion color visualization with a key to force re-render when emotions change */}
            <EmotionColorVisualization 
              key={topEmotions.join('-')} 
              emotions={topEmotions} 
            />
          </div>

          <div className="content-container02">
            {/* Texture Controls */}
            <div className="texture-controls" style={{ marginTop: "10px", display: "flex", flexDirection: "column", gap: "10px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div className="step-wrapper">
              <div className="step-box-group">
                <div className="step-box first" />
                <div className="step-box faded" />
                <div className="step-box faded" />
              </div>
              <span className="step-caption"> Texture Visualization </span>
            </div>
                <button
                  onClick={handleToggleTexture}
                  style={{
                    background: textureEnabled ? "#ffffff" : "#000000",
                    color: textureEnabled ? "#000000" : "#ffffff",
                    border: textureEnabled ? "none" : "1px solid #ffffff",
                    borderRadius: "20px",
                    padding: "5px 15px",
                    cursor: "pointer",
                    transition: "all 0.3s ease",
                    fontWeight: "bold"
                  }}
                >
                  {textureEnabled ? "ON" : "OFF"}
                </button>
              </div>
              
              {/* Current Texture Display */}
              <div style={{ 
                background: "#1a1a1a", 
                padding: "10px", 
                borderRadius: "8px",
                marginTop: "5px" 
              }}>
                <p style={{ margin: "0 0 5px 0", fontSize: "14px" }}>Current Texture:</p>
                <div style={{ 
                  display: "flex",
                  alignItems: "center",
                  gap: "10px" 
                }}>
                  <div style={{ 
                    width: "50px",
                    height: "50px",
                    background: "#333",
                    borderRadius: "4px",
                    backgroundSize: "cover",
                    backgroundImage: currentTextureInfo?.imagePath ? 
                      `url("${currentTextureInfo.imagePath}")` : 
                      "none",
                    position: "relative",
                    overflow: "hidden"
                  }}>
                    {!currentTextureInfo?.imagePath && (
                      <div style={{
                        position: "absolute",
                        top: 0,
                        left: 0,
                        right: 0,
                        bottom: 0,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        color: "#777",
                        fontSize: "10px"
                      }}>
                        No image
                      </div>
                    )}
                  </div>
                  <span style={{ fontSize: "12px", wordBreak: 'break-all' }}>
                      {currentTextureInfo?.filename || "Loading..."}
                  </span>
                </div>
              </div>
              
              <p style={{ fontSize: "13px", color: "#888", marginTop: "5px" }}>
                Textures are automatically selected based on emotional analysis of the audio.
              </p>
>>>>>>> Stashed changes
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LampCreation;
