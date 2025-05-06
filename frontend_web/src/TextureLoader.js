// TextureLoader.js - Loads displacement and normal maps based on emotion data
import { useEffect, useState, useCallback, useRef } from 'react';
import * as THREE from 'three';
import Papa from 'papaparse';
// Import configuration
import { TEXTURE_PATHS, IMAGE_PATHS } from './config';

// Utility function to fetch CSV data
async function fetchCsv(url) {
  try {
    console.log("[TextureLoader] Fetching CSV from:", url);
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`HTTP error ${response.status}`);
    }
    return await response.text();
  } catch (error) {
    console.error(`[TextureLoader] Error fetching CSV from ${url}:`, error);
    return null;
  }
}

// Convert VA values to quadrant (still useful for debugging/logging)
function getQuadrant(valence, arousal) {
  const vClass = valence >= 0 ? 'high' : 'low';
  const aClass = arousal >= 0 ? 'high' : 'low';
  return `${vClass}_${aClass}`;
}

// Emotion to texture type mapping 
// These mappings correlate emotional qualities with appropriate texture patterns
const emotionTextureMapping = {
  // Joy: bright, regular patterns
  "joy": ["grid", "polka-dotted", "dotted", "chequered", "woven", "lined", "striped"],
  
  // Sadness: flowing, smooth patterns
  "sadness": ["woven", "pleated", "fibrous", "swirly", "gauzy", "stratified"],
  "sad": ["woven", "pleated", "fibrous", "swirly", "gauzy", "stratified"],
  
  // Anger: sharp, irregular, intense patterns
  "anger": ["cracked", "crystalline", "zigzagged", "crosshatched", "grooved", "perforated"],
  "angry": ["cracked", "crystalline", "zigzagged", "crosshatched", "grooved", "perforated"],
  
  // Fear: chaotic, uncertain patterns
  "fear": ["cobwebbed", "veined", "cracked", "flecked", "studded", "honeycombed"],
  "fearful": ["cobwebbed", "veined", "cracked", "flecked", "studded", "honeycombed"],
  
  // Surprise: unexpected, unusual patterns
  "surprise": ["bubbly", "honeycombed", "spiralled", "interlaced", "crystalline", "sprinkled"],
  "surprised": ["bubbly", "honeycombed", "spiralled", "interlaced", "crystalline", "sprinkled"],
  
  // Neutral: ordered, balanced patterns
  "neutral": ["lined", "fibrous", "woven", "grid", "matted", "chequered", "waffled"],
  
  // Disgust: irregular, unsettling patterns
  "disgust": ["porous", "potholed", "scaly", "smeared", "blotchy", "bumpy"],
  "disgusted": ["porous", "potholed", "scaly", "smeared", "blotchy", "bumpy"],
  
  // Serene: smooth, gentle patterns
  "serene": ["gauzy", "lined", "woven", "stratified", "pleated", "swirly"],
  
  // For emotions not specifically mapped
  "default": ["lined", "woven", "grid", "dotted", "interlaced", "fibrous"]
};

// Normalize file path to remove duplicated extensions or fix path issues
function normalizeTexturePath(path) {
  if (!path) return null;
  
  let normalized = path;
  
  // Handle cases like texture_0123.jpg_normal.png -> texture_0123_normal.png
  normalized = normalized.replace(/\.jpg_normal\.png$/, '_normal.png');
  
  // Handle cases like texture_0123_normal.png_normal.png -> texture_0123_normal.png
  normalized = normalized.replace(/_normal\.png_normal\.png$/, '_normal.png');

  // Ensure it ends with .png if it's supposed to be a normal map
  if (normalized.includes('_normal') && !normalized.endsWith('.png')) {
    // Attempt to fix cases where extension might be missing or incorrect
    normalized = normalized.replace(/(\.[^.]+)?$/, '.png'); 
  }
  
  // Fallback: If it doesn't end in png or jpg, assume png
  if (!normalized.endsWith('.png') && !normalized.endsWith('.jpg')) {
    normalized = normalized.replace(/(\.[^.]+)?$/, '.png');
  }
  
  return normalized;
}

