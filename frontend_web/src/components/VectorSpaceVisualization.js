import React, { useRef, useState, useEffect, useCallback, Suspense } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Environment, OrbitControls, Text, PerspectiveCamera } from '@react-three/drei';
import * as THREE from 'three';
import Papa from 'papaparse';
import { EffectComposer, Bloom, Vignette } from '@react-three/postprocessing';
// Import configuration
import { TEXTURE_PATHS, IMAGE_PATHS } from '../config';

// Color palette for different texture categories
const categoryColors = {
  'banded': '#FF6B6B',
  'blotchy': '#4ECDC4',
  'braided': '#FFD166',
  'bubbly': '#F25F5C',
  'bumpy': '#6A0572',
  'chequered': '#AB83A1',
  'cobwebbed': '#227C9D',
  'cracked': '#17C3B2',
  'crosshatched': '#FFCB77',
  'crystalline': '#FE6D73',
  'dotted': '#4EA8DE',
  'fibrous': '#48BF84',
  'flecked': '#D62828',
  'frilly': '#F77F00',
  'gauzy': '#FCBF49',
  'grid': '#9B5DE5',
  'grooved': '#F15BB5',
  'honeycombed': '#FEE440',
  'interlaced': '#00BBF9',
  'knitted': '#00F5D4',
  'lacelike': '#FF9770',
  'lined': '#FFC15E',
  'marbled': '#01BAEF',
  'matted': '#FBAE3C',
  'meshed': '#BB4430',
  'paisley': '#7BDFF2',
  'perforated': '#B388EB',
  'pitted': '#F7AEF8',
  'pleated': '#72DDF7',
  'polka-dotted': '#8093F1',
  'porous': '#F582A7',
  'potholed': '#42E2B8',
  'scaly': '#F9C846',
  'smeared': '#F94144',
  'spiralled': '#277DA1',
  'sprinkled': '#4D908E',
  'stained': '#F3722C',
  'stratified': '#F8961E',
  'striped': '#F9844A',
  'studded': '#F9C74F',
  'swirly': '#90BE6D',
  'veined': '#43AA8B',
  'waffled': '#4D908E',
  'woven': '#F94144',
  'wrinkled': '#577590',
  'zigzagged': '#F8961E',
  'rough': '#FF6B6B',
  'smooth': '#4ECDC4',
  'wavy': '#FFD166',
  'spiky': '#F25F5C'
};