// Load and parse the texture classification CSV
async function loadAllTextureData(url) {
  try {
    const csvText = await fetchCsv(url);
    if (!csvText) {
      console.warn("[TextureLoader] Could not load texture classification, returning empty data.");
      return []; // Return empty array if load fails
    }

    // Parse CSV using PapaParse
    const parsed = Papa.parse(csvText, { 
      header: true, 
      dynamicTyping: true,
      skipEmptyLines: true 
    });

    // Map to a flat list of texture objects with normalized VA
    const allTextures = parsed.data
      .filter(row => (row.image_path || row.filename) && row.valence_normalized !== undefined && row.arousal_normalized !== undefined)
      .map(row => ({
        filename: row.filename || row.image_path.split('/').pop(),
        path: row.image_path,
        source: row.source_dir || 'unknown',
        valence: parseFloat(row.valence_normalized) || 0, // Use normalized
        arousal: parseFloat(row.arousal_normalized) || 0, // Use normalized
        quadrant: row.quadrant || getQuadrant(row.valence_normalized || 0, row.arousal_normalized || 0)
      }));
      
    console.log(`[TextureLoader] Loaded ${allTextures.length} total textures from classification data.`);
    
    if (allTextures.length === 0) {
        console.warn("[TextureLoader] No valid textures parsed from classification data.");
    }

    return allTextures;
  } catch (error) {
    console.error("[TextureLoader] Error loading or parsing texture classification:", error);
    return []; // Return empty array on error
  }
}

// Find texture closest to target valence-arousal values
// Now with priority for gray_textures based on emotion type
function findBestTextureForEmotion(emotion, targetValence, targetArousal, allTextures) {
  if (!allTextures || allTextures.length === 0) {
    console.warn("[TextureLoader] No texture data available to find best match.");
    return null; 
  }

  const normalizedEmotion = (emotion || "").toLowerCase().trim();
  
  // Get preferred texture types for this emotion
  const preferredTypes = emotionTextureMapping[normalizedEmotion] || emotionTextureMapping.default;
  
  // Split textures into DTD (gray_textures) and normal_grey categories
  const dtdTextures = allTextures.filter(t => t.source === 'gray_textures');
  const normalGreyTextures = allTextures.filter(t => t.source === 'normal_grey');
  
  // Try to find matching DTD texture first by checking if filename contains any preferred type
  let bestDtdMatches = [];
  
  for (const preferredType of preferredTypes) {
    const matches = dtdTextures.filter(t => 
      t.filename.toLowerCase().includes(preferredType) || 
      t.path?.toLowerCase().includes(preferredType)
    );
    
    if (matches.length > 0) {
      bestDtdMatches = [...bestDtdMatches, ...matches];
      // Once we have at least 5 matches, we can stop searching
      if (bestDtdMatches.length >= 5) break;
    }
  }
  
  console.log(`[TextureLoader] Found ${bestDtdMatches.length} DTD textures matching emotion "${normalizedEmotion}"`);
  
  // If we found DTD textures matching the emotion, find the closest one by VA
  if (bestDtdMatches.length > 0) {
    let closestTexture = null;
    let minDistance = Infinity;
    
    for (const texture of bestDtdMatches) {
      // Calculate squared Euclidean distance in the normalized VA space
      const distSq = Math.pow(texture.valence - targetValence, 2) + Math.pow(texture.arousal - targetArousal, 2);
      
      if (distSq < minDistance) {
        minDistance = distSq;
        closestTexture = texture;
      }
    }
    
    if (closestTexture) {
      console.log(`[TextureLoader] Selected DTD texture for ${normalizedEmotion}: ${closestTexture.filename} (dist: ${Math.sqrt(minDistance).toFixed(3)})`);
      return closestTexture;
    }
  }
  
  // If no matching DTD textures, fall back to the closest normal_grey texture by VA
  console.log(`[TextureLoader] No matching DTD textures found for ${normalizedEmotion}, falling back to VA-based selection`);
  
  // Try all textures (both DTD and normal_grey)
  let closestTexture = null;
  let minDistance = Infinity;
  
  for (const texture of allTextures) {
    // Calculate Euclidean distance in the normalized VA space
    const distSq = Math.pow(texture.valence - targetValence, 2) + Math.pow(texture.arousal - targetArousal, 2);
    
    if (distSq < minDistance) {
      minDistance = distSq;
      closestTexture = texture;
    }
  }
  
  if (closestTexture) {
    console.log(`[TextureLoader] Selected fallback texture for ${normalizedEmotion}: ${closestTexture.filename} (dist: ${Math.sqrt(minDistance).toFixed(3)})`);
    return closestTexture;
  }
  
  console.warn("[TextureLoader] Could not find any suitable texture.");
  return null;
}

export function useTextureLoader(top2CsvPath, textureClassificationCsvPath) {
  const [loadingState, setLoadingState] = useState('idle');
  const [textureMaps, setTextureMaps] = useState({
    texture1: null,
    texture2: null,
  });
  const [allTextureData, setAllTextureData] = useState([]); // Store all parsed textures

  // Keep track of loaded textures to avoid reloading
  const textureCache = useRef({}); // Use ref for cache to avoid re-renders
  // Track if default texture has been created
  const defaultTextureRef = useRef(null);

  // Create and load a default texture
  const createDefaultTexture = useCallback(() => {
    if (defaultTextureRef.current) return defaultTextureRef.current;
    
    const size = 64; // Smaller default texture
    const data = new Uint8Array(size * size * 4);
    for (let i = 0; i < size * size; i++) {
      data[i * 4 + 0] = 128; // R (X normal)
      data[i * 4 + 1] = 128; // G (Y normal)
      data[i * 4 + 2] = 255; // B (Z normal - pointing out)
      data[i * 4 + 3] = 255; // A
    }
    const texture = new THREE.DataTexture(data, size, size, THREE.RGBAFormat);
    texture.wrapS = THREE.RepeatWrapping;
    texture.wrapT = THREE.RepeatWrapping;
    texture.needsUpdate = true;
    texture.name = "default_texture";
    defaultTextureRef.current = texture;
    return texture;
  }, []);

  // Load a specific texture based on its info object
  const loadSpecificTexture = useCallback(async (textureInfo) => {
    if (!textureInfo || !textureInfo.filename) {
      console.warn("[TextureLoader] Invalid textureInfo passed to loadSpecificTexture");
      const defaultTex = createDefaultTexture();
      return { displacementMap: defaultTex, normalMap: defaultTex, textureInfo: { filename: 'default', isFallback: true } };
    }
    
    // Use filename as cache key
    const cacheKey = textureInfo.filename;
    if (textureCache.current[cacheKey]) {
      return textureCache.current[cacheKey];
    }
    
    try {
      let textureUrlPath = null;
      const sourceDir = textureInfo.source;
      const textureFilename = textureInfo.filename;

      // Determine the texture path based on source directory using config paths
      if (sourceDir === 'normal_grey') {
        // Normal grey folder path - use config
        textureUrlPath = `${TEXTURE_PATHS.normalGrey}/${textureFilename}`;
        console.log(`[TextureLoader] Using normal_grey texture: ${textureFilename}`);
      } 
      else if (sourceDir === 'gray_textures') {
        // Extract the texture type (pattern category)
        const parts = textureFilename.split('_');
        const typeMatch = parts[0].match(/^([a-z\-]+)/);
        
        if (typeMatch) {
          const category = typeMatch[1];
          textureUrlPath = `${TEXTURE_PATHS.grayTextures}/${category}/${textureFilename}`;
          console.log(`[TextureLoader] Using DTD gray_texture: ${category}/${textureFilename}`);
        } else {
          // Try to extract category from path if available
          if (textureInfo.path && textureInfo.path.includes('/')) {
            const pathParts = textureInfo.path.split('/');
            const category = pathParts[pathParts.length - 2];
            textureUrlPath = `${TEXTURE_PATHS.grayTextures}/${category}/${textureFilename}`;
            console.log(`[TextureLoader] Using DTD gray_texture with extracted category: ${category}/${textureFilename}`);
          } else {
            console.warn(`[TextureLoader] Could not determine category for gray_texture: ${textureFilename}`);
            // Use a default category
            textureUrlPath = `${TEXTURE_PATHS.grayTextures}/lined/${textureFilename}`;
          }
        }
      } else if (textureInfo.isFallback) {
        console.log("[TextureLoader] Using generated texture for fallback info:", textureInfo.filename);
        const defaultTexture = createDefaultTexture();
        const textureSet = { 
          displacementMap: defaultTexture, 
          normalMap: defaultTexture, 
          textureInfo: textureInfo 
        };
        textureCache.current[cacheKey] = textureSet;
        return textureSet;
      } else {
        console.warn(`[TextureLoader] Unknown source directory: ${sourceDir} for ${textureFilename}. Using placeholder/default.`);
        // Use placeholder from config
        textureUrlPath = IMAGE_PATHS.placeholder;
      }

      console.log(`[TextureLoader] Loading texture from URL: ${textureUrlPath}`);
      const loader = new THREE.TextureLoader();
      
      // Load textures with more robust error handling and options
      const [displacementMap, normalMap] = await Promise.all([
        new Promise((resolve) => {
          loader.load(
            textureUrlPath, 
            (texture) => {
              texture.wrapS = THREE.RepeatWrapping;
              texture.wrapT = THREE.RepeatWrapping;
              texture.name = textureInfo.filename || 'unknown';
              resolve(texture);
            },
            undefined, // onProgress callback
            (error) => {
              console.warn(`[TextureLoader] Failed to load displacement map: ${error.message}`);
              resolve(createDefaultTexture());
            }
          );
        }),
        new Promise((resolve) => {
          loader.load(
            textureUrlPath, 
            (texture) => {
              texture.wrapS = THREE.RepeatWrapping;
              texture.wrapT = THREE.RepeatWrapping;
              texture.name = textureInfo.filename || 'unknown';
              resolve(texture);
            },
            undefined, // onProgress callback
            (error) => {
              console.warn(`[TextureLoader] Failed to load normal map: ${error.message}`);
              resolve(createDefaultTexture());
            }
          );
        })
      ]);

      const textureSet = { 
        displacementMap, 
        normalMap, 
        textureInfo
      };
      
      // Update cache
      textureCache.current[cacheKey] = textureSet;
      
      return textureSet;

    } catch (error) {
      console.error(`[TextureLoader] Error in loadSpecificTexture for ${textureInfo.filename}:`, error);
      const defaultTex = createDefaultTexture();
      const textureSet = { 
        displacementMap: defaultTex, 
        normalMap: defaultTex, 
        textureInfo: { ...textureInfo, isFallback: true }
      };
      textureCache.current[cacheKey] = textureSet;
      return textureSet;
    }
  }, [createDefaultTexture]);

  // Load initial data (Top 2 emotions and all textures)
  useEffect(() => {
    // Requires paths for BOTH top2 summary AND the full classification
    if (!top2CsvPath || !textureClassificationCsvPath) { 
      console.warn("[TextureLoader] Missing required CSV paths for texture loading.");
      return;
    }

    let isActive = true;
    setLoadingState('loading');

    async function loadInitialData() {
      try {
        console.log("[TextureLoader] Loading initial Top 2 emotion and Texture data...");
        // Fetch both CSVs concurrently
        const [top2CsvText, loadedTextureDataResult] = await Promise.all([
          fetchCsv(top2CsvPath),
          loadAllTextureData(textureClassificationCsvPath)
        ]);

        if (!isActive) return;

        // Set the texture data state
        setAllTextureData(loadedTextureDataResult);

        // Get top 2 emotions from CSV
        const top2Emotions = getTop2EmotionsFromCSV(top2CsvText);
        if (!top2Emotions || top2Emotions.length < 2) {
          console.error("[TextureLoader] Could not determine top 2 emotions.");
          setLoadingState('error');
          // Set default textures
          const defaultTex = createDefaultTexture();
          setTextureMaps({ 
            texture1: { displacementMap: defaultTex, normalMap: defaultTex, textureInfo: { filename: 'default1', isFallback: true } },
            texture2: { displacementMap: defaultTex, normalMap: defaultTex, textureInfo: { filename: 'default2', isFallback: true } }
          });
          return;
        }

        const [emotion1Info, emotion2Info] = top2Emotions;
        console.log(`[TextureLoader] Top 2 emotions for texture: ${emotion1Info.emotion} (VA: ${emotion1Info.valence.toFixed(2)}, ${emotion1Info.arousal.toFixed(2)}), ${emotion2Info.emotion} (VA: ${emotion2Info.valence.toFixed(2)}, ${emotion2Info.arousal.toFixed(2)})`);

        // Find textures with closest emotion matches and VA values
        // Use the new function that prioritizes DTD textures
        const closestTexture1 = findBestTextureForEmotion(
          emotion1Info.emotion,
          emotion1Info.valence, 
          emotion1Info.arousal, 
          loadedTextureDataResult
        );
        
        const closestTexture2 = findBestTextureForEmotion(
          emotion2Info.emotion,
          emotion2Info.valence, 
          emotion2Info.arousal, 
          loadedTextureDataResult
        );

        if (!closestTexture1 || !closestTexture2) {
          console.warn("[TextureLoader] Could not find suitable textures for top 2 emotions, using defaults.");
          const defaultTex = createDefaultTexture();
          setTextureMaps({ 
            texture1: { displacementMap: defaultTex, normalMap: defaultTex, textureInfo: { filename: 'default1', isFallback: true } },
            texture2: { displacementMap: defaultTex, normalMap: defaultTex, textureInfo: { filename: 'default2', isFallback: true } }
          });
          setLoadingState('loaded');
          return;
        }
        
        console.log(`[TextureLoader] Loading top texture: ${closestTexture1.filename} for ${emotion1Info.emotion}`);
        console.log(`[TextureLoader] Loading bottom texture: ${closestTexture2.filename} for ${emotion2Info.emotion}`);
        
        // Load both textures concurrently
        const [textureSet1, textureSet2] = await Promise.all([
          loadSpecificTexture(closestTexture1),
          loadSpecificTexture(closestTexture2)
        ]);

        if (isActive) {
          if (textureSet1 && textureSet2) {
            setTextureMaps({ 
              texture1: textureSet1, 
              texture2: textureSet2 
            });
            setLoadingState('loaded');
          } else {
            setLoadingState('error');
          }
        }
      } catch (error) {
        console.error("[TextureLoader] Error loading initial data:", error);
        if (isActive) {
          setLoadingState('error');
          // Set default textures on error
          const defaultTex = createDefaultTexture();
          setTextureMaps({ 
            texture1: { displacementMap: defaultTex, normalMap: defaultTex, textureInfo: { filename: 'default1', isFallback: true } },
            texture2: { displacementMap: defaultTex, normalMap: defaultTex, textureInfo: { filename: 'default2', isFallback: true } }
          });
        }
      }
    }

    loadInitialData();

    return () => { isActive = false; };
  }, [top2CsvPath, textureClassificationCsvPath, loadSpecificTexture, createDefaultTexture]);

  // Function to parse top 2 emotions from CSV text
  const getTop2EmotionsFromCSV = (csvText) => {
    if (!csvText) return null;
    const parsed = Papa.parse(csvText, { header: true, dynamicTyping: true, skipEmptyLines: true });
    const rows = parsed.data.filter(r => r.emotion);
    if (rows.length < 2) return null;
    
    // Return valence/arousal needed for finding closest texture
    return [
      { 
        emotion: rows[0].emotion, 
        valence: parseFloat(rows[0].valence || 0), 
        arousal: parseFloat(rows[0].arousal || 0) 
      },
      { 
        emotion: rows[1].emotion, 
        valence: parseFloat(rows[1].valence || 0), 
        arousal: parseFloat(rows[1].arousal || 0) 
      }
    ];
  };

  return {
    textureMaps,
    loadingState
  };
} 