// Main component
const VectorSpaceVisualization = () => {
  const [textures, setTextures] = useState([]);
  const [loading, setLoading] = useState(true);
  const [hoveredTexture, setHoveredTexture] = useState(null);
  const [activeCategories, setActiveCategories] = useState([]);
  const [sceneReady, setSceneReady] = useState(false);
  const [totalTextures, setTotalTextures] = useState(0);

  // Function to load and process the CSV data
  const loadVisualizationData = useCallback(async () => {
    try {
      setLoading(true);
      // Load texture classification data using config path
      const response = await fetch(TEXTURE_PATHS.classificationCsv);
      const csvText = await response.text();
      
      Papa.parse(csvText, {
        header: true,
        dynamicTyping: true,
        complete: (results) => {
          // Process the data
          const data = results.data
            .filter(row => 
              row.valence_normalized !== undefined && 
              row.arousal_normalized !== undefined && 
              row.category !== undefined
            )
            .map(row => {
              let imagePath = '';
              
              // For texture_XXXX filenames (normal_grey folder)
              if (row.filename && row.filename.includes('texture_')) {
                const textureMatch = row.filename.match(/texture_(\d+)/);
                const textureNumber = textureMatch ? textureMatch[1] : '';
                
                if (textureNumber) {
                  imagePath = `${TEXTURE_PATHS.normalGrey}/texture_${textureNumber}_normal.png`;
                }
              } 
              // For category-based textures (gray_textures folder)
              else if (row.category) {
                const categoryFolder = row.category.toLowerCase();
                
                // Try to extract a number from the filename or ID if available
                let textureId = '';
                if (row.filename) {
                  const idMatch = row.filename.match(/(\d+)/);
                  if (idMatch) textureId = idMatch[1];
                } else if (row.id) {
                  const idMatch = String(row.id).match(/(\d+)/);
                  if (idMatch) textureId = idMatch[1];
                }
                
                // If we have an ID, use it to construct a specific filename
                if (textureId) {
                  // Pad the ID to 4 digits
                  while (textureId.length < 4) {
                    textureId = '0' + textureId;
                  }
                  imagePath = `${TEXTURE_PATHS.grayTextures}/${categoryFolder}/${categoryFolder}_${textureId}.jpg`;
                } else {
                  // Default to first common file pattern
                  imagePath = `${TEXTURE_PATHS.grayTextures}/${categoryFolder}/${categoryFolder}_0001.jpg`;
                }
              }
              // Default to provided path or placeholder
              else if (row.image_path) {
                imagePath = row.image_path;
              } else {
                imagePath = IMAGE_PATHS.placeholder;
              }
              
              return {
                ...row,
                // Ensure we have proper numeric values
                valence_normalized: parseFloat(row.valence_normalized) || 0,
                arousal_normalized: parseFloat(row.arousal_normalized) || 0,
                // Add z-coordinate based on category for 3D separation (slight jitter)
                z: (Math.random() - 0.5) * 0.5,
                // Use the resolved image path
                image_path: imagePath,
                // Store category color
                color: categoryColors[row.category] || '#888888',
                // Flag for hover state
                isHovered: false
              };
            });
          
          // Get the unique categories
          const categories = [...new Set(data.map(item => item.category))];
          setActiveCategories(categories);
          
          console.log(`Processing ${data.length} textures...`); // Log texture count
          setTotalTextures(data.length);
          setTextures(data);
          setLoading(false);
        },
        error: (error) => {
          console.error('CSV parsing error:', error);
          setLoading(false);
        }
      });
    } catch (error) {
      console.error('Failed to load visualization data:', error);
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadVisualizationData();
    // Set scene as ready after a short delay to allow initial setup
    const timer = setTimeout(() => setSceneReady(true), 500);
    return () => clearTimeout(timer);
  }, [loadVisualizationData]);

  // Toggle a category's visibility
  const toggleCategory = (category) => {
    setActiveCategories(prev => 
      prev.includes(category) 
        ? prev.filter(c => c !== category) 
        : [...prev, category]
    );
  };

  return (
    <div 
      className="vector-space-visualization" 
      style={{
        width: '100%',
        height: '70vh',
        position: 'relative',
        backgroundColor: '#000',
        overflow: 'hidden'
      }}
    >
      {loading ? (
        <div 
          style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            color: 'white',
            fontFamily: 'SF Pro Display, -apple-system, BlinkMacSystemFont, sans-serif',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '20px'
          }}
        >
          <div 
            style={{
              width: '40px',
              height: '40px',
              border: '3px solid rgba(255,255,255,0.1)',
              borderTop: '3px solid #fff',
              borderRadius: '50%',
              animation: 'spin 1s linear infinite'
            }}
          ></div>
          <div>Loading texture space...</div>
        </div>
      ) : (
        <>
          <Canvas
            gl={{ 
              antialias: true, 
              alpha: false,
              logarithmicDepthBuffer: true,
              pixelRatio: Math.min(2, window.devicePixelRatio)
            }}
            style={{ background: '#000' }}
            camera={{ position: [0, 0, 5], fov: 60 }}
          >
            <color attach="background" args={['#000000']} />
            <fog attach="fog" args={['#000000', 5, 15]} />
            <ambientLight intensity={0.2} />
            <directionalLight position={[10, 10, 5]} intensity={0.3} />
            <pointLight position={[-10, -10, -5]} intensity={0.2} />
            
            <Suspense fallback={null}>
              <TextureVisualization 
                textures={textures.filter(t => activeCategories.includes(t.category))} 
                setHoveredTexture={setHoveredTexture}
                totalTextures={totalTextures}
              />
              <GridSystem />
              <Environment preset="studio" intensity={0.2} />
              <OrbitControls 
                enableDamping 
                dampingFactor={0.05} 
                minDistance={2} 
                maxDistance={10}
                rotateSpeed={0.5}
                minAzimuthAngle={-Math.PI/4}
                maxAzimuthAngle={Math.PI/4}
                minPolarAngle={Math.PI/3}
                maxPolarAngle={Math.PI/1.5}
                autoRotate={false}
              />
              
              {/* Conditionally render EffectComposer */}
              {sceneReady && (
                <EffectComposer>
                  <Bloom luminanceThreshold={0.3} luminanceSmoothing={0.9} height={300} intensity={0.3} />
                  <Vignette eskil={false} offset={0.1} darkness={0.6} />
                </EffectComposer>
              )}
            </Suspense>
          </Canvas>
          
          {/* Controls panel */}
          <div 
            style={{
              position: 'absolute',
              top: '20px',
              right: '20px',
              backgroundColor: 'rgba(0, 0, 0, 0.7)',
              backdropFilter: 'blur(10px)',
              borderRadius: '12px',
              padding: '16px',
              color: 'white',
              fontFamily: 'SF Pro Display, -apple-system, BlinkMacSystemFont, sans-serif',
              maxWidth: '300px',
              zIndex: 100,
              boxShadow: '0 10px 20px rgba(0, 0, 0, 0.3)',
              border: '1px solid rgba(255, 255, 255, 0.1)'
            }}
          >
            <div style={{ marginBottom: '10px', fontWeight: 500, fontSize: '14px' }}>
              Texture Categories
            </div>
            <div 
              style={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: '8px',
                maxHeight: '120px',
                overflowY: 'auto',
                paddingRight: '5px',
                marginBottom: '10px'
              }}
            >
              {[...new Set(textures.map(t => t.category))].map(category => (
                <div
                  key={category}
                  onClick={() => toggleCategory(category)}
                  style={{
                    padding: '5px 10px',
                    borderRadius: '10px',
                    backgroundColor: activeCategories.includes(category) 
                      ? categoryColors[category] || '#888' 
                      : 'rgba(255, 255, 255, 0.1)',
                    cursor: 'pointer',
                    fontSize: '12px',
                    textTransform: 'capitalize',
                    opacity: activeCategories.includes(category) ? 1 : 0.6,
                    transition: 'all 0.2s ease',
                    whiteSpace: 'nowrap'
                  }}
                >
                  {category}
                </div>
              ))}
            </div>
            
            <div style={{ fontSize: '11px', color: 'rgba(255, 255, 255, 0.6)', lineHeight: 1.4 }}>
              <div>X-axis: Valence (Negative → Positive)</div>
              <div>Y-axis: Arousal (Calm → Energetic)</div>
              <div>Z-axis: Category Grouping</div>
            </div>
          </div>
          
          {/* Add interaction hint */}
          <div 
            style={{
              position: 'absolute',
              bottom: '20px',
              left: '50%',
              transform: 'translateX(-50%)',
              backgroundColor: 'rgba(0, 0, 0, 0.5)',
              backdropFilter: 'blur(5px)',
              borderRadius: '10px',
              padding: '8px 16px',
              color: 'white',
              fontSize: '14px',
              textAlign: 'center',
              opacity: 0.8,
              transition: 'opacity 0.3s',
              zIndex: 99
            }}
          >
            Click and drag to rotate • Scroll to zoom
          </div>
          
          {/* Hover info */}
          {hoveredTexture && (
            <div
              style={{
                position: 'absolute',
                top: '20px',
                left: '20px',
                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                backdropFilter: 'blur(10px)',
                borderRadius: '12px',
                padding: '16px',
                color: 'white',
                fontFamily: 'SF Pro Display, -apple-system, BlinkMacSystemFont, sans-serif',
                zIndex: 100,
                boxShadow: '0 10px 20px rgba(0, 0, 0, 0.3)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                maxWidth: '300px',
                transition: 'all 0.3s ease',
                opacity: 1
              }}
            >
              <div style={{ display: 'flex', gap: '16px' }}>
                <div 
                  style={{
                    width: '80px',
                    height: '80px',
                    borderRadius: '8px',
                    backgroundColor: hoveredTexture.color,
                    backgroundImage: `url(${hoveredTexture.image_path})`,
                    backgroundSize: 'cover',
                    backgroundPosition: 'center',
                    flexShrink: 0,
                    border: '1px solid rgba(255, 255, 255, 0.2)'
                  }}
                ></div>
                <div>
                  <div style={{ fontSize: '18px', fontWeight: '600', textTransform: 'capitalize', marginBottom: '8px' }}>
                    {hoveredTexture.category}
                  </div>
                  <div style={{ fontSize: '14px', opacity: 0.9, marginBottom: '4px' }}>
                    Valence: {parseFloat(hoveredTexture.valence_normalized).toFixed(2)}
                  </div>
                  <div style={{ fontSize: '14px', opacity: 0.9 }}>
                    Arousal: {parseFloat(hoveredTexture.arousal_normalized).toFixed(2)}
                  </div>
                </div>
              </div>
            </div>
          )}
          
          {/* Intro title */}
          <div
            style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              color: 'white',
              fontFamily: 'SF Pro Display, -apple-system, BlinkMacSystemFont, sans-serif',
              fontSize: '30px',
              fontWeight: '600',
              textAlign: 'center',
              pointerEvents: 'none',
              opacity: textures.length > 0 ? 0 : 1,
              transition: 'opacity 1s ease',
              textShadow: '0 2px 10px rgba(0,0,0,0.5)',
              width: '100%'
            }}
          >
            Texture Emotion Space
          </div>
        </>
      )}
      
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
        
        /* Scrollbar styling */
        ::-webkit-scrollbar {
          width: 5px;
          height: 5px;
        }
        
        ::-webkit-scrollbar-track {
          background: rgba(255, 255, 255, 0.1);
          border-radius: 5px;
        }
        
        ::-webkit-scrollbar-thumb {
          background: rgba(255, 255, 255, 0.3);
          border-radius: 5px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
          background: rgba(255, 255, 255, 0.5);
        }
      `}</style>
    </div>
  );
};

// 3D grid system component
const GridSystem = () => {
  const gridRef = useRef();
  
  useFrame(({ clock }) => {
    // Subtle animation for the grid
    if (gridRef.current) {
      gridRef.current.material.opacity = 0.1 + Math.sin(clock.getElapsedTime() * 0.5) * 0.05;
    }
  });

  return (
    <group>
      {/* X-axis */}
      <gridHelper 
        ref={gridRef}
        args={[10, 20, 0x444444, 0x222222]} 
        position={[0, 0, 0]} 
        rotation={[0, 0, 0]}
      />
      
      {/* Axis labels */}
      <Text
        position={[2.5, 0, 0]}
        fontSize={0.1}
        color="#ffffff"
        anchorX="center"
        anchorY="middle"
      >
        Valence
      </Text>
      <Text
        position={[0, 2.5, 0]}
        fontSize={0.1}
        color="#ffffff"
        anchorX="center"
        anchorY="middle"
        rotation={[0, 0, Math.PI / 2]}
      >
        Arousal
      </Text>
    </group>
  );
};

// Individual texture items
const TextureItem = ({ texture, setHoveredTexture, index, totalTextures }) => {
  const meshRef = useRef();
  const [hovered, setHovered] = useState(false);
  const [textureObj, setTextureObj] = useState(null);
  const [displayValue, setDisplayValue] = useState({ valence: 0, arousal: 0 });

  // Much smaller base scale for performance
  const baseScale = 0.15;
  // Larger hover scale for better visibility
  const hoverScale = 1.5;

  // Update display values on hover (keep this logic)
  useEffect(() => {
    if (hovered) {
      const targetValence = parseFloat(texture.valence_normalized);
      const targetArousal = parseFloat(texture.arousal_normalized);
      setDisplayValue({ valence: 0, arousal: 0 });
      const duration = 500; const steps = 15; const interval = duration / steps;
      for (let i = 1; i <= steps; i++) {
        setTimeout(() => {
          const progress = i / steps;
          setDisplayValue({
            valence: (targetValence * progress).toFixed(2),
            arousal: (targetArousal * progress).toFixed(2)
          });
        }, interval * i);
      }
    }
  }, [hovered, texture.valence_normalized, texture.arousal_normalized]);

  // Coordinates
  const x = texture.valence_normalized * 3;
  const y = texture.arousal_normalized * 3;
  const z = texture.z || 0;

  // Optimized and staggered texture loading
  useEffect(() => {
    // Stagger loading based on index to prevent overwhelming the browser
    const loadDelay = (index / totalTextures) * 2000; // Spread loading over 2 seconds
    
    const timer = setTimeout(() => {
      const imagePaths = [];
      // Build paths (same logic)
      if (texture.filename && texture.filename.includes('texture_')) {
        const match = texture.filename.match(/texture_(\d+)/);
        if (match) imagePaths.push(`/data/textures/normal_grey/texture_${match[1]}_normal.png`);
      }
      if (texture.category) {
        const categoryLower = texture.category.toLowerCase();
        let textureId = '';
        if (texture.filename) textureId = (texture.filename.match(/(\d+)/) || [])[1] || '';
        else if (texture.id) textureId = (String(texture.id).match(/(\d+)/) || [])[1] || '';
        if (textureId) {
          while (textureId.length < 4) textureId = '0' + textureId;
          imagePaths.push(`/data/textures/gray_textures/${categoryLower}/${categoryLower}_${textureId}.jpg`);
        }
        ['0001'].forEach(id => { // Try only the most common ID
          imagePaths.push(`/data/textures/gray_textures/${categoryLower}/${categoryLower}_${id}.jpg`);
        });
      }
      if (texture.image_path) imagePaths.push(texture.image_path);
      imagePaths.push('/placeholder.png'); // Ensure placeholder is last

      const loader = new THREE.TextureLoader();
      let loaded = false;

      const loadNextTexture = (pathIndex) => {
        if (pathIndex >= imagePaths.length || loaded) return;
        const path = imagePaths[pathIndex];
        
        loader.load(path, (loadedTexture) => {
          if (loaded) return; 
          loaded = true;
          loadedTexture.minFilter = THREE.LinearFilter;
          loadedTexture.magFilter = THREE.LinearFilter;
          loadedTexture.generateMipmaps = false;
          loadedTexture.needsUpdate = true;
          setTextureObj(loadedTexture);
          // console.log(`Loaded: ${path}`);
        }, undefined, () => {
          // console.log(`Failed: ${path}`);
          loadNextTexture(pathIndex + 1);
        });
      };
      loadNextTexture(0);
      
    }, loadDelay);

    // Cleanup: clear timeout and dispose texture
    return () => {
      clearTimeout(timer);
      if (textureObj) textureObj.dispose();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [texture.filename, texture.category, texture.id, texture.image_path, index, totalTextures]); // Re-run only if key properties change

  // Handle hover events
  const handlePointerOver = (e) => { e.stopPropagation(); setHovered(true); setHoveredTexture(texture); };
  const handlePointerOut = () => { setHovered(false); setHoveredTexture(null); };

  // Optimized frame loop
  useFrame(({ camera }) => {
    if (meshRef.current) {
      // Billboard effect (face camera)
      meshRef.current.quaternion.copy(camera.quaternion);
      
      // Animate scale smoothly towards target
      const targetScale = hovered ? hoverScale : baseScale;
      meshRef.current.scale.lerp(new THREE.Vector3(targetScale, targetScale, targetScale), 0.15); // Slightly faster lerp
    }
  });

  return (
    <mesh
      ref={meshRef}
      position={[x, y, z]}
      scale={[baseScale, baseScale, baseScale]} // Start small
      onPointerOver={handlePointerOver}
      onPointerOut={handlePointerOut}
    >
      {/* Even smaller geometry */}
      <planeGeometry args={[0.5, 0.5]} /> 
      <meshBasicMaterial 
        map={textureObj} // Use loaded texture if available
        color={!textureObj ? texture.color : 0xffffff} // Show category color until texture loads
        transparent={true} 
        alphaTest={0.1}
        opacity={!textureObj ? 0.6 : 1.0} // Slightly transparent until loaded
        side={THREE.DoubleSide}
      />
      
      {/* Hover text - adjust positions and font sizes for new scale */}
      {hovered && (
        <group position={[0, 0, 0.02]}>
          <Text
            position={[0, 0.1, 0]} // Adjusted Y position 
            fontSize={0.05} // Reduced font size
            color="#00ffff"
            anchorX="left"
            anchorY="middle"
            outlineWidth={0.002} // Reduced outline
            outlineColor="#003333"
          >
            {`V: ${displayValue.valence}`}
          </Text>
          <Text
            position={[0, 0.02, 0]} // Adjusted Y position
            fontSize={0.05} // Reduced font size
            color="#ff00ff"
            anchorX="left"
            anchorY="middle"
            outlineWidth={0.002} // Reduced outline
            outlineColor="#330033"
          >
            {`A: ${displayValue.arousal}`}
          </Text>
          <Text
            position={[0, -0.06, 0]} // Adjusted Y position
            fontSize={0.04} // Reduced font size
            color="#ffffff"
            anchorX="left"
            anchorY="middle"
            outlineWidth={0.002} // Reduced outline
            outlineColor="#333333"
          >
            {texture.category}
          </Text>
          {/* Smaller background */}
          <mesh position={[0.15, 0.02, -0.01]}> 
            <planeGeometry args={[0.4, 0.25]} /> // Adjusted background size
            <meshBasicMaterial color="#000000" transparent opacity={0.7} />
          </mesh>
        </group>
      )}
    </mesh>
  );
};

// Main visualization component
const TextureVisualization = ({ textures, setHoveredTexture, totalTextures }) => {
  return (
    <group>
      {textures.map((texture, index) => (
        <TextureItem 
          key={`${texture.category}-${texture.id || index}`} // Use a more stable key if possible
          texture={texture}
          setHoveredTexture={setHoveredTexture}
          index={index} // Pass index
          totalTextures={totalTextures} // Pass total count
        />
      ))}
    </group>
  );
};

export default VectorSpaceVisualization; 